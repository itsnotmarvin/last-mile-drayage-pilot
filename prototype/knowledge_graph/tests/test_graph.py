import unittest

import networkx as nx

from kg.graph import ArchiveError, KnowledgeGraph


class GraphBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kg = KnowledgeGraph()

    def test_all_retained_clauses_imported(self):
        self.assertEqual(31, self.kg.summary()["node_kinds"]["source_clause"])

    def test_real_graph_traversal_reaches_induction_evidence(self):
        self.assertTrue(nx.has_path(self.kg.graph, "panynj_truckers_guide",
                                    "reg_apm_safety_induction"))

    def test_source_publisher_not_replaced_by_rule_operator(self):
        citation = self.kg.citation("reg_apm_safety_induction")
        self.assertEqual("Port Authority of New York and New Jersey", citation["publisher"])

    def test_archive_hashes_match_registry(self):
        self.assertGreater(len(self.kg.verify_archives()), 30)

    def test_mutable_observations_are_quarantined(self):
        observations = [attrs for _, attrs in self.kg.graph.nodes(data=True)
                        if attrs["kind"] == "mutable_observation"]
        self.assertGreater(len(observations), 0)
        self.assertTrue(all(x["layer"] == "quarantined_observation" for x in observations))

    def test_records_returned_by_copy(self):
        record = self.kg.record("reg_apm_safety_induction")
        record["source_text"] = "corrupted"
        self.assertNotEqual(record, self.kg.record("reg_apm_safety_induction"))

    def test_snapshot_version_is_deterministic(self):
        self.assertEqual(self.kg.evidence_version, KnowledgeGraph().evidence_version)

    def test_archive_path_cannot_escape_root(self):
        with self.assertRaises(ArchiveError):
            self.kg._path("../outside-evidence.json")

    def test_checksum_failure_does_not_get_silently_ignored(self):
        graph = KnowledgeGraph()
        archived = next(source["archived_files"][0]
                        for source in graph.documents["data/metadata.json"]["sources"]
                        if source.get("archived_files"))
        archived["sha256"] = "0" * 64
        with self.assertRaises(ArchiveError):
            graph.verify_archives()


if __name__ == "__main__":
    unittest.main()
