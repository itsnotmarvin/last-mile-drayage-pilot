"""Verify saved live MCP evidence delivery; no database or model calls."""
import hashlib
import json
from pathlib import Path
import subprocess

from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def read(name):
    return json.loads((HERE / name).read_text())


def verify():
    transcript = read('direct-stdio-transcript.json')
    tools = {t['name']: t for t in read('tools.json')['tools']}
    focused = read('requirement-evidence.json')
    canonical = {}
    for item in focused.values():
        for source in item['payload']['sources']:
            cid = source['clause_id']
            assert cid not in canonical or canonical[cid] == source
            canonical[cid] = source
    book = read('casebook.json')
    prompts = {p['id']: p for p in book['prompts']}
    cases = {c['id']: c for c in book['cases']}
    traces = {r['request_id']: r for r in
              map(json.loads, (HERE / 'direct-mcp-audit.jsonl').read_text().splitlines())}
    legacy = next(x['response']['result']['structuredContent']['observations']
                  for x in transcript
                  if x['request'].get('params', {}).get('arguments', {}).get('topic') == 'port_street')
    legacy = {o['condition_id']: o for o in legacy}
    results = []
    schema_count = 0
    for exchange in transcript:
        request = exchange['request']
        if request['method'] != 'tools/call':
            continue
        result = exchange['response']['result']
        if result.get('isError'):
            continue
        name = request['params']['name']
        payload = result['structuredContent']
        if 'outputSchema' in tools[name]:
            Draft202012Validator(tools[name]['outputSchema']).validate(payload)
            schema_count += 1
        assert json.loads(result['content'][0]['text']) == payload
        if 'evidence_package' not in payload:
            continue
        package = payload['evidence_package']
        ids = [s['clause_id'] for s in package['sources']]
        assert len(ids) == len(set(ids))
        assert all(canonical[s['clause_id']] == s for s in package['sources'])
        assert [(f['requirement_id'], f['source_clause_ids']) for f in payload['findings']] == [
            (link['requirement_id'], link['source_clause_ids']) for link in package['requirement_links']]
        linked = {cid for link in package['requirement_links'] for cid in link['source_clause_ids']}
        assert linked == set(ids)
        observations = package['observations']
        for observation in observations:
            assert observation['record'] == legacy[observation['condition_id']]
            assert observation in focused['current_route_conditions']['payload']['observations']
            assert observation['operational_use'] is False
        condition_ids = {o['condition_id'] for o in observations}
        assert condition_ids == {cid for link in package['requirement_links'] for cid in link['condition_ids']}
        trace = traces[request['id']]['retrieval_trace']
        assert set(trace['delivered_passage_clause_ids']) == set(ids)
        assert set(trace['delivered_observation_ids']) == condition_ids
        key = request['params']['arguments'].get('request_key')
        if key not in prompts:
            continue
        case = cases[prompts[key]['case_id']]
        expected = set(case['audit_expected_clause_ids'])
        assert expected <= set(ids)
        assert payload['requested_scope_status'] == 'unresolved'
        results.append({'prompt_id': key, 'case_id': case['id'],
                        'expected_count': len(expected), 'missing_clause_ids': [],
                        'delivered_clause_count': len(ids),
                        'observation_ids': sorted(condition_ids),
                        'package_bytes': len(json.dumps(package).encode()),
                        'structured_payload_bytes': len(json.dumps(payload).encode()),
                        'response_envelope_bytes': len(json.dumps(exchange['response']).encode())})
    assert len(results) == 24
    baseline = ROOT / 'audits/evidence-2026-09-10'
    manifest = json.loads((baseline / 'artifact-manifest.json').read_text())
    for name, entry in manifest['files'].items():
        assert hashlib.sha256((baseline / name).read_bytes()).hexdigest() == entry['sha256'], name
    assert (HERE / 'casebook.json').read_bytes() == (baseline / 'casebook.json').read_bytes()
    for name, digest in read('runtime-files.json').items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    assert not subprocess.check_output(['git', 'diff', 'HEAD', '--', 'kg/'], cwd=ROOT)
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    result = {'surface': 'offline verification of exact live Neo4j/stdio MCP capture; no model invoked',
              'status': 'passed', 'broad_assessments_verified': len(results),
              'schema_validated_successful_calls': schema_count,
              'source_objects_equal_focused_endpoints': True,
              'observation_records_equal_legacy_live_context': True,
              'requirement_links_and_delivery_receipts_match': True,
              'baseline_manifest_files_verified': len(manifest['files']),
              'frozen_casebook_unchanged': True, 'runtime_matches_capture': True,
              'historical_kg_git_diff_empty': True, 'git_diff_check_passed': True,
              'assessments': results}
    (HERE / 'bundle-verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'assessments'}, indent=2))
    for field in ('package_bytes', 'structured_payload_bytes', 'response_envelope_bytes'):
        print(field, min(r[field] for r in results), max(r[field] for r in results))


if __name__ == '__main__':
    verify()
