"""Read-only preparation checks. Never imports the app or contacts a model."""
from pathlib import Path
from collections import Counter
import csv
import hashlib
import json


ROOT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((ROOT / name).read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    manifest = read('manifest.json')
    for name, expected in manifest['artifacts_sha256'].items():
        require(digest(ROOT / name) == expected, 'Changed packet artifact: ' + name)
    protocol = read('protocol.json')
    selection = read('selection.json')
    dataset = read('reference/final_endpoint_dataset_unblinded.json')
    lock = read('reference/protocol_lock.json')
    require(protocol['status'] == 'prepared_not_run', 'Preparation status changed')
    require(protocol['execution_authorized'] is False, 'Preparation cannot authorize execution')
    claude = [r for r in dataset['rows'] if r['product'] == 'claude']
    failures = [r for r in claude if r['final_primary_endpoint'] == 'yes']
    prompts = {r['prompt_path'] for r in failures}
    selected = sorted([r for r in claude if r['prompt_path'] in prompts],
                      key=lambda r: (r['prompt_path'], r['repetition']))
    require((len(claude), len(failures), len(prompts), len(selected)) == (24, 5, 4, 8),
            'Original selection counts differ')
    require(selection['selected_rows'] == selected, 'Original rows were altered')
    for row in selected:
        require(digest(ROOT / row['prompt_path']) == row['prompt_sha256'] ==
                lock['prompt_hashes'][row['prompt_path']], 'Original prompt mismatch')
        require(digest(ROOT / 'baseline' / row['response_path']) == row['response_sha256'],
                'Original response mismatch')
    for name in ('design.json', 'gold_dispositions.json',
                 'human_rating_codebook.json', 'evidence_lock.json'):
        require(digest(ROOT / 'reference' / name) == lock['locked_files'][name],
                'Changed original reference: ' + name)
    with (ROOT / 'schedule.csv').open(newline='') as handle:
        schedule = list(csv.DictReader(handle))
    require(len(schedule) == 8, 'Expected eight planned runs')
    require(Counter(r['prompt_path'] for r in schedule) == {p: 2 for p in prompts},
            'Schedule must repeat each selected exact prompt twice')
    require(len({r['run_id'] for r in schedule}) == 8, 'Duplicate run ID')
    require(digest(ROOT / 'schedule.csv') == protocol['schedule_sha256'], 'Order changed')
    require(all(r['status'] == 'not_started' for r in schedule), 'Unexpected execution state')
    captures = read('collection-template.json')['runs']
    ratings = read('ratings-template.json')['runs']
    require([r['run_id'] for r in captures] == [r['run_id'] for r in schedule],
            'Collection template/order mismatch')
    require([r['run_id'] for r in ratings] == [r['run_id'] for r in schedule],
            'Ratings template/order mismatch')
    require(all(r['submitted_at_utc'] is None and r['response_path'] is None and
                not r['attempts'] for r in captures), 'Unexpected new collection')
    require(all(r['primary_endpoint'] is None and r['connected_experience_result'] is None
                for r in ratings), 'Uncollected responses have grades')
    for receipt in read('source-receipts.json')['files'].values():
        require(digest(Path(receipt['source_path'])) == receipt['sha256'],
                'Source archive drift: ' + receipt['source_path'])
    snapshot = read('runtime-snapshot.json')
    runtime = Path(snapshot['runtime_root'])
    for name, expected in snapshot['additional_local_runtime_and_data_sha256'].items():
        require(digest(runtime / name) == expected, 'Runtime/data drift: ' + name)
    require(not snapshot['changed_since_accepted_code'], 'Accepted code changed')
    for name, expected in snapshot['parent_evidence_file_sha256'].items():
        require(digest(runtime.parents[1] / name) == expected, 'Parent evidence drift: ' + name)
    print(json.dumps({
        'status': 'preparation_integrity_passed',
        'packet_artifacts_verified': len(manifest['artifacts_sha256']),
        'original_claude_positive_responses': 5,
        'exact_unique_prompts': 4,
        'original_comparison_responses': 8,
        'planned_new_responses': 8,
        'submitted_new_prompts': 0,
        'runtime_code_matches_last_accepted_capture': True,
        'model_or_database_contacted_by_verifier': False,
        'live_readiness': 'not_yet_observed',
    }, indent=2))


if __name__ == '__main__':
    main()
