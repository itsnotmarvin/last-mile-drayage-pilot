"""Application identities, immutable statements, proposals, and confirmed cases.

All state changes and underlying trip revisions share one SQLite transaction.
Application access keys and proposal capabilities are distinct, expiring secrets.
This is a local development identity adapter, not production identity federation.
"""
from contextlib import contextmanager
import hashlib
import hmac
import json
import re
import secrets
import sqlite3
from pathlib import Path
import time

from neo4j_kg.common import digest, encode
from neo4j_kg.input_review import consistency_issues
from neo4j_kg.service import InputError
from neo4j_kg.trip_models import normalize_facts
from neo4j_kg.trip_state import TripStore, INVALIDATION_RULES


class Denied(InputError):
    pass


class Conflict(InputError):
    pass


def secret_hash(secret):
    if not isinstance(secret, str) or not 20 <= len(secret) <= 200:
        raise Denied('Access unavailable')
    return hashlib.sha256(secret.encode()).hexdigest()


def identifier(prefix):
    return prefix + secrets.token_hex(16)


def fact_order(fields):
    pending, result = set(fields), []
    while pending:
        ready = sorted(f for f in pending if not any(f in INVALIDATION_RULES.get(parent, ()) for parent in pending))
        if not ready:
            raise InputError('Cyclic assignment dependencies')
        result.extend(ready)
        pending.difference_update(ready)
    return result


class Workspace:
    def __init__(self, path, clock=time.time):
        self.clock = clock
        target = Path(path).expanduser().absolute()
        if target.exists():
            if target.is_symlink():
                raise InputError('Application database must not be a symbolic link')
            with sqlite3.connect(target.as_uri() + '?mode=ro', uri=True) as existing:
                tables = {r[0] for r in existing.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if tables and 'app_schema' not in tables:
                    raise InputError('Use a separate application database, not the existing MCP trip database')
                if 'app_schema' in tables and existing.execute('SELECT version FROM app_schema').fetchall() != [(1,)]:
                    raise InputError('Unsupported application schema version')
        self.trips = TripStore(path)
        with self.transaction() as db:
            for statement in SCHEMA:
                db.execute(statement)

    @contextmanager
    def transaction(self):
        with self.trips._transaction(write=True) as db:
            yield db

    def provision(self, user_id, company_id, role='unknown'):
        if not re.fullmatch(r'syn-user-[a-z0-9-]{1,40}', user_id) or not re.fullmatch(r'syn-org-[a-z0-9-]{1,40}', company_id):
            raise InputError('Use synthetic user and organization aliases')
        if role not in ('driver', 'dispatcher', 'unknown'):
            raise InputError('Unsupported role')
        with self.transaction() as db:
            db.execute('INSERT INTO app_users VALUES (?,?,?,1)', (user_id, company_id, role))
            self._event(db, user_id, 'user_provisioned', None, {'role': role})
        return self.issue_access(user_id)

    def issue_access(self, user_id):
        token = secrets.token_urlsafe(32)
        with self.transaction() as db:
            self._user(db, user_id)
            db.execute('INSERT INTO app_access VALUES (?,?,?)', (secret_hash(token), user_id, self.clock() + 86400))
        return token

    def login(self, key):
        with self.transaction() as db:
            row = db.execute('SELECT user_id FROM app_access WHERE hash=? AND expires>?', (secret_hash(key), self.clock())).fetchone()
            if row is None:
                raise Denied('Access unavailable')
            user = self._user(db, row['user_id'])
            token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            db.execute('INSERT INTO app_sessions VALUES (?,?,?,?)', (secret_hash(token), user['user_id'], csrf, self.clock() + 43200))
            self._event(db, user['user_id'], 'session_started', None, {})
            return token, csrf

    def _session(self, db, token, csrf=None):
        row = db.execute('SELECT * FROM app_sessions WHERE hash=? AND expires>?', (secret_hash(token), self.clock())).fetchone()
        if row is None or (csrf is not None and (not isinstance(csrf, str) or not hmac.compare_digest(row['csrf'], csrf))):
            raise Denied('Access unavailable')
        return self._user(db, row['user_id']), row['csrf']

    def _write_session(self, db, token, csrf):
        if not isinstance(csrf, str) or not csrf:
            raise Denied('Access unavailable')
        return self._session(db, token, csrf)

    def session(self, token, csrf=None):
        with self.transaction() as db:
            user, stored_csrf = self._session(db, token, csrf)
            return {**user, 'csrf': stored_csrf}

    def logout(self, token, csrf):
        with self.transaction() as db:
            self._write_session(db, token, csrf)
            db.execute('DELETE FROM app_sessions WHERE hash=?', (secret_hash(token),))

    def revoke_user(self, user_id):
        with self.transaction() as db:
            self._user(db, user_id)
            db.execute('UPDATE app_users SET active=0 WHERE user_id=?', (user_id,))
            db.execute('DELETE FROM app_sessions WHERE user_id=?', (user_id,))
            db.execute('DELETE FROM app_access WHERE user_id=?', (user_id,))
            db.execute('DELETE FROM app_capabilities WHERE user_id=?', (user_id,))
            self._event(db, user_id, 'user_revoked', None, {})

    def _user(self, db, user_id):
        row = db.execute('SELECT * FROM app_users WHERE user_id=? AND active=1', (user_id,)).fetchone()
        if row is None:
            raise Denied('Access unavailable')
        return dict(row)

    def _access(self, db, user, conversation_id, write=False, owner=False):
        row = db.execute('SELECT * FROM app_conversations WHERE id=?', (conversation_id,)).fetchone()
        if row is None or row['company_id'] != user['company_id']:
            raise Denied('Conversation unavailable')
        if row['owner'] != user['user_id']:
            grant = db.execute('SELECT permission FROM app_grants WHERE conversation_id=? AND user_id=?', (conversation_id, user['user_id'])).fetchone()
            if owner or grant is None or (write and grant['permission'] != 'edit'):
                raise Denied('Conversation unavailable')
        return dict(row)

    def conversations(self, token):
        with self.transaction() as db:
            user, _ = self._session(db, token)
            return [dict(r) for r in db.execute('SELECT DISTINCT c.* FROM app_conversations c LEFT JOIN app_grants g ON g.conversation_id=c.id WHERE c.company_id=? AND (c.owner=? OR g.user_id=?) ORDER BY c.created DESC', (user['company_id'], user['user_id'], user['user_id']))]

    def create(self, token, csrf):
        with self.transaction() as db:
            user, _ = self._write_session(db, token, csrf)
            cid = identifier('conversation-')
            db.execute('INSERT INTO app_conversations VALUES (?,?,?,?,0,NULL,NULL,?)', (cid, user['user_id'], user['company_id'], 'New trip', self.clock()))
            self._event(db, user['user_id'], 'conversation_created', cid, {})
            return cid

    def share(self, token, csrf, cid, target, permission):
        if permission not in ('view', 'edit', 'remove'):
            raise InputError('Unsupported sharing permission')
        with self.transaction() as db:
            user, _ = self._write_session(db, token, csrf)
            conversation = self._access(db, user, cid, owner=True)
            recipient = self._user(db, target)
            if recipient['company_id'] != user['company_id'] or target == conversation['owner']:
                raise Denied('Sharing unavailable')
            db.execute('DELETE FROM app_grants WHERE conversation_id=? AND user_id=?', (cid, target))
            # Downgrading access also revokes capabilities issued to the recipient.
            db.execute('DELETE FROM app_capabilities WHERE conversation_id=? AND user_id=?', (cid, target))
            if permission != 'remove':
                db.execute('INSERT INTO app_grants VALUES (?,?,?)', (cid, target, permission))
            self._event(db, user['user_id'], 'sharing_changed', cid, {'target': target, 'permission': permission})

    def message(self, token, csrf, cid, version, text, request_key):
        if not isinstance(text, str) or not text.strip() or len(text) > 8000 or '\x00' in text:
            raise InputError('Enter a statement of 1–8000 characters')
        if not isinstance(request_key, str) or not 1 <= len(request_key) <= 120:
            raise InputError('Missing request key')
        with self.transaction() as db:
            user, _ = self._write_session(db, token, csrf)
            conversation = self._access(db, user, cid, write=True)
            fingerprint = digest({'conversation': cid, 'version': version, 'text': text})
            previous = db.execute('SELECT * FROM app_message_requests WHERE user_id=? AND request_key=?', (user['user_id'], request_key)).fetchone()
            if previous:
                if previous['fingerprint'] != fingerprint:
                    raise Conflict('Request key already used for different text')
                return previous['message_id']
            self._version(conversation, version)
            mid = identifier('message-')
            db.execute('INSERT INTO app_messages VALUES (?,?,?,?,?,?,?)', (mid, cid, user['user_id'], text, hashlib.sha256(text.encode()).hexdigest(), version + 1, self.clock()))
            db.execute('UPDATE app_conversations SET version=version+1,title=? WHERE id=?', (text[:80], cid))
            db.execute('INSERT INTO app_message_requests VALUES (?,?,?,?)', (user['user_id'], request_key, fingerprint, mid))
            self._event(db, user['user_id'], 'statement_captured', cid, {'message_id': mid, 'text_hash': hashlib.sha256(text.encode()).hexdigest()})
            return mid

    @staticmethod
    def _version(conversation, version):
        if type(version) is not int or conversation['version'] != version:
            raise Conflict('The conversation changed. Reload before continuing.')

    def _latest_message(self, db, cid):
        row = db.execute('SELECT * FROM app_messages WHERE conversation_id=? ORDER BY version DESC LIMIT 1', (cid,)).fetchone()
        if row is None:
            raise InputError('Add a statement first')
        message = dict(row)
        if hashlib.sha256(message['body'].encode()).hexdigest() != message['sha256']:
            raise Conflict('Stored statement integrity check failed')
        return message

    def _propose(self, db, user, cid, mid, version, facts, origin):
        conversation = self._access(db, user, cid, write=True)
        self._version(conversation, version)
        message = self._latest_message(db, cid)
        if mid != message['id']:
            raise Conflict('Proposals must use the current captured statement')
        records = normalize_facts(facts, user['role'], 'Unconfirmed extraction proposal; shape validation only.')
        for record in records.values():
            record['source_text'] = message['body']
        issues = consistency_issues(records)
        pid = identifier('proposal-')
        bound_hash = digest({'message_sha256': message['sha256'], 'facts': facts, 'version': version})
        db.execute('INSERT INTO app_proposals VALUES (?,?,?,?,?,?,?,?,?)', (pid, cid, mid, version, encode(facts), bound_hash, origin, encode(issues), self.clock()))
        self._event(db, user['user_id'], 'facts_proposed', cid, {'proposal_id': pid, 'bound_hash': bound_hash, 'origin': origin})
        return pid

    def propose_local(self, token, csrf, cid, mid, version, facts):
        with self.transaction() as db:
            user, _ = self._write_session(db, token, csrf)
            return self._propose(db, user, cid, mid, version, facts, 'bounded_local_extraction')

    def issue_capability(self, token, csrf, cid, allow_assessment=False):
        if type(allow_assessment) is not bool:
            raise InputError('Assessment access must be explicit')
        capability = secrets.token_urlsafe(32)
        with self.transaction() as db:
            user, _ = self._write_session(db, token, csrf)
            self._access(db, user, cid, write=True)
            db.execute('INSERT INTO app_capabilities VALUES (?,?,?,?)', (secret_hash(capability), user['user_id'], cid, self.clock() + 3600))
            if allow_assessment:
                db.execute('INSERT INTO app_capability_scopes VALUES (?,?)', (secret_hash(capability), 'confirmed_assessment'))
            self._event(db, user['user_id'], 'proposal_access_issued', cid, {'confirmed_assessment': allow_assessment})
        return capability

    def revoke_capabilities(self, token, csrf, cid):
        with self.transaction() as db:
            user, _ = self._write_session(db, token, csrf)
            self._access(db, user, cid, owner=True)
            db.execute('DELETE FROM app_capabilities WHERE conversation_id=?', (cid,))
            self._event(db, user['user_id'], 'proposal_access_revoked', cid, {})

    def _capability(self, db, capability):
        row = db.execute('SELECT * FROM app_capabilities WHERE hash=? AND expires>?', (secret_hash(capability), self.clock())).fetchone()
        if row is None:
            raise Denied('Proposal access unavailable')
        user = self._user(db, row['user_id'])
        conversation = self._access(db, user, row['conversation_id'], write=True)
        return user, conversation

    def model_context(self, capability):
        with self.transaction() as db:
            _, conversation = self._capability(db, capability)
            message = self._latest_message(db, conversation['id'])
            return {'message_id': message['id'], 'statement': message['body'], 'statement_sha256': message['sha256'],
                    'conversation_version': conversation['version'], 'mode': 'synthetic_development',
                    'confirmation_state': 'confirmed_report' if conversation['confirmed_message_id'] == message['id'] else 'review_required',
                    'assessment_access': db.execute('SELECT 1 FROM app_capability_scopes WHERE capability_hash=? AND scope=?', (secret_hash(capability), 'confirmed_assessment')).fetchone() is not None,
                    'instruction': 'Propose only facts supported by this captured statement. Confirmation belongs to the application user. Refresh get_statement after user confirmation before reading its assessment.'}

    def model_assessment_context(self, capability, mid, version):
        """Capability-owned snapshot; callers cannot select another conversation/trip."""
        with self.transaction() as db:
            _, conversation = self._capability(db, capability)
            if db.execute('SELECT 1 FROM app_capability_scopes WHERE capability_hash=? AND scope=?',
                          (secret_hash(capability), 'confirmed_assessment')).fetchone() is None:
                raise Denied('Confirmed assessment access not granted')
            self._version(conversation, version)
            latest = self._latest_message(db, conversation['id'])
            if latest['id'] != mid or conversation['confirmed_message_id'] != mid or not conversation['trip_id']:
                raise Conflict('Review and confirm the latest statement in the application first')
            messages = [dict(r) for r in db.execute('SELECT * FROM app_messages WHERE conversation_id=? ORDER BY version', (conversation['id'],))]
            for message in messages:
                if hashlib.sha256(message['body'].encode()).hexdigest() != message['sha256']:
                    raise Conflict('Stored statement integrity check failed')
            row = db.execute('SELECT receipt FROM app_confirmations WHERE conversation_id=? ORDER BY rowid DESC LIMIT 1', (conversation['id'],)).fetchone()
            case = self.trips.get(conversation['trip_id'], _connection=db)
            receipt = json.loads(row['receipt']) if row else {}
            expected = {'message_id':mid, 'statement_sha256':latest['sha256'],
                        'trip_id':case['trip_id'], 'trip_revision':case['revision'],
                        'conversation_version':version, 'verification_status':'reported_facts_only'}
            if any(receipt.get(k) != v for k, v in expected.items()):
                raise Conflict('Confirmation no longer matches this trip')
            return {'conversation_id':conversation['id'], 'conversation_version':version,
                    'case':case, 'confirmation':receipt, 'statements':messages}

    def model_propose(self, capability, mid, version, facts):
        with self.transaction() as db:
            user, conversation = self._capability(db, capability)
            return self._propose(db, user, conversation['id'], mid, version, facts, 'model_proposal')

    def confirm(self, token, csrf, cid, pid, version, facts, scope='trip_dispatch'):
        if scope not in ('unknown', 'trip_dispatch', 'route', 'terminal_entry', 'induction'):
            raise InputError('Unsupported assessment scope')
        # This text is constructed from an explicit application's user action,
        # never accepted from the model. The original message remains immutable.
        statement = 'Application user confirmed these reported facts: ' + encode(facts)
        normalize_facts(facts, 'unknown', statement)
        submitted_hash = digest({'proposal_id': pid, 'facts': facts, 'scope': scope, 'version': version})
        with self.transaction() as db:
            user, _ = self._write_session(db, token, csrf)
            conversation = self._access(db, user, cid, write=True)
            previous = db.execute('SELECT * FROM app_confirmations WHERE proposal_id=?', (pid,)).fetchone()
            if previous:
                if previous['user_id'] != user['user_id'] or previous['submitted_hash'] != submitted_hash or previous['conversation_id'] != cid:
                    raise Conflict('This proposal was already confirmed differently')
                return json.loads(previous['receipt'])
            self._version(conversation, version)
            proposal = db.execute('SELECT * FROM app_proposals WHERE id=? AND conversation_id=?', (pid, cid)).fetchone()
            latest = self._latest_message(db, cid)
            if proposal is None or proposal['base_version'] != version or proposal['message_id'] != latest['id']:
                raise Conflict('The proposal is no longer current')
            expected_hash = digest({'message_sha256': latest['sha256'], 'facts': json.loads(proposal['facts_json']), 'version': version})
            if proposal['bound_hash'] != expected_hash:
                raise Conflict('Stored proposal integrity check failed')
            if conversation['trip_id'] is None:
                case = self.trips.create(user['role'], scope, facts, statement, pid, _connection=db)
            else:
                case = self.trips.get(conversation['trip_id'], _connection=db)
                # Preserve the existing one-independent-correction contract;
                # apply all explicitly confirmed edits atomically in dependency order.
                for field in fact_order(facts):
                    case = self.trips.update(case['trip_id'], case['revision'], user['role'], scope,
                                             {field: facts[field]}, statement, pid + ':' + field,
                                             replace_conflicts=True, _connection=db)
                if not facts:
                    case = self.trips.update(case['trip_id'], case['revision'], user['role'], scope, {}, statement,
                                             pid + ':scope', _connection=db)
            receipt = {'confirmation_id': identifier('confirmation-'), 'proposal_id': pid,
                       'message_id': latest['id'], 'statement_sha256': latest['sha256'],
                       'confirmed_facts_sha256': digest(facts), 'confirmed_by': user['user_id'],
                       'confirmed_at': self.clock(), 'trip_id': case['trip_id'], 'trip_revision': case['revision'],
                       'conversation_version': version + 1, 'verification_status': 'reported_facts_only'}
            db.execute('INSERT INTO app_confirmations VALUES (?,?,?,?,?)', (pid, cid, user['user_id'], submitted_hash, encode(receipt)))
            db.execute('UPDATE app_conversations SET version=version+1,trip_id=?,confirmed_message_id=? WHERE id=?', (case['trip_id'], latest['id'], cid))
            self._event(db, user['user_id'], 'facts_confirmed', cid, receipt)
            return receipt

    def view(self, token, cid):
        with self.transaction() as db:
            user, _ = self._session(db, token)
            conversation = self._access(db, user, cid)
            messages = [dict(r) for r in db.execute('SELECT * FROM app_messages WHERE conversation_id=? ORDER BY version', (cid,))]
            proposals = []
            for row in db.execute('SELECT * FROM app_proposals WHERE conversation_id=? AND base_version=? ORDER BY created DESC', (cid, conversation['version'])):
                item = dict(row)
                item['facts'] = json.loads(item.pop('facts_json'))
                item['issues'] = json.loads(item.pop('issues_json'))
                proposals.append(item)
            for message in messages:
                if hashlib.sha256(message['body'].encode()).hexdigest() != message['sha256']:
                    raise Conflict('Stored statement integrity check failed')
            ready = bool(messages and conversation['confirmed_message_id'] == messages[-1]['id'] and conversation['trip_id'])
            saved_case = self.trips.get(conversation['trip_id'], _connection=db) if conversation['trip_id'] else None
            case = saved_case if ready else None
            receipt_row = db.execute('SELECT receipt FROM app_confirmations WHERE conversation_id=? ORDER BY rowid DESC LIMIT 1', (cid,)).fetchone()
            can_edit = conversation['owner'] == user['user_id'] or db.execute('SELECT 1 FROM app_grants WHERE conversation_id=? AND user_id=? AND permission=?', (cid, user['user_id'], 'edit')).fetchone() is not None
            return {'conversation': conversation, 'messages': messages, 'proposals': proposals, 'case': case,
                    'confirmation': json.loads(receipt_row['receipt']) if receipt_row else None,
                    'prior_reported_facts': saved_case['facts'] if saved_case and not ready else {},
                    'prior_scope': saved_case['question_scope'] if saved_case else None,
                    'ready_for_assessment': ready, 'can_edit': can_edit, 'is_owner': conversation['owner'] == user['user_id']}

    def delete(self, token, csrf, cid, version):
        """Owner-requested purge; hash-only audit events and older backups remain."""
        with self.transaction() as db:
            user, _ = self._write_session(db, token, csrf)
            conversation = self._access(db, user, cid, owner=True)
            self._version(conversation, version)
            db.execute('DELETE FROM app_message_requests WHERE message_id IN (SELECT id FROM app_messages WHERE conversation_id=?)', (cid,))
            for table in ('app_confirmations', 'app_proposals', 'app_messages', 'app_grants', 'app_capabilities'):
                db.execute('DELETE FROM ' + table + ' WHERE conversation_id=?', (cid,))
            db.execute('DELETE FROM app_conversations WHERE id=?', (cid,))
            if conversation['trip_id']:
                # Core request snapshots are private case data too.
                for row in db.execute('SELECT request_key,snapshot_json FROM requests').fetchall():
                    if json.loads(row['snapshot_json'])['trip_id'] == conversation['trip_id']:
                        db.execute('DELETE FROM requests WHERE request_key=?', (row['request_key'],))
                db.execute('DELETE FROM trips WHERE trip_id=?', (conversation['trip_id'],))
            self._event(db, user['user_id'], 'conversation_purged', cid, {})

    def assert_current(self, token, cid, version):
        with self.transaction() as db:
            user, _ = self._session(db, token)
            self._version(self._access(db, user, cid), version)

    def _event(self, db, actor, action, cid, details):
        previous = db.execute('SELECT hash FROM app_events ORDER BY sequence DESC LIMIT 1').fetchone()
        event = {'actor': actor, 'action': action, 'conversation_id': cid, 'details': details,
                 'at': self.clock(), 'previous_hash': previous['hash'] if previous else None}
        db.execute('INSERT INTO app_events(body,hash) VALUES (?,?)', (encode(event), digest(event)))


SCHEMA = (
    'CREATE TABLE IF NOT EXISTS app_schema(version INTEGER PRIMARY KEY CHECK(version=1))',
    'INSERT OR IGNORE INTO app_schema VALUES(1)',
    'CREATE TABLE IF NOT EXISTS app_users(user_id TEXT PRIMARY KEY,company_id TEXT NOT NULL,role TEXT NOT NULL,active INTEGER NOT NULL)',
    'CREATE TABLE IF NOT EXISTS app_access(hash TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES app_users(user_id),expires REAL NOT NULL)',
    'CREATE TABLE IF NOT EXISTS app_sessions(hash TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES app_users(user_id),csrf TEXT NOT NULL,expires REAL NOT NULL)',
    'CREATE TABLE IF NOT EXISTS app_conversations(id TEXT PRIMARY KEY,owner TEXT NOT NULL REFERENCES app_users(user_id),company_id TEXT NOT NULL,title TEXT NOT NULL,version INTEGER NOT NULL,trip_id TEXT REFERENCES trips(trip_id),confirmed_message_id TEXT,created REAL NOT NULL)',
    'CREATE TABLE IF NOT EXISTS app_grants(conversation_id TEXT REFERENCES app_conversations(id),user_id TEXT REFERENCES app_users(user_id),permission TEXT NOT NULL,PRIMARY KEY(conversation_id,user_id))',
    'CREATE TABLE IF NOT EXISTS app_messages(id TEXT PRIMARY KEY,conversation_id TEXT NOT NULL REFERENCES app_conversations(id),author TEXT NOT NULL REFERENCES app_users(user_id),body TEXT NOT NULL,sha256 TEXT NOT NULL,version INTEGER NOT NULL,created REAL NOT NULL)',
    'CREATE TABLE IF NOT EXISTS app_message_requests(user_id TEXT REFERENCES app_users(user_id),request_key TEXT,fingerprint TEXT NOT NULL,message_id TEXT REFERENCES app_messages(id),PRIMARY KEY(user_id,request_key))',
    'CREATE TABLE IF NOT EXISTS app_proposals(id TEXT PRIMARY KEY,conversation_id TEXT NOT NULL REFERENCES app_conversations(id),message_id TEXT NOT NULL REFERENCES app_messages(id),base_version INTEGER NOT NULL,facts_json TEXT NOT NULL,bound_hash TEXT NOT NULL,origin TEXT NOT NULL,issues_json TEXT NOT NULL,created REAL NOT NULL)',
    'CREATE TABLE IF NOT EXISTS app_confirmations(proposal_id TEXT PRIMARY KEY REFERENCES app_proposals(id),conversation_id TEXT NOT NULL REFERENCES app_conversations(id),user_id TEXT NOT NULL REFERENCES app_users(user_id),submitted_hash TEXT NOT NULL,receipt TEXT NOT NULL)',
    'CREATE TABLE IF NOT EXISTS app_capabilities(hash TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES app_users(user_id),conversation_id TEXT NOT NULL REFERENCES app_conversations(id),expires REAL NOT NULL)',
    "CREATE TABLE IF NOT EXISTS app_capability_scopes(capability_hash TEXT NOT NULL REFERENCES app_capabilities(hash) ON DELETE CASCADE,scope TEXT NOT NULL CHECK(scope='confirmed_assessment'),PRIMARY KEY(capability_hash,scope))",
    'CREATE TABLE IF NOT EXISTS app_events(sequence INTEGER PRIMARY KEY AUTOINCREMENT,body TEXT NOT NULL,hash TEXT NOT NULL)',
    "CREATE TRIGGER IF NOT EXISTS app_messages_immutable BEFORE UPDATE ON app_messages BEGIN SELECT RAISE(ABORT, 'Original statements are immutable'); END",
    "CREATE TRIGGER IF NOT EXISTS app_proposals_immutable BEFORE UPDATE ON app_proposals BEGIN SELECT RAISE(ABORT, 'Proposals are immutable'); END",
    "CREATE TRIGGER IF NOT EXISTS app_confirmations_immutable BEFORE UPDATE ON app_confirmations BEGIN SELECT RAISE(ABORT, 'Confirmations are immutable'); END",
    'CREATE INDEX IF NOT EXISTS app_messages_by_conversation ON app_messages(conversation_id,version)',
    'CREATE INDEX IF NOT EXISTS app_proposals_by_conversation ON app_proposals(conversation_id,base_version)',
)
