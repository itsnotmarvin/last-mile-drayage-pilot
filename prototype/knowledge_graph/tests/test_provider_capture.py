"""Integrity checks of the collected run, not claims of perfect provider behavior."""

import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "provider_runs/claude-desktop-20260906"
SPEC = importlib.util.spec_from_file_location("provider_capture_verify", RUN / "verify.py")
verify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify)


class ProviderCaptureTests(unittest.TestCase):
    def setUp(self):
        self.events = [json.loads(line) for line in (RUN / "tool-audit.jsonl").read_text().splitlines()]

    def test_recorded_artifacts_and_manual_quote_anchors_verify(self):
        result = verify.verify()
        self.assertTrue(result["artifact_checks_pass"])
        self.assertEqual(result["cases_captured"], 6)

    def test_provider_failures_are_retained_not_converted_to_success(self):
        result = verify.verify()
        failures = {row["case_id"]: row["argument_differences"] for row in result["results"]
                    if row["argument_differences"]}
        self.assertEqual(set(failures), {"P3_changed_identifier", "P6_missing_time_and_identifier"})
        self.assertEqual(failures["P3_changed_identifier"]["question_scope"],
                         {"expected": "induction", "received": "trip_dispatch"})
        self.assertEqual(failures["P6_missing_time_and_identifier"]["question_scope"],
                         {"expected": "induction", "received": "terminal_entry"})
        self.assertEqual(result["manual_criteria_counts"], {"pass": 16, "partial": 2})

    def test_changed_event_is_rejected(self):
        changed = copy.deepcopy(self.events)
        changed[0]["validated_arguments"]["as_received"]["driver_id"] = "syn-driver-missing"
        with self.assertRaisesRegex(ValueError, "Changed audit event"):
            verify.validate_events(changed)

    def test_reordered_events_are_rejected(self):
        changed = copy.deepcopy(self.events)
        changed[0], changed[1] = changed[1], changed[0]
        with self.assertRaisesRegex(ValueError, "Audit sequence gap"):
            verify.validate_events(changed)

    def test_omitted_middle_event_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Audit sequence gap"):
            verify.validate_events(self.events[:2] + self.events[3:])

    def test_argument_comparison_normalizes_time_but_not_scope(self):
        arguments = self.events[0]["validated_arguments"]["as_received"]
        changed = dict(arguments, trip_at="2026-09-06T18:00:00+00:00", company_changed=None)
        self.assertEqual(verify.score_arguments(arguments, changed), {})
        changed["question_scope"] = "terminal_entry"
        self.assertIn("question_scope", verify.score_arguments(arguments, changed))

    def test_original_inventory_reconstructs_recorded_identity(self):
        manifest = json.loads((RUN / "manifest.json").read_text())
        self.assertEqual(verify.collection_identity(manifest, self.events),
                         "f405c984924cfd85a618ca0b947db4ce30e8be027d2df243a2a2b05a3173bec0")

    def test_replay_cannot_ignore_a_different_recorded_implementation(self):
        manifest = json.loads((RUN / "manifest.json").read_text())
        changed = copy.deepcopy(self.events)
        changed[0]["response"]["result"]["structuredContent"]["versions"]["implementation"] = "unknown"
        with self.assertRaisesRegex(ValueError, "inventory does not match"):
            verify.collection_identity(manifest, changed)


if __name__ == "__main__":
    unittest.main()
