"""Import, inspect, or revoke operator-managed synthetic verification receipts.

This local command is the supported operator receipt-write surface. It does not
authenticate real authorities or issue an operational permission.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from neo4j_kg.common import ArchiveError, EvidenceUnavailable
from neo4j_kg.service import InputError
from neo4j_kg.verification_models import (
    CONTRACT_VERSION,
    case_fingerprint,
    receipt_schema,
)
from neo4j_kg.verification_store import VerificationStore


DEFAULT_STORE = ROOT / ".runtime" / "operator-verifications.sqlite3"
OUTPUT_SCHEMA = "drayage-verification-operator-output-v1"
NOTICE = (
    "Synthetic fixture adapters only; no real authority or provider is "
    "authenticated and no operational permission is issued."
)
METADATA_FIELDS = (
    "id",
    "kind",
    "trip_id",
    "trip_revision",
    "case_sha256",
    "graph_release",
    "provider_id",
    "authority_role",
    "observed_at",
    "valid_from",
    "valid_until",
)


def _read_json(path: Path):
    with path.open("r", encoding="utf-8") as source:
        return json.load(source)


def _snapshot_metadata(snapshot: dict, case: dict, graph_release: str) -> dict:
    return {
        "schema_version": OUTPUT_SCHEMA,
        "mode": "synthetic_only",
        "notice": NOTICE,
        "requested_case": {
            "trip_id": case["trip_id"],
            "trip_revision": case["revision"],
            "case_sha256": case_fingerprint(case),
            "graph_release": graph_release,
        },
        "snapshot_version": snapshot["version"],
        "receipt_count": len(snapshot["receipts"]),
        "receipts": [
            {field: receipt[field] for field in METADATA_FIELDS}
            for receipt in snapshot["receipts"]
        ],
        "revoked_ids": snapshot["revoked_ids"],
    }


def _write_json(value: dict) -> None:
    sys.stdout.write(json.dumps(
        value,
        indent=2,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
    ) + "\n")


def _add_store_argument(command: argparse.ArgumentParser) -> None:
    command.add_argument(
        "--store",
        type=Path,
        default=DEFAULT_STORE,
        help=f"Owner-only SQLite ledger (default: {DEFAULT_STORE})",
    )


def _add_snapshot_arguments(command: argparse.ArgumentParser) -> None:
    _add_store_argument(command)
    command.add_argument("--case", type=Path, required=True)
    command.add_argument(
        "--graph-release",
        required=True,
        help="Pinned 64-character lowercase SHA-256 graph release",
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    schema_command = commands.add_parser(
        "schema", help="Print the accepted receipt JSON Schema",
    )
    schema_command.set_defaults(operation="schema")

    import_command = commands.add_parser(
        "import", help="Validate and atomically append a JSON receipt array",
    )
    _add_snapshot_arguments(import_command)
    import_command.add_argument("--receipts", type=Path, required=True)
    import_command.set_defaults(operation="import")

    list_command = commands.add_parser(
        "list", help="List receipt metadata for one synthetic trip",
    )
    _add_snapshot_arguments(list_command)
    list_command.set_defaults(operation="list")

    revoke_command = commands.add_parser(
        "revoke", help="Append an immutable receipt revocation",
    )
    _add_store_argument(revoke_command)
    revoke_command.add_argument("--id", required=True, dest="receipt_id")
    revoke_command.add_argument("--reason", required=True)
    revoke_command.set_defaults(operation="revoke")

    args = parser.parse_args(argv)
    try:
        if args.operation == "schema":
            _write_json({
                "schema_version": OUTPUT_SCHEMA,
                "mode": "synthetic_only",
                "notice": NOTICE,
                "contract_sha256": CONTRACT_VERSION,
                "receipt_schema": receipt_schema(),
            })
            return 0

        store = VerificationStore(args.store)
        if args.operation == "revoke":
            store.revoke(args.receipt_id, args.reason)
            _write_json({
                "schema_version": OUTPUT_SCHEMA,
                "mode": "synthetic_only",
                "notice": NOTICE,
                "receipt_id": args.receipt_id,
                "status": "revoked",
            })
            return 0

        case = _read_json(args.case)
        if args.operation == "import":
            receipts = _read_json(args.receipts)
            if not isinstance(receipts, list):
                raise InputError("Receipt file must contain a JSON array")
            snapshot = store.put(receipts, case, args.graph_release)
        else:
            snapshot = store.snapshot(case, args.graph_release)
        result = _snapshot_metadata(snapshot, case, args.graph_release)
        result["operation"] = args.operation
        _write_json(result)
        return 0
    except (
        ArchiveError,
        EvidenceUnavailable,
        InputError,
        json.JSONDecodeError,
        OSError,
        UnicodeError,
    ) as exc:
        parser.exit(1, f"Verification operation failed: {exc}\n")


if __name__ == "__main__":
    sys.exit(main())
