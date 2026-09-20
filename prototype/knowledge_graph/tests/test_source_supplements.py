"""Fail-closed source delivery regressions; never mutate archived source files."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import jsonschema
import test_requirement_evaluators as fixtures
from neo4j_kg import source_supplements as supplements
from neo4j_kg.common import ArchiveError
from neo4j_kg.service import Evaluation
from neo4j_kg.trip_tools import ASSESSMENT_SCHEMA
from verification_fixtures import RELEASE


class SourceSupplementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.EvaluatorTests.setUpClass()

    def setUp(self):
        self.fixture = fixtures.EvaluatorTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.store.put(self.fixture.records, self.fixture.case, RELEASE)
        self.evaluation = Evaluation(self.fixture.reader)
        self.ids = list(supplements.REQUIRED_SUPPLEMENTS)
        self.entries = supplements.draft_supplements(self.evaluation, self.ids)
        self.raw = [json.loads((supplements.ROOT / p).read_text()) for p in supplements.PATHS]
        self.validator = jsonschema.Draft202012Validator(ASSESSMENT_SCHEMA)

    def assess_delivery(self, entries, schema_rejection=False):
        with patch('neo4j_kg.evidence.draft_supplements', return_value=entries):
            result = self.fixture.assessment()
        if schema_rejection:
            # Deliberately bypass the loader with forbidden output metadata:
            # both the finding guard and the wire schema must reject a pass.
            with self.assertRaises(jsonschema.ValidationError):
                self.validator.validate(result)
        else:
            self.validator.validate(result)
        self.assertEqual('not_issued', result['decision_brief']['operational_permission'])
        return result

    def assert_unresolved(self, result, rid):
        row = self.fixture.finding(result, rid)
        self.assertEqual('unresolved', row['status'])
        self.assertIn('SOURCE_COVERAGE_INCOMPLETE', row['reason_codes'])
        self.assertNotIn('BOUNDED_SYNTHETIC_PREDICATES_MET', row['reason_codes'])
        self.assertIn('source_coverage_resolution', row['verification_needed'])

    def test_positive_control_delivers_all_exact_source_entries(self):
        result = self.assess_delivery(self.entries)
        for rid, ids in supplements.REQUIRED_SUPPLEMENTS.items():
            self.assertEqual('met', self.fixture.finding(result, rid)['status'])
            self.assertTrue(set(ids) <= {e['id'] for e in self.entries})

    def test_removing_each_required_entry_prevents_a_pass(self):
        for rid, ids in supplements.REQUIRED_SUPPLEMENTS.items():
            for eid in ids:
                with self.subTest(requirement=rid, missing=eid):
                    result = self.assess_delivery([e for e in self.entries if e['id'] != eid])
                    self.assert_unresolved(result, rid)
                    other = next(r for r in self.ids if r != rid)
                    self.assertEqual('met', self.fixture.finding(result, other)['status'])

    def test_empty_delivery_does_not_reuse_a_previous_pass(self):
        before = self.assess_delivery(self.entries)
        after = self.assess_delivery([])
        self.assertNotEqual(before['assessment_id'], after['assessment_id'])
        for rid in self.ids:
            self.assert_unresolved(after, rid)

    def test_remapped_tampered_duplicate_or_wrong_release_delivery_is_unresolved(self):
        changes = (
            {'requirement_ids': ['driver_twic']}, {'source_text': 'Altered rule'},
            {'locator': 'Wrong page'}, {'source_file_sha256': '0' * 64},
            {'source_id': 'different_source'}, {'graph_release': '0' * 64},
            {'approval_status': 'approved'}, {'operational_use': True},
            {'archive_graph_membership': True},
        )
        for rid, ids in supplements.REQUIRED_SUPPLEMENTS.items():
            for mutation in changes:
                with self.subTest(requirement=rid, mutation=mutation):
                    entries = copy.deepcopy(self.entries)
                    next(e for e in entries if e['id'] == ids[0]).update(mutation)
                    self.assert_unresolved(self.assess_delivery(entries, schema_rejection=bool(
                        set(mutation) & {'approval_status', 'operational_use', 'archive_graph_membership'})), rid)
            duplicate = next(e for e in self.entries if e['id'] == ids[0])
            self.assert_unresolved(self.assess_delivery(self.entries + [duplicate]), rid)

    def run_loader(self, raw):
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for i, document in enumerate(raw):
                path = Path(directory) / (str(i) + '.json')
                path.write_text(json.dumps(document))
                paths.append(str(path))
            with patch.object(supplements, 'PATHS', paths):
                return supplements.draft_supplements(self.evaluation, self.ids)

    def test_loader_rejects_each_removed_entry(self):
        for index, document in enumerate(self.raw):
            for entry in document['entries']:
                with self.subTest(missing=entry['id']):
                    raw = copy.deepcopy(self.raw)
                    raw[index]['entries'] = [e for e in raw[index]['entries'] if e['id'] != entry['id']]
                    with self.assertRaises(ArchiveError):
                        self.run_loader(raw)

    def test_loader_rejects_mapping_text_schema_and_release_tampering(self):
        for mutate in (
            lambda d: d.update(graph_release='0'*64),
            lambda d: d.update(operational_use=True),
            lambda d: d.update(unexpected=True),
            lambda d: d['entries'][0].update(requirement_ids=['driver_twic']),
            lambda d: d['entries'][0].update(source_text='Altered rule'),
            lambda d: d['entries'][0].update(unexpected=True),
            lambda d: d['entries'].append(copy.deepcopy(d['entries'][0])),
        ):
            raw = copy.deepcopy(self.raw)
            mutate(raw[0])
            with self.assertRaises(ArchiveError):
                self.run_loader(raw)

    def test_source_pdf_bytes_and_graph_file_mapping_are_required(self):
        # Substitute reads only. The real source archive remains byte-identical.
        original = Path.read_bytes
        def changed_bytes(path):
            return b'tampered PDF' if path.suffix == '.pdf' else original(path)
        with patch.object(Path, 'read_bytes', changed_bytes):
            with self.assertRaises(ArchiveError):
                supplements.draft_supplements(self.evaluation, self.ids)
        original_record = self.fixture.reader.record
        def without_files(record_id):
            record = copy.deepcopy(original_record(record_id))
            if 'archived_files' in record:
                record['archived_files'] = []
            return record
        with patch.object(self.fixture.reader, 'record', side_effect=without_files):
            with self.assertRaises(ArchiveError):
                supplements.draft_supplements(self.evaluation, self.ids)

    def test_loader_failure_returns_no_cached_findings(self):
        self.assertEqual('available', self.fixture.assessment()['service_status'])
        with patch('neo4j_kg.evidence.draft_supplements', side_effect=ArchiveError('Invalid source')):
            result = self.fixture.assessment()
        self.validator.validate(result)
        self.assertEqual('unavailable', result['service_status'])
        self.assertEqual([], result['findings'])
        self.assertEqual([], result['verification_evidence']['accepted_receipts'])


if __name__ == '__main__':
    unittest.main()
