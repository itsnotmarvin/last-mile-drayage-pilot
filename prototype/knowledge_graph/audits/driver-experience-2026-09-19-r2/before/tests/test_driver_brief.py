"""The short delivery must not lose evidence, scope limits, or revision binding."""
import copy
import json
import unittest

from neo4j_kg.driver_brief import driver_brief, retained_text
from neo4j_kg.driver_answer import driver_answer
import test_trip_assessment as fixtures


class DriverBriefTests(unittest.TestCase):
    setUp = fixtures.TripAssessmentTests.setUp
    create = fixtures.TripAssessmentTests.create
    update = fixtures.TripAssessmentTests.update

    @classmethod
    def setUpClass(cls):
        from kg.service import CheckingService
        from test_neo4j_migration import OracleReader
        cls.reader = OracleReader(CheckingService())

    def sample(self, route='path_a_exit13a_to_apm'):
        return self.create({**fixtures.BASE, 'route_id': route, 'height': {'value': 175, 'unit': 'in'},
                            'width': {'value': 102, 'unit': 'in'},
                            'gross_weight': {'value': 80000, 'unit': 'lb'}})

    def test_all_selected_passages_and_source_qualifications_survive_without_mutation(self):
        result = self.sample()
        before = copy.deepcopy(result)
        brief = driver_brief(result)
        for source in result['evidence_package']['sources']:
            for value in (source['url'], retained_text(source['source_text']), source['currentness']):
                self.assertIn(value, brief)
            note = source.get('provenance_review')
            if note:
                self.assertIn(note['recommended_locator'], brief)
                self.assertIn(note['note'], brief)
        for check in result['reported_fact_checks']['checks']:
            if check['comparison'] is not None:
                self.assertIn(check['context'], brief)
        self.assertEqual(before, result)
        self.assertLess(len(brief), len(json.dumps(result)) / 2)

    def test_correction_and_path_b_use_current_facts_and_actual_route_order(self):
        result = self.sample('path_b_us1_9_to_apm')
        changed = self.update(result, {'height': {'value': 162, 'unit': 'in'}}, correction=True)
        brief = driver_brief(changed)
        self.assertIn('revision=2', brief)
        self.assertIn('"height": {"value": 162', brief)
        self.assertNotIn('"height": {"value": 175', brief)
        sequence = changed['evidence_package']['route_context']['segments']
        self.assertEqual(5, len(sequence))
        self.assertIn(' → '.join(s['name'] for s in sequence), brief)
        self.assertNotIn('FR NJ Turnpike SB to NJ 81 NB →', brief)

    def test_outage_contains_no_previous_sources_or_positive_findings(self):
        result = self.sample()
        self.graph.available = False
        unavailable = self.service.assess({'trip_id': result['case']['trip_id']})
        brief = driver_brief(unavailable)
        self.assertIn('Evidence service unavailable', brief)
        self.assertIn('Operational permission: not issued', brief)
        self.assertNotIn('Retained source text:', brief)
        for source in result['evidence_package']['sources']:
            self.assertNotIn(source['url'], brief)

    def test_conflicting_reports_and_historical_observations_remain_explicit(self):
        result = self.update(self.sample(), {'height': {'value': 162, 'unit': 'in'}})
        brief = driver_brief(result)
        self.assertIn('Conflicting fields: height', brief)
        self.assertIn('Historical context only:', brief)
        self.assertIn('not verified for this trip', brief)
        self.assertNotIn('MUST utilize', brief)
        self.assertIn('unresolved', brief)

    def test_prepared_answer_preserves_width_access_and_correction_without_legal_label(self):
        a = self.sample()
        b = self.update(a, {'height': {'value': 162, 'unit': 'in'}}, correction=True)
        text = driver_answer(b)
        self.assertIn('reported height is 162 inches, at the cited 162', text)
        self.assertNotIn('reported height is 175', text)
        source = next(s for s in b['evidence_package']['sources']
                      if s['clause_id'] == 'reg_nj_terminal_access_102_inch_standard_truck')
        self.assertIn(source['source_text'], text)
        self.assertIn(source['url'], text)
        self.assertIn('Whether your truck and route meet those conditions has not been established', text)
        self.assertNotIn('legal length', text)

    def test_prepared_answer_does_not_infer_missing_credentials_or_reuse_outage_evidence(self):
        a = self.sample()
        text = driver_answer(a)
        self.assertNotIn('likely', text)
        self.assertNotIn('SeaLink number changed', text)
        self.graph.available = False
        b = self.service.assess({'trip_id': a['case']['trip_id']})
        self.assertNotIn('https://', driver_answer(b))
        self.assertIn('evidence service is unavailable', driver_answer(b))

    def test_prepared_answer_separates_schedule_heading_closure_excerpt_and_undated_rows(self):
        from test_terminal_status import stub_get
        from neo4j_kg.terminal_status import fetch
        a = self.sample()
        a['evidence_package']['current_terminal_status'] = fetch(get=stub_get)
        text = driver_answer(a)
        self.assertIn('It does not date a separate closure excerpt', text)
        self.assertIn('effective time is not stated', text)
        self.assertIn('Retrieval time does not establish when their contents apply', text)
        for source in a['evidence_package']['current_terminal_status']['sources']:
            self.assertIn(source['url'], text)

    def test_narrow_scope_does_not_become_a_full_trip_answer(self):
        a = self.create(scope='induction')
        self.assertEqual(driver_brief(a), driver_answer(a))
        self.assertNotIn('BEGIN DRIVER ANSWER', driver_answer(a))


if __name__ == '__main__':
    unittest.main()
