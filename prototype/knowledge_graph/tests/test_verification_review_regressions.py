"""Regressions for adversarial verification-boundary review findings."""

import copy
from pathlib import Path
import tempfile
import unittest

from neo4j_kg.trip_state import TripStore
from neo4j_kg.verification import admit, evaluate_requirement
from verification_fixtures import AT, RELEASE, facts, receipts


class VerificationReviewRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.states = TripStore(Path(self.temporary.name) / "trips.sqlite3")
        self.sequence = 0

    def case(self, extra=None):
        self.sequence += 1
        supplied = facts()
        supplied.update(extra or {})
        return self.states.create(
            facts=supplied,
            request_key="review-" + str(self.sequence),
            source_message="Synthetic verification regression case.",
            requester_role="driver",
            question_scope="trip_dispatch",
        )

    @staticmethod
    def admission(case, records):
        return admit(
            {"version": "test", "receipts": records, "revoked_ids": []},
            case,
            RELEASE,
            now=AT,
        )

    def result(self, requirement_id, case, records):
        return evaluate_requirement(
            requirement_id,
            case["facts"],
            self.admission(case, records),
            case["facts"]["trip_at"]["value"],
        )

    def test_permit_route_report_distinguishes_absent_none_false_and_true(self):
        scenarios = (
            ("absent", {}, "met"),
            ("none", {"permit_route_reported": None}, "met"),
            ("false", {"permit_route_reported": False}, "unresolved"),
            ("true", {"permit_route_reported": True}, "met"),
        )
        for label, extra, expected in scenarios:
            with self.subTest(report=label):
                case = self.case(extra)
                result = self.result("permit_eligibility", case, receipts(case))
                self.assertEqual(expected, result["status"])
                self.assertEqual(
                    label == "false",
                    "REPORT_CONFLICTS_WITH_SYNTHETIC_VERIFICATION" in result["reason_codes"],
                )

    def test_rfid_false_only_conflicts_when_class_8_branch_applies(self):
        for class_8, expected in ((False, "met"), (True, "unresolved")):
            with self.subTest(class_8=class_8):
                case = self.case({"rfid_reported": False})
                record = next(r for r in receipts(case) if r["kind"] == "dtr")
                record["payload"]["class_8"] = class_8
                if not class_8:
                    record["payload"].update(
                        rfid_assigned=None,
                        rfid_valid=None,
                        rfid_mounted=None,
                    )
                result = self.result("dtr_registration_and_rfid", case, [record])
                self.assertEqual(expected, result["status"])
                self.assertEqual(
                    class_8,
                    "REPORT_CONFLICTS_WITH_SYNTHETIC_VERIFICATION" in result["reason_codes"],
                )

    def test_wrong_authority_record_for_same_segment_blocks_segment_result(self):
        scenarios = (
            ("approval", "cross_authority_coverage", {"status": "denied"}),
            ("conditions", "current_route_conditions", {"status": "closed"}),
        )
        for kind, requirement_id, negative in scenarios:
            with self.subTest(kind=kind):
                case = self.case()
                records = receipts(case)
                original = next(r for r in records if r["kind"] == kind)
                mismatch = copy.deepcopy(original)
                mismatch["id"] = "syn-verification-" + kind + "-wrong-authority"
                mismatch["payload"].update(authority="county", **negative)
                result = self.result(requirement_id, case, records + [mismatch])

                segment = original["payload"].get("segment_id")
                if segment is None:
                    segment = original["payload"]["segment_ids"][0]
                check_id = segment + "_" + kind + "_authority_mismatch"
                self.assertEqual("unresolved", result["status"])
                self.assertIn(mismatch["id"], result["used_receipt_ids"])
                self.assertIn(check_id.upper(), result["reason_codes"])
                self.assertEqual(
                    "unresolved",
                    next(c for c in result["checks"] if c["id"] == check_id)["status"],
                )


if __name__ == "__main__":
    unittest.main()
