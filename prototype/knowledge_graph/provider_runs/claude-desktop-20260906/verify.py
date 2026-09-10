"""Read-only checks of this recorded run; behavioral failures stay in the output.

This does not launch Claude, collect new responses, or automatically grade prose.
Narration judgments remain the manual author review in review.json.
"""

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
sys.path.insert(0, str(ROOT))

from kg.graph import digest
from kg.service import CheckingService, normalize


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_events(events):
    previous = None
    ids = set()
    for sequence, event in enumerate(events, 1):
        body = {key: value for key, value in event.items() if key != "event_hash"}
        require(event["sequence"] == sequence, "Audit sequence gap")
        require(event["previous_event_hash"] == previous, "Broken audit chain")
        require(event["event_hash"] == digest(body), "Changed audit event")
        require(event["request_id"] not in ids, "Duplicate request id in this session")
        ids.add(event["request_id"])
        require(event["surface"] == "mcp_client_not_yet_attributed_to_provider",
                "Original audit attribution was changed")
        require(event["response"]["id"] == event["request_id"], "Response id mismatch")
        result = event["response"]["result"]
        require(result["isError"] is False, "Unexpected tool-error event")
        require(json.loads(result["content"][0]["text"]) == result["structuredContent"],
                "Text and structured tool results differ")
        require(normalize(event["validated_arguments"]["as_received"]) ==
                event["validated_arguments"]["normalized"], "Normalization mismatch")
        previous = event["event_hash"]


def score_arguments(expected, received):
    expected = normalize(expected)
    received = normalize(received)
    return {key: {"expected": expected[key], "received": received[key]}
            for key in expected if expected[key] != received[key]}


def collection_identity(manifest, events):
    # Reconstruct the original complete package inventory, not an arbitrary
    # version override. The digest must equal every recorded implementation ID.
    hashes = {name: sha256(ROOT / "kg" / name)
              for name in manifest["collection_python_modules"]}
    for name, actual in hashes.items():
        require(actual == manifest["collection_code_sha256"]["kg/" + name],
                f"Recorded module changed: {name}")
    fingerprint = digest(hashes)
    require(all(event["response"]["result"]["structuredContent"]["versions"]["implementation"]
                == fingerprint for event in events), "Collection inventory does not match audit identity")
    return fingerprint


def verify():
    manifest = json.loads((RUN / "manifest.json").read_text())
    review = json.loads((RUN / "review.json").read_text())
    gold = json.loads((ROOT / "tests/provider_cases.json").read_text())
    audit_path = RUN / manifest["audit_file"]
    require(sha256(audit_path) == manifest["audit_sha256"], "Audit file hash changed")
    require(sha256(ROOT / "tests/provider_cases.json") == manifest["provider_cases_sha256"],
            "Frozen provider prompts changed")
    require(sha256(ROOT / "tests/acceptance.json") == manifest["acceptance_sha256"],
            "Frozen local acceptance cases changed")
    for filename, expected_hash in manifest["collection_code_sha256"].items():
        require(sha256(ROOT / filename) == expected_hash, f"Collection code changed: {filename}")
    events = [json.loads(line) for line in audit_path.read_text().splitlines()]
    require(len(events) == len(gold["cases"]) == len(manifest["cases"]) ==
            len(review["cases"]) == 6, "Incomplete or extra case collection")
    validate_events(events)
    service = CheckingService()
    current_worktree_implementation = service.versions["implementation"]
    recorded_implementation = collection_identity(manifest, events)
    # A concurrent kg/export.py addition temporarily changed the glob-based
    # fingerprint. It has since moved outside kg/. Do not override identity:
    # exact replay requires both the original module inventory and the current
    # package fingerprint to match the recorded implementation.
    require(current_worktree_implementation == recorded_implementation,
            "Current checking package differs from the recorded implementation")
    results = []
    verdicts = Counter()
    for observed, expected, reviewed, event in zip(
            manifest["cases"], gold["cases"], review["cases"], events):
        case_id = expected["case_id"]
        require(observed["case_id"] == reviewed["case_id"] == case_id, "Case order mismatch")
        require(observed["audit_sequence"] == event["sequence"] and
                observed["request_id"] == event["request_id"], "Case/audit mapping mismatch")
        require(observed["sent_prompt"] == gold["prompt_prefix"] + expected["prompt"],
                f"Prompt changed: {case_id}")
        payload = event["response"]["result"]["structuredContent"]
        received = event["validated_arguments"]["as_received"]
        require(payload == service.check(received), f"Service replay differs: {case_id}")
        answer_path = RUN / observed["answer_file"]
        answer = answer_path.read_text()
        criteria = reviewed["criteria"]
        require([item["index"] for item in criteria] ==
                list(range(len(expected["required_answer_meaning"]))), "Missing rubric item")
        for item in criteria:
            require(item["verdict"] in {"pass", "partial", "fail"}, "Unknown manual verdict")
            require(item["quote"] and item["quote"] in answer, "Manual quote absent from answer")
            verdicts[item["verdict"]] += 1
        for finding in reviewed["additional_findings"]:
            require(finding["quote"] in answer, "Finding quote absent from answer")
        differences = score_arguments(expected["expected_arguments"], received)
        results.append({
            "case_id": case_id,
            "prompt_sha256": hashlib.sha256(observed["sent_prompt"].encode()).hexdigest(),
            "answer_transcription_sha256": sha256(answer_path),
            "audit_sequence": event["sequence"], "request_id": event["request_id"],
            "recorded_at": event["recorded_at"],
            "tool_called": event["method"],
            "tool_name_matches": event["method"] == expected["expected_tool"],
            "argument_differences": differences,
            "all_material_arguments_match": not differences,
            "expected_check_status": expected["expected_check_status"],
            "returned_check_status": payload["check_status"],
            "service_status_matches": payload["check_status"] == expected["expected_check_status"],
            "full_service_replay_matches": True,
            "reason_codes": payload["reason_codes"],
            "operational_status": payload["operational_status"],
            "manual_criteria": [{"meaning": expected["required_answer_meaning"][item["index"]],
                                 "verdict": item["verdict"]} for item in criteria],
            "additional_findings": reviewed["additional_findings"],
            "broad_clearance_observed_by_reviewer": reviewed["broad_clearance_observed"],
        })
    return {
        "run_id": manifest["run_id"], "artifact_checks_pass": True,
        "audit_sha256": sha256(audit_path), "versions": service.versions,
        "replay_mode": "full_response_replay_with_matching_current_and_recorded_package_identity",
        "current_worktree_implementation": current_worktree_implementation,
        "additional_worktree_kg_modules": sorted(
            path.name for path in (ROOT / "kg").glob("*.py")
            if path.name not in manifest["collection_python_modules"]),
        "cases_captured": len(results),
        "tool_name_matches": sum(item["tool_name_matches"] for item in results),
        "all_material_arguments_match": sum(item["all_material_arguments_match"] for item in results),
        "service_status_matches": sum(item["service_status_matches"] for item in results),
        "manual_criteria_counts": dict(verdicts),
        "broad_clearances_observed_by_reviewer": sum(
            item["broad_clearance_observed_by_reviewer"] for item in results),
        "interpretation": "Artifact integrity passing is not provider behavior passing. Retain argument mismatches, partial manual scores and additional findings.",
        "results": results,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, ensure_ascii=False))
