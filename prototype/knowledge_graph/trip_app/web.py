"""Loopback development HTTP adapter. No public binding or hosted auth claims."""
from collections import deque
from http.cookies import SimpleCookie, CookieError
from pathlib import Path
import re
import threading
import time

from neo4j_kg.mcp_server import strict_loads
from neo4j_kg.common import encode
from neo4j_kg.service import InputError
from neo4j_kg.trip_models import FACTS_SCHEMA
from .store import Conflict, Denied

STATIC = Path(__file__).parent / 'static'
LIMIT = 65536
CSP = "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"


def fields(body, required):
    if not isinstance(body, dict) or set(body) != set(required):
        raise InputError('Unexpected or missing request fields')
    return body


class Web:
    def __init__(self, application, port=8765, clock=time.monotonic):
        self.app = application
        self.ws = application.workspace
        self.origin = f'http://127.0.0.1:{port}'
        self.host = f'127.0.0.1:{port}'
        self.clock = clock
        self.attempts = {}
        self.lock = threading.Lock()
        self.metrics = {'requests': 0, 'errors': 0}

    def throttle(self, category, limit):
        with self.lock:
            queue = self.attempts.setdefault(category, deque())
            now = self.clock()
            while queue and queue[0] <= now - 60:
                queue.popleft()
            if len(queue) >= limit:
                raise Denied('Too many requests. Wait a minute before retrying.')
            queue.append(now)

    def __call__(self, env, start_response):
        status, extra = '200 OK', []
        with self.lock:
            self.metrics['requests'] += 1
        try:
            if env.get('HTTP_HOST') != self.host or env.get('wsgi.url_scheme') != 'http':
                raise Denied('Invalid local origin')
            origin = env.get('HTTP_ORIGIN')
            if origin is not None and origin != self.origin:
                raise Denied('Invalid local origin')
            if env.get('HTTP_SEC_FETCH_SITE') in ('cross-site', 'same-site'):
                raise Denied('Invalid local origin')
            method, path = env.get('REQUEST_METHOD'), env.get('PATH_INFO', '')
            if env.get('QUERY_STRING') or method not in ('GET', 'POST'):
                raise InputError('Unsupported request')
            if method == 'GET' and path in ('/', '/app.js', '/app.css'):
                name, mime = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'), '/app.css': ('app.css', 'text/css')}[path]
                data = (STATIC / name).read_bytes()
                return self.finish(start_response, status, data, mime, extra)
            self.throttle('requests', 240)
            body = None
            if method == 'POST':
                if not path.startswith('/bridge/') and origin != self.origin:
                    raise Denied('A same-origin application request is required')
                if env.get('CONTENT_TYPE', '').split(';')[0] != 'application/json' or env.get('HTTP_TRANSFER_ENCODING'):
                    raise InputError('Use a bounded JSON request')
                length = env.get('CONTENT_LENGTH', '')
                if not length.isdigit() or not 0 < int(length) <= LIMIT:
                    raise InputError('Request is too large or missing a length')
                raw = env['wsgi.input'].read(int(length))
                if len(raw) != int(length):
                    raise InputError('Incomplete request')
                body = strict_loads(raw)
            cookie = SimpleCookie()
            cookie.load(env.get('HTTP_COOKIE', ''))
            token = cookie['trip_session'].value if 'trip_session' in cookie else ''
            csrf = env.get('HTTP_X_CSRF_TOKEN')
            if path == '/api/login' and method == 'POST':
                self.throttle('login', 10)
                fields(body, ['key'])
                token, _ = self.ws.login(body['key'])
                extra.append(('Set-Cookie', f'trip_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=43200'))
                result = self.ws.session(token)
            elif path == '/api/session' and method == 'GET':
                result = {**self.ws.session(token), 'fact_schema': FACTS_SCHEMA}
            elif path == '/api/logout' and method == 'POST':
                fields(body, [])
                self.ws.logout(token, csrf)
                extra.append(('Set-Cookie', 'trip_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'))
                result = {'ok': True}
            elif path == '/api/conversations' and method == 'GET':
                result = self.ws.conversations(token)
            elif path == '/api/conversations' and method == 'POST':
                fields(body, [])
                result = {'id': self.ws.create(token, csrf)}
            elif path == '/api/health' and method == 'GET':
                self.ws.session(token)
                with self.lock:
                    result = {'mode': 'loopback_development', 'http': 'available', **self.metrics}
            elif path.startswith('/bridge/'):
                # Proposal bearer tokens are a distinct namespace from sessions.
                authorization = env.get('HTTP_AUTHORIZATION', '')
                if not authorization.startswith('Bearer '):
                    raise Denied('Proposal access unavailable')
                cap = authorization[7:]
                if path == '/bridge/context' and method == 'GET':
                    result = {**self.ws.model_context(cap), 'fact_schema': FACTS_SCHEMA}
                elif path == '/bridge/assessment' and method == 'POST':
                    fields(body, ['message_id', 'version'])
                    result = self.app.model_assessment(cap, body['message_id'], body['version'])
                elif path == '/bridge/propose' and method == 'POST':
                    fields(body, ['message_id', 'version', 'facts'])
                    result = {'proposal_id': self.ws.model_propose(cap, body['message_id'], body['version'], body['facts']), 'confirmation': 'required_in_application'}
                else:
                    raise Denied('Proposal operation unavailable')
            else:
                match = re.fullmatch(r'/api/conversations/(conversation-[a-f0-9]{32})(?:/(message|confirm|share|capability|assessment-capability|revoke-capabilities|delete))?', path)
                if not match:
                    raise InputError('Endpoint unavailable')
                cid, action = match.groups()
                if method == 'GET' and action is None:
                    result = self.app.view(token, cid)
                elif method == 'POST' and action == 'message':
                    fields(body, ['version', 'statement', 'request_key'])
                    result = self.app.capture(token, csrf, cid, body['version'], body['statement'], body['request_key'])
                elif method == 'POST' and action == 'confirm':
                    fields(body, ['proposal_id', 'version', 'facts', 'scope'])
                    result = self.app.confirm(token, csrf, cid, body['proposal_id'], body['version'], body['facts'], body['scope'])
                elif method == 'POST' and action == 'share':
                    fields(body, ['user_id', 'permission'])
                    self.ws.share(token, csrf, cid, body['user_id'], body['permission'])
                    result = {'ok': True}
                elif method == 'POST' and action in ('capability', 'assessment-capability'):
                    fields(body, [])
                    result = {'capability': self.ws.issue_capability(token, csrf, cid, allow_assessment=action == 'assessment-capability'), 'expires_in_seconds': 3600}
                elif method == 'POST' and action == 'revoke-capabilities':
                    fields(body, [])
                    self.ws.revoke_capabilities(token, csrf, cid)
                    result = {'ok': True}
                elif method == 'POST' and action == 'delete':
                    fields(body, ['version'])
                    self.ws.delete(token, csrf, cid, body['version'])
                    result = {'ok': True}
                else:
                    raise InputError('Unsupported operation')
            data = encode(result).encode()
        except Conflict as exc:
            status, data = '409 Conflict', encode({'error': str(exc)}).encode()
        except Denied as exc:
            status, data = '403 Forbidden', encode({'error': str(exc)}).encode()
        except (InputError, ValueError, TypeError, KeyError, CookieError, UnicodeError, RecursionError):
            status, data = '400 Bad Request', encode({'error': 'Request could not be accepted. Check the supplied fields and reload if needed.'}).encode()
        except Exception:
            # Do not return exception strings containing database paths or secrets.
            status, data = '503 Service Unavailable', encode({'error': 'Service unavailable. Reload to check saved state. No earlier assessment is reused.'}).encode()
        if status != '200 OK':
            with self.lock:
                self.metrics['errors'] += 1
        return self.finish(start_response, status, data, 'application/json', extra)

    def finish(self, start, status, data, mime, extra):
        start(status, [('Content-Type', mime + '; charset=utf-8'), ('Content-Length', str(len(data))),
              ('Cache-Control', 'no-store'), ('Content-Security-Policy', CSP), ('X-Content-Type-Options', 'nosniff'),
              ('Referrer-Policy', 'no-referrer'), ('X-Frame-Options', 'DENY'), ('Cross-Origin-Resource-Policy', 'same-origin'), *extra])
        return [data]
