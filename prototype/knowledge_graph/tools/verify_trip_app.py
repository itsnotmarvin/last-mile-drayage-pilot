"""Verify a running synthetic application via HTTP + stdio, using live Neo4j.

No language model is invoked. Output excludes session cookies and access keys.
Uses only private synthetic users already provisioned in the supplied directory.
"""
import argparse
from datetime import datetime, timezone
from http.cookiejar import CookieJar
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import uuid
from urllib.error import HTTPError
from urllib.request import build_opener, HTTPCookieProcessor, Request, ProxyHandler

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from trip_app.operations import private_write


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origin',default='http://127.0.0.1:8765')
    parser.add_argument('--private-directory',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    from trip_app.mcp_server import Client
    Client(args.origin,'validation-only')  # Validate explicit loopback URL.
    args.output.mkdir(mode=0o700,parents=True,exist_ok=False)
    clients,csrf={},{}
    transcript=[]
    run_key=uuid.uuid4().hex
    def save(name,value):
        private_write(args.output/name,json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    def call(user,path,body=None,expected=200,record=True):
        req=Request(args.origin+path,data=json.dumps(body).encode() if body is not None else None,
                    headers={'Origin':args.origin,'Content-Type':'application/json','X-CSRF-Token':csrf.get(user,'')})
        try:
            with clients[user].open(req,timeout=55) as response:
                status,payload=response.status,json.load(response)
        except HTTPError as response:
            status,payload=response.code,json.load(response)
        assert status==expected,(path,status,expected)
        if record:
            transcript.append({'user':user,'path':path,'body':body,'status':status,'response':payload})
        return payload
    for user in ('driver','dispatch','outsider'):
        clients[user]=build_opener(ProxyHandler({}),HTTPCookieProcessor(CookieJar()))
        response=call(user,'/api/login',{'key':(args.private_directory/(user+'.key')).read_text().strip()},record=False)
        csrf[user]=response['csrf']
    statement='Can I take this truck to APM Elizabeth? Gross weight 80,000 lb. It is 14 ft 7 in high. Permit status is unknown. Trip time is unknown.'
    facts={'terminal_id':'facility_apm_elizabeth','gross_weight':{'value':80000,'unit':'lb'},'height':{'value':175,'unit':'in'},'permit_type':None,'trip_at':None}
    assessments=[]
    for user in ('driver','dispatch'):
        cid=call(user,'/api/conversations',{})['id']
        path='/api/conversations/'+cid
        view=call(user,path+'/message',{'version':0,'statement':statement,'request_key':run_key+'-paired'})
        assert view['assessment'] is None and view['proposals'][0]['facts']['height']['value']==175
        proposal=view['proposals'][0]['id']
        view=call(user,path+'/confirm',{'version':1,'proposal_id':proposal,'facts':facts,'scope':'trip_dispatch'})
        a=view['assessment'];assert a['service_status']=='available'
        assert a['case']['facts']['height']['value']==175 and a['decision_brief']['operational_permission']=='not_issued'
        assert a['evidence_package']['sources'] and a['evidence_package']['requirement_links']
        assessments.append(a)
        if user=='driver':
            driver_id,driver_path=cid,path
    assert assessments[0]['findings']==assessments[1]['findings']
    assert assessments[0]['case']['trip_id']!=assessments[1]['case']['trip_id']
    call('outsider',driver_path,expected=403)
    call('dispatch',driver_path,expected=403)
    call('driver',driver_path+'/share',{'user_id':'syn-user-dispatch','permission':'edit'})
    shared=call('dispatch',driver_path);assert shared['can_edit']
    view=call('driver',driver_path+'/message',{'version':2,'statement':'Correction: height is 14 ft 8 in.','request_key':run_key+'-correction'})
    assert view['assessment'] is None and view['case'] is None
    cap=call('driver',driver_path+'/capability',{},record=False)['capability']
    capfile=args.private_directory/('bridge-'+run_key+'.key');private_write(capfile,cap)
    requests=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'local-integration-verifier','version':'1'}}},
              {'jsonrpc':'2.0','method':'notifications/initialized'},
              {'jsonrpc':'2.0','id':2,'method':'tools/list'},
              {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'get_statement','arguments':{}}},
              {'jsonrpc':'2.0','id':4,'method':'tools/call','params':{'name':'propose_facts','arguments':{'message_id':view['messages'][-1]['id'],'version':3,'facts':{'height':{'value':176,'unit':'in'}}}}},
              {'jsonrpc':'2.0','id':5,'method':'tools/call','params':{'name':'confirm','arguments':{}}}]
    proc=subprocess.run([sys.executable,'-m','trip_app.mcp_server','--origin',args.origin,'--capability-file',str(capfile)],cwd=ROOT,
                        input=''.join(json.dumps(r)+'\n' for r in requests),text=True,capture_output=True,timeout=55)
    assert proc.returncode==0
    responses=[json.loads(line) for line in proc.stdout.splitlines()]
    assert len(responses)==5 and responses[3]['result']['isError'] is False and 'error' in responses[4]
    assert cap not in proc.stdout+proc.stderr
    save('restricted-mcp-transcript.json',{'requests':requests,'responses':responses,'surface':'local_stdio_http_integration_no_model'})
    proposal=responses[3]['result']['structuredContent']['proposal_id']
    view=call('dispatch',driver_path+'/confirm',{'version':3,'proposal_id':proposal,'facts':{'height':{'value':176,'unit':'in'}},'scope':'trip_dispatch'})
    assert view['assessment']['case']['facts']['height']['value']==176
    assert view['confirmation']['confirmed_by']=='syn-user-dispatch'
    call('driver',driver_path+'/share',{'user_id':'syn-user-dispatch','permission':'remove'})
    call('dispatch',driver_path,expected=403)
    call('driver',driver_path+'/revoke-capabilities',{})
    try:
        Client(args.origin,cap).call('get_statement',{})
        raise AssertionError('Revoked capability worked')
    except HTTPError as exc:
        assert exc.code==403
    save('http-transcript.json',transcript)
    save('summary.json',{'at':datetime.now(timezone.utc).isoformat(),'surface':'local_http_and_stdio_no_language_model',
                        'http_requests_recorded':len(transcript),'live_neo4j_assessments':sum(bool(x['response'].get('assessment')) for x in transcript if isinstance(x['response'],dict)),
                        'driver_dispatch_findings_equal':True,'mixed_feet_inches_preserved':True,'correction_inches':176,
                        'isolation_sharing_revocation':'passed','model_self_confirmation':'rejected','operational_permission':'not_issued',
                        'driver_conversation':driver_id,'runtime_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for root in ('neo4j_kg','trip_app') for p in sorted((ROOT/root).rglob('*')) if p.suffix in ('.py','.js','.html','.css')}})
    print('Live local HTTP, Neo4j, and restricted stdio verification passed. No model invoked.')


if __name__=='__main__':main()
