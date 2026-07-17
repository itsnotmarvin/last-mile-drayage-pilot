import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
import analyze


def load(name):
    with open(os.path.join(ROOT, "data", "processed", name)) as fh:
        return json.load(fh)


class TestScanIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nodes = load("regulatory_nodes.json")
        cls.pairs_doc = load("rule_pair_evaluations.json")
        cls.app = load("rule_applicability.json")

    def test_pair_count_is_n_choose_2(self):
        n = len(self.nodes["rules"])
        self.assertEqual(len(self.pairs_doc["pairs"]), n * (n - 1) // 2)

    def test_every_disposition_in_vocab(self):
        for p in self.pairs_doc["pairs"]:
            self.assertIn(p["disposition"], analyze.VOCAB, p["pair_id"])

    def test_summary_counts_match_pairs(self):
        counts = {}
        for p in self.pairs_doc["pairs"]:
            counts[p["disposition"]] = counts.get(p["disposition"], 0) + 1
        self.assertEqual(counts, self.pairs_doc["summary_counts"])

    def test_no_legacy_vocabulary(self):
        for p in self.pairs_doc["pairs"]:
            self.assertNotIn(p["disposition"], analyze.RENAME)

    def test_pair_ids_unique_and_rules_covered(self):
        ids = [p["pair_id"] for p in self.pairs_doc["pairs"]]
        self.assertEqual(len(ids), len(set(ids)))
        keys = {frozenset((p["left_rule_id"], p["right_rule_id"])) for p in self.pairs_doc["pairs"]}
        import itertools
        rule_ids = [r["rule_id"] for r in self.nodes["rules"]]
        for a, b in itertools.combinations(rule_ids, 2):
            self.assertIn(frozenset((a, b)), keys)

    def test_contradiction_never_crosses_acts(self):
        by_id = {r["rule_id"]: r for r in self.app["records"]}
        for p in self.pairs_doc["pairs"]:
            if p["disposition"] == "contradiction_supported":
                ra, rb = by_id[p["left_rule_id"]], by_id[p["right_rule_id"]]
                self.assertEqual(analyze.act_of(ra), analyze.act_of(rb))

    def test_parking_rule_never_contradicts(self):
        for p in self.pairs_doc["pairs"]:
            if "rule_045" in (p["left_rule_id"], p["right_rule_id"]):
                self.assertNotEqual(p["disposition"], "contradiction_supported")


class TestTerminalConclusion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conclusion = load("contradiction_conclusion.json")
        cls.pairs_doc = load("rule_pair_evaluations.json")

    def test_exactly_one_conclusion_value(self):
        self.assertIn(cls_val := self.conclusion["conclusion"], (
            "contradiction_supported",
            "no_contradiction_within_scope",
            "not_determinable_named_source_unavailable"))

    def test_conclusion_consistent_with_pairs(self):
        has_contra = any(p["disposition"] == "contradiction_supported" for p in self.pairs_doc["pairs"])
        has_unresolved = any(p["disposition"] == "unresolved" for p in self.pairs_doc["pairs"])
        if has_contra:
            expected = "contradiction_supported"
        elif has_unresolved:
            expected = "not_determinable_named_source_unavailable"
        else:
            expected = "no_contradiction_within_scope"
        self.assertEqual(self.conclusion["conclusion"], expected)

    def test_named_blocker_present_when_not_determinable(self):
        if self.conclusion["conclusion"] == "not_determinable_named_source_unavailable":
            self.assertTrue(self.conclusion["named_blocker"])
            self.assertIn("34-1140(c)", self.conclusion["named_blocker"])

    def test_unresolved_pairs_listed(self):
        listed = set(self.conclusion["unresolved_pairs"])
        actual = {p["pair_id"] for p in self.pairs_doc["pairs"] if p["disposition"] == "unresolved"}
        self.assertEqual(listed, actual)


class TestScenarioDiscipline(unittest.TestCase):
    def test_unknowns_stay_unresolved(self):
        scenarios = load("scenarios.json")
        for s in scenarios["scenarios"]:
            for k, v in s.items():
                if v == "compliant_by_assumption":
                    self.fail(f"{s['scenario_id']}.{k} assumes compliance")

    def test_scenarios_have_required_fields(self):
        scenarios = load("scenarios.json")
        required = ["fuel_or_powertrain_type", "engine_model_year", "dimensions", "weight_lbs",
                    "credentials", "permit_status", "appointment_status", "route", "datetime_local"]
        for s in scenarios["scenarios"]:
            for f in required:
                self.assertIn(f, s, s["scenario_id"])


if __name__ == "__main__":
    unittest.main()
