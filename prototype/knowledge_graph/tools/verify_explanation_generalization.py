"""Run the predeclared local holdout against the real MCP handler and temp state.

Uses the archived in-memory graph oracle, not a consumer app or live Neo4j.
Artifacts retain all failures; this does not regrade the sealed Claude retest.
"""
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from kg.service import CheckingService as OriginalService
from test_neo4j_migration import OracleReader
from test_trip_assessment import MemoryGraph
from neo4j_kg.assessment import TripService
from neo4j_kg.mcp_server import Session
from neo4j_kg.service import CheckingService
from neo4j_kg.trip_state import TripStore


def check(name, text, result, assessment):
    low = text.lower()
    predicates = {
        'local_access_source': '16.32.pdf' in text and 'unrestricted local roadways' in low,
        'missing_dimensions_explained': 'missing loaded dimensions' in low and 'direct' in low,
        'reported_driver_context_preserved': 'Driver prerequisites are reported satisfied' in text,
        'no_invented_route': '**Your route:**' not in text,
        'permit_source': '90,000' in text and '38,000' in text and 'section 3.4' in text,
        'separate_authorities': all(s in text for s in ['toll-road', 'county/local', 'Port Authority', 'terminal handling']),
        'group_report_preserved': '37,000 on the tractor tandem' in text and '37,000 on the trailer tandem' in text,
        'no_group_split': '18500' not in text and '18,500' not in text,
        'weight_source': '658.17' in text,
        'bridge_spacing_dependency': 'spacings' in low and 'bridge' in low,
        'no_apm_assumption': 'APM requirements and gate observations are not assumed to apply' in text and '[APM status update]' not in text,
        'no_clearance': text.endswith('No operational permission is issued.'),
        'reported_approval_values_preserved': text.count('reported held') == 5,
        'no_verification_promotion': 'reported approval is not independent verification' in text,
        'negative_vs_positive_preserved': 'Port Authority approval: reported not held' in text and 'Terminal handling approval: reported held' in text,
        'rule_survives_removed_measurement': '16.32.pdf' in text and 'unrestricted local roadways' in low,
        'old_measurement_absent': 'Reported width: 100' not in text,
        'date_preserved_without_timestamp': 'September 8, 2026' in text and assessment['case']['facts'].get('trip_at', {}).get('value') is None,
        'permit_explanation_not_erased': 'What the reported permit' in text,
        'no_apm_applicability': 'APM requirements and gate observations are not assumed to apply' in text,
        'height_source': 'Reported height: 168' in text and 'section 2.1.2' in text,
        'terminal_coverage_gap': 'outside the terminal-specific evidence coverage' in text,
        'candidate_route_not_actual_route': 'Stored candidate route' in text and '**Your route:**' not in text,
        'no_route_completion': 'final streets have not been selected' in text and 'not confirmation that you selected every street' in text,
        'archived_not_live': 'Archived operating context, not current directions' in text,
        'no_release_checklist': 'not an exhaustive release checklist' in text,
        'atomic_rejection': bool(result.get('isError')) and 'DIMENSION_TEXT_MISMATCH' in str(result),
        'no_stale_findings_or_sources': 'evidence service is unavailable' in text and 'https://' not in text and '100' not in text,
    }
    return bool(predicates[name])


def main():
    audit = ROOT / 'audits/evidence-answer-generalization-20260920'
    raw = (audit / 'holdout.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == (audit / 'holdout.sha256').read_text().strip()
    out = audit / sys.argv[1]
    out.mkdir(exist_ok=False)
    reader = OracleReader(OriginalService())
    rows = []
    with tempfile.TemporaryDirectory() as temporary:
        for case in json.loads(raw)['cases']:
            graph = MemoryGraph(reader)
            states = TripStore(Path(temporary) / (case['id'] + '.sqlite3'))
            service = TripService(graph, states)
            session = Session(CheckingService(graph), trip_service=service, audit_path=out / (case['id'] + '.jsonl'))
            session.state = 'ready'
            args = {'action': 'create', 'facts': case['facts'], 'source_message': case['statement'],
                    'request_key': 'holdout-' + case['id']}
            def call(arguments):
                return session.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                    'params': {'name': 'assess_driver_move', 'arguments': arguments}})['result']
            result = call(args)
            body = result.get('structuredContent', {})
            if 'update' in case:
                result = call({'action': 'update', 'trip_id': body['trip_id'], 'expected_revision': 1,
                               'requester_role': 'driver', 'request_key': 'update-' + case['id'],
                               'replace_conflicts': True, **case['update']})
            if case['id'] == 'evidence_service_outage':
                graph.available = False
                result = call({'action': 'read', 'trip_id': body['trip_id']})
            body = result.get('structuredContent', {})
            text = body.get('answer_markdown', '')
            event = json.loads(session.audit_path.read_text().splitlines()[-1])
            assessment = event.get('evidence_assessment', {})
            (out / (case['id'] + '.txt')).write_text(text or json.dumps(result, indent=2))
            checks = {name: check(name, text, result, assessment) for name in case['checks']}
            rows.append({'id': case['id'], 'passed': all(checks.values()), 'checks': checks,
                         'answer_characters': len(text), 'graph_reads': graph.reads,
                         'implementation': body.get('versions', {}).get('implementation')})
    report = {'surface': 'local_mcp_handler_with_archived_oracle_not_consumer_app',
              'holdout_sha256': hashlib.sha256(raw).hexdigest(),
              'passed': sum(r['passed'] for r in rows), 'total': len(rows), 'cases': rows,
              'limits': 'Same-author predeclared checks, not independent human scoring or proof of generalization beyond this set.'}
    (out / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] == report['total'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
