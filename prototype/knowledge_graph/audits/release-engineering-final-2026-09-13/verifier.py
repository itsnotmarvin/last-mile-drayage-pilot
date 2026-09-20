"""Capture synthetic axle intake over real stdio/HTTP and live Neo4j, without a model.

The application must already be running current code on the supplied loopback
origin. Only synthetic users in the supplied private directory are used.
This does not attach a connector, alter Neo4j, or perform browser acceptance.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from http.cookiejar import CookieJar
import json
import os
from pathlib import Path
import selectors
import sqlite3
import subprocess
import sys
import tempfile
import time
from urllib.request import build_opener, HTTPCookieProcessor, ProxyHandler, Request
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from neo4j_kg.release_readiness import runtime_hashes
from neo4j_kg.source_review import source_inventory, review_packet, compare_releases
from trip_app.mcp_server import Client
from trip_app.operations import private_write, read_secret
from trip_app.store import Workspace, secret_hash


def example_layout():
    return {'axles': [{'position': {'value': p, 'unit': 'ft'}, 'weight': {'value': w, 'unit': 'lb'}}
                      for p, w in zip((0, 12, 16, 48, 52), (12000, 17000, 17000, 17000, 17000))]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--credentials-file', required=True, type=Path)
    parser.add_argument('--private-directory', required=True, type=Path)
    parser.add_argument('--origin', default='http://127.0.0.1:8765')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    Client(args.origin, 'origin-validation-only')
    out = args.output
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    hashes = runtime_hashes()
    verifier_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    release = json.loads((ROOT/'data/neo4j_release.json').read_text())
    def save(name, value):
        private_write(out/name, json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n')
    save('source-inventory.json', source_inventory(release))
    save('source-review-packet.json', review_packet(release))
    save('unchanged-release-comparison.json', compare_releases(release, release))
    # Retest the prior reported checks against this same frozen implementation.
    subprocess.run([sys.executable, 'tools/verify_reported_checks.py', '--credentials-file',
                    str(args.credentials_file), '--output', str(out/'reported-checks')], cwd=ROOT, check=True)
    transcript, assessments = [], []
    facts = {'terminal_id': 'facility_apm_elizabeth', 'vehicle_id': 'syn-vehicle-axle-a',
             'trailer_id': 'syn-trailer-axle-a', 'axle_count': 5,
             'gross_weight': {'value': 80000, 'unit': 'lb'}, 'axle_layout': example_layout()}
    entry = '''import sys
from pathlib import Path
from neo4j_kg.service import CheckingService
from neo4j_kg.assessment import TripService
from neo4j_kg.trip_state import TripStore
from neo4j_kg.mcp_server import Session,serve
service=CheckingService()
try:serve(sys.stdin.buffer,sys.stdout,Session(service,trip_service=TripService(service.store,TripStore(Path(sys.argv[1])))))
finally:service.close()
'''
    env = os.environ | {'NEO4J_CREDENTIALS_FILE': str(args.credentials_file.resolve()),
                        'DRAYAGE_NEO4J_REVISION': release['revision']}
    with tempfile.TemporaryDirectory(dir=ROOT/'.runtime', prefix='axle-verification-') as temp, (out/'stdio-stderr.txt').open('w') as err:
        process = subprocess.Popen([sys.executable, '-c', entry, str(Path(temp)/'trips.sqlite3')],
                                   cwd=ROOT, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=err, text=True, bufsize=1)
        selector = selectors.DefaultSelector(); selector.register(process.stdout, selectors.EVENT_READ)
        def request(method, params, notification=False):
            payload = {'jsonrpc': '2.0', 'method': method, 'params': params}
            if not notification: payload['id'] = len(transcript)+1
            process.stdin.write(json.dumps(payload)+'\n'); process.stdin.flush()
            if notification: return
            if not selector.select(55): raise RuntimeError('MCP response timeout')
            response = json.loads(process.stdout.readline())
            transcript.append({'request': payload, 'response': response})
            assert response.get('id') == payload['id'] and 'error' not in response
            return response['result']
        def call(name, arguments, reject=False):
            response = request('tools/call', {'name': name, 'arguments': arguments})
            assert response['isError'] is reject
            if reject: return
            a = response['structuredContent']
            assert json.loads(response['content'][0]['text']) == a
            assert a['service_status'] == 'available'
            assert a['coverage']['executed_requirements'] == ['apm_induction']
            assert a['decision_brief']['operational_permission'] == 'not_issued'
            assert a['requested_scope_status'] == 'unresolved'
            assessments.append(a)
            return a
        try:
            request('initialize', {'protocolVersion': '2025-11-25', 'capabilities': {},
                                  'clientInfo': {'name': 'release-engineering-verifier', 'version': '1'}})
            request('notifications/initialized', {}, True)
            save('tools.json', request('tools/list', {}))
            pair = []
            for role in ('driver', 'dispatcher'):
                a = call('assess_trip', {'facts': facts, 'question_scope': 'trip_dispatch', 'requester_role': role,
                                        'source_message': 'Synthetic individual axle reports.', 'request_key': role})
                review = a['input_review']['axle_layout']
                assert review['total_weight_lb'] == 80000 and review['span_inches'] == 624
                assert review['gross_difference_lb'] == 0 and review['status'] == 'reported_only'
                pair.append(a)
            assert pair[0]['findings'] == pair[1]['findings']
            assert pair[0]['input_review']['axle_layout'] == pair[1]['input_review']['axle_layout']
            def update(a, values, key, replace=True):
                return call('update_trip_facts', {'trip_id': a['case']['trip_id'], 'expected_revision': a['case']['revision'],
                           'facts': values, 'replace_conflicts': replace, 'question_scope': 'trip_dispatch',
                           'requester_role': a['case']['requester_role'], 'source_message': 'Synthetic correction.', 'request_key': key})
            mismatch = update(pair[0], {'gross_weight': {'value': 79000, 'unit': 'lb'}}, 'gross-correction')
            assert mismatch['input_review']['axle_layout']['gross_difference_lb'] == 1000
            assert mismatch['decision_brief']['status'] == 'input_correction_required'
            gross = next(c for c in mismatch['reported_fact_checks']['checks'] if c['check_id'] == 'federal_gross_80000')
            assert gross['comparison'] is None
            disputed = update(pair[1], {'gross_weight': {'value': 79000, 'unit': 'lb'}}, 'gross-dispute', replace=False)
            assert disputed['case']['conflicts']
            assert disputed['input_review']['axle_layout']['gross_difference_lb'] is None
            assert disputed['input_review']['axle_layout']['status'] == 'input_review_required'
            for a, field in ((mismatch, 'vehicle_id'), (disputed, 'trailer_id')):
                changed = update(a, {field: 'syn-'+('vehicle' if field == 'vehicle_id' else 'trailer')+'-axle-b'}, field)
                assert changed['input_review']['axle_layout']['status'] == 'not_supplied'
                assert 'axle_layout' in changed['case']['invalidated_fields']
            legacy = call('assess_trip', {'facts': {'axle_weights': [{'value': w, 'unit': 'lb'} for w in (12000, 34000, 34000)]},
                          'question_scope': 'trip_dispatch', 'requester_role': 'driver', 'source_message': 'Reported axle groups.', 'request_key': 'legacy'})
            assert legacy['input_review']['axle_layout']['status'] == 'not_supplied'
            call('assess_trip', {'facts': {**facts, 'axle_count': 3}, 'question_scope': 'trip_dispatch',
                 'requester_role': 'driver', 'source_message': 'Inconsistent synthetic count.', 'request_key': 'reject-count'}, reject=True)
        finally:
            process.stdin.close()
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
            process.stdout.close(); selector.close()
    assert process.returncode == 0
    save('axle-mcp-transcript.json', transcript)

    http, http_assessments, renewals = [], [], []
    for role, user in (('driver', 'syn-user-driver'), ('dispatch', 'syn-user-dispatch')):
        key = read_secret(args.private_directory/(role+'.key'))
        dbpath = (args.private_directory/'app.sqlite3').resolve()
        with sqlite3.connect(dbpath.as_uri()+'?mode=ro', uri=True) as db:
            valid = db.execute('SELECT 1 FROM app_access WHERE hash=? AND expires>?', (secret_hash(key), time.time())).fetchone()
        if not valid:
            key = Workspace(dbpath).issue_access(user)
            private_write(args.private_directory/(role+'-axle-'+uuid.uuid4().hex+'.key'), key)
            renewals.append(user)
        client = build_opener(ProxyHandler({}), HTTPCookieProcessor(CookieJar()))
        csrf = ''
        def http_call(path, body=None, record=True):
            req = Request(args.origin+path, data=json.dumps(body).encode() if body is not None else None,
                          headers={'Origin': args.origin, 'Content-Type': 'application/json', 'X-CSRF-Token': csrf})
            with client.open(req, timeout=55) as response:
                assert response.status == 200
                value = json.load(response)
            if record: http.append({'role': role, 'path': path, 'body': body, 'status': 200, 'response': value})
            return value
        csrf = http_call('/api/login', {'key': key}, record=False)['csrf']
        cid = http_call('/api/conversations', {})['id']; path = '/api/conversations/'+cid
        statement = ('Synthetic APM Elizabeth move. Five individual axles at positions 0, 12, 16, 48, 52 ft from the first axle; '
                     'weights are 12000, 17000, 17000, 17000, 17000 lb. Gross weight 80000 lb.')
        view = http_call(path+'/message', {'version': 0, 'statement': statement, 'request_key': uuid.uuid4().hex})
        assert view['assessment'] is None
        view = http_call(path+'/confirm', {'version': 1, 'proposal_id': view['proposals'][0]['id'], 'facts': facts, 'scope': 'trip_dispatch'})
        a = view['assessment']; http_assessments.append(a)
        assert a['input_review']['axle_layout']['total_weight_lb'] == 80000
        assert a['input_review']['axle_layout']['span_inches'] == 624
        assert a['service_status'] == 'available'
        assert a['decision_brief']['operational_permission'] == 'not_issued'
        assert a['coverage']['executed_requirements'] == ['apm_induction']
    assert http_assessments[0]['findings'] == http_assessments[1]['findings']
    assert http_assessments[0]['case']['trip_id'] != http_assessments[1]['case']['trip_id']
    with build_opener(ProxyHandler({})).open(args.origin+'/app.js', timeout=10) as response:
        served = response.read()
    assert hashlib.sha256(served).hexdigest() == hashes['trip_app/static/app.js']
    assert b"if(key==='axle_layout')" in served
    save('axle-http-transcript.json', http)
    assert runtime_hashes() == hashes, 'Runtime changed during capture'
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest() == verifier_hash
    save('summary.json', {'at': datetime.now(timezone.utc).isoformat(), 'graph_release': release['revision'],
         'surface': 'local_stdio_and_http_live_neo4j_no_model_no_browser', 'runtime_sha256': hashes,
         'verifier_sha256': verifier_hash, 'reported_check_stdio_assessments': 20, 'axle_stdio_assessments': len(assessments),
         'axle_http_assessments': len(http_assessments), 'rejected_inconsistent_stdio_calls': 1,
         'matching_driver_dispatch_findings': True, 'separate_http_conversations': True,
         'axle_gross_correction': 'requests_correction_and_suppresses_comparison',
         'disputed_gross_reconciliation': 'suppressed',
         'vehicle_and_trailer_reassignment': 'invalidates_layout', 'legacy_array_conversion': 'never',
         'temporary_synthetic_access_renewals': renewals, 'served_javascript_matches_runtime': True,
         'operational_permission': 'not_issued', 'browser_acceptance': 'blocked_ERR_BLOCKED_BY_CLIENT',
         'model_acceptance': 'not_run', 'new_proposal_bridge': 'unattached'})
    print(f'Verified {20+len(assessments)} stdio assessments and {len(http_assessments)} confirmed HTTP assessments against live Neo4j; no model or browser acceptance claimed.')


if __name__ == '__main__':
    main()
