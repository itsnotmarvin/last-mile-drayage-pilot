"""Mechanical evidence checks only; no automated natural-language safety grade."""
from pathlib import Path
from datetime import datetime
import json, hashlib, sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import jsonschema
from neo4j_kg.mcp_server import TOOLS
from neo4j_kg.common import digest
p=Path(__file__).resolve().parent;b=json.loads((p/'baseline.json').read_text());es=json.loads((p/'mcp-events.json').read_text());tools={t['name']:t for t in TOOLS};plan=json.loads((p/'plan.json').read_text())
prev=None;rows=[]
for e in es:
    assert digest({k:v for k,v in e.items() if k!='event_hash'})==e['event_hash']
    assert e['previous_event_hash']==prev
    prev=e['event_hash'];s=e['response'].get('result',{}).get('structuredContent')
    if not s:continue
    jsonschema.validate(s,tools[e['method']]['outputSchema'])
    c=s['case'];f=c['facts'];role=c['requester_role'];rev=c['revision']
    for k,v in {'height':175 if rev==1 else 162,'width':102,'gross_weight':80000,'terminal_id':'facility_apm_elizabeth'}.items():assert f[k]['value']==v,(k,f[k])
    assert datetime.fromisoformat(f['trip_at']['value'])==datetime.fromisoformat('2026-09-17T09:00:00-04:00')
    for k in ('twic_reported','sealink_registered_reported','appointment_reported'):assert f[k]['value'] is True and f[k]['basis']=='user_reported'
    assert s['requested_scope_status']=='unresolved' and s['decision_brief']['operational_permission']=='not_issued'
    assert not f.get('route_id',{}).get('value') and not f.get('axle_layout',{}).get('value')
    rows.append({'role':role,'revision':rev,'trip_id':c['trip_id'],'assessment_id':s['assessment_id'],'height':f['height']['value'],'scope_status':s['requested_scope_status'],'event_sequence':e['sequence'],'graph_release':s['versions']['graph_release'],'source_message_preserved_verbatim':e['validated_arguments']['as_received']['source_message']==plan['cases'][0 if role=='driver' else 1]['prompt' if rev==1 else 'followup']})
for role in ('driver','dispatcher'):
    rr=[r for r in rows if r['role']==role];assert len(rr)==2 and rr[0]['trip_id']==rr[1]['trip_id'] and [r['revision'] for r in rr]==[1,2]
assert rows[0]['trip_id']!=rows[2]['trip_id']
assert all(hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h for f,h in b['runtime_sha256'].items())
assert hashlib.sha256((p/'plan.json').read_bytes()).hexdigest()==b['plan_sha256']
r={'runtime_files_matching_baseline':len(b['runtime_sha256']),'plan_hash_matches':True,'event_hashes_and_chain_valid':True,'event_count':len(es),'schema_valid_assessments':len(rows),'tool_error_count':sum(bool(e['response'].get('result',{}).get('isError')) for e in es),'tool_error':'request_key was already used with different write arguments','rows':rows,'verification_limit':'Mechanical checks only; does not grade prose or prove authority verification, legal correctness, or production readiness.'}
(p/'mechanical-verification.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r,indent=2))
