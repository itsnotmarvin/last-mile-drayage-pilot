"""Synthetic HTTP acceptance of reported checks; does not invoke a model or browser."""
from datetime import datetime, timezone
from http.cookiejar import CookieJar
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import time
import uuid
from urllib.request import build_opener, HTTPCookieProcessor, ProxyHandler, Request

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from trip_app.operations import private_write
from trip_app.store import Workspace, secret_hash

OUT = ROOT / 'audits/reported-checks-final-2026-09-13'
PRIVATE = ROOT / '.runtime/integrated-app-2026-09-12'
ORIGIN = 'http://127.0.0.1:8765'
hashes = json.loads((OUT/'summary.json').read_text())['runtime_sha256']
assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in hashes.items())
requests, assessments, renewals = [], [], []
for role, user in [('driver','syn-user-driver'), ('dispatch','syn-user-dispatch')]:
    key = (PRIVATE/(role+'.key')).read_text().strip()
    with sqlite3.connect((PRIVATE/'app.sqlite3').as_uri()+'?mode=ro', uri=True) as db:
        valid = db.execute('SELECT 1 FROM app_access WHERE hash=? AND expires>?', (secret_hash(key), time.time())).fetchone()
    if not valid:
        key = Workspace(PRIVATE/'app.sqlite3').issue_access(user)
        private_write(PRIVATE/(role+'-reported-checks-'+uuid.uuid4().hex+'.key'), key)
        renewals.append(user)
    client = build_opener(ProxyHandler({}), HTTPCookieProcessor(CookieJar()))
    csrf = ''
    def call(path, body=None, record=True):
        req = Request(ORIGIN+path, data=json.dumps(body).encode() if body is not None else None,
                      headers={'Origin':ORIGIN, 'Content-Type':'application/json','X-CSRF-Token':csrf})
        with client.open(req, timeout=55) as response:
            assert response.status==200
            value = json.load(response)
        if record: requests.append({'user':role,'path':path,'body':body,'status':200,'response':value})
        return value
    csrf = call('/api/login', {'key':key}, record=False)['csrf']
    cid = call('/api/conversations', {})['id']
    path = '/api/conversations/'+cid
    statement = 'Can I take this truck to APM Elizabeth? It is 14 ft 7 in high. Gross weight is 80,000 lb. Permit status is unknown. Trip time is unknown.'
    view = call(path+'/message', {'version':0,'statement':statement,'request_key':uuid.uuid4().hex})
    assert view['assessment'] is None
    facts = {'terminal_id':'facility_apm_elizabeth','height':{'value':175,'unit':'in'},'gross_weight':{'value':80000,'unit':'lb'},'permit_type':None,'trip_at':None}
    view = call(path+'/confirm', {'version':1,'proposal_id':view['proposals'][0]['id'],'facts':facts,'scope':'trip_dispatch'})
    a = view['assessment']
    assert a['service_status']=='available'
    pkg = a['reported_fact_checks']
    checks = {c['check_id']:c for c in pkg['checks']}
    assert checks['nj_loaded_height']['comparison']['difference']==13
    assert checks['nj_loaded_height']['status']=='attention_required'
    assert checks['terminal_height_195']['status']=='comparison_only'
    assert checks['terminal_height_195']['comparison']['difference']==-20
    assert 'loaded height' in a['decision_brief']['next_steps'][0]
    assert pkg['operational_permission']=='not_issued'
    assert a['requested_scope_status']=='unresolved'
    assert a['coverage']['executed_requirements']==['apm_induction']
    assert a['evidence_package']['sources']
    assessments.append(a)
assert assessments[0]['reported_fact_checks']==assessments[1]['reported_fact_checks']
assert assessments[0]['case']['trip_id']!=assessments[1]['case']['trip_id']
with build_opener(ProxyHandler({})).open(ORIGIN+'/app.js',timeout=10) as response:
    served_js=response.read()
assert b'function reportedChecks(a)' in served_js
assert hashlib.sha256(served_js).hexdigest()==hashes['trip_app/static/app.js']
assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in hashes.items())
summary={'at':datetime.now(timezone.utc).isoformat(),'surface':'local_http_live_neo4j_no_model_no_browser',
         'origin':ORIGIN,'assessments':2,'recorded_http_requests':len(requests),
         'separate_conversations':True,'matching_role_checks':True,'loaded_height_inches':175,
         'nj_reference_inches':162,'nj_difference_inches':13,'terminal_reference_inches':195,
         'terminal_difference_inches':-20,'height_action_first':True,'requested_scope_status':'unresolved',
         'operational_permission':'not_issued','served_javascript_matches_verified_runtime':True,
         'temporary_synthetic_access_renewals':renewals,'runtime_hashes_match_final_stdio_capture':True}
private_write(OUT/'http-transcript.json',json.dumps(requests,indent=2)+'\n')
private_write(OUT/'http-summary.json',json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
