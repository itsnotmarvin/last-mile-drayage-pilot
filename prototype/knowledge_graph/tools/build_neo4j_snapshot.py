"""Build a reproducible migration snapshot using the frozen NetworkX oracle.

Offline migration/development command only; never imported by the live MCP.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kg.service import CheckingService
from neo4j_kg.common import DATASET, SCHEMA, digest, encode, validate_release


def build_release():
    service = CheckingService()
    archive_edges = {key for _, _, key in service.archive.graph.edges(keys=True)}
    nodes = [{"id": key, "kind": attrs["kind"], "layer": attrs["layer"],
              "archive": key in service.archive.graph, "ordinal": ordinal,
              "record_json": encode(attrs["record"])}
             for ordinal, (key, attrs) in enumerate(service.graph.nodes(data=True))]
    edges = [{"id": key, "from": start, "to": end, "relationship": attrs["relationship"],
              "archive": key in archive_edges, "ordinal": ordinal, "record_json": encode(attrs["record"])}
             for ordinal, (start, end, key, attrs) in enumerate(service.graph.edges(keys=True, data=True))]
    files = dict(service.archive.input_hashes)
    for source in service.archive.documents["data/metadata.json"]["sources"]:
        for item in source.get("archived_files", []):
            files[item["path"]] = item["sha256"]
    for path in (ROOT / "data/model.json", ROOT / "data/synthetic_evidence.json"):
        files[str(path.relative_to(service.archive.archive))] = hashlib.sha256(path.read_bytes()).hexdigest()
    body = {"dataset": DATASET, "schema_version": SCHEMA,
            "baseline_implementation": service.versions["implementation"],
            "versions": {k: v for k, v in service.versions.items() if k != "implementation"},
            "file_hashes": files, "nodes": nodes, "edges": edges}
    return validate_release({**body, "revision": digest(body)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "data/neo4j_release.json")
    parser.add_argument("--oracle-output", type=Path, help="Write exact frozen results for live migration comparison")
    args = parser.parse_args()
    release = build_release()
    args.output.write_text(json.dumps(release, indent=2, ensure_ascii=False) + "\n")
    if args.oracle_output:
        original = CheckingService()
        suite = json.loads((ROOT / "tests/acceptance.json").read_text())
        oracle = {"baseline_implementation": original.versions["implementation"], "checks": [], "contexts": []}
        for case in suite["cases"]:
            arguments = suite["default_input"] | case["changes"]
            oracle["checks"].append({"case_id": case["case_id"], "arguments": arguments,
                                     "result": original.check(arguments)})
        for topic in ("summary", "induction", "route_directions", "port_street", "coverage"):
            oracle["contexts"].append({"topic": topic, "result": original.context(topic)})
        args.oracle_output.parent.mkdir(parents=True, exist_ok=True)
        args.oracle_output.write_text(json.dumps(oracle, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"revision": release["revision"], "nodes": len(release["nodes"]),
                      "relationships": len(release["edges"]), "source_files_verified": len(release["file_hashes"])}))
