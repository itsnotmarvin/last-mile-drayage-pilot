"""Verify captured connector evidence, not the quality of Claude's prose.

Run from the prototype root: python3 audits/driver-experience-2026-09-19/verify_capture.py
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import jsonschema
from neo4j_kg.common import digest
from neo4j_kg.mcp_server import TOOLS
from neo4j_kg.driver_answer import driver_answer
from neo4j_kg.driver_brief import driver_brief

OUT = Path(__file__).resolve().parent
protocol = json.loads((OUT / 'protocol.json').read_text())
rows = json.loads((OUT / 'consumer-audit.json').read_text())
assert len(rows) == 4
for name, expected in protocol['runtime_sha256'].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
schemas = {t['name']: t.get('outputSchema') for t in TOOLS}
expected_a = ['edge_a_exit13a_connector', 'edge_shared_north_avenue',
              'edge_shared_mclester', 'edge_shared_tripoli_gate']
expected_b = ['edge_b_us1_south', 'edge_b_north_avenue_to_merge',
              'edge_shared_north_avenue', 'edge_shared_mclester', 'edge_shared_tripoli_gate']
reports = []
assessments = []
previous = None
for index, row in enumerate(rows):
    event = row['event']
    unhashed = {k: v for k, v in event.items() if k != 'event_hash'}
    assert digest(unhashed) == event['event_hash']
    assert event['previous_event_hash'] == previous
    assert event['sequence'] == index + 1
    previous = event['event_hash']
    result = event['response']['result']
    assert result['isError'] is False
    assessment = result['structuredContent']
    jsonschema.validate(assessment, schemas[event['method']])
    assert len(result['content']) == 3
    assert json.loads(result['content'][-1]['text']) == assessment
    assert result['content'][0]['text'] == driver_answer(assessment)
    assert result['content'][1]['text'] == driver_brief(assessment)
    assert (OUT / f'prepared-answer-{index + 1}.txt').read_text() == result['content'][0]['text'] + '\n'
    assert assessment['service_status'] == 'available'
    assert assessment['decision_brief']['operational_permission'] == 'not_issued'
    assert assessment['versions']['graph_release'] == 'f5dffe0f7a32b5144920efb5a644f8c4dc9f20def76b4217c38b0cdbc454cf5c'
    case = assessment['case']
    facts = case['facts']
    expected = expected_a if index < 3 else expected_b
    route = assessment['evidence_package']['route_context']
    assert [s['segment_id'] for s in route['segments']] == expected
    assert facts['height']['value'] == (175 if index == 0 else 162)
    assert facts['port_street_in_route']['value'] is False
    assert facts['width']['value'] == 102
    assert facts['gross_weight']['value'] == 80000
    assert facts['semitrailer_length']['value'] == 636
    terminal = assessment['evidence_package']['current_terminal_status']
    assert terminal['currentness'] == 'unknown_for_this_trip'
    assert len(terminal['sources']) == 3
    for source in assessment['evidence_package']['sources']:
        assert source['url'] in result['content'][1]['text']
    sent = event['validated_arguments']['as_received'].get('source_message')
    if index == 2:
        assert sent is None  # Read-only reassessment; no new reported facts.
    else:
        assert protocol['prompts'][index].startswith(sent)
    reports.append({
        'turn': index + 1, 'method': event['method'], 'recorded_at': event['recorded_at'],
        'trip_id': case['trip_id'], 'revision': case['revision'], 'scope': case['question_scope'],
        'height_inches': facts['height']['value'], 'route_id': route['route_id'],
        'segments': expected, 'source_count': len(assessment['evidence_package']['sources']),
        'terminal_page_count': len(terminal['sources']),
        'terminal_currentness': terminal['currentness'], 'full_json_parity': True,
        'event_hash_verified': True, 'prepared_answer_reproduced': True,
        'source_message_omitted_prompt_suffix': (protocol['prompts'][index][len(sent):] if sent else None),
        'operational_permission': 'not_issued',
    })
    assessments.append(assessment)
assert [a['case']['revision'] for a in assessments] == [1, 2, 2, 1]
assert len({a['case']['trip_id'] for a in assessments[:3]}) == 1
assert assessments[3]['case']['trip_id'] != assessments[0]['case']['trip_id']
assert [r['method'] for r in reports] == ['assess_trip', 'update_trip_facts', 'assess_trip', 'assess_trip']
report = {
    'connector_evidence_validation': 'passed',
    'consumer_presentation_acceptance': 'not_passed_see_consumer_review',
    'conversation_url': 'https://claude.ai/chat/f2016f85-08cc-4081-bac0-e61032d2452f',
    'runtime_files_verified': len(protocol['runtime_sha256']),
    'provider_attribution': 'Native Claude Desktop UI observed all four requests/results; generic MCP audit alone does not identify the provider.',
    'turns': reports,
}
(OUT / 'consumer-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
