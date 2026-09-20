"""Integrity and lifecycle tests for operator-only synthetic receipts."""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from neo4j_kg.common import ArchiveError, EvidenceUnavailable, digest, encode
from neo4j_kg.service import InputError
from neo4j_kg.verification_models import case_fingerprint, validate_receipt
import neo4j_kg.verification_store as verification_store
from neo4j_kg.verification_store import VerificationStore


ROOT = Path(__file__).resolve().parents[1]


class VerificationStoreTests(unittest.TestCase):
    release = "a" * 64

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.path = self.root / "private" / "operator-verifications.sqlite3"
        self.case = {
            "trip_id": "syn-trip-" + "1" * 32,
            "revision": 1,
            "facts": {
                "gross_weight": {
                    "value": 80_000,
                    "unit": "lb",
                    "basis": "user_reported",
                },
            },
            "conflicts": [],
        }
        self.store = VerificationStore(self.path)

    def tearDown(self):
        self.temporary.cleanup()

    def receipt(self, suffix="a", *, case=None, release=None, payload=None):
        bound_case = self.case if case is None else case
        return {
            "id": "syn-verification-" + suffix,
            "schema_version": "drayage-verification-v1",
            "mode": "synthetic_only",
            "kind": "transaction",
            "provider_id": "syn-provider-transaction",
            "authority_role": "terminal_operator",
            "graph_release": self.release if release is None else release,
            "trip_id": bound_case["trip_id"],
            "trip_revision": bound_case["revision"],
            "case_sha256": case_fingerprint(bound_case),
            "observed_at": "2026-09-13T10:00:00Z",
            "valid_from": "2026-09-13T09:00:00Z",
            "valid_until": "2026-09-13T11:00:00Z",
            "payload": {
                "move_id": "syn-move-test",
                "move_type": "import_pickup",
                "terminal_id": "facility_apm_elizabeth",
                "load_id": "syn-load-test",
                "fully_available": True,
                "holds_complete": True,
                "freight_hold": False,
                "customer_hold": False,
                "demurrage_hold": False,
                "customs_hold": False,
                "other_hold": False,
            } if payload is None else payload,
        }

    def connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def run_cli(self, *arguments):
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "manage_verifications.py"),
                *arguments,
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        return json.loads(completed.stdout)

    def test_missing_snapshot_is_deterministic_and_creates_nothing(self):
        first = self.store.snapshot(self.case, self.release)
        second = self.store.snapshot(copy.deepcopy(self.case), self.release)

        self.assertEqual(first, second)
        self.assertRegex(first["version"], r"^[0-9a-f]{64}$")
        self.assertEqual([], first["receipts"])
        self.assertEqual([], first["revoked_ids"])
        self.assertFalse(self.path.exists())
        self.assertFalse(self.path.parent.exists())
        self.assertEqual(first, self.store.put([], self.case, self.release))
        self.assertFalse(self.path.exists())

    def test_put_is_canonical_sorted_private_and_preserves_parent_mode(self):
        self.path.parent.mkdir()
        os.chmod(self.path.parent, 0o755)
        before = stat_mode(self.path.parent)
        second = self.receipt("b")
        first = self.receipt("a")

        snapshot = self.store.put([second, first], self.case, self.release)

        self.assertEqual([first, second], snapshot["receipts"])
        self.assertEqual([], snapshot["revoked_ids"])
        self.assertEqual(0o600, stat_mode(self.path))
        self.assertEqual(before, stat_mode(self.path.parent))
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT receipt_id, receipt_json FROM verification_receipts ORDER BY receipt_id"
            ).fetchall()
        self.assertEqual(["syn-verification-a", "syn-verification-b"], [r[0] for r in rows])
        self.assertEqual(encode(first), rows[0]["receipt_json"])

    def test_new_directories_are_private(self):
        self.store.put([self.receipt()], self.case, self.release)
        self.assertEqual(0o700, stat_mode(self.path.parent))

    def test_real_contract_validation_rejects_semantic_conflict_before_creation(self):
        receipt = self.receipt()
        receipt["payload"]["freight_hold"] = True

        with self.assertRaisesRegex(InputError, "Available container"):
            self.store.put([receipt], self.case, self.release)

        self.assertFalse(self.path.exists())
        self.assertFalse(self.path.parent.exists())

    def test_real_contract_accepts_receipt_and_returns_none(self):
        receipt = self.receipt()

        self.assertIsNone(validate_receipt(receipt))
        self.assertEqual([receipt], self.store.put(
            [receipt], self.case, self.release,
        )["receipts"])

    def test_exact_bindings_are_checked_before_any_database_is_created(self):
        candidates = []
        wrong_trip = self.receipt()
        wrong_trip["trip_id"] = "syn-trip-" + "2" * 32
        candidates.append(wrong_trip)
        wrong_revision = self.receipt()
        wrong_revision["trip_revision"] = 2
        candidates.append(wrong_revision)
        wrong_case_hash = self.receipt()
        wrong_case_hash["case_sha256"] = "0" * 64
        candidates.append(wrong_case_hash)
        wrong_release = self.receipt()
        wrong_release["graph_release"] = "b" * 64
        candidates.append(wrong_release)

        for receipt in candidates:
            with self.subTest(field=receipt), self.assertRaisesRegex(ArchiveError, "bind"):
                self.store.put([self.receipt("valid"), receipt], self.case, self.release)
            self.assertFalse(self.path.exists())

    def test_batch_rejection_is_atomic_and_receipt_ids_are_immutable(self):
        original = self.receipt("original")
        baseline = self.store.put([original], self.case, self.release)
        changed = copy.deepcopy(original)
        changed["payload"]["fully_available"] = False

        with self.assertRaisesRegex(ArchiveError, "immutable"):
            self.store.put(
                [self.receipt("would-have-been-new"), changed],
                self.case,
                self.release,
            )

        self.assertEqual(baseline, self.store.snapshot(self.case, self.release))
        with self.connect() as connection:
            count = connection.execute(
                "SELECT count(*) FROM verification_receipts"
            ).fetchone()[0]
        self.assertEqual(1, count)

    def test_same_canonical_receipt_is_idempotent_within_and_across_puts(self):
        receipt = self.receipt()
        first = self.store.put([receipt, copy.deepcopy(receipt)], self.case, self.release)
        retry = self.store.put([copy.deepcopy(receipt)], self.case, self.release)

        self.assertEqual(first, retry)
        self.assertEqual([receipt], retry["receipts"])
        with self.connect() as connection:
            self.assertEqual(
                1,
                connection.execute("SELECT count(*) FROM verification_receipts").fetchone()[0],
            )

    def test_input_and_returned_snapshot_mutation_cannot_change_stored_receipt(self):
        receipt = self.receipt()
        expected = copy.deepcopy(receipt)
        snapshot = self.store.put([receipt], self.case, self.release)

        receipt["payload"]["fully_available"] = False
        snapshot["receipts"][0]["payload"]["fully_available"] = False

        self.assertEqual(
            [expected],
            self.store.snapshot(self.case, self.release)["receipts"],
        )

    def test_snapshot_keeps_stale_revision_and_release_receipts_for_same_trip(self):
        old = self.receipt("old")
        self.store.put([old], self.case, self.release)
        current_case = copy.deepcopy(self.case)
        current_case["revision"] = 2
        current_case["facts"]["gross_weight"]["value"] = 81_000
        current_release = "b" * 64

        stale_snapshot = self.store.snapshot(current_case, current_release)
        self.assertEqual([old], stale_snapshot["receipts"])

        current = self.receipt(
            "current", case=current_case, release=current_release,
        )
        combined = self.store.put([current], current_case, current_release)
        self.assertEqual([current, old], combined["receipts"])
        self.assertNotEqual(stale_snapshot["version"], combined["version"])

    def test_snapshot_excludes_other_trips_and_their_revocations(self):
        own = self.receipt("own")
        self.store.put([own], self.case, self.release)
        other_case = copy.deepcopy(self.case)
        other_case["trip_id"] = "syn-trip-" + "2" * 32
        other = self.receipt("other", case=other_case)
        self.store.put([other], other_case, self.release)
        self.store.revoke(other["id"], "Other trip was cancelled")

        snapshot = self.store.snapshot(self.case, self.release)
        self.assertEqual([own], snapshot["receipts"])
        self.assertEqual([], snapshot["revoked_ids"])

    def test_receipt_identity_cannot_be_reused_across_trips(self):
        own = self.receipt("global-id")
        self.store.put([own], self.case, self.release)
        other_case = copy.deepcopy(self.case)
        other_case["trip_id"] = "syn-trip-" + "2" * 32
        other = self.receipt("global-id", case=other_case)

        with self.assertRaisesRegex(ArchiveError, "identity is immutable"):
            self.store.put([other], other_case, self.release)

        self.assertEqual([own], self.store.snapshot(
            self.case, self.release,
        )["receipts"])
        self.assertEqual([], self.store.snapshot(
            other_case, self.release,
        )["receipts"])

    def test_revoke_removes_receipt_records_id_and_is_repeat_safe(self):
        revoked = self.receipt("revoked")
        active = self.receipt("active")
        before = self.store.put([revoked, active], self.case, self.release)

        self.assertIsNone(self.store.revoke(revoked["id"], "Operator withdrew the observation"))
        after = self.store.snapshot(self.case, self.release)

        self.assertEqual([active], after["receipts"])
        self.assertEqual([revoked["id"]], after["revoked_ids"])
        self.assertNotEqual(before["version"], after["version"])
        self.assertIsNone(self.store.revoke(revoked["id"], "Operator withdrew the observation"))
        self.assertEqual(after, self.store.snapshot(self.case, self.release))
        with self.assertRaisesRegex(ArchiveError, "immutable"):
            self.store.revoke(revoked["id"], "A different reason")
        with self.connect() as connection:
            self.assertEqual(
                1,
                connection.execute("SELECT count(*) FROM verification_revocations").fetchone()[0],
            )

    def test_unknown_revocation_does_not_create_a_store(self):
        with self.assertRaisesRegex(ArchiveError, "unknown"):
            self.store.revoke("syn-verification-missing", "No such observation")
        self.assertFalse(self.path.exists())

    def test_receipt_hash_corruption_is_never_an_empty_fallback(self):
        self.store.put([self.receipt()], self.case, self.release)
        with self.connect() as connection:
            connection.execute("DROP TRIGGER verification_receipts_no_update")
            connection.execute(
                "UPDATE verification_receipts SET content_sha256 = ?",
                ("0" * 64,),
            )
            connection.execute(
                """
                CREATE TRIGGER verification_receipts_no_update
                BEFORE UPDATE ON verification_receipts
                BEGIN SELECT RAISE(ABORT, 'Verification receipts are immutable'); END
                """
            )

        with self.assertRaisesRegex(ArchiveError, "integrity"):
            self.store.snapshot(self.case, self.release)

    def test_read_revalidates_schema_even_when_ledger_hashes_match(self):
        receipt = self.receipt()
        self.store.put([receipt], self.case, self.release)
        receipt["payload"]["freight_hold"] = True
        encoded = encode(receipt)
        content_sha256 = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        receipt_set_sha256 = digest([{
            "id": receipt["id"], "sha256": content_sha256,
        }])
        with self.connect() as connection:
            connection.execute("DROP TRIGGER verification_receipts_no_update")
            connection.execute(
                """
                UPDATE verification_receipts
                SET receipt_json = ?, content_sha256 = ?
                WHERE receipt_id = ?
                """,
                (encoded, content_sha256, receipt["id"]),
            )
            connection.execute(
                "UPDATE verification_meta SET receipt_set_sha256 = ?",
                (receipt_set_sha256,),
            )
            connection.execute(
                """
                CREATE TRIGGER verification_receipts_no_update
                BEFORE UPDATE ON verification_receipts
                BEGIN SELECT RAISE(ABORT, 'Verification receipts are immutable'); END
                """
            )

        with self.assertRaisesRegex(ArchiveError, "Stored verification receipt is invalid"):
            self.store.snapshot(self.case, self.release)

    def test_revocation_hash_chain_detects_tampering(self):
        receipt = self.receipt()
        self.store.put([receipt], self.case, self.release)
        self.store.revoke(receipt["id"], "Original reason")
        with self.connect() as connection:
            connection.execute("DROP TRIGGER verification_revocations_no_update")
            event = json.loads(connection.execute(
                "SELECT event_json FROM verification_revocations"
            ).fetchone()[0])
            event["reason"] = "Tampered reason"
            connection.execute(
                "UPDATE verification_revocations SET event_json = ?",
                (encode(event),),
            )
            connection.execute(
                """
                CREATE TRIGGER verification_revocations_no_update
                BEFORE UPDATE ON verification_revocations
                BEGIN SELECT RAISE(ABORT, 'Verification revocations are append-only'); END
                """
            )

        with self.assertRaisesRegex(ArchiveError, "integrity"):
            self.store.snapshot(self.case, self.release)

    def test_missing_immutability_trigger_is_rejected_as_schema_corruption(self):
        self.store.put([self.receipt()], self.case, self.release)
        with self.connect() as connection:
            connection.execute("DROP TRIGGER verification_receipts_no_delete")

        with self.assertRaisesRegex(ArchiveError, "Unsupported.*schema"):
            self.store.snapshot(self.case, self.release)

    def test_database_triggers_enforce_immutable_and_append_only_rows(self):
        receipt = self.receipt()
        self.store.put([receipt], self.case, self.release)
        self.store.revoke(receipt["id"], "Withdrawn")
        with self.connect() as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE verification_receipts SET trip_id = trip_id"
                )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("DELETE FROM verification_revocations")

    def test_corrupt_or_unsupported_existing_store_raises(self):
        corrupt_path = self.root / "corrupt.sqlite3"
        corrupt_path.write_bytes(b"this is not sqlite")
        os.chmod(corrupt_path, 0o600)
        corrupt = VerificationStore(corrupt_path)
        with self.assertRaises((ArchiveError, EvidenceUnavailable)):
            corrupt.snapshot(self.case, self.release)

        unsupported_path = self.root / "unsupported.sqlite3"
        with sqlite3.connect(unsupported_path) as connection:
            connection.execute("CREATE TABLE unrelated(value TEXT)")
        os.chmod(unsupported_path, 0o600)
        unsupported = VerificationStore(unsupported_path)
        with self.assertRaisesRegex(ArchiveError, "Unsupported"):
            unsupported.snapshot(self.case, self.release)

    def test_real_sqlite_write_failure_is_unavailable_and_atomic(self):
        baseline_receipt = self.receipt("baseline")
        baseline = self.store.put([baseline_receipt], self.case, self.release)
        blocker = sqlite3.connect(self.path, isolation_level=None)
        blocker.execute("BEGIN EXCLUSIVE")
        try:
            with mock.patch.object(verification_store, "BUSY_TIMEOUT_MS", 1):
                with self.assertRaisesRegex(EvidenceUnavailable, "unavailable"):
                    self.store.put(
                        [self.receipt("blocked")], self.case, self.release,
                    )
        finally:
            blocker.rollback()
            blocker.close()

        self.assertEqual(baseline, self.store.snapshot(self.case, self.release))

    def test_real_sqlite_read_and_revoke_fail_closed_while_locked(self):
        receipt = self.receipt("locked")
        baseline = self.store.put([receipt], self.case, self.release)
        blocker = sqlite3.connect(self.path, isolation_level=None)
        blocker.execute("BEGIN EXCLUSIVE")
        try:
            with mock.patch.object(verification_store, "BUSY_TIMEOUT_MS", 1):
                with self.assertRaisesRegex(EvidenceUnavailable, "unavailable"):
                    self.store.snapshot(self.case, self.release)
                with self.assertRaisesRegex(EvidenceUnavailable, "unavailable"):
                    self.store.revoke(receipt["id"], "Must not commit while locked")
        finally:
            blocker.rollback()
            blocker.close()

        self.assertEqual(baseline, self.store.snapshot(self.case, self.release))

    def test_schema_version_tampering_raises(self):
        self.store.put([self.receipt()], self.case, self.release)
        with self.connect() as connection:
            connection.execute(
                "UPDATE verification_meta SET schema_version = 'future-version'"
            )
        with self.assertRaisesRegex(ArchiveError, "Unsupported"):
            self.store.snapshot(self.case, self.release)

    def test_unsafe_paths_and_permissions_are_rejected(self):
        with self.assertRaises(ArchiveError):
            VerificationStore(":memory:")

        directory = self.root / "directory.sqlite3"
        directory.mkdir()
        with self.assertRaisesRegex(ArchiveError, "regular file"):
            VerificationStore(directory)

        self.store.put([self.receipt()], self.case, self.release)
        link = self.root / "linked.sqlite3"
        link.symlink_to(self.path)
        with self.assertRaisesRegex(ArchiveError, "symbolic link"):
            VerificationStore(link)

        os.chmod(self.path, 0o640)
        with self.assertRaisesRegex(ArchiveError, "owner-only"):
            VerificationStore(self.path)

    def test_symbolic_link_parent_is_not_followed_on_creation(self):
        target = self.root / "target"
        target.mkdir()
        linked_parent = self.root / "linked-parent"
        linked_parent.symlink_to(target, target_is_directory=True)
        store = VerificationStore(linked_parent / "receipts.sqlite3")

        with self.assertRaisesRegex(ArchiveError, "directory.*symbolic link"):
            store.put([self.receipt()], self.case, self.release)
        self.assertFalse((target / "receipts.sqlite3").exists())

    def test_operator_cli_schema_is_explicit_and_creates_no_store(self):
        result = self.run_cli("schema")

        self.assertEqual("synthetic_only", result["mode"])
        self.assertEqual(
            "drayage-verification-v1",
            result["receipt_schema"]["oneOf"][0]["properties"]["schema_version"]["const"],
        )
        self.assertRegex(result["contract_sha256"], r"^[0-9a-f]{64}$")
        self.assertIn("no real authority", result["notice"])
        self.assertFalse(self.path.exists())

    def test_operator_cli_import_list_and_revoke_exposes_metadata_only(self):
        case_path = self.root / "case.json"
        receipts_path = self.root / "receipts.json"
        case_path.write_text(json.dumps(self.case), encoding="utf-8")
        receipt = self.receipt("cli")
        receipts_path.write_text(json.dumps([receipt]), encoding="utf-8")
        common = (
            "--store", str(self.path), "--case", str(case_path),
            "--graph-release", self.release,
        )

        imported = self.run_cli(
            "import", *common, "--receipts", str(receipts_path),
        )
        listed = self.run_cli("list", *common)

        self.assertEqual("import", imported["operation"])
        self.assertEqual(imported["snapshot_version"], listed["snapshot_version"])
        self.assertEqual(1, listed["receipt_count"])
        self.assertEqual(receipt["id"], listed["receipts"][0]["id"])
        self.assertNotIn("payload", listed["receipts"][0])

        revoked = self.run_cli(
            "revoke", "--store", str(self.path), "--id", receipt["id"],
            "--reason", "Synthetic fixture withdrawn by operator",
        )
        after = self.run_cli("list", *common)
        self.assertEqual("revoked", revoked["status"])
        self.assertEqual([], after["receipts"])
        self.assertEqual([receipt["id"]], after["revoked_ids"])


def stat_mode(path):
    return path.stat().st_mode & 0o777


if __name__ == "__main__":
    unittest.main()
