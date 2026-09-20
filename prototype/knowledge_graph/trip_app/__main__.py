"""Local synthetic trip workspace operations; no public hosting."""
import argparse
import json
from pathlib import Path
import socketserver
import threading
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler, make_server

from neo4j_kg.config import connect
from neo4j_kg.store import Neo4jStore
from .store import Workspace
from .service import Application
from .web import Web
from .operations import private_write, backup, restore, inspect_database

ROOT = Path(__file__).resolve().parents[1]


class LocalServer(socketserver.ThreadingMixIn, WSGIServer):
    daemon_threads = True
    request_queue_size = 8
    slots = threading.BoundedSemaphore(8)

    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.slots.release()


class QuietHandler(WSGIRequestHandler):
    def setup(self):
        self.request.settimeout(15)
        super().setup()

    def log_message(self, *args):
        pass  # Request URLs, cookies and bodies never enter access logs.

    def get_environ(self):
        env = super().get_environ()
        env['wsgi.multithread'] = True
        return env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=ROOT / '.runtime/app.sqlite3')
    commands = parser.add_subparsers(dest='command', required=True)
    provision = commands.add_parser('provision')
    provision.add_argument('--user', required=True)
    provision.add_argument('--organization', required=True)
    provision.add_argument('--role', choices=('driver','dispatcher','unknown'), default='unknown')
    provision.add_argument('--key-file', required=True, type=Path)
    access = commands.add_parser('issue-access')
    access.add_argument('--user', required=True)
    access.add_argument('--key-file', required=True, type=Path)
    revoke = commands.add_parser('revoke-user')
    revoke.add_argument('--user', required=True)
    commands.add_parser('check')
    b = commands.add_parser('backup'); b.add_argument('--output', required=True, type=Path)
    r = commands.add_parser('restore'); r.add_argument('--source', required=True, type=Path)
    server = commands.add_parser('serve')
    server.add_argument('--port', type=int, default=8765)
    server.add_argument('--credentials-file', type=Path, required=True)
    server.add_argument('--revision', required=True)
    args = parser.parse_args()
    driver = None
    try:
        if args.command == 'restore':
            print(json.dumps(restore(args.source, args.database), indent=2)); return
        if args.command == 'check':
            print(json.dumps(inspect_database(args.database), indent=2)); return
        if args.command in ('provision','issue-access') and args.key_file.exists():
            parser.error('Use a new private key file; existing files are never overwritten')
        if args.command not in ('provision','serve') and not args.database.is_file():
            parser.error('Workspace database does not exist')
        ws = Workspace(args.database)
        if args.command in ('provision','issue-access'):
            key = ws.provision(args.user, args.organization, args.role) if args.command == 'provision' else ws.issue_access(args.user)
            private_write(args.key_file, key + '\n')
            print('Temporary access key saved to ' + str(args.key_file))
        elif args.command == 'revoke-user':
            ws.revoke_user(args.user); print('Synthetic user access revoked.')
        elif args.command == 'backup':
            print(json.dumps(backup(ws, args.output), indent=2))
        elif args.command == 'serve':
            if not 1024 <= args.port <= 65535:
                parser.error('Use an unprivileged local port')
            driver, database = connect(args.credentials_file)
            graph = Neo4jStore(driver, database, args.revision)
            web = Web(Application(ws, graph), args.port)
            with make_server('127.0.0.1', args.port, web, LocalServer, QuietHandler) as http:
                print(f'Local synthetic workspace: http://127.0.0.1:{args.port}', flush=True)
                print('Development identity and HTTP server. No operational clearance or public hosting.', flush=True)
                http.serve_forever()
    except KeyboardInterrupt:
        pass
    except Exception:
        parser.exit(1, 'Workspace operation failed. Check private paths, schema, access and Neo4j configuration. No secrets are logged.\n')
    finally:
        if driver is not None:
            driver.close()


if __name__ == '__main__':
    main()
