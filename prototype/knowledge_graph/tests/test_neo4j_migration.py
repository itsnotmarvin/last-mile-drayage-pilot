"""Migration contracts against the byte-preserved historical evaluator."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from kg.service import CheckingService as OriginalService
from neo4j_kg.common import ArchiveError, digest, validate_release, verify_files
from neo4j_kg.service import CheckingService, Evaluation, normalize
from neo4j_kg.mcp_server import Session
from neo4j_kg.store import Neo4jStore

ROOT = Path(__file__).resolve().parents[1]
SUITE = json.loads((ROOT / "tests/acceptance.json").read_text())
RELEASE = json.loads((ROOT / "data/neo4j_release.json").read_text())


def substantive(result):
    result = copy.deepcopy(result)
    result.pop("evaluation_id", None)
    result["versions"].pop("implementation")
    result["versions"].pop("graph_release", None)
    if "engine" in result:
        result.pop("engine")
    return result


class OracleReader:
    """Independent adapter to the frozen graph for pure evaluator parity tests."""
    def __init__(self, original):
        self.original = original
        self.release = RELEASE

    def node(self, node_id, required=True):
        if node_id not in self.original.graph:
            if required:
                raise ArchiveError("Missing record")
            return None
        return {**copy.deepcopy(self.original.graph.nodes[node_id]),
                "archive": node_id in self.original.archive.graph}

    def record(self, node_id):
        return self.node(node_id)["record"]

    def neighbors(self, node_id, relationship, incoming=False):
        if incoming:
            return sorted(a for a, _, attrs in self.original.graph.in_edges(node_id, data=True)
                          if attrs["relationship"] == relationship)
        return self.original.targets(node_id, relationship)

    def records_by_kind(self, kinds, archive_only=True):
        return [copy.deepcopy(attrs["record"]) for _, attrs in self.original.archive.graph.nodes(data=True)
                if attrs["kind"] in kinds]

    def summary(self):
        return {**self.original.archive.summary(),
                "prototype_node_count": self.original.graph.number_of_nodes(),
                "prototype_edge_count": self.original.graph.number_of_edges()}


class MigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = OriginalService()
        cls.new = Evaluation(OracleReader(cls.original))

    def test_every_frozen_acceptance_result_field_is_preserved(self):
        for case in SUITE["cases"]:
            with self.subTest(case=case["case_id"]):
                args = SUITE["default_input"] | case["changes"]
                self.assertEqual(substantive(self.original.check(args)), substantive(self.new.check(args)))

    def test_every_context_result_field_is_preserved(self):
        for topic in ("summary", "induction", "route_directions", "port_street", "coverage"):
            with self.subTest(topic=topic):
                self.assertEqual(substantive(self.original.context(topic)), substantive(self.new.context(topic)))

    def test_normalization_and_invalid_inputs_match_original(self):
        from kg.service import normalize as original_normalize
        for args in ({}, SUITE["default_input"], {"question_scope": None}, {"question_scope": "route"}):
            self.assertEqual(original_normalize(args), normalize(args))
        for args in ({"completed": True}, {"driver_id": "real-person"}, {"trip_at": "tomorrow"}, {"company_changed": 1}):
            with self.assertRaises(ValueError):
                normalize(args)

    def test_snapshot_rebuild_matches_every_record_and_edge(self):
        spec = importlib.util.spec_from_file_location("snapshot_builder", ROOT / "tools/build_neo4j_snapshot.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(RELEASE, module.build_release())

    def test_original_files_and_archived_bytes_are_verified(self):
        verify_files(RELEASE)

    def test_modified_node_or_edge_fails_release_validation(self):
        for key in ("nodes", "edges"):
            changed = copy.deepcopy(RELEASE)
            changed[key][0]["record_json"] = '{}'
            with self.assertRaises(ArchiveError):
                validate_release(changed)

    def test_missing_node_or_edge_fails_release_validation(self):
        for key in ("nodes", "edges"):
            changed = copy.deepcopy(RELEASE)
            changed[key].pop()
            with self.assertRaises(ArchiveError):
                validate_release(changed)

    def test_recomputed_hash_does_not_allow_dangling_endpoints(self):
        changed = copy.deepcopy(RELEASE)
        changed["edges"][0]["to"] = "nonexistent"
        changed["revision"] = digest({k: v for k, v in changed.items() if k != "revision"})
        with self.assertRaisesRegex(ArchiveError, "endpoint"):
            validate_release(changed)

    def test_source_path_escape_and_changed_bytes_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "source.txt"
            p.write_text("new data")
            for hashes in ({"../outside": "0" * 64}, {"source.txt": "0" * 64}, {"absent": "0" * 64}):
                with self.assertRaises(ArchiveError):
                    verify_files({"file_hashes": hashes}, Path(folder))

    def test_unpinned_or_malformed_revision_rejected(self):
        for revision in (None, "", "active", "0" * 63, "x" * 64):
            with self.assertRaises(ArchiveError):
                Neo4jStore(None, "neo4j", revision)

    def test_fresh_read_after_success_cannot_hide_database_outage(self):
        reader = OracleReader(self.original)
        class Store:
            calls = 0
            def read(self, operation):
                self.calls += 1
                if self.calls > 1:
                    raise RuntimeError("private connection detail")
                return operation(reader)
        session = Session(CheckingService(Store()))
        session.state = "ready"
        request = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
            "name": "check_apm_induction", "arguments": SUITE["default_input"]}}
        self.assertEqual("met", session.handle(request)["result"]["structuredContent"]["check_status"])
        failed = session.handle(request)["result"]
        self.assertTrue(failed["isError"])
        self.assertNotIn("structuredContent", failed)
        self.assertNotIn("private connection detail", str(failed))

    def test_runtime_imports_without_networkx_or_frozen_package(self):
        script = '''
import importlib.abc, sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('networkx', 'kg'):
            raise AssertionError('Forbidden live dependency: '+fullname)
sys.meta_path.insert(0, Block())
import neo4j_kg.mcp_server
assert 'networkx' not in sys.modules
assert 'kg' not in sys.modules
'''
        result = subprocess.run([sys.executable, "-c", script], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)


if __name__ == "__main__":
    unittest.main()
