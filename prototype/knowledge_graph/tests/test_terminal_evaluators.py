"""Boundary tests for the six source-bounded terminal evaluators."""

from __future__ import annotations

import copy
import unittest

from neo4j_kg.terminal_evaluators import EVALUATORS, evaluate_terminal
from neo4j_kg.trip_models import normalize_facts
from verification_fixtures import AT, RELEASE, facts as raw_facts, receipts


TERMINAL_REQUIREMENTS = {
    "dtr_registration_and_rfid": "dtr",
    "dtr_engine_policy": "dtr",
    "driver_twic": "twic",
    "sealink_registration": "sealink",
    "apm_appointment": "appointment",
    "transaction_release": "transaction",
}


class TerminalEvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.facts = normalize_facts(raw_facts(), "driver", "Synthetic evaluator facts")
        self.case = {
            "trip_id": "syn-trip-" + "1" * 32,
            "revision": 1,
            "facts": self.facts,
            "conflicts": [],
        }
        records = receipts(self.case)
        self.evidence = {record["kind"]: [record] for record in records}

    def result(self, requirement_id, *, evidence=None, trip_at=AT):
        return evaluate_terminal(
            requirement_id,
            self.facts,
            self.evidence if evidence is None else evidence,
            trip_at,
        )

    def changed(self, kind, **values):
        evidence = copy.deepcopy(self.evidence)
        evidence[kind][0]["payload"].update(values)
        return evidence

    def check(self, result, check_id):
        return next(check for check in result["checks"] if check["id"] == check_id)

    def test_public_registry_and_result_shape_are_stable(self):
        self.assertEqual(set(TERMINAL_REQUIREMENTS), set(EVALUATORS))
        for requirement_id in TERMINAL_REQUIREMENTS:
            with self.subTest(requirement=requirement_id):
                result = self.result(requirement_id)
                self.assertEqual(
                    {"status", "reason_codes", "checks", "limits", "used_receipt_ids"},
                    set(result),
                )
                self.assertIn(result["status"], {"met", "not_met", "unresolved"})
                self.assertTrue(result["checks"])
                self.assertTrue(result["limits"])
                self.assertTrue(all(check["detail"] for check in result["checks"]))
                self.assertTrue(all(
                    check["status"] in {"met", "not_met", "unresolved"}
                    for check in result["checks"]
                ))

    def test_positive_receipts_meet_every_terminal_predicate_except_engine_conflict(self):
        for requirement_id in TERMINAL_REQUIREMENTS:
            with self.subTest(requirement=requirement_id):
                expected = "unresolved" if requirement_id == "dtr_engine_policy" else "met"
                self.assertEqual(expected, self.result(requirement_id)["status"])

    def test_missing_and_conflicting_same_kind_receipts_stay_unresolved(self):
        for requirement_id, kind in TERMINAL_REQUIREMENTS.items():
            with self.subTest(requirement=requirement_id, state="missing"):
                result = self.result(requirement_id, evidence={})
                self.assertEqual("unresolved", result["status"])
                self.assertIn("VERIFICATION_RECEIPT_MISSING", result["reason_codes"])

            conflict = copy.deepcopy(self.evidence)
            second = copy.deepcopy(conflict[kind][0])
            second["id"] += "-conflict"
            if kind == "dtr":
                second["payload"]["active"] = False
            elif kind == "twic":
                second["payload"]["status"] = "revoked"
            elif kind == "sealink":
                second["payload"]["active"] = False
            elif kind == "appointment":
                second["payload"]["status"] = "cancelled"
            else:
                second["payload"]["fully_available"] = False
            conflict[kind].append(second)
            with self.subTest(requirement=requirement_id, state="conflict"):
                result = self.result(requirement_id, evidence=conflict)
                self.assertEqual("unresolved", result["status"])
                self.assertIn("CONFLICTING_VERIFICATION_RECEIPTS", result["reason_codes"])
                self.assertEqual([], result["used_receipt_ids"])

    def test_identical_duplicate_receipts_are_all_accounted_for(self):
        evidence = copy.deepcopy(self.evidence)
        duplicate = copy.deepcopy(evidence["sealink"][0])
        duplicate["id"] += "-duplicate"
        evidence["sealink"].append(duplicate)

        result = self.result("sealink_registration", evidence=evidence)

        self.assertEqual("met", result["status"])
        self.assertEqual(
            sorted([evidence["sealink"][0]["id"], duplicate["id"]]),
            result["used_receipt_ids"],
        )

    def test_dtr_registration_uses_new_york_calendar_date_not_utc_date(self):
        prior_local_date = self.changed("dtr", registered_at="2026-09-13T01:00:00Z")
        same_local_date = self.changed("dtr", registered_at="2026-09-13T01:00:00-04:00")

        self.assertEqual("met", self.result("dtr_registration_and_rfid", evidence=prior_local_date)["status"])
        result = self.result("dtr_registration_and_rfid", evidence=same_local_date)
        self.assertEqual("not_met", result["status"])
        self.assertEqual(
            "not_met",
            self.check(result, "dtr_registered_before_entry_date")["status"],
        )

    def test_dtr_registration_and_rfid_negative_unknown_and_class_scope(self):
        scenarios = [
            ({"registered": False}, "not_met"),
            ({"active": None}, "unresolved"),
            ({"rfid_valid": False}, "not_met"),
            ({"rfid_mounted": None}, "unresolved"),
            ({"class_8": None}, "unresolved"),
            ({"drayage_truck": False}, "unresolved"),
        ]
        for change, expected in scenarios:
            with self.subTest(change=change):
                result = self.result(
                    "dtr_registration_and_rfid",
                    evidence=self.changed("dtr", **change),
                )
                self.assertEqual(expected, result["status"])

        non_class_8 = self.changed(
            "dtr",
            class_8=False,
            rfid_assigned=None,
            rfid_mounted=None,
            rfid_valid=None,
        )
        self.assertEqual(
            "met",
            self.result("dtr_registration_and_rfid", evidence=non_class_8)["status"],
        )

    def test_dtr_ownership_amendment_uses_inclusive_ten_calendar_day_limit(self):
        exact_limit = self.changed(
            "dtr",
            registration_event="ownership_change",
            registration_changed_at="2026-09-01T23:59:00-04:00",
            registration_amended_at="2026-09-11T00:01:00-04:00",
        )
        late = self.changed(
            "dtr",
            registration_event="ownership_change",
            registration_changed_at="2026-09-01T00:01:00-04:00",
            registration_amended_at="2026-09-12T00:00:00-04:00",
        )
        missing = self.changed(
            "dtr",
            registration_event="ownership_change",
            registration_changed_at="2026-09-01T00:01:00-04:00",
            registration_amended_at=None,
        )

        self.assertEqual("met", self.result("dtr_registration_and_rfid", evidence=exact_limit)["status"])
        self.assertEqual("not_met", self.result("dtr_registration_and_rfid", evidence=late)["status"])
        self.assertEqual("unresolved", self.result("dtr_registration_and_rfid", evidence=missing)["status"])

    def test_engine_policy_always_exposes_both_tariff_branches_and_stays_unresolved(self):
        negative_branches = self.changed(
            "dtr",
            engine_model_year=1998,
            meets_2014_emissions_standard=False,
        )
        result = self.result("dtr_engine_policy", evidence=negative_branches)

        self.assertEqual("unresolved", result["status"])
        self.assertIn("UNRESOLVED_DTR_TARIFF_CONFLICT", result["reason_codes"])
        self.assertEqual(
            "not_met",
            self.check(result, "subrule_34_1101_registration_branch")["status"],
        )
        self.assertEqual(
            "not_met",
            self.check(result, "subrule_34_1140_entry_branch")["status"],
        )

    def test_engine_year_cannot_substitute_for_emissions_standard(self):
        evidence = self.changed(
            "dtr",
            engine_model_year=2026,
            meets_2014_emissions_standard=None,
        )
        result = self.result("dtr_engine_policy", evidence=evidence)
        branch = self.check(result, "subrule_34_1101_registration_branch")

        self.assertEqual("unresolved", result["status"])
        self.assertEqual("unresolved", branch["status"])
        self.assertIn("alone cannot establish", branch["detail"])

    def test_engine_registration_branch_uses_registration_event_not_trip_date(self):
        evidence = self.changed(
            "dtr",
            registered_at="2023-07-01T23:00:00-04:00",
            meets_2014_emissions_standard=True,
        )
        result = self.result("dtr_engine_policy", evidence=evidence)
        branch = self.check(result, "subrule_34_1101_registration_branch")

        self.assertEqual("unresolved", branch["status"])
        self.assertIn("later trip date does not turn it into", branch["detail"])

    def test_twic_requires_unescorted_scope_no_exception_validity_and_possession(self):
        scenarios = [
            ({"unescorted_secure_access": False}, "unresolved"),
            ({"exception_claimed": True, "status": "revoked"}, "unresolved"),
            ({"status": "revoked"}, "not_met"),
            ({"status": "unknown"}, "unresolved"),
            ({"physically_present": False}, "not_met"),
            ({"physically_present": None}, "unresolved"),
        ]
        for change, expected in scenarios:
            with self.subTest(change=change):
                result = self.result("driver_twic", evidence=self.changed("twic", **change))
                self.assertEqual(expected, result["status"])

    def test_twic_expiry_is_strict(self):
        result = self.result(
            "driver_twic",
            evidence=self.changed("twic", credential_expires_at=AT),
        )

        self.assertEqual("not_met", result["status"])
        self.assertEqual("not_met", self.check(result, "twic_unexpired_at_trip")["status"])

    def test_sealink_requires_active_record_and_twic_registration(self):
        for change, expected in [
            ({"active": False}, "not_met"),
            ({"twic_registered": False}, "not_met"),
            ({"active": None}, "unresolved"),
            ({"twic_registered": None}, "unresolved"),
        ]:
            with self.subTest(change=change):
                result = self.result(
                    "sealink_registration",
                    evidence=self.changed("sealink", **change),
                )
                self.assertEqual(expected, result["status"])

    def test_appointment_slot_is_start_inclusive_and_end_exclusive(self):
        at_start = self.changed(
            "appointment",
            slot_start=AT,
            slot_end="2026-09-13T15:00:00-04:00",
        )
        at_end = self.changed(
            "appointment",
            slot_start="2026-09-13T13:00:00-04:00",
            slot_end=AT,
        )

        self.assertEqual("met", self.result("apm_appointment", evidence=at_start)["status"])
        result = self.result("apm_appointment", evidence=at_end)
        self.assertEqual("not_met", result["status"])
        self.assertEqual("not_met", self.check(result, "appointment_slot")["status"])

    def test_appointment_status_and_apm_scope_fail_closed(self):
        for change, expected in [
            ({"status": "cancelled"}, "not_met"),
            ({"status": "not_found"}, "not_met"),
            ({"status": "unknown"}, "unresolved"),
        ]:
            with self.subTest(change=change):
                result = self.result(
                    "apm_appointment",
                    evidence=self.changed("appointment", **change),
                )
                self.assertEqual(expected, result["status"])

        self.facts["terminal_id"]["value"] = None
        self.assertEqual("unresolved", self.result("apm_appointment")["status"])

    def test_import_transaction_requires_full_availability_and_all_five_clear_holds(self):
        scenarios = [
            ({"fully_available": False}, "not_met"),
            ({"fully_available": None}, "unresolved"),
            ({"holds_complete": False}, "unresolved"),
            ({"fully_available": None, "customs_hold": True}, "not_met"),
            ({"fully_available": None, "other_hold": None}, "unresolved"),
        ]
        for change, expected in scenarios:
            with self.subTest(change=change):
                result = self.result(
                    "transaction_release",
                    evidence=self.changed("transaction", **change),
                )
                self.assertEqual(expected, result["status"])

    def test_transaction_other_move_types_and_unknown_apm_scope_are_unresolved(self):
        for move_type in ("empty_pickup", "export_dropoff", "empty_return", "unknown"):
            with self.subTest(move_type=move_type):
                result = self.result(
                    "transaction_release",
                    evidence=self.changed("transaction", move_type=move_type),
                )
                self.assertEqual("unresolved", result["status"])
                self.assertIn("TRANSACTION_MOVE_TYPE_UNRESOLVED", result["reason_codes"])

        self.facts["terminal_id"]["value"] = None
        self.assertEqual("unresolved", self.result("transaction_release")["status"])

    def test_missing_trip_time_never_becomes_a_negative(self):
        for requirement_id in ("dtr_registration_and_rfid", "driver_twic", "apm_appointment"):
            with self.subTest(requirement=requirement_id):
                self.assertEqual("unresolved", self.result(requirement_id, trip_at=None)["status"])

    def test_unknown_requirement_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported terminal requirement"):
            evaluate_terminal("not_a_requirement", self.facts, self.evidence, AT)


if __name__ == "__main__":
    unittest.main()
