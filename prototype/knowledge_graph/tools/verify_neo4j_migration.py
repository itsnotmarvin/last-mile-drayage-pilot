"""Exercise the actual Neo4j MCP entry point against frozen full-result expectations."""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from neo4j_kg.common import digest, validate_release


def substantive(result):
    result = copy.deepcopy(result)
    result.pop("evaluation_id", None)
    result["versions"].pop("implementation")
    result["versions"].pop("graph_release", None)
    result.pop("engine", None)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--oracle", type=Path, required=True)
    parser.add_argument("--credentials-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if importlib.util.find_spec("networkx") is not None:
        raise RuntimeError("Run this proof in the isolated runtime without NetworkX installed")
    release = validate_release(json.loads((ROOT / "data/neo4j_release.json").read_text()))
    oracle = json.loads(args.oracle.read_text())
    if oracle["baseline_implementation"] != release["baseline_implementation"]:
        raise RuntimeError("Oracle implementation differs from migration release")
    requests = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-11-25", "capabilities": {},
        "clientInfo": {"name": "neo4j-migration-verifier", "version": "1"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}]
    expectations = []
    for row in oracle["checks"]:
        expectations.append((row["case_id"], "check_apm_induction", row["arguments"], row["result"]))
    for row in oracle["contexts"]:
        expectations.append((row["topic"], "get_drayage_graph_context", {"topic": row["topic"]}, row["result"]))
    for number, (_, tool, arguments, _) in enumerate(expectations, 10):
        requests.append({"jsonrpc": "2.0", "id": number, "method": "tools/call",
                         "params": {"name": tool, "arguments": arguments}})
    env = os.environ | {"NEO4J_CREDENTIALS_FILE": str(args.credentials_file),
                        "DRAYAGE_NEO4J_REVISION": release["revision"]}
    process = subprocess.run([sys.executable, str(ROOT / "run_neo4j_mcp.py"), "--audit"],
        input="\n".join(json.dumps(r) for r in requests) + "\n", text=True, capture_output=True,
        cwd=ROOT, env=env, timeout=240)
    if process.returncode:
        raise RuntimeError("Neo4j MCP subprocess failed")
    responses = [json.loads(line) for line in process.stdout.splitlines()]
    if len(responses) != len(expectations) + 2:
        raise RuntimeError("Missing or extra MCP responses")
    by_id = {r["id"]: r for r in responses}
    if by_id[1]["result"]["serverInfo"]["name"] != "drayage-neo4j":
        raise RuntimeError("Wrong MCP runtime")
    if len(by_id[2]["result"]["tools"]) != 2:
        raise RuntimeError("Unexpected tool contract")
    rows = []
    for number, (case_id, _, _, expected) in enumerate(expectations, 10):
        result = by_id[number]["result"]
        if result["isError"]:
            raise RuntimeError("Tool failed for " + case_id)
        actual = result["structuredContent"]
        if actual != json.loads(result["content"][0]["text"]):
            raise RuntimeError("MCP result representations differ")
        if substantive(actual) != substantive(expected):
            raise RuntimeError("Substantive result differs for " + case_id)
        if actual["versions"]["graph_release"] != release["revision"]:
            raise RuntimeError("Unexpected graph release")
        if "evaluation_id" in actual:
            wanted = digest({"facts": actual["normalized_facts"], "versions": actual["versions"],
                             "check_id": actual["check_id"]})
            if actual["evaluation_id"] != wanted:
                raise RuntimeError("Invalid evaluation identity")
        if case_id == "summary" and not actual["engine"].startswith("Neo4j"):
            raise RuntimeError("Wrong graph engine")
        rows.append({"case_id": case_id, "full_substantive_comparison": "passed"})
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "stdio-transcript.json").write_text(json.dumps({"requests": requests, "responses": responses}, indent=2) + "\n")
    receipt = {"surface": "local_stdio_integration_not_consumer_app", "verified_at_utc": datetime.now(timezone.utc).isoformat(),
               "revision": release["revision"], "implementation": by_id[10]["result"]["structuredContent"]["versions"]["implementation"],
               "networkx_installed": False, "check_cases": len(oracle["checks"]),
               "context_topics": len(oracle["contexts"]), "comparisons": rows}
    (args.output / "verification.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
