"""Verify live import idempotence, transaction rollback, and Wave4 preservation."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from neo4j_kg.common import digest, validate_release, verify_files
from neo4j_kg.config import connect
from neo4j_kg.store import read_release


def wave4_fingerprint(session):
    nodes = [dict(r) for r in session.run(
        "MATCH (n:Wave4Entity) RETURN elementId(n) AS id, labels(n) AS labels, "
        "properties(n) AS properties ORDER BY id")]
    edges = [dict(r) for r in session.run(
        "MATCH (a:Wave4Entity)-[r]->(b:Wave4Entity) RETURN elementId(a) AS start, "
        "elementId(b) AS end, elementId(r) AS id, type(r) AS type, properties(r) AS properties ORDER BY id")]
    return {"nodes": len(nodes), "relationships": len(edges), "fingerprint": digest({"nodes": nodes, "edges": edges})}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credentials-file", type=Path, required=True)
    parser.add_argument("--wave4-baseline", type=Path)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("migration_import", ROOT / "tools/import_neo4j.py")
    importer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(importer)
    release = validate_release(json.loads((ROOT / "data/neo4j_release.json").read_text()))
    verify_files(release)
    driver, database = connect(args.credentials_file)
    with driver, driver.session(database=database) as session:
        before = wave4_fingerprint(session)
        if args.wave4_baseline:
            assert before == json.loads(args.wave4_baseline.read_text()), "Wave4 differs from pre-migration baseline"
        again = session.execute_write(importer.import_transaction, release, False)
        assert again["created"] is False, "Import was not idempotent"
        probe = copy.deepcopy(release)
        probe["rollback_probe"] = "injected verification failure"
        probe["revision"] = digest({k: v for k, v in probe.items() if k != "revision"})
        # Failure is injected after node/relationship writes and before commit.
        with patch.object(importer, "verify_transaction", side_effect=RuntimeError("intentional rollback probe")):
            try:
                session.execute_write(importer.import_transaction, probe, False)
            except RuntimeError as exc:
                assert str(exc) == "intentional rollback probe"
            else:
                raise AssertionError("Injected failure did not abort import")
        remaining = session.run(
            "MATCH (n) WHERE (n:DrayageRecord OR n:DrayageRelease) "
            "AND n.dataset=$dataset AND n.revision=$revision RETURN count(n) AS count",
            dataset=release["dataset"], revision=probe["revision"]).single()["count"]
        assert remaining == 0, "Failed import left records behind"
        assert session.execute_read(read_release, release["revision"]) == release
        after = wave4_fingerprint(session)
        assert before == after, "Wave4 changed during verification"
    receipt = {"idempotent_reimport": "passed", "failed_import_rollback": "passed",
               "rollback_probe_remaining_records": remaining, "original_release_intact": True,
               "wave4_unchanged": after}
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
