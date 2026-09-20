"""Durable, isolated conversation state for synthetic trip assessments."""

from __future__ import annotations

import copy
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sqlite3

from .service import InputError
from .trip_models import REPORTER_ROLES, normalize_facts


QUESTION_SCOPES = ("induction", "terminal_entry", "trip_dispatch", "route", "unknown")
MODE = "synthetic_prototype_only"
MAX_REQUEST_KEY = 120

_TRIP_ID = re.compile(r"syn-trip-[0-9a-f]{32}\Z")

# A replacement is accepted only when it is an explicit correction (or when a
# known identity is deliberately cleared to unknown).  Facts supplied in that
# same update are new observations for the replacement and survive the clear.
INVALIDATION_RULES = {
    "terminal_id": frozenset((
        "appointment_reported", "transaction_release_reported",
        "terminal_approval_reported", "port_approval_reported",
        "route_conditions_checked_at", "induction_reported",
    )),
    "driver_id": frozenset((
        "subject_role", "company_changed", "current_sealink_id", "twic_reported",
        "sealink_registered_reported", "induction_reported",
    )),
    "vehicle_id": frozenset((
        "gross_weight", "axle_weights", "axle_spacings", "axle_count", "axle_layout", "width",
        "height", "overall_length", "semitrailer_length", "dtr_reported",
        "rfid_reported", "engine_model_year", "permit_type",
        "permit_route_reported", "turnpike_approval_reported",
        "local_approval_reported", "port_approval_reported",
        "terminal_approval_reported", "appointment_reported",
        "transaction_release_reported",
    )),
    "trailer_id": frozenset((
        "gross_weight", "axle_weights", "axle_spacings", "axle_count", "axle_layout", "width",
        "height", "overall_length", "semitrailer_length", "container_sealed",
        "load_divisible", "cargo_hazardous", "permit_type",
        "permit_route_reported", "turnpike_approval_reported",
        "local_approval_reported", "port_approval_reported",
        "terminal_approval_reported", "appointment_reported",
        "transaction_release_reported",
    )),
    "current_sealink_id": frozenset((
        "sealink_registered_reported", "induction_reported",
    )),
    "route_id": frozenset((
        "permit_route_reported", "turnpike_approval_reported",
        "local_approval_reported", "port_approval_reported",
        "terminal_approval_reported", "port_street_in_route",
        "route_conditions_checked_at",
    )),
    "route_description": frozenset((
        "permit_route_reported", "turnpike_approval_reported",
        "local_approval_reported", "port_approval_reported",
        "terminal_approval_reported", "port_street_in_route",
        "route_conditions_checked_at",
    )),
    "trip_at": frozenset((
        "appointment_reported", "transaction_release_reported",
        "permit_route_reported", "turnpike_approval_reported",
        "local_approval_reported", "port_approval_reported",
        "terminal_approval_reported", "route_conditions_checked_at",
        "twic_reported", "sealink_registered_reported", "induction_reported",
        "dtr_reported", "rfid_reported",
    )),
}


INVALIDATION_RULES["load_id"] = frozenset(("gross_weight", "axle_layout", "axle_weights", "axle_spacings", "width", "height", "overall_length", "semitrailer_length", "container_sealed", "load_divisible", "cargo_hazardous", "permit_type", "permit_route_reported", "turnpike_approval_reported", "local_approval_reported", "port_approval_reported", "terminal_approval_reported", "transaction_release_reported", "appointment_reported"))
for _move_field in ("move_id", "move_type"):
    INVALIDATION_RULES[_move_field] = frozenset(("transaction_release_reported", "appointment_reported"))

class TripStateError(InputError):
    """Base class for caller-correctable trip-state errors."""


class TripNotFound(TripStateError):
    """The requested server-issued synthetic trip does not exist."""


class RevisionConflict(TripStateError):
    """The caller tried to update a revision that is no longer current."""


class RequestKeyReuse(TripStateError):
    """An idempotency key was reused for different write arguments."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _encode(value) -> str:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise InputError("Trip state must contain only finite JSON values") from exc


def _decode(value: str) -> dict:
    decoded = json.loads(value)
    if not isinstance(decoded, dict):
        raise sqlite3.DatabaseError("Stored trip snapshot is not an object")
    return decoded


def _fingerprint(value: dict) -> str:
    return hashlib.sha256(_encode(value).encode("utf-8")).hexdigest()


def _validate_role(role: str) -> None:
    if not isinstance(role, str) or role not in REPORTER_ROLES:
        raise InputError(f"requester_role must be one of: {', '.join(REPORTER_ROLES)}")


def _validate_scope(scope: str) -> None:
    if not isinstance(scope, str) or scope not in QUESTION_SCOPES:
        raise InputError(f"question_scope must be one of: {', '.join(QUESTION_SCOPES)}")


def _validate_request_key(request_key: str) -> None:
    if (not isinstance(request_key, str) or not request_key.strip()
            or len(request_key) > MAX_REQUEST_KEY
            or any(ord(character) < 32 for character in request_key)):
        raise InputError(
            f"request_key is required and must be a nonblank string of at most {MAX_REQUEST_KEY} characters"
        )


def _validate_trip_id(trip_id: str) -> None:
    if not isinstance(trip_id, str) or _TRIP_ID.fullmatch(trip_id) is None:
        raise InputError("trip_id must be a server-issued syn-trip-* identifier")


def _validate_revision(expected_revision: int) -> None:
    if type(expected_revision) is not int or expected_revision < 1:
        raise InputError("expected_revision must be a positive integer")


def _fact_request(normalized: dict) -> dict:
    """Canonical request facts without server-owned observation timestamps."""
    return {
        field: {"value": record["value"], "unit": record["unit"]}
        for field, record in normalized.items()
    }


def _same_value(left: dict, right: dict) -> bool:
    return left.get("value") == right.get("value") and left.get("unit") == right.get("unit")


def _conflict_marker(incoming: dict, prior: dict | None = None) -> dict:
    marker = copy.deepcopy(incoming)
    marker["value"] = None
    if marker.get("unit") is None and prior is not None:
        marker["unit"] = prior.get("unit")
    return marker


def _new_trip_id() -> str:
    # os.urandom owns the identity; no client fact can select or impersonate it.
    return "syn-trip-" + os.urandom(16).hex()


class TripStore:
    """SQLite-backed optimistic state with process-safe idempotent writes.

    A connection is opened for each operation, which keeps instances usable
    across threads and processes.  ``BEGIN IMMEDIATE`` serializes the short
    read/modify/write section, while the expected revision prevents lost
    updates from callers that raced on the same snapshot.
    """

    def __init__(self, path: str | os.PathLike[str]):
        if not isinstance(path, (str, os.PathLike)):
            raise InputError("TripStore path must be a filesystem path")
        raw_path = Path(path).expanduser()
        if str(raw_path) == ":memory:":
            raise InputError("TripStore requires a private on-disk SQLite file")
        if raw_path.exists() and raw_path.is_symlink():
            raise InputError("TripStore database path cannot be a symbolic link")
        self.path = raw_path.absolute()
        parent_existed = self.path.parent.exists()
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not parent_existed:
            os.chmod(self.path.parent, 0o700)
        self._initialize()
        os.chmod(self.path, 0o600)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path, timeout=30, isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    @contextmanager
    def _transaction(self, supplied=None, *, write=False):
        """Join a trusted application's transaction or own a standalone operation.

        Supplied connections are never committed, rolled back, or closed here.
        MCP argument validation does not expose this internal integration point.
        """
        if supplied is not None and not supplied.in_transaction:
            raise InputError('A supplied connection must have an active transaction')
        connection = supplied if supplied is not None else self._connect()
        owned = supplied is None
        try:
            if owned and write:
                connection.execute('BEGIN IMMEDIATE')
            yield connection
            if owned and write:
                connection.commit()
        except BaseException:
            if owned and write:
                connection.rollback()
            raise
        finally:
            if owned:
                connection.close()

    def _initialize(self) -> None:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS trips (
                    trip_id TEXT PRIMARY KEY,
                    revision INTEGER NOT NULL CHECK (revision >= 1),
                    snapshot_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS requests (
                    request_key TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL,
                    snapshot_json TEXT NOT NULL
                )
                """
            )
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _existing_request(
            connection: sqlite3.Connection, request_key: str, fingerprint: str,
    ) -> dict | None:
        row = connection.execute(
            "SELECT fingerprint, snapshot_json FROM requests WHERE request_key = ?",
            (request_key,),
        ).fetchone()
        if row is None:
            return None
        if not hmac.compare_digest(row["fingerprint"], fingerprint):
            raise RequestKeyReuse("request_key was already used with different write arguments")
        return _decode(row["snapshot_json"])

    @staticmethod
    def _save_request(
            connection: sqlite3.Connection, request_key: str, fingerprint: str,
            snapshot_json: str,
    ) -> None:
        connection.execute(
            "INSERT INTO requests(request_key, fingerprint, snapshot_json) VALUES (?, ?, ?)",
            (request_key, fingerprint, snapshot_json),
        )

    def create(
            self, requester_role: str, question_scope: str, facts: dict,
            source_message: str, request_key: str, *, _connection=None,
    ) -> dict:
        _validate_role(requester_role)
        _validate_scope(question_scope)
        _validate_request_key(request_key)
        normalized = normalize_facts(facts, requester_role, source_message)
        request_fingerprint = _fingerprint({
            "operation": "create",
            "requester_role": requester_role,
            "question_scope": question_scope,
            "facts": _fact_request(normalized),
            "source_message": source_message,
        })
        event_at = next(iter(normalized.values()))["recorded_at"] if normalized else _utc_now()

        with self._transaction(_connection, write=True) as connection:
            previous = self._existing_request(connection, request_key, request_fingerprint)
            if previous is not None:
                return previous

            trip_id = _new_trip_id()
            history = [{
                "revision": 1,
                "operation": "create",
                "requester_role": requester_role,
                "question_scope": question_scope,
                "reported_facts": copy.deepcopy(normalized),
                "invalidated_fields": [],
                "conflicted_fields": [],
                "corrected_fields": [],
                "replace_conflicts": False,
                "recorded_at": event_at,
            }]
            snapshot = {
                "trip_id": trip_id,
                "revision": 1,
                "requester_role": requester_role,
                "question_scope": question_scope,
                "facts": copy.deepcopy(normalized),
                "history": history,
                "invalidated_fields": [],
                "conflicts": [],
                "mode": MODE,
            }
            encoded = _encode(snapshot)
            connection.execute(
                "INSERT INTO trips(trip_id, revision, snapshot_json) VALUES (?, ?, ?)",
                (trip_id, 1, encoded),
            )
            self._save_request(connection, request_key, request_fingerprint, encoded)
            return _decode(encoded)

    def update(
            self, trip_id: str, expected_revision: int, requester_role: str,
            question_scope: str, facts: dict, source_message: str, request_key: str,
            replace_conflicts: bool = False, *, _connection=None,
    ) -> dict:
        _validate_trip_id(trip_id)
        _validate_revision(expected_revision)
        _validate_role(requester_role)
        _validate_scope(question_scope)
        _validate_request_key(request_key)
        if type(replace_conflicts) is not bool:
            raise InputError("replace_conflicts must be boolean")
        normalized = normalize_facts(facts, requester_role, source_message)
        request_fingerprint = _fingerprint({
            "operation": "update",
            "trip_id": trip_id,
            "expected_revision": expected_revision,
            "requester_role": requester_role,
            "question_scope": question_scope,
            "facts": _fact_request(normalized),
            "source_message": source_message,
            "replace_conflicts": replace_conflicts,
        })
        event_at = next(iter(normalized.values()))["recorded_at"] if normalized else _utc_now()

        with self._transaction(_connection, write=True) as connection:
            previous = self._existing_request(connection, request_key, request_fingerprint)
            if previous is not None:
                return previous

            row = connection.execute(
                "SELECT revision, snapshot_json FROM trips WHERE trip_id = ?", (trip_id,),
            ).fetchone()
            if row is None:
                raise TripNotFound(f"Synthetic trip not found: {trip_id}")
            if row["revision"] != expected_revision:
                raise RevisionConflict(
                    f"Revision conflict for {trip_id}: expected {expected_revision}, "
                    f"current revision is {row['revision']}"
                )

            snapshot = _decode(row["snapshot_json"])
            next_revision = expected_revision + 1
            current_facts = copy.deepcopy(snapshot["facts"])
            conflicts = copy.deepcopy(snapshot["conflicts"])
            invalidated = set(snapshot["invalidated_fields"])
            conflicts_by_field = {item["field"]: item for item in conflicts}

            correction_candidates = set()
            if replace_conflicts:
                for field, incoming in normalized.items():
                    current = current_facts.get(field)
                    if field in conflicts_by_field or (
                            current is not None and not _same_value(current, incoming)
                            and current["value"] is not None
                    ):
                        correction_candidates.add(field)
                dependent_candidates = set()
                for controller in correction_candidates:
                    dependent_candidates.update(INVALIDATION_RULES.get(controller, ()))
                correction_roots = correction_candidates - dependent_candidates
                if len(correction_roots) > 1:
                    raise InputError(
                        "replace_conflicts can correct only one independent field per update; "
                        "submit unrelated corrections as separate revisioned writes"
                    )
            else:
                correction_roots = set()

            dependency_triggers = set()
            unresolved_controllers = set()
            corrected_fields = set(correction_roots)
            for field, incoming in normalized.items():
                current = current_facts.get(field)
                active_conflict = conflicts_by_field.get(field)
                if field not in INVALIDATION_RULES:
                    continue
                if active_conflict is not None:
                    dependency_triggers.add(field)
                    if not replace_conflicts or incoming["value"] is None:
                        unresolved_controllers.add(field)
                elif (current is not None and not _same_value(current, incoming)
                      and current["value"] is not None):
                    dependency_triggers.add(field)
                    if not replace_conflicts or incoming["value"] is None:
                        # The controller remains conflicted or explicitly unknown,
                        # so dependent reports have no selected association.
                        unresolved_controllers.add(field)

            event_invalidated = set()
            for controller in dependency_triggers:
                for dependent in INVALIDATION_RULES[controller]:
                    if dependent in current_facts:
                        del current_facts[dependent]
                        event_invalidated.add(dependent)
                        invalidated.add(dependent)
                    conflicts_by_field.pop(dependent, None)

            event_conflicted = set()
            for field, incoming in normalized.items():
                invalidated.discard(field)
                active_conflict = conflicts_by_field.get(field)
                current = current_facts.get(field)

                if active_conflict is not None:
                    if replace_conflicts:
                        conflicts_by_field.pop(field, None)
                        current_facts[field] = copy.deepcopy(incoming)
                    else:
                        active_conflict["observations"].append(copy.deepcopy(incoming))
                        current_facts[field] = _conflict_marker(incoming, current)
                        event_conflicted.add(field)
                    continue

                if current is None or _same_value(current, incoming) or incoming["value"] is None:
                    current_facts[field] = copy.deepcopy(incoming)
                    continue

                if current["value"] is None or replace_conflicts:
                    current_facts[field] = copy.deepcopy(incoming)
                    continue

                conflict = {
                    "field": field,
                    "observations": [copy.deepcopy(current), copy.deepcopy(incoming)],
                    "detected_at": event_at,
                    "revision": next_revision,
                }
                conflicts_by_field[field] = conflict
                current_facts[field] = _conflict_marker(incoming, current)
                event_conflicted.add(field)

            # If the controlling identity/assignment remains unknown or
            # conflicted, even dependent facts in this same message cannot be
            # attached to a selected subject in this flat prototype model.
            for controller in unresolved_controllers:
                for dependent in INVALIDATION_RULES[controller]:
                    if dependent in current_facts:
                        del current_facts[dependent]
                        event_invalidated.add(dependent)
                        invalidated.add(dependent)
                    conflicts_by_field.pop(dependent, None)

            history = copy.deepcopy(snapshot["history"])
            history.append({
                "revision": next_revision,
                "operation": "update",
                "requester_role": requester_role,
                "question_scope": question_scope,
                "reported_facts": copy.deepcopy(normalized),
                "invalidated_fields": sorted(event_invalidated),
                "conflicted_fields": sorted(event_conflicted),
                "corrected_fields": sorted(corrected_fields),
                "replace_conflicts": replace_conflicts,
                "recorded_at": event_at,
            })
            updated = {
                "trip_id": trip_id,
                "revision": next_revision,
                "requester_role": requester_role,
                "question_scope": question_scope,
                "facts": current_facts,
                "history": history,
                "invalidated_fields": sorted(invalidated),
                "conflicts": sorted(conflicts_by_field.values(), key=lambda item: item["field"]),
                "mode": MODE,
            }
            encoded = _encode(updated)
            cursor = connection.execute(
                """
                UPDATE trips SET revision = ?, snapshot_json = ?
                WHERE trip_id = ? AND revision = ?
                """,
                (next_revision, encoded, trip_id, expected_revision),
            )
            if cursor.rowcount != 1:
                raise RevisionConflict(f"Revision changed while updating {trip_id}")
            self._save_request(connection, request_key, request_fingerprint, encoded)
            return _decode(encoded)

    def get(self, trip_id: str, *, _connection=None) -> dict:
        _validate_trip_id(trip_id)
        with self._transaction(_connection) as connection:
            row = connection.execute(
                "SELECT snapshot_json FROM trips WHERE trip_id = ?", (trip_id,),
            ).fetchone()
            if row is None:
                raise TripNotFound(f"Synthetic trip not found: {trip_id}")
            return _decode(row["snapshot_json"])
