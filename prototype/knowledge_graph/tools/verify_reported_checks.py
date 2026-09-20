"""Live Neo4j/stdio verification of reported-fact checks; no model invocation."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from neo4j_kg.common import digest
from neo4j_kg.decision_brief import render_trip_report
from neo4j_kg.reported_checks import catalog

CASES=[
 ('mixed_height',{'height':{'value':175,'unit':'in'}},{'nj_loaded_height':'attention_required','terminal_height_195':'comparison_only'}),
 ('height_boundary',{'height':{'value':162,'unit':'in'}},{'nj_loaded_height':'comparison_only'}),
 ('wide_ocean_container',{'width':{'value':144,'unit':'in'},'permit_type':'nj_ocean_container_annual','gross_weight':{'value':90001,'unit':'lb'},'container_sealed':True},
  {'nj_width_102':'attention_required','terminal_width_132':'attention_required','ocean_permit_gross_90000':'attention_required','ocean_container_seal':'reported_unverified'}),
 ('gross_and_axle_groups',{'gross_weight':{'value':80000,'unit':'lb'},'axle_count':5,'axle_weights':[{'value':12000,'unit':'lb'},{'value':34000,'unit':'lb'},{'value':34000,'unit':'lb'}]},
  {'federal_gross_80000':'comparison_only','axle_and_bridge_gap':'manual_review_required'}),
 ('gross_above_baseline',{'gross_weight':{'value':80001,'unit':'lb'}},{'federal_gross_80000':'attention_required','terminal_container_gross_128000':'comparison_only'}),
 ('single_trip_divisible',{'permit_type':'nj_single_trip','load_divisible':True},{'single_trip_nondivisible':'attention_required'}),
 ('old_engine_active_report',{'engine_model_year':2007,'dtr_reported':True},{'dtr_interpretation_gap':'manual_review_required','dtr_report':'reported_unverified'}),
 ('missing_appointment',{'appointment_reported':False},{'appointment_report':'attention_required'}),
 ('no_rfid',{'rfid_reported':False},{'rfid_report':'attention_required'}),
 ('all_unknown',{}, {'nj_loaded_height':'missing_facts','twic_report':'missing_facts'}),
]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--credentials-file',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();out=args.output
    out.mkdir(mode=0o700,parents=True,exist_ok=False)
    def save(name,value):
        (out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    release=json.loads((ROOT/'data/neo4j_release.json').read_text())
    env=os.environ|{'NEO4J_CREDENTIALS_FILE':str(args.credentials_file.resolve()),'DRAYAGE_NEO4J_REVISION':release['revision']}
    entry='''import sys
from pathlib import Path
from neo4j_kg.service import CheckingService
from neo4j_kg.assessment import TripService
from neo4j_kg.trip_state import TripStore
from neo4j_kg.mcp_server import Session,serve
service=CheckingService()
try:serve(sys.stdin.buffer,sys.stdout,Session(service,trip_service=TripService(service.store,TripStore(Path(sys.argv[1])))))
finally:service.close()
'''
    runtime=[*sorted((ROOT/'neo4j_kg').glob('*.py')),*sorted((ROOT/'trip_app').rglob('*.py')),
             *sorted((ROOT/'trip_app/static').glob('*')),ROOT/'data/reported_checks.json',Path(__file__).resolve()]
    runtime_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in runtime if p.is_file()}
    transcript=[];results=[]
    with tempfile.TemporaryDirectory(dir=ROOT/'.runtime',prefix='reported-checks-') as temp, (out/'stderr.txt').open('w') as err:
        process=subprocess.Popen([sys.executable,'-c',entry,str(Path(temp)/'trips.sqlite3')],cwd=ROOT,env=env,
                                 stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,text=True,bufsize=1)
        selector=selectors.DefaultSelector();selector.register(process.stdout,selectors.EVENT_READ)
        def request(method,params,notification=False):
            payload={'jsonrpc':'2.0','method':method,'params':params}
            if not notification:payload['id']=len(transcript)+1
            process.stdin.write(json.dumps(payload)+'\n');process.stdin.flush()
            if notification:return
            if not selector.select(50):raise RuntimeError('MCP response timeout')
            response=json.loads(process.stdout.readline());transcript.append({'request':payload,'response':response})
            assert response.get('id')==payload['id'] and 'error' not in response
            return response['result']
        try:
            request('initialize',{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'reported-check-verifier','version':'1'}})
            request('notifications/initialized',{},True)
            save('tools.json',request('tools/list',{}))
            for name,facts,expected in CASES:
                variants=[]
                for role in ('driver','dispatcher'):
                    response=request('tools/call',{'name':'assess_trip','arguments':{
                        'facts':{'terminal_id':'facility_apm_elizabeth',**facts},'question_scope':'trip_dispatch','requester_role':role,
                        'source_message':'Synthetic source-bound comparison control.','request_key':name+'-'+role}})
                    assert not response['isError']
                    body=response['structuredContent'];assert json.loads(response['content'][-1]['text'])==body
                    assert body['service_status']=='available'
                    package=body['reported_fact_checks'];assert package['status']=='available'
                    checks={c['check_id']:c for c in package['checks']}
                    for check_id,status in expected.items():assert checks[check_id]['status']==status,(name,check_id)
                    for c in checks.values():
                        for cid,sha in c['source_text_sha256'].items():
                            source=next(s for s in body['evidence_package']['sources'] if s['clause_id']==cid)
                            assert digest(source['source_text'])==sha
                    assert body['requested_scope_status']=='unresolved'
                    assert body['decision_brief']['operational_permission']=='not_issued'
                    assert body['coverage']['executed_requirements']==['apm_induction']
                    if name=='mixed_height':
                        assert checks['nj_loaded_height']['comparison']['difference']==13
                        if role=='driver':(out/'mixed-height-report.html').write_text(render_trip_report(body))
                    if name=='missing_appointment':assert 'appointment' in body['decision_brief']['next_steps'][0]
                    variants.append(package)
                    results.append({'case':name,'role':role,'expected':expected,'actual':{cid:checks[cid]['status'] for cid in expected},'assessment_id':body['assessment_id']})
                assert variants[0]==variants[1],name
        finally:
            process.stdin.close()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait()
            process.stdout.close();selector.close()
    assert process.returncode==0
    save('mcp-transcript.json',transcript)
    save('cases.json',CASES)
    save('comparison-results.json',results)
    save('reported-check-catalog.json',catalog())
    assert all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==sha for path,sha in runtime_hashes.items()), 'Source changed during capture'
    save('summary.json',{'at':datetime.now(timezone.utc).isoformat(),'surface':'local_stdio_mcp_live_neo4j_no_model',
                        'scenarios':len(CASES),'assessments':len(results),'matching_role_pairs':len(CASES),
                        'checks_defined':len(catalog()['checks']),'referenced_clauses':len(catalog()['source_bindings']),
                        'operational_permission':'not_issued','legal_evaluators_beyond_induction':'not_activated',
                        'runtime_sha256':runtime_hashes})
    print('Verified 20 live Neo4j/MCP assessments across 10 driver/dispatcher pairs; no model invoked.')


if __name__=='__main__':main()
