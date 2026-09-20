"""Private local files and verified SQLite recovery for synthetic workspaces."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat

from neo4j_kg.common import digest, encode
from neo4j_kg.service import InputError


def private_write(path, text):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w') as handle:
        handle.write(text)


def read_secret(path):
    path = Path(path)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor) as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid():
            raise InputError('Use an owner-only regular secret file')
        value = handle.read(201).strip()
        from .store import secret_hash
        secret_hash(value)
        return value


def inspect_database(path):
    try:
        return _inspect_database(path)
    except InputError:
        raise
    except (sqlite3.DatabaseError, KeyError, TypeError, ValueError):
        raise InputError('Stored database structure or audit content is invalid') from None


def _inspect_database(path):
    """Read-only physical, FK, transcript, proposal, receipt, and audit checks."""
    path = Path(path).absolute()
    if path.is_symlink() or not path.is_file():
        raise InputError('Use an existing regular workspace database')
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or db.execute('PRAGMA foreign_key_check').fetchall():
            raise InputError('Database integrity check failed')
        if [r[0] for r in db.execute('SELECT version FROM app_schema')] != [1]:
            raise InputError('Unsupported application schema')
        messages = {r['id']: dict(r) for r in db.execute('SELECT * FROM app_messages')}
        for m in messages.values():
            if hashlib.sha256(m['body'].encode()).hexdigest() != m['sha256']:
                raise InputError('Statement integrity check failed')
        for p in db.execute('SELECT * FROM app_proposals'):
            if p['bound_hash'] != digest({'message_sha256': messages[p['message_id']]['sha256'], 'facts': json.loads(p['facts_json']), 'version': p['base_version']}):
                raise InputError('Proposal integrity check failed')
        for c in db.execute('SELECT * FROM app_confirmations'):
            receipt = json.loads(c['receipt'])
            if receipt['statement_sha256'] != messages[receipt['message_id']]['sha256']:
                raise InputError('Confirmation statement binding failed')
        previous, events = None, 0
        for event in db.execute('SELECT body,hash FROM app_events ORDER BY sequence'):
            body = json.loads(event['body'])
            if body['previous_hash'] != previous or digest(body) != event['hash']:
                raise InputError('Audit chain verification failed')
            previous, events = event['hash'], events + 1
        return {'sqlite': 'ok', 'schema': 1, 'statements': len(messages), 'events': events,
                'conversations': db.execute('SELECT count(*) FROM app_conversations').fetchone()[0],
                'audit_head': previous, 'limits': 'Hashes detect inconsistency, not forgery by an actor able to rewrite the database.'}


def backup(workspace, destination):
    destination = Path(destination)
    private_write(destination, '')
    try:
        with workspace.trips._transaction() as source, sqlite3.connect(destination) as target:
            source.backup(target)
        result = inspect_database(destination)
        result['sha256'] = hashlib.sha256(destination.read_bytes()).hexdigest()
        private_write(str(destination) + '.manifest.json', encode(result) + '\n')
        return result
    except BaseException:
        destination.unlink(missing_ok=True)
        raise


def restore(source, destination):
    source, destination = Path(source), Path(destination)
    manifest = json.loads(Path(str(source) + '.manifest.json').read_text())
    if hashlib.sha256(source.read_bytes()).hexdigest() != manifest['sha256']:
        raise InputError('Backup hash does not match its manifest')
    inspect_database(source)
    private_write(destination, '')
    try:
        with sqlite3.connect(source.absolute().as_uri() + '?mode=ro', uri=True) as original, sqlite3.connect(destination) as target:
            original.backup(target)
        # Restore always invalidates previous access, sessions, and capabilities.
        from .store import Workspace
        ws = Workspace(destination)
        with ws.transaction() as db:
            for table in ('app_sessions', 'app_access', 'app_capabilities', 'app_grants'):
                db.execute('DELETE FROM ' + table)
            ws._event(db, 'local_operator', 'workspace_restored', None, {'backup_sha256': manifest['sha256']})
        return inspect_database(destination)
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
