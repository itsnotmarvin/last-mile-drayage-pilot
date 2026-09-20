"""Live Neo4j + real stdio MCP audit; no model/provider inference is simulated."""
import argparse
from collections import Counter
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
from neo4j_kg.common import digest, verify_files


def write(path,data):
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')


def coverage(expected,returned):
    expected=set(expected); returned=set(returned)
    return {'expected':sorted(expected),'returned':sorted(returned),'missing':sorted(expected-returned),
            'required_evidence_recall':len(expected & returned)/len(expected) if expected else None,
            'extra_clause_ids_not_automatically_errors':sorted(returned-expected)}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,default=ROOT/'audits/evidence-2026-09-10')
    ap.add_argument('--credentials-file',type=Path,required=True)
    args=ap.parse_args(); out=args.output.resolve()
    if (out/'direct-results.json').exists():raise SystemExit('Refusing to overwrite a completed run.')
    book=json.loads((out/'casebook.json').read_text())
    assert hashlib.sha256((out/'casebook.json').read_bytes()).hexdigest()==(out/'casebook.sha256').read_text().strip()
    release=json.loads((ROOT/'data/neo4j_release.json').read_text()); verify_files(release)
    records={n['id']:json.loads(n['record_json']) for n in release['nodes']}
    runtime={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'neo4j_kg').glob('*.py'))}
    write(out/'runtime-files.json',runtime)
    env=os.environ|{'NEO4J_CREDENTIALS_FILE':str(args.credentials_file.resolve()),'DRAYAGE_NEO4J_REVISION':release['revision']}
    transcript=[]; results=[]; evidence={}; direct_prompts={p['id']:p for p in book['prompts'] if p['repeat']==1}
    cases={c['id']:c for c in book['cases']}
    entry='''import sys
from pathlib import Path
from neo4j_kg.service import CheckingService
from neo4j_kg.assessment import TripService
from neo4j_kg.trip_state import TripStore
from neo4j_kg.mcp_server import Session,serve
s=CheckingService()
try: serve(sys.stdin.buffer,sys.stdout,Session(service=s,trip_service=TripService(s.store,TripStore(Path(sys.argv[1]))),audit_path=Path(sys.argv[2])))
finally:s.store.close()
'''
    with tempfile.TemporaryDirectory(prefix='evidence-audit-') as tmp:
        log=out/'direct-mcp-audit.jsonl'; log.touch(mode=0o600,exist_ok=False)
        err=(out/'direct-stderr.txt').open('w')
        process=subprocess.Popen([sys.executable,'-c',entry,str(Path(tmp)/'trips.sqlite3'),str(log)],cwd=ROOT,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,text=True,bufsize=1)
        selector=selectors.DefaultSelector();selector.register(process.stdout,selectors.EVENT_READ)
        def request(method,params,notify=False):
            message={'jsonrpc':'2.0','method':method,'params':params}
            if not notify:message['id']=len(transcript)+1
            process.stdin.write(json.dumps(message)+'\n');process.stdin.flush()
            row={'request':message,'response':None};transcript.append(row)
            if notify:return
            if not selector.select(50):raise RuntimeError('MCP response timeout')
            line=process.stdout.readline()
            if not line:raise RuntimeError('MCP process exited')
            response=json.loads(line);row['response']=response
            if response.get('id')!=message['id'] or 'error' in response:raise RuntimeError('MCP protocol failure')
            return response['result']
        def call(name,arguments,allow_error=False):
            result=request('tools/call',{'name':name,'arguments':arguments})
            if result.get('isError'):
                if allow_error:return result
                raise RuntimeError('MCP tool failure: '+name)
            body=result['structuredContent']
            assert body==json.loads(result['content'][0]['text'])
            assert body['versions']['graph_release']==release['revision']
            return body
        def assess(facts,key,role='driver',scope='trip_dispatch',source='Synthetic audit control'):
            return call('assess_trip',{'facts':facts,'requester_role':role,'question_scope':scope,'source_message':source,'request_key':key})
        controls=[]
        try:
            request('initialize',{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'evidence-delivery-audit','version':'1'}})
            request('notifications/initialized',{},True)
            write(out/'tools.json',request('tools/list',{}))
            for p in direct_prompts.values():
                case=cases[p['case_id']]
                result=assess(case['expected_facts'],p['id'],p['role'],case['expected_scope'],p['prompt'])
                normalized={k:{'value':v['value'],'unit':v['unit']} for k,v in result['case']['facts'].items()}
                results.append({'id':p['id'],'case_id':case['id'],'role':p['role'],'pressure':p['pressure'],
                                'assessment_request_id':transcript[-1]['request']['id'],'normalized_facts':normalized,
                                'selected_requirements':result['coverage']['selected_requirements'],
                                'findings':result['findings'],'next_questions':result['next_questions'],
                                'status':result['requested_scope_status'],'service_status':result['service_status'],
                                'operational_status':result['operational_status'],'versions':result['versions']})
                print(p['id'],result['requested_scope_status'],flush=True)
            for rid in results[0]['selected_requirements']:
                result=call('get_requirement_evidence',{'requirement_id':rid})
                problems=[]
                for source in result['sources']:
                    clause=records[source['clause_id']]; original=records[clause['source_id']]
                    for field,expected in [('source_text',clause['source_text']),('locator',clause['source_locator']),('source_id',clause['source_id']),('publisher',original['publisher']),('url',original['url']),('publication_date',original.get('publication_date')),('accessed_date',original.get('accessed_date')),('archived_files',original.get('archived_files',[]))]:
                        if source.get(field)!=expected:problems.append({'clause_id':source['clause_id'],'field':field})
                    if source['currentness']!='archived_evidence_only_not_verified_for_this_trip':problems.append({'clause_id':source['clause_id'],'field':'currentness'})
                evidence[rid]={'request_id':transcript[-1]['request']['id'],'payload':result,'field_mismatches':problems}
            for topic in ('port_street','route_directions','coverage'):
                call('get_drayage_graph_context',{'topic':topic})
            base={'terminal_id':'facility_apm_elizabeth','subject_role':'truck_driver','driver_id':'syn-driver-complete','current_sealink_id':'SYN-SL-A','trip_at':'2026-09-06T14:00:00-04:00'}
            for name,changes,expected in [('positive',{},'met'),('negative',{'driver_id':'syn-driver-incomplete','current_sealink_id':'SYN-SL-B'},'not_met'),('missing',{'driver_id':'syn-driver-missing'},'unresolved'),('changed_identifier',{'current_sealink_id':'SYN-SL-NEW'},'unresolved'),('other_subject',{'subject_role':'other'},'not_applicable')]:
                r=assess(base|changes,'control-'+name,scope='induction')
                controls.append({'id':name,'expected':expected,'actual':r['requested_scope_status'],'passed':r['requested_scope_status']==expected,'request_id':transcript[-1]['request']['id']})
            initial=assess(base|{'height':{'value':14,'unit':'ft'}},'correction-initial')
            changed=call('update_trip_facts',{'trip_id':initial['case']['trip_id'],'expected_revision':1,'requester_role':'dispatcher','question_scope':'trip_dispatch','source_message':'Explicit synthetic correction: loaded height is 14 feet 7 inches, not 14 feet.','facts':{'height':{'value':175,'unit':'in'}},'replace_conflicts':True,'request_key':'height-correction'})
            controls.append({'id':'height_correction','passed':changed['case']['facts']['height']['value']==175 and changed['case']['revision']==2,'request_id':transcript[-1]['request']['id']})
            reassigned=call('update_trip_facts',{'trip_id':changed['case']['trip_id'],'expected_revision':2,'requester_role':'dispatcher','question_scope':'trip_dispatch','source_message':'Explicit synthetic reassignment: the driver is now syn-driver-missing.','facts':{'driver_id':'syn-driver-missing'},'replace_conflicts':True,'request_key':'driver-swap'})
            controls.append({'id':'driver_swap_invalidates_sealink','passed':reassigned['case']['facts'].get('current_sealink_id',{}).get('value') is None,'request_id':transcript[-1]['request']['id']})
            bad=call('get_requirement_evidence',{'requirement_id':'unknown-requirement'},True)
            controls.append({'id':'unknown_requirement_rejected','passed':bad.get('isError') is True,'request_id':transcript[-1]['request']['id']})
        finally:
            process.stdin.close()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=5)
            selector.close();err.close()
            write(out/'direct-stdio-transcript.json',transcript)
            write(out/'direct-partial-results.json',results)
    source_coverage=[]
    all_returned={s['clause_id'] for r in evidence.values() for s in r['payload']['sources']}
    for c in book['cases']:
        focus_returned={s['clause_id'] for rid in c['focus_requirements'] for s in evidence[rid]['payload']['sources']}
        group=[r for r in results if r['case_id']==c['id']]
        invariant=all((r['findings'],r['normalized_facts'],r['selected_requirements'])==(group[0]['findings'],group[0]['normalized_facts'],group[0]['selected_requirements']) for r in group)
        source_coverage.append({'case_id':c['id'],'focus_requirements':c['focus_requirements'],'focus_coverage':coverage(c['audit_expected_clause_ids'],focus_returned),
                                'all_catalog_coverage':coverage(c['audit_expected_clause_ids'],all_returned),
                                'four_condition_invariance':invariant,'all_unresolved':all(r['status']=='unresolved' and r['service_status']=='available' for r in group)})
    audits=[json.loads(line) for line in log.read_text().splitlines()]
    previous=None
    for event in audits:
        expected_hash=digest({k:v for k,v in event.items() if k!='event_hash'})
        assert expected_hash==event['event_hash'] and event['previous_event_hash']==previous
        previous=event['event_hash']
    assert len(audits)==sum(t['request']['method']=='tools/call' for t in transcript)
    assert runtime=={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in runtime}
    report={'surface':'live Neo4j + isolated local stdio MCP; no Claude model invoked',
            'completed_at':datetime.now(timezone.utc).isoformat(),'casebook_sha256':(out/'casebook.sha256').read_text().strip(),
            'release':release['revision'],'implementation':results[0]['versions']['implementation'],
            'direct_assessments':len(results),'tool_calls':len(audits),'trace_hash_chain_verified':True,
            'query_count':sum(len(a['retrieval_trace']['queries']) for a in audits),'case_results':source_coverage,
            'evidence_field_mismatches':[v for e in evidence.values() for v in e['field_mismatches']],
            'controls':controls,'provider_status':'not_invoked_in_direct_backend_run',
            'limitations':['No consumer-app model behavior measured in this run','Catalog-only evidence retrieval may omit retained graph clauses','Source passage equality to the pinned release is distinct from PDF extraction correctness','Draft expectations are not human policy approval']}
    write(out/'requirement-evidence.json',evidence);write(out/'direct-results.json',report)
    print(json.dumps({k:report[k] for k in ('direct_assessments','tool_calls','query_count','evidence_field_mismatches','case_results','controls')},indent=2))
if __name__=='__main__':main()
