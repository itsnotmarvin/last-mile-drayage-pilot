"""Trip intake and state tests use synthetic facts only."""

from __future__ import annotations

import json
import math
import multiprocessing
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch

from neo4j_kg.service import InputError
from neo4j_kg.trip_models import FACT_FIELDS, FACTS_SCHEMA, normalize_facts
from neo4j_kg.trip_state import (
    RequestKeyReuse,
    RevisionConflict,
    TripNotFound,
    TripStore,
)


def _process_update(path, trip_id, barrier, queue, request_key):
    try:
        store = TripStore(path)
        barrier.wait(timeout=10)
        result = store.update(
            trip_id, 1, "dispatcher", "trip_dispatch",
            {"route_description": request_key}, request_key, request_key,
        )
        queue.put(("ok", result["revision"]))
    except RevisionConflict:
        queue.put(("conflict", None))
    except BaseException as exc:  # pragma: no cover - diagnostic for child process
        queue.put(("error", repr(exc)))


class TripFactNormalizationTests(unittest.TestCase):
    def test_normalizes_complete_supported_intake_with_provenance(self):
        facts = {
            "terminal_id": "facility_apm_elizabeth",
            "subject_role": "truck_driver",
            "driver_id": "syn-driver-complete",
            "vehicle_id": "syn-vehicle-tractor-a",
            "trailer_id": "syn-trailer-chassis-a",
            "current_sealink_id": "SYN-SL-A",
            "trip_at": "2026-09-10T09:00:00-04:00",
            "gross_weight": {"value": 36_000, "unit": "kg"},
            "axle_weights": [
                {"value": 12_000, "unit": "lb"},
                {"value": 10_000, "unit": "kg"},
            ],
            "axle_spacings": [
                {"value": 12, "unit": "ft"},
                {"value": 48, "unit": "in"},
            ],
            "axle_count": 5,
            "width": {"value": 8.5, "unit": "ft"},
            "height": {"value": 162, "unit": "in"},
            "overall_length": {"value": 70, "unit": "ft"},
            "semitrailer_length": {"value": 53, "unit": "ft"},
            "cargo_hazardous": False,
            "container_sealed": True,
            "load_divisible": False,
            "route_id": "path_a_exit13a_to_apm",
            "route_description": "Turnpike Exit 13A to the APM gate",
            "twic_reported": True,
            "sealink_registered_reported": True,
            "induction_reported": True,
            "dtr_reported": True,
            "rfid_reported": True,
            "appointment_reported": True,
            "transaction_release_reported": True,
            "company_changed": False,
            "engine_model_year": 2022,
            "permit_type": "none",
            "permit_route_reported": False,
            "turnpike_approval_reported": False,
            "local_approval_reported": False,
            "port_approval_reported": False,
            "terminal_approval_reported": False,
            "port_street_in_route": False,
            "route_conditions_checked_at": "2026-09-10T12:30:00Z",
        }
        normalized = normalize_facts(facts, "driver", "Synthetic trip details")

        self.assertEqual(set(FACT_FIELDS), set(normalized))
        self.assertAlmostEqual(79_366.41438655594, normalized["gross_weight"]["value"])
        self.assertEqual("lb", normalized["gross_weight"]["unit"])
        self.assertEqual([12_000, 22_046.226218487757], normalized["axle_weights"]["value"])
        self.assertEqual("inch", normalized["axle_spacings"]["unit"])
        self.assertEqual([144, 48], normalized["axle_spacings"]["value"])
        self.assertEqual(102, normalized["width"]["value"])
        self.assertEqual("2026-09-10T13:00:00+00:00", normalized["trip_at"]["value"])
        self.assertEqual(
            "2026-09-10T12:30:00+00:00",
            normalized["route_conditions_checked_at"]["value"],
        )
        recorded = {record["recorded_at"] for record in normalized.values()}
        self.assertEqual(1, len(recorded))
        for record in normalized.values():
            self.assertEqual("user_reported", record["basis"])
            self.assertEqual("driver", record["reported_by"])
            self.assertEqual("Synthetic trip details", record["source_text"])
            self.assertEqual(
                {"value", "unit", "basis", "reported_by", "source_text", "recorded_at"},
                set(record),
            )

    def test_null_is_retained_as_explicit_unknown(self):
        normalized = normalize_facts(
            {"gross_weight": None, "appointment_reported": None},
            "unknown", "The user did not know these facts",
        )
        self.assertIsNone(normalized["gross_weight"]["value"])
        self.assertIsNone(normalized["gross_weight"]["unit"])
        self.assertIsNone(normalized["appointment_reported"]["value"])

    def test_input_is_not_mutated(self):
        facts = {"gross_weight": {"value": 1_000, "unit": "lb"}}
        before = json.loads(json.dumps(facts))
        normalize_facts(facts, "dispatcher", "reported weight")
        self.assertEqual(before, facts)

    def test_unknown_or_client_evidence_fields_are_rejected(self):
        for field in ("verified", "verification", "evidence", "approval_status", "actor_role"):
            with self.subTest(field=field), self.assertRaises(InputError):
                normalize_facts({field: True}, "driver", "attempted override")
        with self.assertRaises(InputError):
            normalize_facts(
                {"gross_weight": {
                    "value": 80_000, "unit": "lb", "basis": "verified",
                }},
                "driver", "attempted envelope",
            )

    def test_real_or_malformed_identifiers_are_rejected(self):
        cases = (
            ("driver_id", "123456"),
            ("driver_id", "syn-driver-a1"),
            ("driver_id", "syn-driver-" + "a" * 41),
            ("vehicle_id", "VIN-123"),
            ("vehicle_id", "syn-vehicle-../../secret"),
            ("trailer_id", "real-trailer"),
            ("current_sealink_id", "SYN-SL-A1"),
            ("current_sealink_id", "123456"),
        )
        for field, value in cases:
            with self.subTest(field=field, value=value), self.assertRaises(InputError):
                normalize_facts({field: value}, "driver", "synthetic only")

    def test_ambiguous_or_malformed_quantities_have_static_errors(self):
        invalid = (
            80_000,
            "80000 lb",
            {"value": 80_000},
            {"value": 80_000, "unit": "tons"},
            {"value": 80_000, "unit": "lb", "verified": True},
            {"value": True, "unit": "lb"},
            {"value": math.inf, "unit": "lb"},
            {"value": math.nan, "unit": "lb"},
            {"value": -1, "unit": "lb"},
            {"value": 10_000_001, "unit": "lb"},
        )
        for value in invalid:
            with self.subTest(value=value), self.assertRaisesRegex(InputError, "gross_weight"):
                normalize_facts({"gross_weight": value}, "driver", "weight report")
        with self.assertRaisesRegex(InputError, "raw numeric arrays are ambiguous"):
            normalize_facts({"axle_weights": [10_000, 20_000]}, "driver", "axles")
        with self.assertRaises(InputError):
            normalize_facts({"axle_spacings": []}, "driver", "spacings")

    def test_strict_booleans_integers_enums_and_timestamps(self):
        invalid = (
            {"cargo_hazardous": 1},
            {"company_changed": "false"},
            {"axle_count": True},
            {"axle_count": 0},
            {"engine_model_year": 2022.0},
            {"engine_model_year": 2101},
            {"terminal_id": "somewhere"},
            {"subject_role": "dispatcher"},
            {"route_id": "shortcut"},
            {"permit_type": "blanket"},
            {"trip_at": "2026-09-10T09:00:00"},
            {"route_conditions_checked_at": "tomorrow"},
            {"route_description": "   "},
        )
        for facts in invalid:
            with self.subTest(facts=facts), self.assertRaises(InputError):
                normalize_facts(facts, "other", "invalid fact")

    def test_reporter_and_source_are_bounded(self):
        for role in (None, "truck_driver", "admin", 1):
            with self.subTest(role=role), self.assertRaises(InputError):
                normalize_facts({}, role, "source")
        for source in (None, "", "  ", "x" * 8_001, "bad\x00text"):
            with self.subTest(source=source), self.assertRaises(InputError):
                normalize_facts({}, "unknown", source)

    def test_schema_covers_exact_vocabulary_and_closes_nested_objects(self):
        self.assertFalse(FACTS_SCHEMA["additionalProperties"])
        self.assertEqual(set(FACT_FIELDS), set(FACTS_SCHEMA["properties"]))
        gross = FACTS_SCHEMA["properties"]["gross_weight"]["anyOf"][0]
        self.assertEqual(["value", "unit"], gross["required"])
        self.assertFalse(gross["additionalProperties"])
        self.assertEqual(["lb", "kg"], gross["properties"]["unit"]["enum"])
        spacing = FACTS_SCHEMA["properties"]["axle_spacings"]["anyOf"][0]["items"]
        self.assertEqual(["in", "ft"], spacing["properties"]["unit"]["enum"])


class TripStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "private" / "trips.sqlite"
        self.store = TripStore(self.path)

    def tearDown(self):
        self.temporary.cleanup()

    def create(self, facts=None, key="create-1"):
        return self.store.create(
            "driver", "trip_dispatch", facts or {}, "Initial synthetic report", key,
        )

    def test_create_get_snapshot_and_private_file(self):
        snapshot = self.create({
            "driver_id": "syn-driver-a",
            "subject_role": "truck_driver",
            "gross_weight": {"value": 80_000, "unit": "lb"},
        })
        self.assertRegex(snapshot["trip_id"], r"^syn-trip-[0-9a-f]{32}$")
        self.assertEqual(1, snapshot["revision"])
        self.assertEqual("driver", snapshot["requester_role"])
        self.assertEqual("trip_dispatch", snapshot["question_scope"])
        self.assertEqual("synthetic_prototype_only", snapshot["mode"])
        self.assertEqual([], snapshot["invalidated_fields"])
        self.assertEqual([], snapshot["conflicts"])
        self.assertEqual("create", snapshot["history"][0]["operation"])
        self.assertEqual(snapshot, self.store.get(snapshot["trip_id"]))
        self.assertEqual(0o600, os.stat(self.path).st_mode & 0o777)

    def test_no_default_induction_scope_and_role_scope_are_strict(self):
        for role, scope in (("driver", None), (None, "unknown"), ("admin", "route"),
                            ("other", "everything")):
            with self.subTest(role=role, scope=scope), self.assertRaises(InputError):
                self.store.create(role, scope, {}, "source", f"key-{role}-{scope}")
        snapshot = self.store.create("unknown", "unknown", {}, "unclear question", "unknown-1")
        self.assertEqual("unknown", snapshot["question_scope"])

    def test_write_request_key_is_required_and_bounded(self):
        for key in (None, "", " ", "x" * 121, "line\nbreak"):
            with self.subTest(key=key), self.assertRaises(InputError):
                self.store.create("driver", "route", {}, "source", key)

    def test_create_retry_returns_exact_snapshot_and_one_history_event(self):
        first = self.create({"driver_id": "syn-driver-a"}, "create-retry")
        retry = self.create({"driver_id": "syn-driver-a"}, "create-retry")
        self.assertEqual(first, retry)
        self.assertEqual(1, len(retry["history"]))

    def test_request_key_reuse_with_different_args_is_rejected(self):
        self.create({"driver_id": "syn-driver-a"}, "reused-key")
        with self.assertRaises(RequestKeyReuse):
            self.create({"driver_id": "syn-driver-b"}, "reused-key")

    def test_update_retry_returns_historical_exact_snapshot_after_newer_write(self):
        created = self.create()
        first = self.store.update(
            created["trip_id"], 1, "dispatcher", "route",
            {"route_id": "path_a_exit13a_to_apm"}, "Use route A", "update-retry",
        )
        self.store.update(
            created["trip_id"], 2, "driver", "route",
            {"port_street_in_route": False}, "No Port Street", "update-later",
        )
        retry = self.store.update(
            created["trip_id"], 1, "dispatcher", "route",
            {"route_id": "path_a_exit13a_to_apm"}, "Use route A", "update-retry",
        )
        self.assertEqual(first, retry)
        self.assertEqual(2, retry["revision"])
        self.assertEqual(3, self.store.get(created["trip_id"])["revision"])

    def test_stale_revision_fails_without_changing_state(self):
        created = self.create()
        updated = self.store.update(
            created["trip_id"], 1, "driver", "route",
            {"route_id": "other"}, "other route", "update-1",
        )
        with self.assertRaises(RevisionConflict):
            self.store.update(
                created["trip_id"], 1, "driver", "route",
                {"route_id": "path_a_exit13a_to_apm"}, "stale", "update-stale",
            )
        self.assertEqual(updated, self.store.get(created["trip_id"]))

    def test_default_changed_fact_is_an_unresolved_conflict(self):
        created = self.create({"axle_count": 5})
        updated = self.store.update(
            created["trip_id"], 1, "dispatcher", "trip_dispatch",
            {"axle_count": 6}, "Dispatcher says six", "axle-conflict",
        )
        self.assertIsNone(updated["facts"]["axle_count"]["value"])
        self.assertEqual([5, 6], [
            record["value"] for record in updated["conflicts"][0]["observations"]
        ])
        self.assertEqual("axle_count", updated["conflicts"][0]["field"])
        self.assertEqual(["axle_count"], updated["history"][-1]["conflicted_fields"])

    def test_explicit_correction_resolves_conflict_and_retains_history(self):
        created = self.create({"axle_count": 5})
        conflicted = self.store.update(
            created["trip_id"], 1, "dispatcher", "trip_dispatch",
            {"axle_count": 6}, "Dispatcher says six", "conflict",
        )
        corrected = self.store.update(
            created["trip_id"], 2, "driver", "trip_dispatch",
            {"axle_count": 6}, "Driver corrects count", "correction", True,
        )
        self.assertEqual(6, corrected["facts"]["axle_count"]["value"])
        self.assertEqual([], corrected["conflicts"])
        self.assertEqual(["axle_count"], corrected["history"][-1]["corrected_fields"])
        self.assertEqual(3, len(corrected["history"]))
        self.assertEqual(conflicted["conflicts"][0]["observations"][0],
                         corrected["history"][0]["reported_facts"]["axle_count"])

    def test_global_correction_flag_rejects_two_unrelated_changes_atomically(self):
        created = self.create({
            "axle_count": 5,
            "route_id": "path_a_exit13a_to_apm",
        })
        with self.assertRaisesRegex(InputError, "only one independent field"):
            self.store.update(
                created["trip_id"], 1, "dispatcher", "trip_dispatch",
                {"axle_count": 6, "route_id": "path_b_us1_9_to_apm"},
                "Two corrections mixed together", "two-corrections", True,
            )
        self.assertEqual(created, self.store.get(created["trip_id"]))

    def test_first_value_after_explicit_unknown_does_not_conflict(self):
        created = self.create({"axle_count": None})
        updated = self.store.update(
            created["trip_id"], 1, "driver", "trip_dispatch",
            {"axle_count": 5}, "Counted five", "known-now",
        )
        self.assertEqual(5, updated["facts"]["axle_count"]["value"])
        self.assertEqual([], updated["conflicts"])

    def test_explicit_unknown_is_not_a_competing_observation(self):
        created = self.create({"axle_count": 5})
        updated = self.store.update(
            created["trip_id"], 1, "driver", "trip_dispatch",
            {"axle_count": None}, "I no longer know", "unknown-now",
        )
        self.assertIsNone(updated["facts"]["axle_count"]["value"])
        self.assertEqual([], updated["conflicts"])

    def test_driver_correction_invalidates_old_driver_facts_but_keeps_atomic_new_facts(self):
        created = self.create({
            "driver_id": "syn-driver-a",
            "subject_role": "truck_driver",
            "company_changed": False,
            "current_sealink_id": "SYN-SL-A",
            "twic_reported": True,
            "induction_reported": True,
        })
        updated = self.store.update(
            created["trip_id"], 1, "dispatcher", "terminal_entry",
            {
                "driver_id": "syn-driver-b",
                "subject_role": "truck_driver",
                "current_sealink_id": "SYN-SL-B",
            },
            "Correct driver is B with SeaLink B", "driver-correction", True,
        )
        self.assertEqual("syn-driver-b", updated["facts"]["driver_id"]["value"])
        self.assertEqual("SYN-SL-B", updated["facts"]["current_sealink_id"]["value"])
        self.assertEqual("truck_driver", updated["facts"]["subject_role"]["value"])
        self.assertNotIn("company_changed", updated["facts"])
        self.assertNotIn("twic_reported", updated["facts"])
        self.assertNotIn("induction_reported", updated["facts"])
        self.assertIn("company_changed", updated["invalidated_fields"])
        self.assertNotIn("subject_role", updated["invalidated_fields"])

    def test_identity_conflict_invalidates_dependent_reports(self):
        created = self.create({
            "driver_id": "syn-driver-a",
            "current_sealink_id": "SYN-SL-A",
            "twic_reported": True,
            "induction_reported": True,
        })
        updated = self.store.update(
            created["trip_id"], 1, "dispatcher", "terminal_entry",
            {"driver_id": "syn-driver-b"}, "Maybe driver B", "driver-conflict",
        )
        self.assertIsNone(updated["facts"]["driver_id"]["value"])
        self.assertEqual(["driver_id"], [item["field"] for item in updated["conflicts"]])
        self.assertNotIn("current_sealink_id", updated["facts"])
        self.assertNotIn("twic_reported", updated["facts"])
        self.assertIn("current_sealink_id", updated["invalidated_fields"])

    def test_vehicle_change_invalidates_measurements_registry_and_assignment_reports(self):
        facts = {
            "vehicle_id": "syn-vehicle-a",
            "gross_weight": {"value": 80_000, "unit": "lb"},
            "dtr_reported": True,
            "rfid_reported": True,
            "engine_model_year": 2020,
            "permit_type": "nj_single_trip",
            "permit_route_reported": True,
            "appointment_reported": True,
            "transaction_release_reported": True,
            "local_approval_reported": True,
        }
        created = self.create(facts)
        updated = self.store.update(
            created["trip_id"], 1, "dispatcher", "trip_dispatch",
            {"vehicle_id": "syn-vehicle-b"}, "Correct tractor B", "vehicle-correct", True,
        )
        for field in set(facts) - {"vehicle_id"}:
            self.assertNotIn(field, updated["facts"])
            self.assertIn(field, updated["invalidated_fields"])

    def test_sealink_terminal_route_and_time_changes_clear_transient_reports(self):
        created = self.create({
            "terminal_id": "facility_apm_elizabeth",
            "current_sealink_id": "SYN-SL-A",
            "sealink_registered_reported": True,
            "induction_reported": True,
            "appointment_reported": True,
            "transaction_release_reported": True,
            "terminal_approval_reported": True,
            "route_id": "path_a_exit13a_to_apm",
            "permit_route_reported": True,
            "port_street_in_route": False,
            "route_conditions_checked_at": "2026-09-10T12:00:00Z",
            "trip_at": "2026-09-10T13:00:00Z",
            "twic_reported": True,
            "dtr_reported": True,
            "rfid_reported": True,
        })
        sealink = self.store.update(
            created["trip_id"], 1, "driver", "terminal_entry",
            {"current_sealink_id": "SYN-SL-B"}, "Correct SeaLink", "sealink", True,
        )
        self.assertNotIn("sealink_registered_reported", sealink["facts"])
        self.assertNotIn("induction_reported", sealink["facts"])

        terminal = self.store.update(
            created["trip_id"], 2, "dispatcher", "terminal_entry",
            {"terminal_id": "synthetic_other_terminal"}, "Other terminal", "terminal", True,
        )
        for field in ("appointment_reported", "transaction_release_reported",
                      "terminal_approval_reported", "route_conditions_checked_at"):
            self.assertNotIn(field, terminal["facts"])

        # Repopulate route/time-dependent reports, then replace route and time.
        repopulated = self.store.update(
            created["trip_id"], 3, "dispatcher", "route",
            {
                "permit_route_reported": True,
                "port_street_in_route": False,
                "route_conditions_checked_at": "2026-09-10T12:05:00Z",
                "twic_reported": True,
                "dtr_reported": True,
                "rfid_reported": True,
            }, "Fresh checks", "fresh",
        )
        route = self.store.update(
            created["trip_id"], 4, "dispatcher", "route",
            {"route_id": "path_b_us1_9_to_apm"}, "Correct route B", "route", True,
        )
        for field in ("permit_route_reported", "port_street_in_route",
                      "route_conditions_checked_at"):
            self.assertNotIn(field, route["facts"])
        timed = self.store.update(
            created["trip_id"], 5, "dispatcher", "trip_dispatch",
            {"trip_at": "2026-09-11T13:00:00Z"}, "Trip moved a day", "time", True,
        )
        for field in ("twic_reported", "dtr_reported", "rfid_reported"):
            self.assertNotIn(field, timed["facts"])
        self.assertEqual(4, repopulated["revision"])

    def test_invalidated_field_can_be_repopulated_without_transplant(self):
        created = self.create({
            "vehicle_id": "syn-vehicle-a", "dtr_reported": True,
        })
        changed = self.store.update(
            created["trip_id"], 1, "dispatcher", "trip_dispatch",
            {"vehicle_id": "syn-vehicle-b"}, "new tractor", "vehicle", True,
        )
        self.assertIn("dtr_reported", changed["invalidated_fields"])
        refreshed = self.store.update(
            created["trip_id"], 2, "dispatcher", "trip_dispatch",
            {"dtr_reported": True}, "checked new tractor", "dtr-new",
        )
        self.assertNotIn("dtr_reported", refreshed["invalidated_fields"])
        self.assertEqual("checked new tractor", refreshed["facts"]["dtr_reported"]["source_text"])

    def test_cases_are_isolated_and_returned_objects_are_detached(self):
        first = self.create({"driver_id": "syn-driver-a"}, "first")
        second = self.create({"driver_id": "syn-driver-b"}, "second")
        first["facts"]["driver_id"]["value"] = "syn-driver-mutated"
        first["history"].clear()
        stored_first = self.store.get(first["trip_id"])
        stored_second = self.store.get(second["trip_id"])
        self.assertEqual("syn-driver-a", stored_first["facts"]["driver_id"]["value"])
        self.assertEqual(1, len(stored_first["history"]))
        self.assertEqual("syn-driver-b", stored_second["facts"]["driver_id"]["value"])

    def test_missing_or_forged_trip_id_is_rejected(self):
        with self.assertRaises(InputError):
            self.store.get("real-trip-123")
        with self.assertRaises(TripNotFound):
            self.store.get("syn-trip-" + "0" * 32)

    def test_failed_write_rolls_back_snapshot_and_idempotency_record(self):
        created = self.create({"route_id": "other"})
        original = self.store.get(created["trip_id"])
        with patch.object(self.store, "_save_request", side_effect=RuntimeError("injected")):
            with self.assertRaisesRegex(RuntimeError, "injected"):
                self.store.update(
                    created["trip_id"], 1, "driver", "route",
                    {"route_description": "A route"}, "route", "atomic-update",
                )
        self.assertEqual(original, self.store.get(created["trip_id"]))
        # The rolled-back key remains available for a successful retry.
        result = self.store.update(
            created["trip_id"], 1, "driver", "route",
            {"route_description": "A route"}, "route", "atomic-update",
        )
        self.assertEqual(2, result["revision"])

    def test_threaded_updates_on_one_revision_have_one_winner(self):
        created = self.create()
        barrier = threading.Barrier(2)
        results = []
        lock = threading.Lock()

        def update(suffix):
            try:
                store = TripStore(self.path)
                barrier.wait(timeout=10)
                value = store.update(
                    created["trip_id"], 1, "dispatcher", "route",
                    {"route_description": suffix}, suffix, f"thread-{suffix}",
                )
                outcome = ("ok", value["revision"])
            except RevisionConflict:
                outcome = ("conflict", None)
            with lock:
                results.append(outcome)

        threads = [threading.Thread(target=update, args=(suffix,)) for suffix in ("alpha", "beta")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(["conflict", "ok"], sorted(result[0] for result in results))
        self.assertEqual(2, self.store.get(created["trip_id"])["revision"])

    def test_process_updates_on_one_revision_have_one_winner(self):
        created = self.create()
        context = multiprocessing.get_context("spawn")
        barrier = context.Barrier(2)
        queue = context.Queue()
        processes = [
            context.Process(
                target=_process_update,
                args=(str(self.path), created["trip_id"], barrier, queue, f"process-{index}"),
            )
            for index in range(2)
        ]
        for process in processes:
            process.start()
        for process in processes:
            process.join(timeout=20)
        self.assertFalse(any(process.is_alive() for process in processes))
        self.assertTrue(all(process.exitcode == 0 for process in processes))
        results = [queue.get(timeout=5), queue.get(timeout=5)]
        self.assertEqual(["conflict", "ok"], sorted(result[0] for result in results))
        self.assertEqual(2, self.store.get(created["trip_id"])["revision"])

    def test_sqlite_contains_no_cross_case_or_failed_hidden_copy(self):
        first = self.create({"route_description": "only first"}, "case-one")
        second = self.create({}, "case-two")
        self.assertNotIn("route_description", second["facts"])
        connection = sqlite3.connect(self.path)
        try:
            self.assertEqual(2, connection.execute("SELECT COUNT(*) FROM trips").fetchone()[0])
            self.assertEqual(2, connection.execute("SELECT COUNT(*) FROM requests").fetchone()[0])
        finally:
            connection.close()
        self.assertEqual("only first", self.store.get(first["trip_id"])["facts"]["route_description"]["value"])


if __name__ == "__main__":
    unittest.main()
