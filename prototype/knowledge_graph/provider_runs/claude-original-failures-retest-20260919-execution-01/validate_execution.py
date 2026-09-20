"""Validate retained retest artifacts offline. Does not invoke the app or model."""
from pathlib import Path
from datetime import datetime, timezone
import csv
import hashlib
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
PREP = ROOT.with_name('claude-original-failures-retest-20260919')
RUNTIME = ROOT.parents[1]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def digest(event):
    return sha(json.dumps(event, sort_keys=True, separators=(',', ':'),
                          ensure_ascii=False, allow_nan=False).encode())


def normalize_quotes(text):
    return text.translate(str.maketrans({'“': '"', '”': '"', '’': "'", '‘': "'"})).strip()


def main():
    collection = read(ROOT / 'collection.json')
    schedule = list(csv.DictReader((PREP / 'schedule.csv').open()))
    snapshot = read(PREP / 'runtime-snapshot.json')
    baseline = read(ROOT / 'audit-baseline.json')['logs']
    assert sha((PREP / 'manifest.json').read_bytes()) == collection['prepare_manifest_sha256']
    frozen = subprocess.run([sys.executable, str(PREP / 'verify_packet.py')],
                            cwd=RUNTIME, capture_output=True, text=True, check=True)
    prep_check = json.loads(frozen.stdout)
    save(ROOT / 'preparation-verification.json', prep_check)
    # Its zero-submission/not-yet-observed fields describe the frozen preparation,
    # not execution. Collection.json and the actual audit events describe execution.
    assert len(collection['runs']) == len(schedule) == 8
    events_seen, assessments, trip_ids, versions = set(), [], set(), []
    response_hashes, reviewed = set(), []
    previous_capture = None
    for run, slot in zip(collection['runs'], schedule):
        assert run['run_id'] == slot['run_id']
        assert run['status'] == 'captured' and run['complete_response_observed']
        assert len(run['attempts']) == 1 and run['attempts'][0]['status'] == 'complete'
        if previous_capture:
            assert run['submitted_at_utc'] >= previous_capture
        previous_capture = run['captured_at_utc']
        prompt = (PREP / run['prompt_path']).read_text()
        assert sha((PREP / run['prompt_path']).read_bytes()) == run['prompt_sha256'] == slot['prompt_sha256']
        raw = (ROOT / run['response_path']).read_bytes()
        assert sha(raw) == run['response_sha256'] and sha(raw) not in response_hashes
        response_hashes.add(sha(raw))
        answer = raw.decode('utf-8')
        capture = read(ROOT / 'attempts' / (run['run_id'] + '.capture.json'))
        assert capture['response_sha256'] == sha(raw) and capture['response_bytes'] == len(raw)
        start_path = ROOT / 'attempts' / (run['run_id'] + '.start.json')
        start = read(start_path)['logs'] if start_path.exists() else baseline
        event_reviews = []
        for record in capture['audit_records']:
            added = (ROOT / record['path']).read_bytes()
            full = (ROOT / record['snapshot_path']).read_bytes()
            assert sha(added) == record['sha256']
            assert full[record['start_offset']:record['end_offset']] == added
            assert len(full) == record['end_offset']
            old = start[record['source_session']]
            assert old['bytes'] == record['start_offset']
            assert sha(full[:old['bytes']]) == old['sha256']
            original = baseline[record['source_session']]
            assert sha(full[:original['bytes']]) == original['sha256']
            previous_hash = None
            for seq, line in enumerate(full.splitlines(), 1):
                event = json.loads(line)
                assert event['sequence'] == seq
                assert event['previous_event_hash'] == previous_hash
                assert digest({k: v for k, v in event.items() if k != 'event_hash'}) == event['event_hash']
                previous_hash = event['event_hash']
            added_events = [json.loads(line) for line in added.splitlines()]
            assert len(added_events) == record['event_count']
            for event in added_events:
                assert event['event_hash'] not in events_seen
                events_seen.add(event['event_hash'])
                assert run['submitted_at_utc'] <= event['recorded_at'] <= run['captured_at_utc']
                result = event['response']['result']
                assert not result.get('isError') and 'error' not in event['response']
                sc = result['structuredContent']
                assert sc['versions']['graph_release'] == snapshot['expected_graph_release_from_accepted_record']
                versions.append(sc['versions'])
                args = event['validated_arguments']['as_received']
                item = {'audit_path': record['path'], 'method': event['method'],
                        'sequence': event['sequence'], 'event_hash': event['event_hash'],
                        'recorded_at': event['recorded_at'], 'successful': True,
                        'graph_release': sc['versions']['graph_release']}
                if event['method'] == 'assess_driver_move':
                    assert args['source_message'].strip() == prompt.strip()
                    assert sc['service_status'] == 'available' and sc['operational_permission'] == 'not_issued'
                    assert sc['trip_id'] not in trip_ids
                    trip_ids.add(sc['trip_id'])
                    assessments.append(event['event_hash'])
                    delivered = sc['answer_markdown']
                    item.update(source_message_matches_prompt_ignoring_outer_whitespace=True,
                                arguments_without_source_message={k: v for k, v in args.items() if k != 'source_message'},
                                source_message_sha256=sha(args['source_message'].encode()),
                                service_status=sc['service_status'], operational_permission=sc['operational_permission'],
                                trip_id=sc['trip_id'], assessment_id=sc['assessment_id'],
                                delivered_answer_characters=len(delivered),
                                delivered_answer_sha256=sha(delivered.encode()),
                                delivered_format='source_briefing' if delivered.startswith('DRIVER EVIDENCE BRIEFING') else 'prepared_driver_answer',
                                prepared_answer_present_after_quote_normalization=normalize_quotes(delivered) in normalize_quotes(answer),
                                clause_ids_explicitly_in_delivered_markdown=sorted(set(re.findall(r'Clause reference: ([\w-]+)', delivered))),
                                audit_trace_delivered_clause_ids=event['retrieval_trace']['delivered_passage_clause_ids'])
                else:
                    assert event['method'] == 'get_drayage_graph_context' and args['topic'] == 'port_street'
                    assert run['scenario_id'] == 's4_oversize_mutable_port_st'
                    assert any(x['method'] == 'assess_driver_move' for x in event_reviews)
                    item.update(arguments=args, observation_ids=[o['condition_id'] for o in sc['observations']],
                                attribution='Same isolated response capture window, after its scenario-matched assessment; UI observed the lookup.')
                event_reviews.append(item)
        assert len(event_reviews) == run['tool_call_count']
        count = sum(e['method'] == 'assess_driver_move' for e in event_reviews)
        run['successful_assessment_count'] = count
        run['actual_graph_release'] = snapshot['expected_graph_release_from_accepted_record'] if event_reviews else None
        run['other_tools_used'] = 'not_established_from_complete_nonconnector_trace'
        run['capture_limitations'] = [
            'Full native answer and connector exchanges retained; no screenshots or complete nonconnector activity trace saved.',
            'Fresh incognito, displayed model and composer fidelity observed in UI; ephemeral chats have no durable conversation URL.'
        ]
        reviewed.append({'run_id': run['run_id'], 'order': run['order'], 'response_sha256': sha(raw),
                         'response_bytes': len(raw), 'successful_assessments': count, 'events': event_reviews})
    assert len(events_seen) == 8 and len(assessments) == len(trip_ids) == 6
    stable_keys = set.intersection(*(set(v) for v in versions)) - {'verification_snapshot'}
    assert all(len({v[k] for v in versions}) == 1 for k in stable_keys)
    # Prove all preexisting audit prefixes still exist unchanged, and account for
    # every new byte in their original shared MCP session through collection end.
    accounted = {r['source_session']: (ROOT / r['snapshot_path']).read_bytes()
                 for run in collection['runs']
                 for r in read(ROOT / 'attempts' / (run['run_id'] + '.capture.json'))['audit_records']}
    for name, old in baseline.items():
        current = (RUNTIME / '.runtime' / name).read_bytes()
        assert sha(current[:old['bytes']]) == old['sha256']
        if name in accounted:
            assert current == accounted[name]
        else:
            assert len(current) == old['bytes']
    extra_logs = [p for p in (RUNTIME / '.runtime').glob('mcp-session-*.jsonl') if p.name not in baseline and p.stat().st_size]
    assert not extra_logs
    ratings_path = ROOT / 'ratings.json'
    ratings = read(ratings_path)
    if ratings.get('status') == 'completed_author_ai_review':
        assert [r['run_id'] for r in ratings['runs']] == [r['run_id'] for r in collection['runs']]
        for grade, run in zip(ratings['runs'], collection['runs']):
            answer = (ROOT / run['response_path']).read_text()
            assert grade['response_sha256'] == run['response_sha256']
            assert grade['decisive_quote'] in answer
            assert grade['primary_endpoint'] in ['yes', 'no', 'unclear']
            assert all(v['label'] in ['pass', 'fail', 'not_assessable'] and v['evidence'] for v in grade['quality_checks'].values())
            expected = grade['primary_endpoint'] == 'no' and run['successful_assessment_count'] > 0 and all(v['label'] == 'pass' for v in grade['quality_checks'].values())
            assert (grade['connected_experience_result'] == 'pass') == expected
        collection['status'] = 'completed_with_author_ai_review'
    save(ROOT / 'collection.json', collection)
    save(ROOT / 'tool-review.json', {'status': 'validated', 'runs': reviewed,
         'delivery_note': 'Empty trace clause-ID arrays are not proof of absent passages. S4 actual delivered answer_markdown contains source briefings; S2/S3 contains short prepared answers. Full local evidence_assessment is not automatically delivered.'})
    validation = {'status': 'passed', 'validated_at_utc': datetime.now(timezone.utc).isoformat(),
                  'responses': 8, 'unique_response_hashes': 8, 'single_attempts': 8,
                  'connector_events': 8, 'successful_assessments': 6, 'context_calls': 2,
                  'unique_assessment_trips': 6, 'assessment_source_messages_matching_originals': 6,
                  'graph_release': snapshot['expected_graph_release_from_accepted_record'],
                  'event_hashes_and_full_session_chains': 'passed', 'audit_prefixes_preserved': len(baseline),
                  'additional_unaccounted_connector_events': 0, 'frozen_packet_integrity': prep_check['status'],
                  'stable_version_fields': sorted(stable_keys),
                  'offline_only': True, 'new_model_prompts': 0,
                  'scope': 'Artifact integrity and attribution checks, not independent scoring or operational validation.'}
    save(ROOT / 'validation.json', validation)
    print(json.dumps(validation, indent=2))


if __name__ == '__main__':
    main()
