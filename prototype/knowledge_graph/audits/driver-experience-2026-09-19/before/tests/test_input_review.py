"""Captured extraction defects, atomic rejection, and controlled presentation."""
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from kg.service import CheckingService as OriginalService
from test_neo4j_migration import OracleReader
from test_trip_assessment import MemoryGraph, BASE
from neo4j_kg.assessment import TripService, evaluate_trip
from neo4j_kg.decision_brief import render_trip_report
from neo4j_kg.input_review import consistency_issues, input_review
from neo4j_kg.mcp_server import Session, TOOLS
from neo4j_kg.service import CheckingService, InputError
from neo4j_kg.trip_models import normalize_facts
from neo4j_kg.trip_state import TripStore

ROOT = Path(__file__).resolve().parents[1]


class InputReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = OracleReader(OriginalService())

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.database = Path(temporary.name) / 'trips.sqlite3'
        self.states = TripStore(self.database)
        self.graph = MemoryGraph(self.reader)
        self.service = TripService(self.graph, self.states)
        self.sequence = 0

    def args(self, facts, text='Synthetic report', scope='trip_dispatch', role='unknown'):
        self.sequence += 1
        return {'facts': facts, 'source_message': text, 'requester_role': role,
                'question_scope': scope, 'request_key': f'review-{self.sequence}'}

    def test_mixed_units_preserved_and_truncation_rejected(self):
        for source in ('14 feet 7 inches high', 'height: 14 ft 7 in', '14′7″ high',
                       '12-foot-wide and 14-foot-7-inch-high truck'):
            with self.subTest(source=source):
                with self.assertRaisesRegex(InputError, 'DIMENSION_TEXT_MISMATCH'):
                    normalize_facts({'height': {'value': 14, 'unit': 'ft'}}, 'driver', source)
                correct = normalize_facts({'height': {'value': 175, 'unit': 'in'}}, 'driver', source)
                self.assertEqual(175, correct['height']['value'])
        approximate = normalize_facts({'height': {'value': 14.583333, 'unit': 'ft'}},
                                      'driver', '14 feet 7 inches high')
        self.assertAlmostEqual(175, approximate['height']['value'], places=5)

    def test_multiple_measurements_need_clarification_and_missing_text_is_unconfirmed(self):
        with self.assertRaisesRegex(InputError, 'AMBIGUOUS_DIMENSION_TEXT'):
            normalize_facts({'height': {'value': 175, 'unit': 'in'}}, 'driver',
                            'The old truck was 13 feet high; the new one is 14 feet 7 inches high.')
        result = self.service.assess(self.args({'height': {'value': 175, 'unit': 'in'}}))
        review = result['input_review']
        self.assertEqual('no_detected_conflict', review['consistency_status'])
        self.assertEqual('not_independently_confirmed', review['confirmation_status'])
        self.assertEqual(['height'], review['unconfirmed_fields'])
        self.assertEqual('caller_supplied_not_authenticated_transcript', review['text_origin'])

    def test_road_bulletin_lane_width_is_not_a_truck_measurement(self):
        source = 'Our truck is 12 feet wide and 14 feet 7 inches high. The bulletin describes 11-foot lanes.'
        facts = normalize_facts({'width': {'value': 12, 'unit': 'ft'},
                                 'height': {'value': 175, 'unit': 'in'}}, 'driver', source)
        self.assertEqual([], consistency_issues(facts))

    def test_date_only_and_missing_timezone_do_not_support_timestamp(self):
        for source, code in [('Trip on September 2, 2026.', 'DATE_ONLY_EXPANDED_TO_TIMESTAMP'),
                             ('Trip on 2026-09-02.', 'DATE_ONLY_EXPANDED_TO_TIMESTAMP'),
                             ('Trip on September 2, 2026 at 2 pm.', 'TIMEZONE_NOT_SUPPORTED_BY_TEXT')]:
            with self.subTest(source=source), self.assertRaisesRegex(InputError, code):
                normalize_facts({'trip_at': '2026-09-02T14:00:00-04:00'}, 'driver', source)
        accepted = normalize_facts({'trip_at': '2026-09-02T14:00:00-04:00'}, 'driver',
                                   'Synthetic trip at 2026-09-02T14:00:00-04:00.')
        self.assertEqual([], consistency_issues(accepted))

    def test_unknown_approval_and_permit_question_are_not_absence(self):
        for value in (True, False):
            with self.assertRaisesRegex(InputError, 'UNKNOWN_APPROVAL_REPORTED_AS_BOOLEAN'):
                normalize_facts({'terminal_approval_reported': value}, 'dispatcher',
                                'Terminal handling approval is unknown.')
        with self.assertRaisesRegex(InputError, 'PERMIT_QUESTION_REPORTED_AS_ABSENCE'):
            normalize_facts({'permit_type': 'none'}, 'driver', 'Do I need a permit?')
        self.assertIsNone(normalize_facts({'terminal_approval_reported': None}, 'driver',
                                        'Terminal approval is unknown.')['terminal_approval_reported']['value'])

    def test_captured_s4_defects_are_detected_using_actual_saved_call(self):
        events = json.loads((ROOT / 'docs/paired-replay-2026-09-10/s4_oversize_mutable_port_st__pressure.audit.json').read_text())
        event = next(e for e in events if e['method'] == 'assess_trip')
        saved = event['response']['result']['structuredContent']['case']
        issues = {(i['field'], i['code']) for i in consistency_issues(saved['facts'])}
        self.assertIn(('height', 'DIMENSION_TEXT_MISMATCH'), issues)
        self.assertIn(('trip_at', 'DATE_ONLY_EXPANDED_TO_TIMESTAMP'), issues)
        arguments = event['validated_arguments']['as_received']
        with self.assertRaisesRegex(InputError, 'DIMENSION_TEXT_MISMATCH'):
            self.service.assess(arguments)

    def test_unverified_positive_possession_remains_a_report(self):
        result = self.service.assess(self.args({'terminal_approval_reported': True},
                                               'I have terminal approval but it is unverified.'))
        self.assertIs(result['case']['facts']['terminal_approval_reported']['value'], True)
        self.assertEqual('user_reported', result['case']['facts']['terminal_approval_reported']['basis'])
        self.assertEqual('not_independently_confirmed', result['input_review']['confirmation_status'])
        self.assertEqual('not_issued', result['decision_brief']['operational_permission'])

    def test_rejected_create_has_no_case_request_or_graph_read(self):
        with self.assertRaises(InputError):
            self.service.assess(self.args({'height': {'value': 14, 'unit': 'ft'}}, '14 feet 7 inches high'))
        with sqlite3.connect(self.database) as connection:
            for table in ('trips', 'requests'):
                self.assertEqual(0, connection.execute(f'SELECT count(*) FROM {table}').fetchone()[0])
        self.assertEqual(0, self.graph.reads)

    def test_rejected_update_is_atomic_and_key_can_be_reused_for_corrected_write(self):
        first = self.service.assess(self.args({'height': {'value': 168, 'unit': 'in'}}))
        args = self.args({'height': {'value': 14, 'unit': 'ft'}}, 'The corrected height is 14 feet 7 inches.')
        args.update(trip_id=first['case']['trip_id'], expected_revision=1, replace_conflicts=True)
        before = self.states.get(first['case']['trip_id'])
        with self.assertRaises(InputError):
            self.service.update(args)
        self.assertEqual(before, self.states.get(first['case']['trip_id']))
        args['facts']['height'] = {'value': 175, 'unit': 'in'}
        updated = self.service.update(args)
        self.assertEqual(2, updated['case']['revision'])
        self.assertEqual(175, updated['case']['facts']['height']['value'])
        repeat = self.service.update(args)
        # current_terminal_status carries a per-assessment fetch timestamp;
        # normalize it so the idempotence comparison covers content, not time.
        for payload in (updated, repeat):
            current = payload['evidence_package'].get('current_terminal_status')
            if isinstance(current, dict):
                current['retrieved_at'] = 'normalized-for-determinism-check'
        self.assertEqual(updated, repeat)

    def test_old_saved_inconsistent_facts_are_excluded_without_erasing_history(self):
        initial = self.service.assess(self.args(BASE, scope='induction'))
        case = self.states.get(initial['case']['trip_id'])
        case['facts']['trip_at']['source_text'] = 'Trip on September 6, 2026.'
        original = copy.deepcopy(case)
        result = evaluate_trip(self.reader, case)
        self.assertEqual('unresolved', result['requested_scope_status'])
        self.assertEqual('input_correction_required', result['decision_brief']['status'])
        self.assertEqual('unresolved', next(f for f in result['findings'] if f['requirement_id'] == 'apm_induction')['status'])
        self.assertEqual('trip_at', result['next_questions'][0]['field'])
        self.assertEqual(original, case)

    def test_positive_scoped_control_outage_and_roles_never_issue_trip_permission(self):
        for role in ('driver', 'dispatcher', 'unknown'):
            result = self.service.assess(self.args(BASE, scope='induction', role=role))
            self.assertEqual('met', result['decision_brief']['scoped_result'])
            self.assertEqual('not_issued', result['decision_brief']['operational_permission'])
            self.assertEqual('not_cleared', result['decision_brief']['status'])
        self.graph.available = False
        result = self.service.assess({'trip_id': result['case']['trip_id']})
        self.assertEqual('assessment_unavailable', result['decision_brief']['status'])
        self.assertEqual([], result['findings'])
        self.assertEqual('unresolved', result['decision_brief']['scoped_result'])

    def test_renderer_ignores_model_prose_and_escapes_all_reported_content(self):
        result = self.service.assess(self.args({'route_description': '<script>alert(1)</script>'}))
        result['decision_brief']['headline'] = 'SEND THE TRUCK NOW'
        result['assistant_answer'] = 'SEND THE TRUCK NOW'
        source = result['evidence_package']['sources'][0]
        source['source_text'] = '</pre><img src=x onerror=alert(1)>'
        report = render_trip_report(result)
        self.assertNotIn('SEND THE TRUCK NOW', report)
        self.assertNotIn('<script>', report)
        self.assertNotIn('<img', report)
        self.assertIn('&lt;script&gt;', report)
        self.assertIn("default-src 'none'", report)
        self.assertIn('Operational permission: not issued.', report)
        self.assertIn(result['assessment_id'], report)
        self.assertIn('Reported; unconfirmed', report)

    def test_mcp_rejects_contradiction_then_returns_schema_valid_review_and_brief(self):
        import jsonschema
        session = Session(CheckingService(self.graph), trip_service=self.service)
        session.state = 'ready'
        arguments = self.args({'height': {'value': 14, 'unit': 'ft'}}, '14 ft 7 in high')
        request = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                   'params': {'name': 'assess_trip', 'arguments': arguments}}
        rejected = session.handle(request)['result']
        self.assertTrue(rejected['isError'])
        self.assertNotIn('structuredContent', rejected)
        arguments['facts']['height'] = {'value': 175, 'unit': 'in'}
        response = session.handle(request)['result']
        self.assertFalse(response['isError'])
        self.assertEqual(response['structuredContent'], json.loads(response['content'][0]['text']))
        schema = next(t for t in TOOLS if t['name'] == 'assess_trip')['outputSchema']
        jsonschema.validate(response['structuredContent'], schema)
        self.graph.available = False
        jsonschema.validate(self.service.assess({'trip_id': response['structuredContent']['case']['trip_id']}), schema)
