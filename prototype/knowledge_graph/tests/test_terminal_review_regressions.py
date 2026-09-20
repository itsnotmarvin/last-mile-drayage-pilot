"""Adversarial regressions for terminal-receipt event chronology."""

from __future__ import annotations

import copy
import unittest

from neo4j_kg.service import InputError
from neo4j_kg.terminal_evaluators import evaluate_terminal
from neo4j_kg.trip_models import normalize_facts
from neo4j_kg.verification import admit, evaluate_requirement
from neo4j_kg.verification_models import validate_receipt
from verification_fixtures import AT, RELEASE, facts as raw_facts, receipts


class TerminalReviewRegressionTests(unittest.TestCase):
    def setUp(self):
        self.facts = normalize_facts(raw_facts(), "driver", "Temporal regression")
        self.case = {
            "trip_id": "syn-trip-" + "1" * 32,
            "revision": 1,
            "facts": self.facts,
            "conflicts": [],
        }
        self.dtr = next(
            record for record in receipts(self.case) if record["kind"] == "dtr"
        )

    def changed_receipt(self, **payload_changes):
        receipt = copy.deepcopy(self.dtr)
        receipt["payload"].update(payload_changes)
        return receipt

    def test_completed_dtr_events_cannot_postdate_observation(self):
        observed = "2026-08-01T08:00:00-04:00"
        future = "2026-09-12T08:00:00-04:00"
        scenarios = (
            {"registered_at": future},
            {
                "registration_event": "ownership_change",
                "registration_changed_at": future,
            },
            {
                "registration_event": "ownership_change",
                "registration_changed_at": observed,
                "registration_amended_at": future,
            },
        )

        for changes in scenarios:
            with self.subTest(changes=changes):
                receipt = self.changed_receipt(**changes)
                receipt.update(observed_at=observed, valid_from=observed)
                with self.assertRaisesRegex(InputError, "after observed_at"):
                    validate_receipt(receipt)

    def test_completed_dtr_events_may_equal_observation(self):
        observed = "2026-09-01T12:00:00-04:00"
        receipt = self.changed_receipt(
            registered_at=observed,
            registration_event="ownership_change",
            registration_changed_at=observed,
            registration_amended_at=observed,
        )
        receipt.update(observed_at=observed, valid_from=observed)

        self.assertIsNone(validate_receipt(receipt))

    def test_exact_ten_calendar_day_limit_remains_met(self):
        receipt = self.changed_receipt(
            registration_event="ownership_change",
            registration_changed_at="2026-09-01T12:00:00-04:00",
            registration_amended_at="2026-09-11T12:00:00-04:00",
        )
        receipt.update(
            observed_at="2026-09-11T12:00:00-04:00",
            valid_from="2026-09-11T12:00:00-04:00",
        )

        self.assertIsNone(validate_receipt(receipt))
        result = evaluate_terminal(
            "dtr_registration_and_rfid",
            self.facts,
            {"dtr": [receipt]},
            AT,
        )
        amendment = next(
            check
            for check in result["checks"]
            if check["id"] == "dtr_change_amended_within_ten_days"
        )
        self.assertEqual("met", result["status"])
        self.assertEqual("met", amendment["status"])

    def test_dtr_event_chronology_must_follow_semantic_order(self):
        scenarios = (
            {
                "registered_at": "2026-09-02T12:00:00-04:00",
                "registration_event": "ownership_change",
                "registration_changed_at": "2026-09-01T12:00:00-04:00",
                "registration_amended_at": "2026-09-03T12:00:00-04:00",
            },
            {
                "registration_event": "ownership_change",
                "registration_changed_at": "2026-09-01T23:00:00-04:00",
                "registration_amended_at": "2026-09-01T01:00:00-04:00",
            },
            {
                "registered_at": "2026-09-02T12:00:00-04:00",
                "registration_event": "ownership_change",
                "registration_changed_at": None,
                "registration_amended_at": "2026-09-01T12:00:00-04:00",
            },
        )

        for changes in scenarios:
            with self.subTest(changes=changes):
                with self.assertRaisesRegex(InputError, "DTR event chronology"):
                    validate_receipt(self.changed_receipt(**changes))

    def test_same_day_reversed_amendment_never_becomes_met_directly(self):
        receipt = self.changed_receipt(
            registration_event="ownership_change",
            registration_changed_at="2026-09-01T23:00:00-04:00",
            registration_amended_at="2026-09-01T01:00:00-04:00",
        )

        result = evaluate_terminal(
            "dtr_registration_and_rfid",
            self.facts,
            {"dtr": [receipt]},
            AT,
        )
        amendment = next(
            check
            for check in result["checks"]
            if check["id"] == "dtr_change_amended_within_ten_days"
        )
        self.assertEqual("unresolved", result["status"])
        self.assertEqual("unresolved", amendment["status"])
        self.assertIn("predates", amendment["detail"])

    def test_future_registration_is_rejected_before_it_can_produce_met(self):
        observed = "2026-08-01T08:00:00-04:00"
        receipt = self.changed_receipt(registered_at="2026-09-12T08:00:00-04:00")
        receipt.update(observed_at=observed, valid_from=observed)

        admission = admit(
            {"version": "test", "receipts": [receipt], "revoked_ids": []},
            self.case,
            RELEASE,
            now=AT,
        )
        result = evaluate_requirement(
            "dtr_registration_and_rfid",
            self.facts,
            admission,
            AT,
        )

        self.assertNotIn("dtr", admission["evidence"])
        self.assertEqual(
            ["INVALID_VERIFICATION_RECEIPT"],
            admission["rejected"][0]["reason_codes"],
        )
        self.assertEqual("unresolved", result["status"])
        self.assertIn("VERIFICATION_RECEIPT_MISSING", result["reason_codes"])


if __name__ == "__main__":
    unittest.main()
