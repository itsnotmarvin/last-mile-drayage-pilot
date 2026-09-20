"""Live Neo4j / local HTTP / stdio bridge capture; no model or browser is invoked."""
import argparse, json, os, sys, threading, subprocess, hashlib
from pathlib import Path
from urllib.request import Request, build_opener, ProxyHandler
from wsgiref.simple_server import make_server
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from neo4j_kg.config import connect
from neo4j_kg.store import Neo4jStore
from trip_app.store import Workspace
from trip_app.service import Application
from trip_app.web import Web
from trip_app.operations import private_write, inspect_database
from trip_app.__main__ import QuietHandler


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--credentials-file',required=True,type=Path)
    parser.add_argument('--private-directory',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    args.private_directory.mkdir(mode=0o700,parents=False,exist_ok=False)
    args.output.mkdir(parents=False,exist_ok=False)
    out=args.output
    def save(name,value): (out/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
    files=[p for folder in ('neo4j_kg','trip_app') for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    save('runtime-before.json',hashes)
    driver,database=connect(args.credentials_file)
    release='f5dffe0f7a32b5144920efb5a644f8c4dc9f20def76b4217c38b0cdbc454cf5c'
    ws=Workspace(args.private_directory/'app.sqlite3')
    web=Web(Application(ws,Neo4jStore(driver,database,release)))
    http=make_server('127.0.0.1',0,web,handler_class=QuietHandler)
    web.host=f'127.0.0.1:{http.server_port}';web.origin='http://'+web.host
    thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
    opener=build_opener(ProxyHandler({}));http_events=[];results=[]
    def call(path,body,token,csrf):
        headers={'Content-Type':'application/json','Origin':web.origin,'Cookie':'trip_session='+token,'X-CSRF-Token':csrf}
        req=Request(web.origin+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
        with opener.open(req,timeout=60) as r: value=json.load(r)
        # No authorization headers, session tokens, or capability responses saved.
        if not path.endswith('capability'):http_events.append({'path':path,'request':body,'response':value})
        return value
    def bridge(role,stage,key,calls):
        reqs=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'non-model-capture','version':'1'}}}, {'jsonrpc':'2.0','method':'notifications/initialized'}]
        reqs += [{'jsonrpc':'2.0','id':i+2,'method':'tools/call','params':{'name':name,'arguments':arg}} for i,(name,arg) in enumerate(calls)]
        audit=out/f'{role}-{stage}.audit.jsonl'
        proc=subprocess.run([sys.executable,'-m','trip_app.mcp_server','--origin',web.origin,'--capability-file',str(key),'--audit-file',str(audit)],input=''.join(json.dumps(r)+'\n' for r in reqs),capture_output=True,text=True,timeout=90,cwd=ROOT)
        assert proc.returncode==0,'Bridge process failed'
        responses=[json.loads(l) for l in proc.stdout.splitlines()]
        save(f'{role}-{stage}.json',{'requests':reqs,'responses':responses})
        return [r['result'] for r in responses[1:]]
    try:
        plan=json.loads((ROOT/'provider_runs/claude-desktop-exploratory-20260916-r2/plan.json').read_text())
        for c in plan['cases']:
            role=c['role'];key=ws.provision('syn-user-advice-'+role,'syn-org-advice',role);token,csrf=ws.login(key)
            cid=call('/api/conversations',{},token,csrf)['id'];base='/api/conversations/'+cid
            v=call(base+'/message',{'version':0,'statement':c['prompt'],'request_key':role+'-initial'},token,csrf)
            mid=v['messages'][-1]['id']
            cap=call(base+'/assessment-capability',{},token,csrf)['capability'];kp=args.private_directory/(role+'.key');private_write(kp,cap)
            facts={'terminal_id':'facility_apm_elizabeth','height':{'value':175,'unit':'in'},'width':{'value':102,'unit':'in'},'gross_weight':{'value':80000,'unit':'lb'},'trip_at':'2026-09-17T09:00:00-04:00','twic_reported':True,'sealink_registered_reported':True,'appointment_reported':True}
            b=bridge(role,'propose',kp,[('get_statement',{}),('get_confirmed_assessment',{'message_id':mid,'version':1}),('propose_facts',{'message_id':mid,'version':1,'facts':facts})])
            assert b[1]['isError'] and not b[2]['isError']
            v=call(base+'/confirm',{'proposal_id':b[2]['structuredContent']['proposal_id'],'version':1,'facts':facts,'scope':'trip_dispatch'},token,csrf)
            first=bridge(role,'confirmed',kp,[('get_statement',{}),('get_confirmed_assessment',{'message_id':mid,'version':2})])[-1]['structuredContent']
            assert first['original_statements'][0]['body']==c['prompt']
            assert first['explanation']['service_status']=='available'
            v=call(base+'/message',{'version':2,'statement':c['followup'],'request_key':role+'-correction'},token,csrf)
            stale=bridge(role,'pending',kp,[('get_confirmed_assessment',{'message_id':mid,'version':2})])[-1]
            assert stale['isError']
            mid=v['messages'][-1]['id'];pid=v['proposals'][0]['id']
            call(base+'/confirm',{'proposal_id':pid,'version':3,'facts':{'height':{'value':162,'unit':'in'}},'scope':'trip_dispatch'},token,csrf)
            last=bridge(role,'corrected',kp,[('get_statement',{}),('get_confirmed_assessment',{'message_id':mid,'version':4})])[-1]['structuredContent']
            assert first['binding']['trip_id']==last['binding']['trip_id'] and last['binding']['trip_revision']==2
            assert last['reported_facts']['height']['value']==162
            assert last['explanation']['decision_brief']['operational_permission']=='not_issued'
            assert last['explanation']['answer_guidance']['historical_context'][0]['current_status']=='unknown_for_this_trip'
            assert last['original_statements'][-1]['body']==c['followup']
            results.append({'role':role,'first_assessment':first['binding'],'corrected_assessment':last['binding'],'pending_read_rejected':True,'original_messages_preserved':True,'scope_status':last['explanation']['decision_brief']['scoped_result']})
        save('http-events.json',http_events)
        assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in hashes.items())
        save('summary.json',{'surface':'non-model live Neo4j + HTTP + stdio integration','graph_release':release,'results':results,'runtime_unchanged':True,'database_integrity':inspect_database(ws.trips.path) if hasattr(ws.trips,'path') else 'checked separately','python':sys.executable,'networkx_present':__import__('importlib.util').util.find_spec('networkx') is not None,'limits':['No browser or Claude advice collected by this harness.','Confirmation actions are scripted synthetic user actions, not human domain approval.']})
        print('Live bridge capture complete; two roles, four confirmed reads, pending reads rejected.')
    finally:
        http.shutdown();http.server_close();thread.join(3);driver.close()

if __name__=='__main__':main()
