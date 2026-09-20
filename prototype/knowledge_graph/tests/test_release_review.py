"""Source-impact and audit-integrity controls; no asserted legal approvals."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from neo4j_kg.common import ROOT, ArchiveError, digest, encode
from neo4j_kg.requirements import applicable_requirements
from neo4j_kg.source_review import compare_releases, review_packet, source_inventory
from neo4j_kg.release_readiness import assess_readiness, runtime_hashes, verify_capture


def seal(release):
    release['revision'] = digest({k: v for k, v in release.items() if k != 'revision'})
    return release


class SourceReviewTests(unittest.TestCase):
    def setUp(self):
        self.release = json.loads((ROOT/'data/neo4j_release.json').read_text())
        self.source = 'ecfr_23_cfr_658_17_2026_07_29'
        self.clause = 'reg_federal_interstate_weight'
        self.all_requirements = {r['id'] for r in applicable_requirements({}, 'trip_dispatch')}

    def change_record(self, nid, field, value):
        candidate = copy.deepcopy(self.release)
        node = next(n for n in candidate['nodes'] if n['id'] == nid)
        record = json.loads(node['record_json']); record[field] = value
        node['record_json'] = encode(record)
        return seal(candidate)

    def affected(self, candidate):
        report = compare_releases(self.release, candidate)
        self.assertEqual('review_required', report['status'])
        self.assertFalse(report['automatic_activation'])
        return {r['requirement_id'] for r in report['affected_requirements']}

    def test_inventory_preserves_dates_draft_owners_and_operating_context(self):
        result = source_inventory(self.release)
        self.assertEqual(33, len(result['sources']))
        self.assertEqual(['transaction_release'], result['requirements_without_retained_clauses'])
        self.assertEqual([], result['missing_required_clause_ids'])
        federal = next(s for s in result['sources'] if s['source_id'] == self.source)
        self.assertIsNone(federal['publication_date'])
        self.assertEqual('2026-07-31', federal['accessed_date'])
        self.assertIsNone(federal['assigned_reviewer'])
        self.assertEqual(['axle_weight_evidence'], federal['requirement_ids'])
        for source in result['sources']:
            self.assertEqual(bool(source['observation_ids']), bool(source['operating_context_requirement']))

    def test_packet_retains_exact_records_and_all_requirements(self):
        packet = review_packet(self.release)
        self.assertTrue(packet['reported_catalog_matches_release'])
        self.assertEqual(self.all_requirements, {r['id'] for r in packet['requirements']})
        original = {n['id']: json.loads(n['record_json']) for n in self.release['nodes'] if n['kind'] == 'source_clause'}
        self.assertEqual(original, {r['clause_id']: r['record'] for r in packet['retained_clauses']})
        self.assertEqual(23, len(packet['reported_check_catalog']['checks']))

    def test_equal_snapshots_do_not_certify_current_law(self):
        result = compare_releases(self.release, copy.deepcopy(self.release))
        self.assertEqual('no_change', result['status'])
        self.assertFalse(result['operational_use'])
        self.assertEqual([], result['affected_requirements'])
        self.assertIn('not current law', result['limits'][0])

    def test_clause_text_and_locator_changes_map_to_requirement(self):
        for field in ('source_text', 'source_locator', 'source_text_verbatim'):
            with self.subTest(field=field):
                self.assertEqual({'axle_weight_evidence'}, self.affected(self.change_record(self.clause, field, 'Synthetic candidate edit')))

    def test_source_metadata_and_archived_bytes_affect_dependent_rules(self):
        for field in ('publication_date', 'url', 'publisher'):
            with self.subTest(field=field):
                self.assertEqual({'axle_weight_evidence'}, self.affected(self.change_record(self.source, field, 'Synthetic candidate edit')))
        candidate = copy.deepcopy(self.release)
        path = next(s for s in source_inventory(candidate)['sources'] if s['source_id'] == self.source)['archived_files'][0]['path']
        candidate['file_hashes'][path] = '0'*64
        self.assertEqual({'axle_weight_evidence'}, self.affected(seal(candidate)))

    def test_relationship_context_unattributed_file_and_metadata_require_broad_review(self):
        candidates = []
        candidate = copy.deepcopy(self.release); candidate['edges'][0]['relationship'] = 'SYNTHETIC_CHANGED'; candidates.append(candidate)
        candidate = copy.deepcopy(self.release); candidate['nodes'][0]['layer'] = 'synthetic_changed'; candidates.append(candidate)
        candidate = copy.deepcopy(self.release); candidate['file_hashes']['unattributed.json'] = '0'*64; candidates.append(candidate)
        candidate = copy.deepcopy(self.release); candidate['versions']['review_test'] = 'changed'; candidates.append(candidate)
        for candidate in candidates:
            with self.subTest(revision=seal(candidate)['revision']):
                self.assertEqual(self.all_requirements, self.affected(candidate))

    def test_removed_required_clause_is_explicit(self):
        candidate = copy.deepcopy(self.release)
        candidate['nodes'] = [n for n in candidate['nodes'] if n['id'] != self.clause]
        candidate['edges'] = [e for e in candidate['edges'] if self.clause not in (e['from'], e['to'])]
        for collection in ('nodes', 'edges'):
            for i, row in enumerate(candidate[collection]): row['ordinal'] = i
        result = compare_releases(self.release, seal(candidate))
        affected = next(r for r in result['affected_requirements'] if r['requirement_id'] == 'axle_weight_evidence')
        self.assertIn(self.clause, affected['missing_clause_ids'])
        self.assertIn(self.clause, source_inventory(candidate)['missing_required_clause_ids'])

    def test_tampered_and_malformed_releases_are_rejected(self):
        tampered = copy.deepcopy(self.release); tampered['versions']['x'] = 'unsealed'
        malformed = self.change_record(self.source, 'archived_files', [None])
        for value in (None, [], {}, tampered, malformed):
            with self.subTest(value=type(value)), self.assertRaises(ArchiveError):
                source_inventory(value)


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.release = json.loads((ROOT/'data/neo4j_release.json').read_text())
        self.scope = json.loads((ROOT/'data/release_scope.json').read_text())
        self.hashes = runtime_hashes()

    def capture(self, directory, hashes=None):
        path = Path(directory)
        (path/'summary.json').write_text(json.dumps({'runtime_sha256': self.hashes if hashes is None else hashes,
                                                   'graph_release': self.release['revision']}))
        (path/'result.txt').write_text('Synthetic test capture')
        manifest = {'algorithm': 'sha256', 'files': {
            p.name: {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size}
            for p in path.iterdir() if p.name != 'artifact-manifest.json'}}
        (path/'artifact-manifest.json').write_text(json.dumps(manifest))
        return path

    def test_runtime_hashes_cover_application_mcp_catalog_and_review_command(self):
        for path in ('run_neo4j_mcp.py', 'neo4j_kg/axle_layout.py', 'trip_app/static/app.js',
                     'data/reported_checks.json', 'data/release_scope.json', 'tools/review_release.py'):
            self.assertIn(path, self.hashes)
        self.assertFalse(any(p.startswith('kg/') for p in self.hashes))

    def test_manifest_bound_current_capture_passes_binding_only(self):
        with tempfile.TemporaryDirectory() as d:
            result = verify_capture(self.capture(d), self.hashes)
            self.assertEqual('matches_current_runtime', result['status'])
            self.assertIn('does not authenticate reviewers', result['limits'])

    def test_missing_changed_and_removed_runtime_paths_are_stale(self):
        variants = []
        missing = dict(self.hashes); missing.pop('trip_app/static/app.js'); variants.append((missing, 'missing_runtime_paths'))
        changed = dict(self.hashes); changed['trip_app/static/app.js'] = '0'*64; variants.append((changed, 'changed_runtime_paths'))
        removed = dict(self.hashes); removed['removed.py'] = '0'*64; variants.append((removed, 'removed_runtime_paths'))
        for hashes, field in variants:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as d:
                result = verify_capture(self.capture(d, hashes), self.hashes)
                self.assertEqual('stale_for_current_runtime', result['status'])
                self.assertTrue(result[field])

    def test_capture_must_bind_the_expected_graph_release_when_readiness_checks_it(self):
        with tempfile.TemporaryDirectory() as d:
            path = self.capture(d)
            result = verify_capture(path, self.hashes, '0'*64)
            self.assertEqual('stale_for_current_release', result['status'])
            self.assertEqual('failed', result['graph_release_binding'])
            result = verify_capture(path, self.hashes, self.release['revision'])
            self.assertEqual('matches_current_runtime', result['status'])
            self.assertEqual('passed', result['graph_release_binding'])

    def test_tampered_artifact_unbound_summary_malformed_and_escaping_manifests_fail(self):
        for variant in ('tampered', 'summary', 'escape', 'malformed', 'hashes'):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as d:
                path = self.capture(d)
                manifest = json.loads((path/'artifact-manifest.json').read_text())
                if variant == 'tampered': (path/'result.txt').write_text('Changed')
                elif variant == 'summary': del manifest['files']['summary.json']
                elif variant == 'escape': manifest['files']['../outside.txt'] = '0'*64
                elif variant == 'malformed': manifest['files'] = []
                else:
                    self.capture(d, [])
                    manifest = json.loads((path/'artifact-manifest.json').read_text())
                (path/'artifact-manifest.json').write_text(json.dumps(manifest))
                self.assertEqual('invalid_capture', verify_capture(path, self.hashes)['status'])

    def test_honest_readiness_includes_actual_gaps_even_with_current_capture(self):
        with tempfile.TemporaryDirectory() as d:
            result = assess_readiness(self.release, self.scope, self.capture(d), check_source_files=False)
        self.assertEqual('blocked', result['status'])
        self.assertFalse(result['production_launch_authorized'])
        self.assertEqual([], result['unimplemented_requirement_ids'])
        self.assertEqual(11, len(result['implemented_bounded_requirement_ids']))
        self.assertIn('bounded_evaluator_coverage', {b['id'] for b in result['blockers']})
        self.assertIn('draft_supplement_review', {b['id'] for b in result['blockers']})
        self.assertEqual(['transaction_release'], result['requirements_without_retained_clauses'])
        blockers = {b['id'] for b in result['blockers']}
        self.assertNotIn('current_runtime_capture_missing', blockers)
        self.assertIn('source_bytes_unverified', blockers)
        self.assertIn('governing_evidence_gaps', blockers)
        self.assertIn('runtime_is_synthetic', blockers)

    def test_scope_narrowing_pretend_approval_and_omitted_acceptance_are_rejected(self):
        variants = []
        narrowed = copy.deepcopy(self.scope); narrowed['required_requirement_ids'].pop(); variants.append(narrowed)
        approved = copy.deepcopy(self.scope); approved['approval_status'] = 'approved'; variants.append(approved)
        omitted = copy.deepcopy(self.scope); omitted['external_acceptance_required'].pop(); variants.append(omitted)
        malformed = copy.deepcopy(self.scope); malformed['required_families'] = None; variants.append(malformed)
        for scope in variants:
            with self.subTest(scope=scope['approval_status']), self.assertRaises(ArchiveError):
                assess_readiness(self.release, scope, check_source_files=False)
        submitted = copy.deepcopy(self.scope); submitted['production_launch_authorized'] = True
        self.assertFalse(assess_readiness(self.release, submitted, check_source_files=False)['production_launch_authorized'])

    def test_cli_generates_private_reports_refuses_overwrite_and_returns_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)/'review.json'
            command = ['python3', 'tools/review_release.py', 'inventory', '--output', str(out)]
            run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(0, run.returncode, run.stderr)
            self.assertEqual(0o600, out.stat().st_mode & 0o777)
            before = out.read_bytes()
            run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(1, run.returncode)
            self.assertEqual(before, out.read_bytes())
            run = subprocess.run(['python3', 'tools/review_release.py', 'readiness'], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(2, run.returncode, run.stderr)
            self.assertEqual('blocked', json.loads(run.stdout)['status'])


if __name__ == '__main__':
    unittest.main()
