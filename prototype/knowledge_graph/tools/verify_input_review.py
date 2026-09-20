"""Replay saved extraction failures through fresh stdio; verify controlled report.

No Claude model is invoked. Synthetic cases use an isolated temporary database.
"""
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--credentials-file', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists():
        parser.error('Use a new output directory to preserve previous runs.')
    out.mkdir(parents=True, mode=0o700)
    def save(name, value):
        (out / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    release = json.loads((ROOT / 'data/neo4j_release.json').read_text())
    runtime = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in sorted((ROOT / 'neo4j_kg').glob('*.py'))}
    env = os.environ | {'NEO4J_CREDENTIALS_FILE': str(args.credentials_file.resolve()),
                        'DRAYAGE_NEO4J_REVISION': release['revision']}
    entry = '''import sys
from pathlib import Path
from neo4j_kg.service import CheckingService
from neo4j_kg.assessment import TripService
from neo4j_kg.trip_state import TripStore
from neo4j_kg.mcp_server import Session, serve
s = CheckingService()
try: serve(sys.stdin.buffer, sys.stdout, Session(s, trip_service=TripService(s.store, TripStore(Path(sys.argv[1])))))
finally: s.store.close()
'''
    transcript, rejections = [], []
    with tempfile.TemporaryDirectory(prefix='input-review-') as tmp, (out / 'stderr.txt').open('w') as stderr:
        state = Path(tmp) / 'trips.sqlite3'
        process = subprocess.Popen([sys.executable, '-c', entry, str(state)], cwd=ROOT, env=env,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr,
                                   text=True, bufsize=1)
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        def request(method, params, notification=False):
            message = {'jsonrpc': '2.0', 'method': method, 'params': params}
            if not notification:
                message['id'] = len(transcript) + 1
            process.stdin.write(json.dumps(message) + '\n')
            process.stdin.flush()
            if notification:
                return
            if not selector.select(50):
                raise RuntimeError('MCP response timeout')
            response = json.loads(process.stdout.readline())
            transcript.append({'request': message, 'response': response})
            assert response['id'] == message['id'] and 'error' not in response
            return response['result']
        def call(name, arguments):
            return request('tools/call', {'name': name, 'arguments': arguments})
        try:
            request('initialize', {'protocolVersion': '2025-11-25', 'capabilities': {},
                                  'clientInfo': {'name': 'input-review-verifier', 'version': '1'}})
            request('notifications/initialized', {}, True)
            save('tools.json', request('tools/list', {}))
            for path in sorted((ROOT / 'docs/paired-replay-2026-09-10').glob('s*__*.audit.json')):
                event = next(e for e in json.loads(path.read_text()) if e['method'] == 'assess_trip')
                result = call('assess_trip', event['validated_arguments']['as_received'])
                assert result['isError'] and 'Trip facts were not saved' in result['content'][0]['text']
                rejections.append({'capture': str(path.relative_to(ROOT)),
                                   'capture_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                                   'error': result['content'][0]['text']})
            assert len(rejections) == 4
            import sqlite3
            with sqlite3.connect(state) as connection:
                assert connection.execute('SELECT count(*) FROM trips').fetchone()[0] == 0
                assert connection.execute('SELECT count(*) FROM requests').fetchone()[0] == 0
            def create(key, role):
                result = call('assess_trip', {
                    'request_key': key, 'requester_role': role, 'question_scope': 'trip_dispatch',
                    'source_message': 'Synthetic truck to APM Elizabeth. Loaded width is 12 feet and height is 14 feet 7 inches. Trip time is unknown.',
                    'facts': {'terminal_id': 'facility_apm_elizabeth', 'width': {'value': 144, 'unit': 'in'},
                              'height': {'value': 175, 'unit': 'in'}, 'trip_at': None}})
                assert not result['isError']
                body = result['structuredContent']
                assert body == json.loads(result['content'][-1]['text'])
                assert body['service_status'] == 'available'
                assert body['case']['facts']['height']['value'] == 175
                assert body['decision_brief']['operational_permission'] == 'not_issued'
                assert body['input_review']['confirmation_status'] == 'not_independently_confirmed'
                return body
            first = create('corrected-driver', 'driver')
            second = create('corrected-dispatcher', 'dispatcher')
            assert first['findings'] == second['findings']
            assert first['case']['trip_id'] != second['case']['trip_id']
            update = {'trip_id': first['case']['trip_id'], 'expected_revision': 1,
                      'request_key': 'correction', 'requester_role': 'driver', 'question_scope': 'trip_dispatch',
                      'replace_conflicts': True, 'source_message': 'Correction: height is 14 feet 8 inches.',
                      'facts': {'height': {'value': 14, 'unit': 'ft'}}}
            assert call('update_trip_facts', update)['isError']
            fresh = call('assess_trip', {'trip_id': first['case']['trip_id']})['structuredContent']
            assert fresh['case']['revision'] == 1
            update['facts']['height'] = {'value': 176, 'unit': 'in'}
            corrected = call('update_trip_facts', update)['structuredContent']
            assert corrected['case']['revision'] == 2
            assert corrected['decision_brief']['revision'] == 2
            report_path = out / 'controlled-trip-report.html'
            subprocess.run([sys.executable, str(ROOT / 'tools/export_trip_report.py'),
                            '--trip-id', first['case']['trip_id'], '--state-file', str(state),
                            '--credentials-file', str(args.credentials_file.resolve()),
                            '--revision', release['revision'], '--output', str(report_path)],
                           cwd=ROOT, env=env, check=True, stdout=subprocess.DEVNULL, stderr=stderr)
            report = report_path.read_text()
            assert '176 inch' in report and 'Revision: 2' in report
            assert 'Operational permission: not issued.' in report and '<script' not in report
            save('representative-assessment.json', corrected)
            save('results.json', {
                'surface': 'live Neo4j and fresh stdio MCP; no model invoked',
                'completed_at': datetime.now(timezone.utc).isoformat(),
                'implementation': corrected['versions']['implementation'], 'release': release['revision'],
                'captured_bad_calls_rejected_without_saved_state': rejections,
                'corrected_driver_dispatcher_findings_equal': True,
                'rejected_update_kept_revision': True, 'corrected_update_revision': 2,
                'report_exported_from_fresh_service_assessment': True,
                'report_permission': 'not_issued',
                'tool_calls': sum(t['request']['method'] == 'tools/call' for t in transcript)})
        finally:
            process.stdin.close()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=5)
            selector.close()
            save('stdio-transcript.json', transcript)
            save('runtime-files.json', runtime)
    assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h for p, h in runtime.items())
    print('Live input review and report checks passed; see results.json.')


if __name__ == '__main__':
    main()
