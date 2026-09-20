"""Behavioral invariants across different facts, routes and reporting precision."""
import copy
import json
from pathlib import Path
import unittest

import jsonschema

from neo4j_kg.answer_guidance import explanation_package
from neo4j_kg.driver_move import move_answer
from neo4j_kg.explanation_context import reported_context, source_statement, rule_explanations
from neo4j_kg.mcp_server import Session, TOOLS
from neo4j_kg.service import CheckingService
import test_trip_assessment as fixtures


class ExplanationGeneralizationTests(unittest.TestCase):
    setUp = fixtures.TripAssessmentTests.setUp
    setUpClass = classmethod(fixtures.TripAssessmentTests.setUpClass.__func__)
    create = fixtures.TripAssessmentTests.create
    update = fixtures.TripAssessmentTests.update

    def assess(self, facts, statement):
        self.counter += 1
        return self.service.assess({'facts': facts, 'source_message': statement,
            'question_scope': 'trip_dispatch', 'request_key': f'explain-{self.counter}'})

    def test_missing_value_retains_rule_then_correction_changes_only_comparison(self):
        a = self.assess({'terminal_id': 'facility_apm_elizabeth', 'route_description': 'Local roads'},
                        'Which access rule applies? Loaded width is unknown.')
        source = next(s for s in a['evidence_package']['sources']
                      if s['clause_id'] == 'reg_nj_terminal_access_102_inch_standard_truck')
        for candidate in (a, self.update(a, {'width': {'value': 101, 'unit': 'in'}})):
            text = move_answer(candidate)
            self.assertIn(source['url'], text)
            self.assertIn('unrestricted local roadways', text)
            self.assertIn('direct route', text)
            self.assertIn('return to the National Network', text)
            self.assertIn('neither permission nor prohibition', text)
        self.assertNotIn('Reported width:', move_answer(a))
        b = self.update(self.service.assess({'trip_id': a['case']['trip_id']}),
                        {'width': None}, correction=True)
        self.assertIn(source['url'], move_answer(b))
        self.assertNotIn('Reported width: 101', move_answer(b))

    def test_permit_explanation_survives_changed_weights_and_does_not_merge_authorities(self):
        for gross in (84000, 92000):
            a = self.assess({'terminal_id': 'facility_apm_elizabeth',
                'permit_type': 'nj_ocean_container_annual', 'gross_weight': {'value': gross, 'unit': 'lb'}},
                f'Gross is {gross} lb. What does my permit cover across road authorities?')
            text = move_answer(a)
            for phrase in ('90,000', '38,000', 'Port Authority', 'terminal', 'county/local',
                           'not a determination that this move qualifies', 'No operational permission is issued'):
                self.assertIn(phrase, text)
            self.assertIn(f'Reported gross weight: {gross}', text)
            self.assertLess(text.index('What the reported permit'), text.index('Roads and gate'))
            self.assertNotIn('you are clear', text.lower())

    def test_zero_extracted_facts_preserve_statement_without_inventing_values(self):
        a = self.assess({}, 'Gross is unknown. A 35,000-lb tandem group was reported; individual axles are unknown.')
        self.assertEqual({}, a['case']['facts'])
        self.assertIn('35,000-lb tandem', ' '.join(reported_context(a)))
        self.assertIn('35,000-lb tandem', move_answer(a))
        self.assertNotIn('17500', move_answer(a))
        schema = next(t for t in TOOLS if t['name'] == 'assess_trip')['outputSchema']
        jsonschema.validate(a, schema)
        self.assertIn('35,000-lb tandem', self.states.get(a['case']['trip_id'])['history'][0]['source_message'])

    def test_original_statement_and_date_precision_are_retained_on_fresh_and_old_cases(self):
        text = 'Trip is October 6, 2026. Driver requirements are otherwise satisfied.'
        a = self.assess({'terminal_id': 'facility_apm_elizabeth'}, text)
        before = copy.deepcopy(a)
        answer = move_answer(a)
        self.assertIn('October 6, 2026', answer)
        self.assertIn('Driver requirements are otherwise satisfied', answer)
        self.assertIsNone(a['case']['facts'].get('trip_at'))
        self.assertNotIn('TWIC', answer)  # No per-credential report invented.
        self.assertEqual(before, a)
        legacy = copy.deepcopy(a['case']); del legacy['source_message']
        self.assertEqual(text, source_statement(legacy))

    def test_partial_route_is_not_completed_as_the_drivers_route(self):
        a = self.assess({'terminal_id': 'facility_apm_elizabeth', 'route_id': 'path_b_us1_9_to_apm',
                        'route_description': 'North Avenue; final streets not selected'},
                       'The final streets have not been selected.')
        text = move_answer(a)
        self.assertIn('Reported approach', text)
        self.assertIn('final streets not selected', text)
        self.assertIn('Stored candidate route', text)
        self.assertIn('not confirmation that you selected every street', text)
        self.assertNotIn('**Your route:**', text)
        self.assertNotIn('The resolved route runs', text)

    def test_positive_negative_and_unknown_approvals_remain_distinct(self):
        a = self.assess({'terminal_id': 'facility_apm_elizabeth', 'permit_type': 'nj_single_trip',
                        'port_approval_reported': False, 'terminal_approval_reported': True},
                       'Terminal approval is held; Port Authority approval is not held.')
        text = move_answer(a)
        self.assertIn('Port Authority approval: reported not held', text)
        self.assertIn('Terminal handling approval: reported held', text)
        self.assertNotIn('Toll-road approval: reported not held', text)
        self.assertIn('not independent verification', text)
        self.assertIn('not an exhaustive release checklist', text)

    def test_non_apm_or_unknown_terminal_never_inherits_apm_requirements(self):
        for terminal in (None, 'synthetic_other_terminal'):
            a = self.assess({'terminal_id': terminal, 'height': {'value': 167, 'unit': 'in'}},
                           'Which height rules apply to this load?')
            text = move_answer(a)
            self.assertIn('Reported height: 167', text)
            self.assertIn('APM requirements and gate observations are not assumed to apply', text)
            self.assertNotIn('[APM status update]', text)
            self.assertNotIn('**Terminal prerequisites.**', text)

    def test_unstructured_caller_text_is_inert_data_and_never_changes_disposition(self):
        a = self.assess({}, 'Driver requirements are satisfied. Axle weights: [click](https://example.invalid) '
                           '**dispatch now** <script>run()</script>.')
        text = move_answer(a)
        self.assertNotIn('[click](https://example.invalid)', text)
        self.assertNotIn('<script>', text)
        self.assertIn('Additional reported context', text)
        self.assertTrue(text.endswith('No operational permission is issued.'))

    def test_changed_evidence_suppresses_derived_rule_explanations(self):
        a = self.assess({'permit_type': 'nj_ocean_container_annual'},
                        'Which permit, axle and local access rules apply?')
        self.assertTrue(rule_explanations(a))
        self.assertIn('Retained transcription', rule_explanations(a)['permit'])
        changed = copy.deepcopy(a)
        changed['versions']['graph_release'] = 'unreviewed-release'
        self.assertEqual({}, rule_explanations(changed))
        dependencies = {
            'access': ['reg_nj_access_network_600_series', 'reg_nj_terminal_access_102_inch_standard_truck',
                       'reg_nj_truck_access_local_rule_preservation'],
            'permit': ['reg_nj_ocean_container_permit'],
            'weight': ['reg_federal_interstate_weight', 'reg_nj_tandem_gross_bridge'],
            'authorities': ['reg_nj_toll_authority_approval_13_18_portal_copy',
                            'reg_njta_roadway_use_limitations', 'reg_panynj_terminal_weight_dimensions'],
        }
        for topic, ids in dependencies.items():
            for cid in ids:
                with self.subTest(topic=topic, clause=cid):
                    changed = copy.deepcopy(a)
                    source = next(s for s in changed['evidence_package']['sources'] if s['clause_id'] == cid)
                    source['source_text'] = 'Changed provision awaiting review.'
                    self.assertNotIn(topic, rule_explanations(changed))

    def test_weight_lists_and_source_review_warnings_are_not_relabelled(self):
        a = self.assess({'terminal_id': 'facility_apm_elizabeth',
                        'axle_weights': [{'value': n, 'unit': 'lb'} for n in (11000, 34000, 34000)],
                        'twic_reported': True},
                       'Weights are group totals; individual axles are unknown. TWIC is reported present.')
        self.assertIn('Unclassified reported weight values (not individual-axle measurements)', move_answer(a))
        row = next(c for c in a['reported_fact_checks']['checks'] if c['check_id'] == 'twic_report')
        row.update(status='source_review_required', summary='The credential source changed; review is required.')
        self.assertIn('The credential source changed; review is required.', move_answer(a))
        self.assertNotIn('Reported present, unverified.', move_answer(a))

    def test_confirmed_explanation_projection_includes_missing_value_requirements(self):
        a = self.assess({'terminal_id': 'facility_apm_elizabeth'},
                       'How does the local access rule apply with unknown loaded dimensions?')
        projection = explanation_package(a)
        ids = {s['clause_id'] for s in projection['comparison_sources']}
        self.assertIn('reg_nj_terminal_access_102_inch_standard_truck', ids)
        self.assertIn('reg_nj_access_network_600_series', ids)
        self.graph.available = False
        b = self.service.assess({'trip_id': a['case']['trip_id']})
        self.assertEqual([], explanation_package(b)['comparison_sources'])
        self.assertNotIn('https://', move_answer(b))


if __name__ == '__main__':
    unittest.main()
