"""Verify saved artifacts and replay captured calls; does not invoke a model."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent.parent))
from kg.graph import digest
from kg.service import CheckingService


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    for name, expected in manifest.items():
        assert sha(ROOT / name) == expected, name
    service = CheckingService()
    for folder in [ROOT, ROOT / 'defined-status-followup']:
        frozen = (folder / 'protocol.sha256').read_text().split()[0]
        assert sha(folder / 'protocol.json') == frozen
        protocol = json.loads((folder / 'protocol.json').read_text())
        for name, expected in protocol['prompt_sha256'].items():
            assert sha(folder / name) == expected, name
        a = (folder / 'A-no-tool.prompt.txt').read_text().split('\n\n', 1)[1]
        b = (folder / 'B-with-tool.prompt.txt').read_text().split('\n\n', 1)[1]
        assert a == b == (folder / 'common-packet.txt').read_text()
        lines = (folder / 'B-tool-audit.jsonl').read_text().splitlines()
        assert len(lines) == 1
        event = json.loads(lines[0])
        recorded_hash = event.pop('event_hash')
        assert digest(event) == recorded_hash
        args = event['validated_arguments']['as_received']
        for name, value in protocol['expected_tool_arguments'].items():
            assert args[name] == value, name
        expected_company = None if folder != ROOT else False
        assert args['company_changed'] is expected_company
        captured = event['response']['result']['structuredContent']
        assert captured == service.check(args), 'Exact service replay differs'
        assert captured['check_status'] == 'unresolved'
        assert captured['reason_codes'] == ['SEALINK_EVIDENCE_MISMATCH']
    collection = json.loads((ROOT / 'defined-status-followup/collection.json').read_text())
    assert collection['graph_events_since_initial_precollection'] == 2
    print(f'PASS: {len(manifest)} artifact hashes; both frozen protocols and shared packets; two audit hashes and exact service replays.')


if __name__ == '__main__':
    main()
