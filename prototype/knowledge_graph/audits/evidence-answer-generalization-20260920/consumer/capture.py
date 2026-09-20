"""Local evidence bookkeeping only; no UI, model, database, or app invocation."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT.parents[2] / '.runtime'


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def logs():
    return {p.name: {'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())}
            for p in sorted(RUNTIME.glob('mcp-session-*.jsonl'))}


def main():
    command, number = sys.argv[1], int(sys.argv[2])
    data = json.loads((ROOT / 'collection.json').read_text())
    run = data['runs'][number - 1]
    prefix = run['run_id']
    if command == 'begin':
        run.update(status='submitting', submitted_at_utc=now(),
                   actual_model='Sonnet 5 Medium', actual_context='fresh_incognito_chat',
                   prompt_hash_verified=True, submitted_text_verified=True,
                   prompt_ui_normalization='Original trailing newline may be trimmed by chat submission; wording unchanged.')
        run['attempts'] = [{'attempt': 1, 'status': 'in_progress'}]
        save(ROOT / 'attempts' / (prefix + '.start.json'), {'time': now(), 'logs': logs()})
    elif command == 'finish':
        answer = (ROOT / 'capture-buffer.txt').read_bytes()
        if len(answer) < 100:
            raise ValueError('Capture too short; inspect UI first')
        for other in data['runs']:
            if other.get('response_sha256') == sha(answer):
                raise ValueError('Duplicate capture; inspect whether buffer was saved')
        dest = ROOT / 'responses' / (prefix + '.txt')
        if dest.exists():
            raise ValueError('Do not overwrite an existing capture')
        dest.write_bytes(answer)
        start_path = ROOT / 'attempts' / (prefix + '.start.json')
        start = json.loads((start_path if start_path.exists() else ROOT / 'audit-baseline.json').read_text())['logs']
        records = []
        for path in sorted(RUNTIME.glob('mcp-session-*.jsonl')):
            old = start.get(path.name, {}).get('bytes', 0)
            raw = path.read_bytes()
            if len(raw) == old:
                continue
            if len(raw) < old:
                raise ValueError('Audit shrank: ' + path.name)
            old_hash = start.get(path.name, {}).get('sha256')
            if old_hash and sha(raw[:old]) != old_hash:
                raise ValueError('Audit prefix changed: ' + path.name)
            added = raw[old:]
            events = [json.loads(line) for line in added.splitlines() if line.strip()]
            record_path = ROOT / 'audits' / (prefix + '__' + path.name)
            record_path.write_bytes(added)
            snapshot_path = ROOT / 'audits' / ('snapshot__' + prefix + '__' + path.name)
            snapshot_path.write_bytes(raw)
            records.append({'path': str(record_path.relative_to(ROOT)),
                            'snapshot_path': str(snapshot_path.relative_to(ROOT)),
                            'source_session': path.name, 'start_offset': old,
                            'end_offset': len(raw), 'sha256': sha(added),
                            'event_count': len(events),
                            'methods': [e.get('method') for e in events]})
        run.update(status='captured', captured_at_utc=now(),
                   response_path=str(dest.relative_to(ROOT)), response_sha256=sha(answer),
                   complete_response_observed=True,
                   extraction_method='product_native_Copy_to_plain_text_TextEdit_UTF8_save',
                   conversation_reference='claude.ai/new?incognito= (ephemeral)',
                   tool_event_paths=[r['path'] for r in records],
                   tool_call_count=sum(r['event_count'] for r in records))
        run['attempts'][0]['status'] = 'complete'
        save(ROOT / 'attempts' / (prefix + '.capture.json'),
             {'captured_at_utc': now(), 'response_sha256': sha(answer),
              'response_bytes': len(answer), 'audit_records': records,
              'note': 'Events are time-window candidates; validate prompt/session attribution before scoring.'})
        print(json.dumps({'run': number, 'bytes': len(answer), 'events': run['tool_call_count'],
                          'methods': [m for r in records for m in r['methods']]}))
    else:
        raise ValueError('Use begin or finish')
    save(ROOT / 'collection.json', data)


if __name__ == '__main__':
    main()
