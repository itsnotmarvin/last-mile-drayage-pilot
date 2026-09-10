"""Validate and import an immutable drayage release without touching Wave4.

Default is local validation. --apply commits only after exact database comparison.
--verify-only reads the live release; --activate additionally updates its pointer.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from neo4j_kg.common import ArchiveError, DATASET, encode, validate_release, verify_files
from neo4j_kg.config import connect
from neo4j_kg.store import read_release


CONSTRAINTS = (
    "CREATE CONSTRAINT drayage_record_identity IF NOT EXISTS FOR (n:DrayageRecord) "
    "REQUIRE (n.dataset,n.revision,n.id) IS UNIQUE",
    "CREATE CONSTRAINT drayage_release_identity IF NOT EXISTS FOR (n:DrayageRelease) "
    "REQUIRE (n.dataset,n.revision) IS UNIQUE",
    "CREATE CONSTRAINT drayage_dataset_identity IF NOT EXISTS FOR (n:DrayageDataset) REQUIRE n.id IS UNIQUE",
)


def verify_transaction(tx, release):
    actual = read_release(tx, release["revision"])
    if actual != release:
        raise ArchiveError("Neo4j release differs from the complete source representation")
    return {"dataset": DATASET, "revision": release["revision"],
            "nodes": len(actual["nodes"]), "relationships": len(actual["edges"]),
            "exact_graph_comparison": "passed"}


def import_transaction(tx, release, activate=False):
    params = {"dataset": DATASET, "revision": release["revision"]}
    existing = list(tx.run(
        "MATCH (r:DrayageRelease {dataset:$dataset, revision:$revision}) RETURN r.revision AS revision", **params))
    if existing:
        # Never repair/overwrite an existing release silently. Reimports verify it.
        receipt = verify_transaction(tx, release)
        receipt["created"] = False
    else:
        manifest = {k: v for k, v in release.items() if k not in ("nodes", "edges")}
        tx.run("CREATE (r:DrayageRelease {dataset:$dataset, revision:$revision, manifest_json:$manifest})",
               **params, manifest=encode(manifest)).consume()
        tx.run("UNWIND $nodes AS row CREATE (n:DrayageRecord) SET n=row, n.dataset=$dataset, n.revision=$revision",
               **params, nodes=release["nodes"]).consume()
        groups = defaultdict(list)
        for edge in release["edges"]:
            if not re.fullmatch(r"[A-Z][A-Z0-9_]*", edge["relationship"]):
                raise ArchiveError("Unsupported relationship type in release")
            groups[edge["relationship"]].append(edge)
        for relation, edges in groups.items():
            tx.run(
                "UNWIND $edges AS row "
                "MATCH (a:DrayageRecord {dataset:$dataset, revision:$revision, id:row.from}) "
                "MATCH (b:DrayageRecord {dataset:$dataset, revision:$revision, id:row.to}) "
                f"CREATE (a)-[e:{relation}]->(b) "
                "SET e.id=row.id, e.dataset=$dataset, e.revision=$revision, "
                "e.archive=row.archive, e.ordinal=row.ordinal, e.record_json=row.record_json",
                **params, edges=edges).consume()
        receipt = verify_transaction(tx, release)
        receipt["created"] = True
    if activate:
        tx.run("MERGE (d:DrayageDataset {id:$dataset}) SET d.active_revision=$revision", **params).consume()
    receipt["activated"] = activate
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=ROOT / "data/neo4j_release.json")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--verify-only", action="store_true")
    parser.add_argument("--activate", action="store_true")
    parser.add_argument("--credentials-file", type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    if args.activate and not args.apply:
        parser.error("--activate requires --apply")
    release = validate_release(json.loads(args.snapshot.read_text()))
    verify_files(release)
    receipt = {"local_validation": "passed", "revision": release["revision"],
               "nodes": len(release["nodes"]), "relationships": len(release["edges"])}
    if args.apply or args.verify_only:
        driver, database = connect(args.credentials_file)
        from neo4j import unit_of_work
        with driver, driver.session(database=database) as session:
            if args.apply:
                for constraint in CONSTRAINTS:
                    session.run(constraint).consume()
                receipt.update(session.execute_write(unit_of_work(timeout=90)(import_transaction), release, args.activate))
            else:
                receipt.update(session.execute_read(unit_of_work(timeout=30)(verify_transaction), release))
    receipt["verified_at_utc"] = datetime.now(timezone.utc).isoformat()
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # The database driver may embed connection details in exception messages.
        print(f"Drayage import/verification failed ({type(exc).__name__}); no successful receipt issued.", file=sys.stderr)
        raise SystemExit(1) from None
