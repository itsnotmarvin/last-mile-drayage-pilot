import hashlib
import json
from pathlib import Path
import unittest

from kg.graph import KnowledgeGraph
from kg.service import CheckingService, InputError, normalize


HERE = Path(__file__).parent
SUITE = json.loads((HERE / "acceptance.json").read_text())
BASE = SUITE["default_input"]


class ServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = CheckingService()

    def test_frozen_acceptance_hash(self):
        self.assertEqual((HERE / "acceptance.sha256").read_text().strip(),
                         hashlib.sha256((HERE / "acceptance.json").read_bytes()).hexdigest())

    def test_frozen_provider_prompts_hash(self):
        self.assertEqual((HERE / "provider_cases.sha256").read_text().strip(),
                         hashlib.sha256((HERE / "provider_cases.json").read_bytes()).hexdigest())

    def test_provider_vectors_have_consistent_local_expectations_not_provider_results(self):
        plan = json.loads((HERE / "provider_cases.json").read_text())
        self.assertEqual(6, len(plan["cases"]))
        for case in plan["cases"]:
            with self.subTest(case=case["case_id"]):
                self.assertEqual(case["expected_check_status"],
                                 self.service.check(case["expected_arguments"])["check_status"])

    def test_repeat_is_byte_identical(self):
        self.assertEqual(json.dumps(self.service.check(BASE), sort_keys=True),
                         json.dumps(self.service.check(BASE), sort_keys=True))

    def test_timezone_equivalence_does_not_change_result(self):
        self.assertEqual(self.service.check(BASE),
                         self.service.check(BASE | {"trip_at": "2026-09-06T18:00:00Z"}))

    def test_fact_update_rechecks_without_sticky_pass(self):
        first = self.service.check(BASE)
        changed = self.service.check(BASE | {"current_sealink_id": "SYN-SL-NEW"})
        restored = self.service.check(BASE)
        self.assertEqual("met", first["check_status"])
        self.assertEqual("unresolved", changed["check_status"])
        self.assertNotEqual(first["evaluation_id"], changed["evaluation_id"])
        self.assertEqual(first, restored)

    def test_every_result_has_draft_sources_and_coverage(self):
        for case in SUITE["cases"]:
            with self.subTest(case=case["case_id"]):
                result = self.service.check(BASE | case["changes"])
                self.assertEqual("draft_not_human_approved", result["approval_status"])
                self.assertEqual("unresolved_not_assessed", result["operational_status"])
                self.assertFalse(result["coverage"]["complete_trip_check"])
                self.assertIn("current_policy", result["coverage"]["not_evaluated"])
                self.assertEqual(2, len(result["sources"]))
                self.assertNotIn("safe_to_dispatch", result)
                self.assertNotIn("can_enter", result)
                self.assertTrue(all(s["source_text"] and s["locator"] for s in result["sources"]))

    def test_positive_and_negative_cases_prevent_always_hold(self):
        outcomes = {self.service.check(BASE | case["changes"])["check_status"] for case in SUITE["cases"]}
        self.assertEqual({"met", "not_met", "unresolved", "not_applicable"}, outcomes)

    def test_rule_and_evidence_relationships_are_queryable(self):
        self.assertEqual(["facility_apm_elizabeth"], self.service.targets("check_apm_induction_v1", "APPLIES_AT"))
        self.assertEqual(["SYN-SL-A"], self.service.targets("syn-observation-complete", "FOR_SEALINK"))
        self.assertEqual(["training_apm_safety_induction"], self.service.targets("syn-observation-complete", "FOR_PROGRAM"))

    def test_no_private_records_are_imported_into_public_graph(self):
        self.assertNotIn("syn-driver-complete", self.service.archive.graph)

    def test_caller_cannot_inject_evidence_rule_or_time_override(self):
        for field in ("completed", "verification", "evidence", "model_version", "current_policy", "as_of", "approval_status"):
            with self.subTest(field=field), self.assertRaises(InputError):
                self.service.check(BASE | {field: True})

    def test_real_identifiers_rejected(self):
        for field, value in (("driver_id", "123456"), ("current_sealink_id", "543210")):
            with self.subTest(field=field), self.assertRaises(InputError):
                self.service.check(BASE | {field: value})

    def test_invalid_or_naive_timestamps_rejected(self):
        for value in ("2026-09-06", "2026-09-06T14:00:00", "2026-02-30T14:00:00-04:00",
                      "2026-09-06T14:00:00+25:00", "tomorrow", "", 1, True):
            with self.subTest(value=value), self.assertRaises(InputError):
                self.service.check(BASE | {"trip_at": value})

    def test_string_booleans_and_numbers_rejected(self):
        for value in ("true", "false", 1, 0, [], {}):
            with self.subTest(value=value), self.assertRaises(InputError):
                self.service.check(BASE | {"company_changed": value})

    def test_nonobject_and_oversized_inputs_rejected(self):
        for value in (None, [], "string", 3):
            with self.subTest(value=value), self.assertRaises(InputError):
                normalize(value)
        with self.assertRaises(InputError):
            self.service.check(BASE | {"driver_id": "syn-driver-" + "a" * 10000})

    def test_unknown_enumerations_rejected(self):
        for key, value in (("terminal_id", "somewhere"), ("actor_role", "maybe"), ("question_scope", "all_clear")):
            with self.subTest(key=key), self.assertRaises(InputError):
                self.service.check(BASE | {key: value})

    def test_other_drivers_completion_does_not_transfer(self):
        result = self.service.check(BASE | {"driver_id": "syn-driver-missing"})
        self.assertEqual("unresolved", result["check_status"])
        self.assertEqual([], result["evidence_ids"])

    def test_archive_evidence_version_unchanged_by_checks(self):
        before = self.service.archive.evidence_version
        for case in SUITE["cases"]:
            self.service.check(BASE | case["changes"])
        self.assertEqual(before, KnowledgeGraph().evidence_version)

    def test_port_street_never_becomes_current_rule(self):
        context = self.service.context("port_street")
        self.assertIn("No current Port Street", context["limit"])
        self.assertFalse(context["operational_use"])
        for node, attrs in self.service.graph.nodes(data=True):
            if attrs["kind"] == "mutable_observation":
                self.assertEqual([], self.service.targets(node, "SUPPORTS"))

    def test_route_directions_not_legality(self):
        context = self.service.context("route_directions")
        self.assertIn("not legal route designation", context["limit"])
        self.assertTrue(any(r.get("approach_id") == "approach_a_turnpike_nb" for r in context["routes"]))

    def test_result_mutation_cannot_change_later_result(self):
        result = self.service.check(BASE)
        result["coverage"]["not_evaluated"].clear()
        result["sources"][0]["source_text"] = "altered"
        again = self.service.check(BASE)
        self.assertGreater(len(again["coverage"]["not_evaluated"]), 0)
        self.assertNotEqual(result["sources"], again["sources"])


def acceptance_test(case):
    def run(self):
        result = self.service.check(BASE | case["changes"])
        self.assertEqual(case["expected"], result["check_status"])
        for reason in case["required_reasons"]:
            self.assertIn(reason, result["reason_codes"])
        self.assertEqual(case.get("expected_requested_scope", case["expected"]), result["requested_scope_status"])
    return run


for _case in SUITE["cases"]:
    setattr(ServiceTests, "test_acceptance_" + _case["case_id"], acceptance_test(_case))


if __name__ == "__main__":
    unittest.main()
