"""Verify connector events; actual final-answer review is a separate artifact."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import jsonschema
from neo4j_kg.common import digest
from neo4j_kg.driver_answer import driver_answer
from neo4j_kg.driver_brief import driver_brief
from neo4j_kg.driver_conditions import conditions_answer
from neo4j_kg.driver_move import move_answer, PRESENTATION
from neo4j_kg.mcp_server import TOOLS

OUT = Path(__file__).resolve().parent
protocol = json.loads((OUT / 'protocol.json').read_text())
all_rows = json.loads((OUT / 'consumer-audit.json').read_text())
previous = None
rejections = []
for row in all_rows:
    event = row['event']
    assert event['event_hash'] == digest({k: v for k, v in event.items() if k != 'event_hash'})
    assert event['previous_event_hash'] == previous
    previous = event['event_hash']
    if event['response']['result']['isError']:
        assert event['method'] == 'assess_driver_move'
        assert event['response']['result']['content'] == [{'type': 'text', 'text': 'request_key was already used with different write arguments'}]
        assert 'evidence_assessment' not in event
        rejections.append({'sequence': event['sequence'], 'reason': 'request_key collision rejected before write'})
assert len(rejections) == 1
rows = [r for r in all_rows if not r['event']['response']['result']['isError']]
assert len(rows) == 4, len(rows)
for name, expected in protocol['runtime_sha256'].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
schemas = {t['name']: t.get('outputSchema') for t in TOOLS}
route_a = ['edge_a_exit13a_connector', 'edge_shared_north_avenue',
           'edge_shared_mclester', 'edge_shared_tripoli_gate']
route_b = ['edge_b_us1_south', 'edge_b_north_avenue_to_merge',
           'edge_shared_north_avenue', 'edge_shared_mclester', 'edge_shared_tripoli_gate']
expected_methods = ['assess_driver_move', 'assess_driver_move', 'get_trip_conditions_answer', 'assess_driver_move']
report = []
previous = None
assessments = []
for i, row in enumerate(rows):
    event = row['event']
    assert event['method'] == expected_methods[i]
    assert event['event_hash'] == digest({k: v for k, v in event.items() if k != 'event_hash'})
    result = event['response']['result']
    assert result['isError'] is False
    body = result['structuredContent']
    jsonschema.validate(body, schemas[event['method']])
    assert body == json.loads(result['content'][-1]['text'])
    a = event['evidence_assessment']
    jsonschema.validate(a, schemas['assess_trip'])
    expected_text = conditions_answer(a) if i == 2 else move_answer(a)
    assert body['answer_markdown'] == expected_text
    assert body['trip_id'] == a['case']['trip_id']
    assert body['revision'] == a['case']['revision']
    assert body['assessment_id'] == a['assessment_id']
    assert body['versions'] == a['versions']
    assert event['retrieval_trace']['delivered_passage_clause_ids'] == []
    assert len(json.dumps(body)) < 12000
    assert len(result['content']) == 1
    text = body['answer_markdown']
    if i != 2:
        assert body['presentation'] == PRESENTATION
        assert '**102-inch-wide standard truck**' in text
        assert 'one motor-drawn vehicle' in text
        assert 'food, fuel, rest, repairs' in text
        assert event['validated_arguments']['as_received']['action'] == ('update' if i == 1 else 'create')
    assert a['service_status'] == 'available'
    assert a['decision_brief']['operational_permission'] == 'not_issued'
    assert a['case']['question_scope'] == 'trip_dispatch'
    assert a['case']['revision'] == [1, 2, 2, 1][i]
    facts = a['case']['facts']
    assert facts['height']['value'] == (175 if i == 0 else 162)
    assert facts['width']['value'] == 102
    assert facts['gross_weight']['value'] == 80000
    assert facts['semitrailer_length']['value'] == 636
    assert facts['port_street_in_route']['value'] is False
    route = a['evidence_package']['route_context']
    assert [s['segment_id'] for s in route['segments']] == (route_b if i == 3 else route_a)
    terminal = a['evidence_package']['current_terminal_status']
    assert terminal['currentness'] == 'unknown_for_this_trip'
    assert len(terminal['sources']) == 3
    for source in terminal['sources']:
        assert source['url'] in text
    assert len(a['evidence_package']['sources']) == 26
    assert a['versions']['graph_release'] == 'f5dffe0f7a32b5144920efb5a644f8c4dc9f20def76b4217c38b0cdbc454cf5c'
    sent = event['validated_arguments']['as_received'].get('source_message')
    if i != 2:
        assert sent and protocol['prompts'][i].startswith(sent)
    (OUT / f'service-answer-{i + 1}.md').write_text(text + '\n')
    report.append({'turn': i + 1, 'method': event['method'], 'recorded_at': event['recorded_at'],
                   'trip_id': a['case']['trip_id'], 'revision': a['case']['revision'],
                   'scope': a['case']['question_scope'], 'source_count_in_supporting_assessment': 26,
                   'route_id': route['route_id'], 'segments': [s['segment_id'] for s in route['segments']],
                   'source_message_omitted_suffix': protocol['prompts'][i][len(sent):] if sent else None,
                   'output_schema': 'passed', 'json_parity': 'passed', 'rendered_text_parity': 'passed',
                   'event_hash': 'passed', 'operational_permission': 'not_issued'})
    assessments.append(a)
assert len({a['case']['trip_id'] for a in assessments[:3]}) == 1
assert assessments[3]['case']['trip_id'] != assessments[0]['case']['trip_id']
report = {'connector_verification': 'passed', 'total_connector_calls': len(all_rows), 'recovered_rejections': rejections, 'runtime_files_verified': len(protocol['runtime_sha256']),
          'consumer_presentation_acceptance': 'see consumer-review.md; not established by this script',
          'conversation_url': 'https://claude.ai/chat/0ce6f46c-fd0d-484f-b544-bb0d0dfaa5ef',
          'turns': report}
(OUT / 'consumer-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
