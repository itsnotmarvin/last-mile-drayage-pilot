"""Private operator-managed synthetic verification receipts.

The store is deliberately separate from trip state and the public graph.  It is
opened lazily so an absent optional provider stays a deterministic empty
snapshot without creating local state during an assessment.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sqlite3
import stat

from .common import ArchiveError, EvidenceUnavailable, ROOT, digest, encode


STORE_SCHEMA = "drayage-verification-store-v1"
EMPTY_SET_SHA256 = digest([])
BUSY_TIMEOUT_MS = 30_000

_GRAPH_RELEASE = re.compile(r"[0-9a-f]{64}\Z")
_TRIP_ID = re.compile(r"syn-trip-[0-9a-f]{32}\Z")
_RECEIPT_ID = re.compile(r"syn-verification-[a-z0-9][a-z0-9-]{0,119}\Z")
_REVOCATION_AT = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z"
)

_TABLE_COLUMNS = {
    "verification_meta": (
        "singleton", "schema_version", "receipt_count", "receipt_set_sha256",
        "revocation_count", "revocation_head_sha256",
    ),
    "verification_receipts": (
        "receipt_id", "trip_id", "receipt_json", "content_sha256",
    ),
    "verification_revocations": (
        "sequence", "receipt_id", "event_json", "event_sha256",
        "previous_sha256", "chain_sha256",
    ),
}

_REQUIRED_SCHEMA_OBJECTS = {
    ("table", table, table) for table in _TABLE_COLUMNS
} | {
    ("index", "verification_receipts_by_trip", "verification_receipts"),
    ("trigger", "verification_receipts_no_update", "verification_receipts"),
    ("trigger", "verification_receipts_no_delete", "verification_receipts"),
    ("trigger", "verification_revocations_no_update", "verification_revocations"),
    ("trigger", "verification_revocations_no_delete", "verification_revocations"),
}

_SCHEMA = (
    """
    CREATE TABLE verification_meta (
        singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
        schema_version TEXT NOT NULL,
        receipt_count INTEGER NOT NULL CHECK (receipt_count >= 0),
        receipt_set_sha256 TEXT NOT NULL,
        revocation_count INTEGER NOT NULL CHECK (revocation_count >= 0),
        revocation_head_sha256 TEXT
    )
    """,
    """
    CREATE TABLE verification_receipts (
        receipt_id TEXT PRIMARY KEY,
        trip_id TEXT NOT NULL,
        receipt_json TEXT NOT NULL,
        content_sha256 TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE verification_revocations (
        sequence INTEGER PRIMARY KEY CHECK (sequence >= 1),
        receipt_id TEXT NOT NULL UNIQUE
            REFERENCES verification_receipts(receipt_id),
        event_json TEXT NOT NULL,
        event_sha256 TEXT NOT NULL,
        previous_sha256 TEXT,
        chain_sha256 TEXT NOT NULL
    )
    """,
    """
    CREATE TRIGGER verification_receipts_no_update
    BEFORE UPDATE ON verification_receipts
    BEGIN SELECT RAISE(ABORT, 'Verification receipts are immutable'); END
    """,
    """
    CREATE TRIGGER verification_receipts_no_delete
    BEFORE DELETE ON verification_receipts
    BEGIN SELECT RAISE(ABORT, 'Verification receipts are immutable'); END
    """,
    """
    CREATE TRIGGER verification_revocations_no_update
    BEFORE UPDATE ON verification_revocations
    BEGIN SELECT RAISE(ABORT, 'Verification revocations are append-only'); END
    """,
    """
    CREATE TRIGGER verification_revocations_no_delete
    BEFORE DELETE ON verification_revocations
    BEGIN SELECT RAISE(ABORT, 'Verification revocations are append-only'); END
    """,
    "CREATE INDEX verification_receipts_by_trip ON verification_receipts(trip_id)",
)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _case_context(case: dict, graph_release: str) -> dict:
    """Return the exact case/release values that receipts must bind."""
    if not isinstance(case, dict):
        raise ArchiveError("Verification receipts require a trip case object")
    if not isinstance(graph_release, str) or _GRAPH_RELEASE.fullmatch(graph_release) is None:
        raise ArchiveError("Verification receipts require a pinned graph release")

    try:
        trip_id = case["trip_id"]
        revision = case["revision"]
        facts = case["facts"]
        conflicts = case["conflicts"]
    except KeyError as exc:
        raise ArchiveError("Verification receipts require a complete trip case") from exc
    if not isinstance(trip_id, str) or _TRIP_ID.fullmatch(trip_id) is None:
        raise ArchiveError("Verification receipts require a server-issued synthetic trip")
    if type(revision) is not int or revision < 1:
        raise ArchiveError("Verification receipts require a positive trip revision")
    if not isinstance(facts, dict) or not isinstance(conflicts, list):
        raise ArchiveError("Verification receipts require canonical case facts and conflicts")

    bound_facts = {}
    for field, record in facts.items():
        if not isinstance(field, str) or not isinstance(record, dict) or "value" not in record:
            raise ArchiveError("Verification receipts require canonical case facts")
        bound_facts[field] = {"value": record["value"], "unit": record.get("unit")}
    try:
        from .verification_models import case_fingerprint

        case_sha256 = case_fingerprint({
            "trip_id": trip_id,
            "revision": revision,
            "facts": bound_facts,
            "conflicts": conflicts,
        })
    except (KeyError, TypeError, ValueError, RecursionError) as exc:
        raise ArchiveError("Verification receipts require finite JSON case values") from exc
    return {
        "trip_id": trip_id,
        "revision": revision,
        "case_sha256": case_sha256,
        "graph_release": graph_release,
    }


def _validate_receipt(receipt: dict, *, stored: bool) -> None:
    """Load the contract at use time so storage never becomes its authority."""
    try:
        from .verification_models import validate_receipt

        validate_receipt(receipt)
    except (KeyError, TypeError, ValueError, RecursionError) as exc:
        if not stored:
            raise
        raise ArchiveError("Stored verification receipt is invalid") from exc


def _canonical_receipt(receipt: dict, *, stored: bool) -> tuple[dict, str, str]:
    _validate_receipt(receipt, stored=stored)
    try:
        encoded = encode(receipt)
        copied = json.loads(encoded)
    except (json.JSONDecodeError, TypeError, ValueError, RecursionError) as exc:
        if not stored:
            raise
        raise ArchiveError("Stored verification receipt is not canonical JSON") from exc
    return copied, encoded, _sha256_text(encoded)


def _validate_reason(reason: str) -> None:
    if (not isinstance(reason, str) or not reason.strip() or len(reason) > 500
            or any(ord(character) < 32 for character in reason)):
        raise ArchiveError(
            "Revocation reason must be a nonblank single-line string of at most 500 characters"
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _empty_snapshot(context: dict) -> dict:
    version = digest({
        "trip_id": context["trip_id"],
        "case_sha256": context["case_sha256"],
        "graph_release": context["graph_release"],
        "receipts": [],
        "revocations": [],
    })
    return {"version": version, "receipts": [], "revoked_ids": []}


class VerificationStore:
    """SQLite receipt ledger writable only through the local operator surface."""

    def __init__(
            self,
            path: str | os.PathLike[str] = ROOT / ".runtime" / "operator-verifications.sqlite3",
    ):
        if not isinstance(path, (str, os.PathLike)):
            raise ArchiveError("VerificationStore path must be a filesystem path")
        raw_path = Path(path).expanduser()
        if str(raw_path) == ":memory:":
            raise ArchiveError("VerificationStore requires a private on-disk SQLite file")
        self.path = raw_path.absolute()
        self._check_target(allow_missing=True)

    def _check_target(self, *, allow_missing: bool) -> os.stat_result | None:
        try:
            info = self.path.lstat()
        except FileNotFoundError:
            if allow_missing:
                return None
            raise EvidenceUnavailable("Verification receipt store is unavailable") from None
        except OSError as exc:
            raise EvidenceUnavailable("Verification receipt store is unavailable") from exc
        if stat.S_ISLNK(info.st_mode):
            raise ArchiveError("Verification receipt store cannot be a symbolic link")
        if not stat.S_ISREG(info.st_mode):
            raise ArchiveError("Verification receipt store must be a regular file")
        if hasattr(os, "getuid") and info.st_uid != os.getuid():
            raise ArchiveError("Verification receipt store must be owned by the current operator")
        if stat.S_IMODE(info.st_mode) & 0o077:
            raise ArchiveError("Verification receipt store must be owner-only")
        return info

    def _ensure_parent(self) -> None:
        missing = []
        current = self.path.parent
        while True:
            try:
                info = current.lstat()
            except FileNotFoundError:
                missing.append(current)
                parent = current.parent
                if parent == current:
                    raise EvidenceUnavailable("Verification receipt directory is unavailable")
                current = parent
                continue
            except OSError as exc:
                raise EvidenceUnavailable("Verification receipt directory is unavailable") from exc
            if stat.S_ISLNK(info.st_mode):
                raise ArchiveError("Verification receipt directory cannot be a symbolic link")
            if not stat.S_ISDIR(info.st_mode):
                raise ArchiveError("Verification receipt parent must be a directory")
            break

        for directory in reversed(missing):
            try:
                directory.mkdir(mode=0o700)
            except FileExistsError:
                pass
            except OSError as exc:
                raise EvidenceUnavailable("Verification receipt directory is unavailable") from exc
            try:
                info = directory.lstat()
            except OSError as exc:
                raise EvidenceUnavailable("Verification receipt directory is unavailable") from exc
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                raise ArchiveError("Verification receipt directory path is unsafe")

    def _create_file(self) -> tuple[int, int]:
        self._ensure_parent()
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(self.path, flags, 0o600)
            try:
                os.fchmod(descriptor, 0o600)
                info = os.fstat(descriptor)
                if not stat.S_ISREG(info.st_mode):
                    raise ArchiveError("Verification receipt store must be a regular file")
                identity = (info.st_dev, info.st_ino)
            finally:
                os.close(descriptor)
        except FileExistsError:
            self._check_target(allow_missing=False)
            raise
        except ArchiveError:
            raise
        except OSError as exc:
            raise EvidenceUnavailable("Verification receipt store is unavailable") from exc
        return identity

    @contextmanager
    def _connect(self, *, readonly: bool):
        self._check_target(allow_missing=False)
        uri = self.path.as_uri() + ("?mode=ro" if readonly else "?mode=rw")
        try:
            connection = sqlite3.connect(
                uri, uri=True, timeout=30, isolation_level=None,
            )
            connection.row_factory = sqlite3.Row
            connection.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
            connection.execute("PRAGMA foreign_keys = ON")
            if readonly:
                connection.execute("PRAGMA query_only = ON")
            else:
                connection.execute("PRAGMA synchronous = FULL")
        except (OSError, sqlite3.DatabaseError) as exc:
            if "connection" in locals():
                connection.close()
            raise EvidenceUnavailable("Verification receipt store is unavailable") from exc
        try:
            yield connection
        except ArchiveError:
            raise
        except (OSError, sqlite3.DatabaseError) as exc:
            raise EvidenceUnavailable("Verification receipt store is unavailable") from exc
        finally:
            connection.close()

    def _initialize(self) -> None:
        identity = self._create_file()
        try:
            with self._connect(readonly=False) as connection:
                connection.execute("BEGIN IMMEDIATE")
                try:
                    for statement in _SCHEMA:
                        connection.execute(statement)
                    connection.execute(
                        """
                        INSERT INTO verification_meta(
                            singleton, schema_version, receipt_count,
                            receipt_set_sha256, revocation_count,
                            revocation_head_sha256
                        ) VALUES (1, ?, 0, ?, 0, NULL)
                        """,
                        (STORE_SCHEMA, EMPTY_SET_SHA256),
                    )
                    connection.commit()
                except BaseException:
                    connection.rollback()
                    raise
        except BaseException:
            try:
                info = self.path.lstat()
                if (info.st_dev, info.st_ino) == identity:
                    self.path.unlink()
            except OSError:
                pass
            raise
        self._check_target(allow_missing=False)

    def _ensure_initialized(self) -> None:
        if self._check_target(allow_missing=True) is not None:
            return
        try:
            self._initialize()
        except FileExistsError:
            # Another process created the file after our existence check.
            pass

    @staticmethod
    def _verify_schema(connection: sqlite3.Connection) -> sqlite3.Row:
        integrity = [row[0] for row in connection.execute("PRAGMA integrity_check")]
        if integrity != ["ok"] or connection.execute("PRAGMA foreign_key_check").fetchall():
            raise ArchiveError("Verification receipt database integrity check failed")

        objects = {
            (row["type"], row["name"], row["tbl_name"])
            for row in connection.execute(
                "SELECT type, name, tbl_name FROM sqlite_master "
                "WHERE type IN ('table', 'index', 'trigger') AND name NOT LIKE 'sqlite_%'"
            )
        }
        if objects != _REQUIRED_SCHEMA_OBJECTS:
            raise ArchiveError("Unsupported verification receipt store schema")
        for table, expected in _TABLE_COLUMNS.items():
            columns = tuple(row[1] for row in connection.execute(f'PRAGMA table_info("{table}")'))
            if columns != expected:
                raise ArchiveError("Unsupported verification receipt store schema")

        rows = connection.execute("SELECT * FROM verification_meta").fetchall()
        if len(rows) != 1 or rows[0]["singleton"] != 1:
            raise ArchiveError("Verification receipt store metadata is invalid")
        metadata = rows[0]
        if metadata["schema_version"] != STORE_SCHEMA:
            raise ArchiveError("Unsupported verification receipt store schema")
        return metadata

    @staticmethod
    def _decode_receipt_row(row: sqlite3.Row) -> dict:
        raw = row["receipt_json"]
        if not all(isinstance(row[field], str) for field in (
                "receipt_id", "trip_id", "receipt_json", "content_sha256")):
            raise ArchiveError("Stored verification receipt fields are invalid")
        try:
            receipt = json.loads(raw)
        except (json.JSONDecodeError, TypeError, RecursionError) as exc:
            raise ArchiveError("Stored verification receipt is unreadable") from exc
        if not isinstance(receipt, dict):
            raise ArchiveError("Stored verification receipt must be an object")
        canonical, encoded, content_sha256 = _canonical_receipt(receipt, stored=True)
        if raw != encoded:
            raise ArchiveError("Stored verification receipt is not canonical JSON")
        if (not hmac.compare_digest(row["content_sha256"], content_sha256)
                or receipt.get("id") != row["receipt_id"]
                or receipt.get("trip_id") != row["trip_id"]):
            raise ArchiveError("Stored verification receipt integrity check failed")
        return canonical

    @staticmethod
    def _decode_revocation_row(
            row: sqlite3.Row, expected_sequence: int, previous_sha256: str | None,
            receipt_ids: set[str],
    ) -> dict:
        if row["sequence"] != expected_sequence:
            raise ArchiveError("Verification revocation journal sequence is invalid")
        text_fields = ("receipt_id", "event_json", "event_sha256", "chain_sha256")
        if not all(isinstance(row[field], str) for field in text_fields):
            raise ArchiveError("Verification revocation journal fields are invalid")
        if row["previous_sha256"] is not None and not isinstance(row["previous_sha256"], str):
            raise ArchiveError("Verification revocation journal fields are invalid")
        try:
            event = json.loads(row["event_json"])
        except (json.JSONDecodeError, TypeError, RecursionError) as exc:
            raise ArchiveError("Verification revocation journal is unreadable") from exc
        if (not isinstance(event, dict)
                or set(event) != {"receipt_id", "reason", "revoked_at"}
                or event.get("receipt_id") != row["receipt_id"]
                or row["receipt_id"] not in receipt_ids):
            raise ArchiveError("Verification revocation journal is invalid")
        _validate_reason(event.get("reason"))
        if (not isinstance(event.get("revoked_at"), str)
                or _REVOCATION_AT.fullmatch(event["revoked_at"]) is None):
            raise ArchiveError("Verification revocation timestamp is invalid")
        try:
            datetime.fromisoformat(event["revoked_at"].replace("Z", "+00:00"))
        except ValueError as exc:
            raise ArchiveError("Verification revocation timestamp is invalid") from exc
        encoded = encode(event)
        event_sha256 = _sha256_text(encoded)
        chain_sha256 = digest({
            "sequence": expected_sequence,
            "previous_sha256": previous_sha256,
            "event_sha256": event_sha256,
        })
        if (row["event_json"] != encoded
                or row["previous_sha256"] != previous_sha256
                or not hmac.compare_digest(row["event_sha256"], event_sha256)
                or not hmac.compare_digest(row["chain_sha256"], chain_sha256)):
            raise ArchiveError("Verification revocation journal integrity check failed")
        return {"event": event, "chain_sha256": chain_sha256}

    @classmethod
    def _read_verified(cls, connection: sqlite3.Connection) -> tuple[dict, list[dict]]:
        metadata = cls._verify_schema(connection)
        receipts = {}
        receipt_rows = connection.execute(
            "SELECT receipt_id, trip_id, receipt_json, content_sha256 "
            "FROM verification_receipts ORDER BY receipt_id"
        ).fetchall()
        for row in receipt_rows:
            receipt = cls._decode_receipt_row(row)
            receipts[row["receipt_id"]] = {
                "receipt": receipt,
                "content_sha256": row["content_sha256"],
            }
        receipt_set_sha256 = digest([
            {"id": receipt_id, "sha256": item["content_sha256"]}
            for receipt_id, item in receipts.items()
        ])
        if (metadata["receipt_count"] != len(receipts)
                or not isinstance(metadata["receipt_set_sha256"], str)
                or not hmac.compare_digest(metadata["receipt_set_sha256"], receipt_set_sha256)):
            raise ArchiveError("Verification receipt ledger integrity check failed")

        revocations = []
        previous_sha256 = None
        rows = connection.execute(
            "SELECT sequence, receipt_id, event_json, event_sha256, "
            "previous_sha256, chain_sha256 "
            "FROM verification_revocations ORDER BY sequence"
        ).fetchall()
        for expected_sequence, row in enumerate(rows, 1):
            decoded = cls._decode_revocation_row(
                row, expected_sequence, previous_sha256, set(receipts),
            )
            previous_sha256 = decoded["chain_sha256"]
            revocations.append(decoded["event"])
        if (metadata["revocation_count"] != len(revocations)
                or metadata["revocation_head_sha256"] != previous_sha256):
            raise ArchiveError("Verification revocation journal integrity check failed")
        return receipts, revocations

    @staticmethod
    def _snapshot_from_state(
            receipts: dict, revocations: list[dict], context: dict,
    ) -> dict:
        trip_id = context["trip_id"]
        relevant_ids = {
            receipt_id for receipt_id, item in receipts.items()
            if item["receipt"]["trip_id"] == trip_id
        }
        relevant_revocations = sorted(
            (event for event in revocations if event["receipt_id"] in relevant_ids),
            key=lambda event: (event["receipt_id"], event["revoked_at"], event["reason"]),
        )
        revoked_ids = sorted({event["receipt_id"] for event in relevant_revocations})
        revoked = set(revoked_ids)
        active_receipts = [
            receipts[receipt_id]["receipt"] for receipt_id in sorted(relevant_ids - revoked)
        ]
        version = digest({
            "trip_id": trip_id,
            "case_sha256": context["case_sha256"],
            "graph_release": context["graph_release"],
            "receipts": active_receipts,
            "revocations": relevant_revocations,
        })
        return {
            "version": version,
            "receipts": active_receipts,
            "revoked_ids": revoked_ids,
        }

    def put(self, receipts: list[dict], case: dict, graph_release: str) -> dict:
        context = _case_context(case, graph_release)
        if not isinstance(receipts, list):
            raise ArchiveError("Verification receipts must be supplied as a list")

        pending = {}
        for receipt in receipts:
            canonical, encoded, content_sha256 = _canonical_receipt(receipt, stored=False)
            if (canonical["trip_id"] != context["trip_id"]
                    or canonical["trip_revision"] != context["revision"]
                    or canonical["case_sha256"] != context["case_sha256"]
                    or canonical["graph_release"] != context["graph_release"]):
                raise ArchiveError("Verification receipt does not bind the supplied case and graph release")
            receipt_id = canonical["id"]
            previous = pending.get(receipt_id)
            if previous is not None and previous["encoded"] != encoded:
                raise ArchiveError("Verification receipt identity is immutable")
            pending[receipt_id] = {
                "receipt": canonical,
                "encoded": encoded,
                "content_sha256": content_sha256,
            }

        if not pending and self._check_target(allow_missing=True) is None:
            return _empty_snapshot(context)
        self._ensure_initialized()
        with self._connect(readonly=False) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                stored, revocations = self._read_verified(connection)
                for receipt_id, item in pending.items():
                    previous = stored.get(receipt_id)
                    if previous is not None and previous["content_sha256"] != item["content_sha256"]:
                        raise ArchiveError("Verification receipt identity is immutable")
                for receipt_id, item in pending.items():
                    if receipt_id in stored:
                        continue
                    receipt = item["receipt"]
                    connection.execute(
                        """
                        INSERT INTO verification_receipts(
                            receipt_id, trip_id, receipt_json, content_sha256
                        ) VALUES (?, ?, ?, ?)
                        """,
                        (receipt_id, receipt["trip_id"], item["encoded"], item["content_sha256"]),
                    )
                if any(receipt_id not in stored for receipt_id in pending):
                    rows = connection.execute(
                        "SELECT receipt_id, content_sha256 FROM verification_receipts "
                        "ORDER BY receipt_id"
                    ).fetchall()
                    connection.execute(
                        """
                        UPDATE verification_meta
                        SET receipt_count = ?, receipt_set_sha256 = ?
                        WHERE singleton = 1
                        """,
                        (len(rows), digest([
                            {"id": row["receipt_id"], "sha256": row["content_sha256"]}
                            for row in rows
                        ])),
                    )
                stored, revocations = self._read_verified(connection)
                result = self._snapshot_from_state(stored, revocations, context)
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
        return result

    def revoke(self, receipt_id: str, reason: str) -> None:
        if not isinstance(receipt_id, str) or _RECEIPT_ID.fullmatch(receipt_id) is None:
            raise ArchiveError("Revocation requires a synthetic verification receipt ID")
        _validate_reason(reason)
        if self._check_target(allow_missing=True) is None:
            raise ArchiveError("Cannot revoke an unknown verification receipt")

        with self._connect(readonly=False) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                receipts, revocations = self._read_verified(connection)
                if receipt_id not in receipts:
                    raise ArchiveError("Cannot revoke an unknown verification receipt")
                previous_event = next(
                    (event for event in revocations if event["receipt_id"] == receipt_id), None,
                )
                if previous_event is not None:
                    if previous_event["reason"] == reason:
                        connection.commit()
                        return None
                    raise ArchiveError("Verification receipt revocation is immutable")

                metadata = connection.execute(
                    "SELECT * FROM verification_meta WHERE singleton = 1"
                ).fetchone()
                sequence = metadata["revocation_count"] + 1
                event = {
                    "receipt_id": receipt_id,
                    "reason": reason,
                    "revoked_at": _utc_now(),
                }
                event_json = encode(event)
                event_sha256 = _sha256_text(event_json)
                previous_sha256 = metadata["revocation_head_sha256"]
                chain_sha256 = digest({
                    "sequence": sequence,
                    "previous_sha256": previous_sha256,
                    "event_sha256": event_sha256,
                })
                connection.execute(
                    """
                    INSERT INTO verification_revocations(
                        sequence, receipt_id, event_json, event_sha256,
                        previous_sha256, chain_sha256
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (sequence, receipt_id, event_json, event_sha256,
                     previous_sha256, chain_sha256),
                )
                connection.execute(
                    """
                    UPDATE verification_meta
                    SET revocation_count = ?, revocation_head_sha256 = ?
                    WHERE singleton = 1
                    """,
                    (sequence, chain_sha256),
                )
                self._read_verified(connection)
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
        return None

    def snapshot(self, case: dict, graph_release: str) -> dict:
        context = _case_context(case, graph_release)
        if self._check_target(allow_missing=True) is None:
            return _empty_snapshot(context)
        with self._connect(readonly=True) as connection:
            receipts, revocations = self._read_verified(connection)
            result = self._snapshot_from_state(receipts, revocations, context)
        self._check_target(allow_missing=False)
        return result
