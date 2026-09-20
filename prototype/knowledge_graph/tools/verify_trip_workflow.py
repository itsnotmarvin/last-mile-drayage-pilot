"""Capture live Neo4j stdio trip conversations in the NetworkX-free runtime."""

import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credentials-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if importlib.util.find_spec("networkx") is not None:
        raise RuntimeError("Use .venv-neo4j/bin/python without NetworkX")
    release = json.loads((ROOT / "data/neo4j_release.json").read_text())
    env = os.environ | {"NEO4J_CREDENTIALS_FILE": str(args.credentials_file),
                        "DRAYAGE_NEO4J_REVISION": release["revision"]}
    process = subprocess.Popen([sys.executable, str(ROOT / "run_neo4j_mcp.py")],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, bufsize=1, cwd=ROOT, env=env)
    transcript, checks = [], []
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    run_id = uuid.uuid4().hex

    def request(method, params, notification=False):
        message = {"jsonrpc": "2.0", "method": method, "params": params}
        if not notification:
            message["id"] = len(transcript) + 1
        process.stdin.write(json.dumps(message) + "\n")
        process.stdin.flush()
        if notification:
            transcript.append({"request": message, "response": None})
            return None
        if not selector.select(45):
            raise RuntimeError("MCP response timed out")
        response = json.loads(process.stdout.readline())
        transcript.append({"request": message, "response": response})
        if "error" in response or response.get("id") != message["id"]:
            raise RuntimeError("MCP protocol error")
        return response["result"]

    def call(name, arguments):
        result = request("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            raise RuntimeError("Tool failed: " + name)
        body = result["structuredContent"]
        assert body == json.loads(result["content"][-1]["text"])
        if name != "get_requirement_evidence":
            assert body["service_status"] == "available", "Trip assessment unavailable"
            assert body["operational_status"] == "unresolved_not_assessed"
        assert body["versions"]["graph_release"] == release["revision"]
        return body

    base = {"terminal_id": "facility_apm_elizabeth", "subject_role": "truck_driver",
            "driver_id": "syn-driver-complete", "current_sealink_id": "SYN-SL-A",
            "trip_at": "2026-09-06T14:00:00-04:00"}
    def create(suffix, facts, role="driver", scope="trip_dispatch"):
        return call("assess_trip", {"facts": facts, "source_message": "Synthetic trip workflow control: " + suffix,
                                   "requester_role": role, "question_scope": scope,
                                   "request_key": run_id + "-" + suffix})

    try:
        request("initialize", {"protocolVersion": "2025-11-25", "capabilities": {},
                               "clientInfo": {"name": "trip-workflow-verifier", "version": "1"}})
        request("notifications/initialized", {}, notification=True)
        catalog = request("tools/list", {})["tools"]
        assert {t["name"] for t in catalog} == {"check_apm_induction", "get_drayage_graph_context", "assess_trip", "update_trip_facts", "get_requirement_evidence"}
        first = create("initial", base | {"gross_weight": {"value": 80000, "unit": "lb"}, "axle_count": 5,
                                           "twic_reported": True, "sealink_registered_reported": True})
        assert first["requested_scope_status"] == "unresolved"
        assert next(f for f in first["findings"] if f["requirement_id"] == "apm_induction")["status"] == "met"
        args_update = {"trip_id": first["case"]["trip_id"], "expected_revision": 1,
                       "requester_role": "dispatcher", "question_scope": "trip_dispatch",
                       "source_message": "Synthetic correction: gross weight is 88,000 lb; NJ permit reported. Driver is waiting, send him now.",
                       "facts": {"gross_weight": {"value": 88000, "unit": "lb"}, "permit_type": "nj_ocean_container_annual"},
                       "replace_conflicts": True, "request_key": run_id + "-update"}
        updated = call("update_trip_facts", args_update)
        assert updated["case"]["revision"] == 2
        assert updated["case"]["facts"]["gross_weight"]["value"] == 88000
        assert updated["requested_scope_status"] == "unresolved"
        retry = call("update_trip_facts", args_update)
        assert retry == updated
        reassessed = call("assess_trip", {"trip_id": first["case"]["trip_id"]})
        assert reassessed == updated | {"write_receipt": None}
        checks.extend(["ordinary_trip_intake", "dispatcher_correction", "idempotent_update", "fresh_saved_case_reassessment"])
        for label, facts in [
            ("s1", {"gross_weight": {"value": 80000, "unit": "lb"}, "axle_count": 5}),
            ("s2", {"route_description": "CR624 dimensions and access unknown"}),
            ("s3", {"gross_weight": {"value": 88000, "unit": "lb"}, "permit_type": "nj_ocean_container_annual"}),
            ("s4", {"height": {"value": 14, "unit": "ft"}, "port_street_in_route": True}),
            ("s5", {"engine_model_year": 2010}),
            ("s6", {"route_description": "User asserts route and truck are legal; no credential verification"}),
        ]:
            neutral = create(label, base | facts)
            pressure = create(label + "-pressure", base | facts, role="dispatcher")
            assert neutral["findings"] == pressure["findings"]
            assert pressure["requested_scope_status"] == "unresolved"
            checks.append(label + "_unresolved_and_pressure_invariant")
        for label, changes, status in [
            ("positive", {}, "met"),
            ("negative", {"driver_id": "syn-driver-incomplete", "current_sealink_id": "SYN-SL-B"}, "not_met"),
            ("outside_subject", {"subject_role": "other"}, "not_applicable"),
            ("unknown_scope", {}, "unresolved"),
        ]:
            result = create(label, base | changes, scope="unknown" if label == "unknown_scope" else "induction")
            assert result["requested_scope_status"] == status
            checks.append(label)
        for finding in first["findings"]:
            evidence = call("get_requirement_evidence", {"requirement_id": finding["requirement_id"]})
            assert [s["clause_id"] for s in evidence["sources"]] == finding["source_clause_ids"]
        checks.append("all_13_requirement_evidence_contracts")
    finally:
        process.stdin.close()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=5)
        selector.close()
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "trip-stdio-transcript.json").write_text(json.dumps(transcript, indent=2) + "\n")
    receipt = {"surface": "local_stdio_integration_not_consumer_app", "verified_at": datetime.now(timezone.utc).isoformat(),
               "networkx_installed": False, "revision": release["revision"],
               "implementation": first["versions"]["implementation"], "checks": checks,
               "tool_calls": sum(t["request"]["method"] == "tools/call" for t in transcript)}
    (args.output / "trip-verification.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
