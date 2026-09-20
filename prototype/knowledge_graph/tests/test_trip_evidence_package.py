"""Evidence delivery fixes against frozen scenario expectations and source bytes."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from kg.service import CheckingService as OriginalService
from test_neo4j_migration import OracleReader
from test_trip_assessment import MemoryGraph
from neo4j_kg.assessment import TripService
from neo4j_kg.common import ArchiveError
from neo4j_kg.evidence import PORT_STREET_OBSERVATION
from neo4j_kg.provenance_notes import provenance_review
from neo4j_kg.retrieval_trace import receipt
from neo4j_kg.trip_state import TripStore

ROOT = Path(__file__).resolve().parents[1]
BOOK = json.loads((ROOT / 'audits/evidence-2026-09-10/casebook.json').read_text())


class TripEvidencePackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = OracleReader(OriginalService())

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.states = TripStore(Path(tmp.name) / 'trips.sqlite3')
        self.graph = MemoryGraph(self.reader)
        self.service = TripService(self.graph, self.states)
        self.count = 0

    def assess(self, facts=None, scope='trip_dispatch', role='unknown'):
        self.count += 1
        return self.service.assess({'facts': facts or {}, 'question_scope': scope,
                                   'requester_role': role, 'source_message': 'Synthetic package test',
                                   'request_key': f'package-{self.count}'})

    def test_all_frozen_families_receive_expected_passages_in_assessment(self):
        for case in BOOK['cases']:
            with self.subTest(case=case['id']):
                result = self.assess(case['expected_facts'])
                package = result['evidence_package']
                ids = [s['clause_id'] for s in package['sources']]
                self.assertTrue(set(case['audit_expected_clause_ids']) <= set(ids))
                self.assertEqual(len(ids), len(set(ids)))
                self.assertEqual('unresolved', result['requested_scope_status'])
                for source in package['sources']:
                    original = self.reader.record(source['clause_id'])
                    self.assertEqual(original['source_text'], source['source_text'])
                    self.assertEqual(original['source_locator'], source['locator'])
                for link, finding in zip(package['requirement_links'], result['findings']):
                    self.assertEqual(finding['requirement_id'], link['requirement_id'])
                    self.assertEqual(finding['source_clause_ids'], link['source_clause_ids'])

    def test_driver_dispatcher_unknown_share_evidence_without_shared_trip_facts(self):
        facts = BOOK['cases'][0]['expected_facts']
        runs = [self.assess(facts, role=role) for role in ('driver', 'dispatcher', 'unknown')]
        self.assertEqual(3, len({r['case']['trip_id'] for r in runs}))
        for result in runs[1:]:
            # current_terminal_status carries a per-assessment fetch timestamp;
            # normalize it so the comparison covers evidence identity, not time.
            for run in (runs[0], result):
                current = run['evidence_package'].get('current_terminal_status')
                if isinstance(current, dict):
                    current['retrieved_at'] = 'normalized-for-determinism-check'
                    for source in current.get('sources', []):
                        source['retrieved_at'] = 'normalized-for-determinism-check'
            self.assertEqual(runs[0]['evidence_package'], result['evidence_package'])
            self.assertEqual(runs[0]['findings'], result['findings'])
        new_move = self.assess({'terminal_id': 'facility_apm_elizabeth'})
        self.assertNotIn('gross_weight', new_move['case']['facts'])
        self.assertNotIn('user_reported', json.dumps(new_move['evidence_package']['sources']))

    def test_port_street_is_separate_dated_context_and_trace_reports_it(self):
        result = self.assess({'port_street_in_route': True})
        obs = result['evidence_package']['observations'][0]
        self.assertEqual(self.reader.record(PORT_STREET_OBSERVATION), obs['record'])
        self.assertFalse(obs['operational_use'])
        self.assertIn('observed_at', obs['record']['archive_context'])
        self.assertNotIn(PORT_STREET_OBSERVATION, [s['clause_id'] for s in result['evidence_package']['sources']])
        self.assertEqual([PORT_STREET_OBSERVATION], receipt(result)['delivered_observation_ids'])
        focused = self.service.evidence({'requirement_id': 'current_route_conditions'})
        self.assertEqual([obs], focused['observations'])

    def test_scope_and_route_reports_bound_context_without_promoting_unknowns(self):
        unknown = self.assess()
        self.assertTrue(unknown['evidence_package']['observations'])
        no_port = self.assess({'port_street_in_route': False})
        self.assertEqual([], no_port['evidence_package']['observations'])
        for scope in ('induction', 'terminal_entry'):
            narrow = self.assess(scope=scope)['evidence_package']
            self.assertEqual([], narrow['observations'])
            self.assertNotIn('reg_njta_roadway_use_limitations', [s['clause_id'] for s in narrow['sources']])
        conflicted = self.service.update({'trip_id': no_port['case']['trip_id'],
            'expected_revision': 1, 'requester_role': 'driver', 'question_scope': 'trip_dispatch',
            'facts': {'port_street_in_route': True}, 'source_message': 'Conflicting synthetic report',
            'request_key': 'port-conflict'})
        self.assertTrue(conflicted['case']['conflicts'])
        self.assertTrue(conflicted['evidence_package']['observations'])

    def test_correction_rebuilds_package_without_mutating_returned_or_shared_evidence(self):
        initial = self.assess({'port_street_in_route': True})
        before = copy.deepcopy(self.reader.record(PORT_STREET_OBSERVATION))
        initial['evidence_package']['observations'][0]['record']['source_text'] = 'forged'
        corrected = self.service.update({'trip_id': initial['case']['trip_id'],
            'expected_revision': 1, 'requester_role': 'dispatcher', 'question_scope': 'trip_dispatch',
            'facts': {'port_street_in_route': False}, 'replace_conflicts': True,
            'source_message': 'Explicit synthetic correction', 'request_key': 'port-correct'})
        self.assertEqual([], corrected['evidence_package']['observations'])
        self.assertEqual(before, self.reader.record(PORT_STREET_OBSERVATION))
        self.assertEqual(before, self.assess()['evidence_package']['observations'][0]['record'])

    def test_missing_bundle_evidence_fails_closed_after_fact_write(self):
        original = self.reader
        class MissingEvidence:
            release = original.release
            def __getattr__(self, name):
                return getattr(original, name)
            def record(self, node_id):
                if node_id == PORT_STREET_OBSERVATION:
                    raise ArchiveError('missing observation')
                return original.record(node_id)
        self.graph.reader = MissingEvidence()
        failed = self.assess()
        self.assertEqual('unavailable', failed['service_status'])
        self.assertEqual(1, failed['write_receipt']['revision'])
        self.assertEqual([], failed['findings'])
        self.assertEqual([], failed['evidence_package']['sources'])
        self.assertEqual([], failed['evidence_package']['observations'])

    def test_provenance_reviews_are_release_scoped_and_preserve_archive(self):
        package = self.assess()['evidence_package']
        sources = {s['clause_id']: s for s in package['sources']}
        route = sources['reg_nj_single_trip_route_review_13_18_portal_copy']
        self.assertIn('pages 3-4', route['locator'])
        self.assertIn('pages 2-3', route['provenance_review']['recommended_locator'])
        table = sources['reg_nj_ocean_container_permit']
        self.assertTrue(table['verbatim'])  # Retained archive declaration, with explicit correction note.
        self.assertEqual('prose_and_linearized_table', table['provenance_review']['quotation_form'])
        self.assertIsNone(provenance_review('different-release', table['clause_id']))
