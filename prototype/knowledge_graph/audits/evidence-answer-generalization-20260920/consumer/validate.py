"""Validate captured local consumer evidence; does not grade the final prose."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import jsonschema
from neo4j_kg.common import digest
from neo4j_kg.trip_tools import TRIP_TOOLS

D = Path(__file__).resolve().parent
sha = lambda data: hashlib.sha256(data).hexdigest()
collection = json.loads((D / 'collection.json').read_text())
final = json.loads((D / 'final-runtime-plan.json').read_text())
current = {f: sha((ROOT / f).read_bytes()) for f in final['runtime_hashes']}
assert current == final['runtime_hashes']
assert digest(current) == final['implementation']
old_implementation = json.loads((D.parent / 'holdout-run-3/results.json').read_text())['cases'][0]['implementation']
rows = []
for run in collection['runs']:
    assert run['status'] == 'captured'
    prompt = (D / run['prompt_path']).read_text()
    answer = (D / run['response_path']).read_bytes()
    assert sha(prompt.encode()) == run['prompt_sha256']
    assert sha(answer) == run['response_sha256']
    capture = json.loads((D / 'attempts' / (run['run_id'] + '.capture.json')).read_text())
    bound = []
    for record in capture['audit_records']:
        raw = (D / record['path']).read_bytes()
        assert sha(raw) == record['sha256']
        snapshot = (D / record['snapshot_path']).read_bytes()
        assert snapshot[record['start_offset']:record['end_offset']] == raw
        previous = None
        for event in map(json.loads, snapshot.splitlines()):
            body = {k: v for k, v in event.items() if k != 'event_hash'}
            assert digest(body) == event['event_hash']
            assert event['previous_event_hash'] == previous
            previous = event['event_hash']
        for event in map(json.loads, raw.splitlines()):
            assert event['method'] == 'assess_driver_move'
            args = event['validated_arguments']['as_received']
            assert args['source_message'] == prompt
            result = event['response']['result']
            assert not result.get('isError')
            body = result['structuredContent']
            schema = next(t for t in TRIP_TOOLS if t['name'] == event['method'])['outputSchema']
            jsonschema.validate(body, schema)
            a = event['evidence_assessment']
            expected = final['implementation'] if run['run_id'].startswith('final_') else old_implementation
            assert a['versions']['implementation'] == expected
            assert body['versions']['implementation'] == expected
            assert a['case']['source_message'] == prompt
            assert a['case']['question_scope'] == 'trip_dispatch'
            assert a['versions']['graph_release'] == 'f5dffe0f7a32b5144920efb5a644f8c4dc9f20def76b4217c38b0cdbc454cf5c'
            prepared = body['answer_markdown']
            bound.append({'method': event['method'], 'implementation': expected,
                          'assessment_id': a['assessment_id'],
                          'raw_final_equals_prepared': answer.decode().strip() == prepared.strip(),
                          'prepared_characters': len(prepared), 'final_bytes': len(answer)})
    assert len(bound) == 1
    rows.append({'run_id': run['run_id'], 'checks_passed': True, 'calls': bound})
report = {'artifact_integrity_passed': True, 'runtime_hashes_match_final': True,
          'runs': rows, 'limit': 'Artifact integrity and schema checks do not establish prose quality, independent grading, or causal benefit.'}
(D / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
