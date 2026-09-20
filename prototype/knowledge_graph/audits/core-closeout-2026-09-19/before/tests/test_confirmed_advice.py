"""Observed narration failures and confirmed-read authorization boundaries.

These check the evidence contract, not whether arbitrary model prose is safe.
"""
import json
from unittest.mock import patch
import unittest

from neo4j_kg.answer_guidance import answer_guidance, explanation_package
from trip_app.store import Conflict, Denied
from trip_app.service import Application
from trip_app.mcp_server import Client
import test_trip_app as workspace_fixtures
import test_trip_app_web as http_fixtures
from test_trip_assessment import MemoryGraph
from test_neo4j_migration import OracleReader
from kg.service import CheckingService


class ConfirmedAdviceTests(unittest.TestCase):
    setUp = workspace_fixtures.WorkspaceTests.setUp
    def proposal(self, facts=None, text='Synthetic trip', version=0):
        mid=self.ws.message(self.token,self.csrf,self.cid,version,text,self.cid+':'+str(version))
        return mid,self.ws.propose_local(self.token,self.csrf,self.cid,mid,version+1,facts or {})

    def confirmed(self, role='driver'):
        if role != 'driver':
            self.token, self.csrf = self.sessions[role]
            self.cid = self.ws.create(self.token, self.csrf)
        self.graph = MemoryGraph(OracleReader(CheckingService()))
        self.app = Application(self.ws, self.graph)
        text = 'Synthetic only: can I take this truck to APM Elizabeth? Height 14 ft 7 in, width 102 inches, gross weight 80000 lb. I do not know the route.'
        self.facts = {'height':{'value':175,'unit':'in'},'width':{'value':102,'unit':'in'},
                      'gross_weight':{'value':80000,'unit':'lb'},'terminal_id':'facility_apm_elizabeth'}
        self.mid, pid = self.proposal(self.facts, text)
        self.ws.confirm(self.token,self.csrf,self.cid,pid,1,self.facts)
        self.cap = self.ws.issue_capability(self.token,self.csrf,self.cid,allow_assessment=True)
        return self.app.model_assessment(self.cap,self.mid,2)

    def test_confirmed_read_preserves_statement_and_binds_fresh_result(self):
        r = self.confirmed()
        self.assertEqual(self.ws.view(self.token,self.cid)['messages'],r['original_statements'])
        self.assertEqual(r['binding']['trip_revision'],r['confirmation']['trip_revision'])
        self.assertEqual(r['binding']['assessment_id'],r['explanation']['answer_guidance']['assessment_id'])
        self.assertEqual('reported_facts_only',r['confirmation']['verification_status'])
        self.assertEqual(175,r['reported_facts']['height']['value'])
        self.assertTrue(self.ws.model_context(self.cap)['assessment_access'])
        reads=self.graph.reads
        self.app.model_assessment(self.cap,self.mid,2)
        self.assertGreater(self.graph.reads,reads)

    def test_legacy_proposal_key_cannot_read_confirmed_assessment(self):
        self.confirmed()
        old=self.ws.issue_capability(self.token,self.csrf,self.cid)
        self.assertFalse(self.ws.model_context(old)['assessment_access'])
        with self.assertRaises(Denied):self.app.model_assessment(old,self.mid,2)
        with self.assertRaises(Denied):self.app.model_assessment(self.token,self.mid,2)
        with self.assertRaises(Denied):self.ws.session(self.cap)

    def test_new_statement_and_unconfirmed_proposal_suppress_old_result(self):
        self.confirmed()
        mid,pid=self.proposal({'height':{'value':162,'unit':'in'}},'Correction: height 13 ft 6 in.',2)
        for message,version in [(self.mid,2),(mid,3)]:
            with self.assertRaises(Conflict):self.app.model_assessment(self.cap,message,version)
        self.ws.confirm(self.token,self.csrf,self.cid,pid,3,{'height':{'value':162,'unit':'in'}})
        r=self.app.model_assessment(self.cap,mid,4)
        self.assertEqual(162,r['reported_facts']['height']['value'])
        self.assertEqual(2,r['binding']['trip_revision'])
        self.assertEqual(2,len(r['original_statements']))
        self.assertEqual('not_cleared',r['explanation']['decision_brief']['status'])
        heights=[c['comparison']['reported'] for c in r['explanation']['answer_guidance']['reported_comparisons'] if c['comparison']['field']=='height']
        self.assertTrue(heights);self.assertEqual({162},set(heights))

    def test_other_conversation_message_and_boolean_version_rejected(self):
        self.confirmed()
        for mid,version in [('message-other',2),(self.mid,True),(self.mid,1)]:
            with self.assertRaises(Conflict):self.app.model_assessment(self.cap,mid,version)
        with self.assertRaises(ValueError):Client('http://127.0.0.1:8765',self.cap).call('get_confirmed_assessment',{'message_id':self.mid,'version':2,'trip_id':'another'})

    def test_revocation_expiry_and_delete_during_graph_read_suppress_response(self):
        for mutation in ('revoke','expire','delete','statement'):
            with self.subTest(mutation=mutation):
                self.confirmed()
                original=self.graph.read
                def race(fn):
                    result=original(fn)
                    if mutation=='revoke':self.ws.revoke_capabilities(self.token,self.csrf,self.cid)
                    elif mutation=='expire':self.now+=3601
                    elif mutation=='delete':self.ws.delete(self.token,self.csrf,self.cid,2)
                    else:self.ws.message(self.token,self.csrf,self.cid,2,'Truck changed','race')
                    return result
                with patch.object(self.graph,'read',race),self.assertRaises((Denied,Conflict)):
                    self.app.model_assessment(self.cap,self.mid,2)
                # A new isolated conversation for the next mutation.
                self.cid=self.ws.create(self.token,self.csrf)

    def test_sharing_downgrade_revokes_assessment_scope_and_access(self):
        self.confirmed()
        other,csrf=self.sessions['dispatch']
        self.ws.share(self.token,self.csrf,self.cid,'syn-user-dispatch','edit')
        cap=self.ws.issue_capability(other,csrf,self.cid,allow_assessment=True)
        original=self.graph.read
        def race(fn):
            r=original(fn);self.ws.share(self.token,self.csrf,self.cid,'syn-user-dispatch','view');return r
        with patch.object(self.graph,'read',race),self.assertRaises(Denied):self.app.model_assessment(cap,self.mid,2)
        with self.ws.transaction() as db:
            self.assertEqual(1,db.execute('SELECT count(*) FROM app_capability_scopes').fetchone()[0])

    def test_out_of_band_revision_cannot_reuse_confirmation(self):
        self.confirmed();case=self.ws.view(self.token,self.cid)['case']
        self.ws.trips.update(case['trip_id'],case['revision'],'driver','trip_dispatch',{'height':{'value':162,'unit':'in'}},'Height 13 ft 6 in','outside',replace_conflicts=True)
        with self.assertRaises(Conflict):self.app.model_assessment(self.cap,self.mid,2)

    def test_outage_clears_explanation_sources_and_comparisons(self):
        self.confirmed();self.graph.available=False
        r=self.app.model_assessment(self.cap,self.mid,2)['explanation']
        self.assertEqual('unavailable',r['service_status'])
        for key in ('reported_comparisons','open_requirements','historical_context'):self.assertEqual([],r['answer_guidance'][key])
        self.assertEqual([],r['comparison_sources']);self.assertEqual([],r['findings'])
        self.assertEqual('assessment_unavailable',r['decision_brief']['status'])

    def test_archived_bulletin_is_not_a_current_instruction_in_projection(self):
        r=self.confirmed()['explanation'];g=r['answer_guidance']
        self.assertEqual('unknown_for_this_trip',g['historical_context'][0]['current_status'])
        self.assertNotIn('MUST utilize',json.dumps(r))
        full=self.app.assessments.assess({'trip_id':g['trip_id']})
        self.assertIn('MUST utilize',json.dumps(full['evidence_package']['observations']))
        self.assertEqual(full['answer_guidance'],answer_guidance(full))
        for c in g['reported_comparisons']:
            self.assertTrue(c['qualification']);self.assertEqual('reported_fact_comparison_not_legal_finding',c['claim_type'])
            self.assertTrue(set(c['source_clause_ids']) <= {s['clause_id'] for s in r['comparison_sources']})

    def test_driver_dispatcher_same_qualified_comparisons_and_boundary(self):
        a=self.confirmed()['explanation']['answer_guidance']
        b=self.confirmed('dispatch')['explanation']['answer_guidance']
        for key in ('reported_comparisons','historical_context','boundaries','opening'):self.assertEqual(a[key],b[key])
        self.assertNotEqual(a['trip_id'],b['trip_id'])


class ConfirmedAdviceHttpTests(unittest.TestCase):
    setUp = http_fixtures.HttpTests.setUp
    request = http_fixtures.HttpTests.request
    proposal = workspace_fixtures.WorkspaceTests.proposal

    def test_explicit_key_required_and_pending_confirmation_rejected_over_http(self):
        mid,pid=self.proposal({'height':{'value':175,'unit':'in'}})
        h,r=self.request('/api/conversations/'+self.cid+'/assessment-capability',{})
        self.assertEqual('200 OK',h['status']);cap=r['capability']
        h,_=self.request('/bridge/assessment',{'message_id':mid,'version':1},HTTP_AUTHORIZATION='Bearer '+cap)
        self.assertEqual('409 Conflict',h['status'])
        self.ws.confirm(self.token,self.csrf,self.cid,pid,1,{'height':{'value':175,'unit':'in'}})
        h,r=self.request('/bridge/assessment',{'message_id':mid,'version':2},HTTP_AUTHORIZATION='Bearer '+cap)
        self.assertEqual('200 OK',h['status']);self.assertEqual('unavailable',r['explanation']['service_status'])
        h,_=self.request('/bridge/assessment',{'message_id':mid,'version':2,'trip_id':'other'},HTTP_AUTHORIZATION='Bearer '+cap)
        self.assertEqual('400 Bad Request',h['status'])
        old=self.ws.issue_capability(self.token,self.csrf,self.cid)
        h,_=self.request('/bridge/assessment',{'message_id':mid,'version':2},HTTP_AUTHORIZATION='Bearer '+old)
        self.assertEqual('403 Forbidden',h['status'])

    def test_stdio_confirmed_read_and_audit_through_http(self):
        import subprocess, sys, threading
        from pathlib import Path
        from wsgiref.simple_server import make_server
        from trip_app.__main__ import QuietHandler
        from trip_app.operations import private_write
        from neo4j_kg.common import digest
        mid,pid=self.proposal({'height':{'value':175,'unit':'in'}})
        self.ws.confirm(self.token,self.csrf,self.cid,pid,1,{'height':{'value':175,'unit':'in'}})
        cap=self.ws.issue_capability(self.token,self.csrf,self.cid,allow_assessment=True)
        key=Path(self.tmp.name)/'new-key';private_write(key,cap)
        audit=Path(self.tmp.name)/'new-audit.jsonl'
        http=make_server('127.0.0.1',0,self.web,handler_class=QuietHandler)
        self.web.host=f'127.0.0.1:{http.server_port}';self.web.origin='http://'+self.web.host
        thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
        try:
            requests=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{}}},
                      {'jsonrpc':'2.0','method':'notifications/initialized'},
                      {'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'get_confirmed_assessment','arguments':{'message_id':mid,'version':2}}},
                      {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'get_confirmed_assessment','arguments':{'message_id':mid,'version':1}}}]
            proc=subprocess.run([sys.executable,'-m','trip_app.mcp_server','--origin',self.web.origin,'--capability-file',str(key),'--audit-file',str(audit)],input=''.join(json.dumps(r)+'\n' for r in requests),text=True,capture_output=True,timeout=15)
            self.assertEqual(0,proc.returncode)
            responses=[json.loads(l) for l in proc.stdout.splitlines()]
            self.assertFalse(responses[1]['result']['isError']);self.assertTrue(responses[2]['result']['isError'])
            self.assertEqual('unavailable',responses[1]['result']['structuredContent']['explanation']['service_status'])
            events=[json.loads(l) for l in audit.read_text().splitlines()]
            self.assertEqual(2,len(events));self.assertEqual(events[0]['event_hash'],events[1]['previous_event_hash'])
            for e in events:self.assertEqual(e['event_hash'],digest({k:v for k,v in e.items() if k!='event_hash'}))
            self.assertNotIn(cap,proc.stdout+proc.stderr+audit.read_text())
            self.assertEqual(0o600,audit.stat().st_mode & 0o777)
        finally:http.shutdown();http.server_close();thread.join(3)
