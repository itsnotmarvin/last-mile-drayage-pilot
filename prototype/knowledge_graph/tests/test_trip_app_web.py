"""HTTP and stdio tests exercise actual authorization boundaries, not model prose."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from wsgiref.simple_server import make_server

from neo4j_kg.common import EvidenceUnavailable
from neo4j_kg.service import InputError
from neo4j_kg.trip_state import TripStore
from trip_app.mcp_server import Client, Session
from trip_app.operations import backup, restore, inspect_database, read_secret, private_write
from trip_app.service import Application
from trip_app.store import Workspace, Denied
from trip_app.web import Web
import test_trip_app as fixtures


class OfflineGraph:
    def read(self, fn):
        raise EvidenceUnavailable('sensitive database details')


class HttpTests(unittest.TestCase):
    proposal = fixtures.WorkspaceTests.proposal

    def setUp(self):
        fixtures.WorkspaceTests.setUp(self)
        self.web = Web(Application(self.ws, OfflineGraph()))

    def request(self, path, body=None, token=None, csrf=None, **extra):
        raw = json.dumps(body).encode() if body is not None else b''
        env = {'HTTP_HOST':'127.0.0.1:8765','wsgi.url_scheme':'http','REQUEST_METHOD':'POST' if body is not None else 'GET',
               'PATH_INFO':path,'QUERY_STRING':'','HTTP_ORIGIN':'http://127.0.0.1:8765','CONTENT_TYPE':'application/json',
               'CONTENT_LENGTH':str(len(raw)),'wsgi.input':io.BytesIO(raw),'HTTP_COOKIE':'trip_session=' + (token or self.token),
               'HTTP_X_CSRF_TOKEN':csrf if csrf is not None else self.csrf, **extra}
        headers = {}
        def start(status, items):
            headers['status'] = status
            headers.update(items)
        data = b''.join(self.web(env, start))
        return headers, json.loads(data) if 'application/json' in headers['Content-Type'] else data

    def test_session_cookie_security_and_headers(self):
        key = self.ws.issue_access('syn-user-driver')
        h, body = self.request('/api/login', {'key':key})
        self.assertEqual('200 OK',h['status'])
        for flag in ('HttpOnly','SameSite=Strict','Max-Age=43200'):
            self.assertIn(flag,h['Set-Cookie'])
        self.assertEqual('no-store', h['Cache-Control'])
        self.assertIn("frame-ancestors 'none'", h['Content-Security-Policy'])
        self.assertEqual('syn-user-driver', body['user_id'])
        self.assertNotIn(key,json.dumps(body))
        _, schema = self.request('/api/session')
        self.assertIn('height',schema['fact_schema']['properties'])

    def test_csrf_origin_host_and_content_type_rejections_do_not_write(self):
        cases = [{'HTTP_X_CSRF_TOKEN':None},{'HTTP_ORIGIN':None},{'HTTP_ORIGIN':'https://evil.example'},
                 {'HTTP_HOST':'evil.example:8765'},{'HTTP_SEC_FETCH_SITE':'cross-site'},{'CONTENT_TYPE':'text/plain'},
                 {'CONTENT_LENGTH':'9999999'},{'HTTP_TRANSFER_ENCODING':'chunked'},{'QUERY_STRING':'token=secret'}]
        for extra in cases:
            with self.subTest(extra=extra):
                h,_ = self.request('/api/conversations',{},**extra)
                self.assertNotEqual('200 OK',h['status'])
        self.assertEqual(1,len(self.ws.conversations(self.token)))

    def test_duplicate_json_nonfinite_and_unknown_fields_rejected(self):
        for raw in (b'{"key":"x","key":"y"}',b'{"key":NaN}'):
            h,_ = self.request('/api/login',{},**{'wsgi.input':io.BytesIO(raw),'CONTENT_LENGTH':str(len(raw))})
            self.assertEqual('400 Bad Request',h['status'])
        h,_=self.request('/api/conversations',{'role':'dispatcher'})
        self.assertEqual('400 Bad Request',h['status'])

    def test_http_confirmed_outage_and_stale_conflict(self):
        base='/api/conversations/'+self.cid
        h,v=self.request(base+'/message',{'version':0,'statement':'14 ft 7 in high','request_key':'http'})
        self.assertEqual('200 OK',h['status']); self.assertIsNone(v['assessment'])
        pid=v['proposals'][0]['id']
        h,v=self.request(base+'/confirm',{'proposal_id':pid,'version':1,'facts':{'height':{'value':175,'unit':'in'}},'scope':'trip_dispatch'})
        self.assertEqual('unavailable',v['assessment_state'])
        self.assertEqual([],v['assessment']['findings'])
        self.assertNotIn('sensitive',json.dumps(v))
        h,v=self.request(base+'/message',{'version':0,'statement':'Different move','request_key':'different'})
        self.assertEqual('409 Conflict',h['status']);self.assertNotIn('assessment',v)

    def test_capability_cannot_use_session_endpoints_or_confirm(self):
        mid,pid=self.proposal()
        cap=self.ws.issue_capability(self.token,self.csrf,self.cid)
        h,_=self.request('/api/conversations',{},token=cap)
        self.assertEqual('403 Forbidden',h['status'])
        h,context=self.request('/bridge/context',HTTP_AUTHORIZATION='Bearer '+cap)
        self.assertEqual('200 OK',h['status']);self.assertEqual(mid,context['message_id'])
        h,p=self.request('/bridge/propose',{'message_id':mid,'version':1,'facts':{}},HTTP_AUTHORIZATION='Bearer '+cap,HTTP_ORIGIN=None)
        self.assertEqual('200 OK',h['status'])
        self.assertEqual('required_in_application',p['confirmation'])
        h,_=self.request('/bridge/confirm',{},HTTP_AUTHORIZATION='Bearer '+cap,HTTP_ORIGIN=None)
        self.assertEqual('403 Forbidden',h['status'])
        self.assertIsNone(self.ws.view(self.token,self.cid)['case'])

    def test_sensitive_errors_are_redacted(self):
        from unittest.mock import patch
        with patch.object(self.ws,'conversations',side_effect=RuntimeError('password=private')):
            h,body=self.request('/api/conversations')
        self.assertEqual('503 Service Unavailable',h['status']);self.assertNotIn('private',json.dumps(body))

    def test_login_is_rate_limited(self):
        key=self.ws.issue_access('syn-user-driver')
        for _ in range(10):
            h,_=self.request('/api/login',{'key':key});self.assertEqual('200 OK',h['status'])
        h,b=self.request('/api/login',{'key':key})
        self.assertEqual('403 Forbidden',h['status']);self.assertIn('Too many',b['error'])

    def test_real_stdio_bridge_through_local_http(self):
        from trip_app.__main__ import QuietHandler
        mid,_=self.proposal()
        cap=self.ws.issue_capability(self.token,self.csrf,self.cid)
        cap_path=Path(self.tmp.name)/'capability'
        private_write(cap_path,cap)
        http=make_server('127.0.0.1',0,self.web,handler_class=QuietHandler)
        port=http.server_port
        self.web.host=f'127.0.0.1:{port}';self.web.origin='http://'+self.web.host
        thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
        try:
            requests=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{}}},
                      {'jsonrpc':'2.0','method':'notifications/initialized'},
                      {'jsonrpc':'2.0','id':2,'method':'tools/list'},
                      {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'get_statement','arguments':{}}},
                      {'jsonrpc':'2.0','id':4,'method':'tools/call','params':{'name':'propose_facts','arguments':{'message_id':mid,'version':1,'facts':{'height':{'value':175,'unit':'in'}}}}},
                      {'jsonrpc':'2.0','id':5,'method':'tools/call','params':{'name':'confirm','arguments':{}}}]
            proc=subprocess.run([sys.executable,'-m','trip_app.mcp_server','--origin',self.web.origin,'--capability-file',str(cap_path)],
                                input=''.join(json.dumps(r)+'\n' for r in requests),text=True,capture_output=True,timeout=15)
            self.assertEqual(0,proc.returncode,proc.stderr)
            responses=[json.loads(line)for line in proc.stdout.splitlines()]
            self.assertEqual({'get_statement','propose_facts','get_confirmed_assessment'},{t['name']for t in responses[1]['result']['tools']})
            self.assertEqual(mid,responses[2]['result']['structuredContent']['message_id'])
            self.assertFalse(responses[3]['result']['isError'])
            self.assertIn('error',responses[4]);self.assertNotIn(cap,proc.stdout+proc.stderr)
            self.assertIsNone(self.ws.view(self.token,self.cid)['case'])
        finally:
            http.shutdown();http.server_close();thread.join(3)

    def test_mcp_rejects_early_tools_remote_urls_and_bad_ids(self):
        session=Session(None)
        self.assertIn('error',session.handle({'jsonrpc':'2.0','id':1,'method':'tools/list'}))
        self.assertIn('error',session.handle({'jsonrpc':'2.0','id':True,'method':'ping'}))
        for url in ('https://evil.example','http://localhost:8765','http://127.0.0.1:8765/evil','http://127.0.0.1:99999'):
            with self.assertRaises(ValueError):Client(url,'x')


class OperationsTests(unittest.TestCase):
    proposal=fixtures.WorkspaceTests.proposal

    def setUp(self):
        fixtures.WorkspaceTests.setUp(self)

    def test_separate_workspace_database_is_required(self):
        old=Path(self.tmp.name)/'legacy.sqlite3';TripStore(old)
        with self.assertRaisesRegex(InputError,'separate application'):
            Workspace(old)

    def test_verified_restore_revokes_previous_credentials_and_preserves_confirmed_case(self):
        _,pid=self.proposal()
        self.ws.confirm(self.token,self.csrf,self.cid,pid,1,{'height':{'value':175,'unit':'in'}})
        cap=self.ws.issue_capability(self.token,self.csrf,self.cid)
        self.ws.share(self.token,self.csrf,self.cid,'syn-user-dispatch','edit')
        path=Path(self.tmp.name)/'backup.sqlite3';dest=Path(self.tmp.name)/'restored.sqlite3'
        result=backup(self.ws,path);self.assertEqual(1,result['statements'])
        restore(path,dest);restored=Workspace(dest)
        with self.assertRaises(Denied):restored.session(self.token)
        with self.assertRaises(Denied):restored.model_context(cap)
        with restored.transaction() as db:
            self.assertEqual(0,db.execute('SELECT count(*) FROM app_grants').fetchone()[0])
        key=restored.issue_access('syn-user-driver');token,_=restored.login(key)
        self.assertEqual(175,restored.view(token,self.cid)['case']['facts']['height']['value'])
        self.assertEqual(0o600,path.stat().st_mode & 0o777)
        with self.assertRaises(FileExistsError):backup(self.ws,path)
        with self.assertRaises(FileExistsError):restore(path,dest)

    def test_modified_backup_or_audit_chain_rejected(self):
        path=Path(self.tmp.name)/'backup.sqlite3';backup(self.ws,path)
        with self.ws.transaction() as db:db.execute("UPDATE app_events SET body='{}' WHERE sequence=1")
        with self.assertRaises(InputError):inspect_database(self.ws.trips.path)
        with path.open('ab') as handle:handle.write(b'tampered')
        with self.assertRaises(InputError):restore(path,Path(self.tmp.name)/'bad.sqlite3')
        self.assertFalse((Path(self.tmp.name)/'bad.sqlite3').exists())

    def test_delete_purges_snapshots_requests_and_revokes_capabilities(self):
        _,pid=self.proposal()
        self.ws.confirm(self.token,self.csrf,self.cid,pid,1,{'height':{'value':175,'unit':'in'}})
        cap=self.ws.issue_capability(self.token,self.csrf,self.cid)
        self.ws.delete(self.token,self.csrf,self.cid,2)
        for table in ('app_messages','app_proposals','app_confirmations','app_capabilities','app_conversations','app_message_requests','trips','requests'):
            with self.ws.transaction() as db:self.assertEqual(0,db.execute('SELECT count(*) FROM '+table).fetchone()[0],table)
        with self.assertRaises(Denied):self.ws.model_context(cap)
        self.assertGreater(inspect_database(self.ws.trips.path)['events'],0)

    def test_secret_file_must_be_private_regular_and_owned(self):
        path=Path(self.tmp.name)/'key';private_write(path,'a'*40)
        self.assertEqual('a'*40,read_secret(path))
        os.chmod(path,0o644)
        with self.assertRaises(InputError):read_secret(path)
        link=Path(self.tmp.name)/'link';link.symlink_to(path)
        with self.assertRaises(OSError):read_secret(link)
