"""Complete-move delivery preserves state, evidence and conditional source rules."""
import copy
import json
from pathlib import Path
import unittest

import jsonschema
from neo4j_kg.driver_brief import driver_brief, retained_text
from neo4j_kg.driver_move import move_answer
from neo4j_kg.mcp_server import Session, TOOLS
from neo4j_kg.service import CheckingService
from neo4j_kg.terminal_status import fetch
from test_terminal_status import stub_get
import test_trip_assessment as fixtures


class DriverMoveTests(unittest.TestCase):
    setUp = fixtures.TripAssessmentTests.setUp
    create = fixtures.TripAssessmentTests.create
    setUpClass = classmethod(fixtures.TripAssessmentTests.setUpClass.__func__)

    def session(self):
        s = Session(CheckingService(self.graph), trip_service=self.service,
                    audit_path=Path(self.tmp.name) / 'audit.jsonl')
        s.state = 'ready'
        return s

    def args(self, key='new'):
        return {'action': 'create', 'requester_role': 'driver', 'source_message': 'Synthetic trip report',
                'request_key': key, 'facts': {**fixtures.BASE,
                    'trip_at': '2026-09-19T18:00:00-04:00', 'route_id': 'path_a_exit13a_to_apm',
                    'height': {'value': 175, 'unit': 'in'}, 'width': {'value': 102, 'unit': 'in'},
                    'semitrailer_length': {'value': 53, 'unit': 'ft'},
                    'gross_weight': {'value': 80000, 'unit': 'lb'},
                    'twic_reported': True, 'sealink_registered_reported': True, 'appointment_reported': True}}

    def call(self, s, args):
        return s.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                         'params': {'name': 'assess_driver_move', 'arguments': args}})['result']

    def last_assessment(self, s):
        return json.loads(s.audit_path.read_text().splitlines()[-1])['evidence_assessment']

    def test_create_correct_retry_read_and_separate_move_preserve_identity_and_full_scope(self):
        s = self.session()
        initial = self.call(s, self.args())['structuredContent']
        self.assertEqual('trip_dispatch', self.last_assessment(s)['case']['question_scope'])
        update = {'action': 'update', 'trip_id': initial['trip_id'], 'expected_revision': 1,
                  'requester_role': 'driver', 'source_message': 'Correction: loaded height is 13 ft 6 in.',
                  'request_key': 'correction', 'replace_conflicts': True,
                  'facts': {'height': {'value': 162, 'unit': 'in'}}}
        corrected = self.call(s, update)['structuredContent']
        self.assertEqual(2, corrected['revision'])
        self.assertIn('height: 162 in', corrected['answer_markdown'])
        self.assertNotIn('height: 175 in', corrected['answer_markdown'])
        self.assertEqual(2, self.call(s, update)['structuredContent']['revision'])
        reads = self.graph.reads
        reread = self.call(s, {'action': 'read', 'trip_id': initial['trip_id']})['structuredContent']
        self.assertGreater(self.graph.reads, reads)
        self.assertEqual(2, reread['revision'])
        separate = self.args('separate'); separate['facts']['route_id'] = 'path_b_us1_9_to_apm'
        other = self.call(s, separate)['structuredContent']
        self.assertNotEqual(initial['trip_id'], other['trip_id'])
        self.assertEqual(5, len(self.last_assessment(s)['evidence_package']['route_context']['segments']))
        self.assertEqual(1, other['revision'])

    def test_conditional_rules_links_and_observation_dates_survive_compact_projection(self):
        self.service.terminal_status_fetcher = lambda: fetch(get=stub_get)
        s = self.session(); result = self.call(s, self.args())
        self.assertFalse(result['isError'])
        body = result['structuredContent']; a = self.last_assessment(s); text = body['answer_markdown']
        schema = next(t for t in TOOLS if t['name'] == 'assess_driver_move')['outputSchema']
        jsonschema.validate(body, schema)
        self.assertEqual(body, json.loads(result['content'][0]['text']))
        self.assertEqual(text, move_answer(a))
        for source in a['evidence_package']['sources']:
            if source['clause_id'] in ('reg_nj_terminal_access_102_inch_standard_truck', 'reg_nj_semitrailer_length'):
                self.assertIn(retained_text(source['source_text']), text)
                self.assertIn(source['url'], text)
        self.assertIn('**102-inch-wide standard truck**', text)
        self.assertIn('13 ft 6 in, including the load, except as otherwise identified', text)
        self.assertIn('lower bridge-formula limit', text)
        for page in a['evidence_package']['current_terminal_status']['sources']:
            self.assertIn(page['url'], text)
        self.assertIn('The heading does not date that closure', text)
        self.assertLess(len(text), 7500)
        event = json.loads(s.audit_path.read_text())
        self.assertEqual([], event['retrieval_trace']['delivered_passage_clause_ids'])
        self.assertEqual(26, len(a['evidence_package']['sources']))
        self.assertNotIn(body['trip_id'], text)

    def test_schema_and_runtime_reject_cross_operation_fields_scope_and_receipt_injection(self):
        s = self.session(); initial = self.call(s, self.args())['structuredContent']
        schema = next(t for t in TOOLS if t['name'] == 'assess_driver_move')['inputSchema']
        bad = [self.args() | {'question_scope': 'route'}, self.args() | {'expected_revision': 1},
               self.args() | {'trip_id': initial['trip_id']}, self.args() | {'receipt': {}},
               {'action': 'read', 'trip_id': initial['trip_id'], 'facts': {}},
               {'action': 'read', 'trip_id': initial['trip_id'], 'replace_conflicts': True},
               {'action': 'update', 'trip_id': initial['trip_id']}, self.args() | {'action': []}]
        for args in bad:
            with self.subTest(args=args):
                with self.assertRaises(jsonschema.ValidationError):
                    jsonschema.validate(args, schema)
                self.assertTrue(self.call(s, args)['isError'])
        self.assertEqual(1, self.states.get(initial['trip_id'])['revision'])

    def test_narrow_case_is_not_silently_rescoped(self):
        a = self.create(scope='route'); s = self.session()
        result = self.call(s, {'action': 'read', 'trip_id': a['case']['trip_id']})
        self.assertTrue(result['isError'])
        self.assertEqual('route', self.states.get(a['case']['trip_id'])['question_scope'])

    def test_conflicting_reports_and_bounded_results_keep_detailed_findings(self):
        s = self.session(); result = self.call(s, self.args())['structuredContent']; a = self.last_assessment(s)
        before = copy.deepcopy(a); move_answer(a); self.assertEqual(before, a)
        for status in ('met', 'not_met', 'not_applicable'):
            a['findings'][0]['status'] = status
            self.assertEqual(driver_brief(a), move_answer(a))
        update = {'action': 'update', 'trip_id': result['trip_id'], 'expected_revision': 1,
                  'requester_role': 'driver', 'source_message': 'Additional report', 'request_key': 'conflict',
                  'facts': {'height': {'value': 162, 'unit': 'in'}}}
        body = self.call(s, update)['structuredContent']; a = self.last_assessment(s)
        self.assertTrue(a['case']['conflicts'])
        self.assertEqual(driver_brief(a), body['answer_markdown'])

    def test_outage_never_reuses_prior_positive_comparisons(self):
        s = self.session(); body = self.call(s, self.args())['structuredContent']; self.graph.available = False
        result = self.call(s, {'action': 'read', 'trip_id': body['trip_id']})['structuredContent']
        self.assertEqual('unavailable', result['service_status'])
        self.assertNotIn('https://', result['answer_markdown'])
        self.assertNotIn('175', result['answer_markdown'])
        self.assertEqual('not_issued', result['operational_permission'])


if __name__ == '__main__':
    unittest.main()
