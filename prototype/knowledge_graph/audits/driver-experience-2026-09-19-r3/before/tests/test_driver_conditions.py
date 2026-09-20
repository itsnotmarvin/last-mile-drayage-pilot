"""A small follow-up must retain fresh evidence, sources and saved-trip identity."""
import copy
import json
from pathlib import Path
import unittest

import jsonschema
from neo4j_kg.driver_conditions import conditions_answer
from neo4j_kg.mcp_server import Session, TOOLS
from neo4j_kg.service import CheckingService
from neo4j_kg.terminal_status import fetch
from test_terminal_status import stub_get
import test_trip_assessment as fixtures


class ConditionsAnswerTests(unittest.TestCase):
    setUp = fixtures.TripAssessmentTests.setUp
    create = fixtures.TripAssessmentTests.create
    update = fixtures.TripAssessmentTests.update
    setUpClass = classmethod(fixtures.TripAssessmentTests.setUpClass.__func__)

    def sample(self):
        return self.create({**fixtures.BASE, 'route_id': 'path_a_exit13a_to_apm',
                            'height': {'value': 175, 'unit': 'in'},
                            'gross_weight': {'value': 80000, 'unit': 'lb'}})

    def session(self):
        session = Session(CheckingService(self.graph), trip_service=self.service,
                          audit_path=Path(self.tmp.name) / 'audit.jsonl')
        session.state = 'ready'
        return session

    def call(self, session, args):
        return session.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                               'params': {'name': 'get_trip_conditions_answer', 'arguments': args}})['result']

    def test_separate_notice_dates_have_their_own_source_links_and_no_mutation(self):
        a = self.sample()
        a['evidence_package']['current_terminal_status'] = fetch(get=stub_get)
        before = copy.deepcopy(a)
        text = conditions_answer(a)
        terminal = a['evidence_package']['current_terminal_status']
        for s in terminal['sources']:
            self.assertIn(s['url'], text)
        for key in ('retrieved_at', 'latest_notice_heading', 'closure_notice_text'):
            self.assertIn(terminal[key], text)
        self.assertIn('does not date a separate closure excerpt', text)
        self.assertIn('effective time is **not stated**', text)
        self.assertIn('reported height is 175 inches', text)
        self.assertIn('reported gross weight is 80000 lb', text)
        self.assertLess(len(text), 6500)
        self.assertEqual(before, a)

    def test_actual_tool_reassesses_latest_revision_and_audits_full_source_binding(self):
        initial = self.sample()
        corrected = self.update(initial, {'height': {'value': 162, 'unit': 'in'}}, correction=True)
        session = self.session()
        before_reads = self.graph.reads
        result = self.call(session, {'trip_id': corrected['case']['trip_id']})
        self.assertFalse(result['isError'])
        self.assertGreater(self.graph.reads, before_reads)
        body = result['structuredContent']
        self.assertEqual(json.loads(result['content'][-1]['text']), body)
        schema = next(t for t in TOOLS if t['name'] == 'get_trip_conditions_answer')['outputSchema']
        jsonschema.validate(body, schema)
        self.assertEqual(2, body['revision'])
        self.assertEqual(corrected['case']['trip_id'], body['trip_id'])
        self.assertIn('height is 162 inches', body['answer_markdown'])
        self.assertNotIn('height is 175', body['answer_markdown'])
        event = json.loads(session.audit_path.read_text())
        a = event['evidence_assessment']
        self.assertEqual(corrected['case'], a['case'])
        self.assertEqual(body['assessment_id'], a['assessment_id'])
        self.assertEqual([], event['retrieval_trace']['delivered_passage_clause_ids'])
        self.assertTrue(a['evidence_package']['sources'])
        self.assertEqual(conditions_answer(a), body['answer_markdown'])

    def test_outage_does_not_reuse_sources_or_positive_comparisons(self):
        a = self.sample()
        self.graph.available = False
        result = self.call(self.session(), {'trip_id': a['case']['trip_id']})
        self.assertFalse(result['isError'])
        text = result['structuredContent']['answer_markdown']
        self.assertIn('evidence service is unavailable', text)
        self.assertNotIn('https://', text)
        self.assertNotIn('height is 175', text)

    def test_followup_cannot_change_scope_or_facts(self):
        a = self.sample()
        session = self.session()
        for extra in ({'facts': {'height': {'value': 162, 'unit': 'in'}}}, {'question_scope': 'route'}):
            result = self.call(session, {'trip_id': a['case']['trip_id'], **extra})
            self.assertTrue(result['isError'])
        current = self.service.assess({'trip_id': a['case']['trip_id']})
        self.assertEqual(a['case'], current['case'])

    def test_conflicting_height_does_not_become_a_useful_comparison(self):
        a = self.update(self.sample(), {'height': {'value': 162, 'unit': 'in'}})
        text = conditions_answer(a)
        self.assertNotIn('reported height is', text)
        self.assertIn('reported gross weight is 80000', text)

    def test_bounded_operator_conditions_and_narrow_scope_keep_the_full_findings(self):
        from neo4j_kg.driver_brief import driver_brief
        a = self.sample()
        finding = next(f for f in a['findings'] if f['requirement_id'] == 'current_route_conditions')
        for status in ('met', 'not_met'):
            finding['status'] = status
            self.assertEqual(driver_brief(a), conditions_answer(a))
        narrow = self.create(scope='induction')
        self.assertEqual(driver_brief(narrow), conditions_answer(narrow))


if __name__ == '__main__':
    unittest.main()
