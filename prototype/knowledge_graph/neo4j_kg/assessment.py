"""Versioned trip conversation service over Neo4j evidence and local case state.

Reports advance intake. Only server-owned evidence can establish a check result.
Every request evaluates its saved revision against a fresh graph read.
"""

from __future__ import annotations

import copy

from .common import ArchiveError, EvidenceUnavailable, ROOT, digest
from .evidence import requirement_evidence
from .requirements import CATALOG_VERSION, applicable_requirements
from .service import Evaluation, InputError
from .trip_state import TripStore


SCOPES = ("unknown", "induction", "terminal_entry", "trip_dispatch", "route")
ROLES = ("unknown", "driver", "dispatcher", "other")
LIMITS = [
    "Synthetic development cases only; no operational entry or dispatch clearance.",
    "Reported facts are not authoritative verification, even when a reporter says verified.",
    "The catalog is incomplete; current policy, CDL, gate state and other duties remain outside executable coverage.",
    "Archived directions and bulletins do not establish legal access or current road conditions.",
    "Only APM induction has an executable evaluator, using server-owned synthetic fixtures.",
]


def value(facts, field):
    return facts.get(field, {}).get("value")


def public_case(case):
    """Return current provenance and conflicts without unbounded historical turns."""
    return {k: copy.deepcopy(v) for k, v in case.items() if k != "history"}


def evaluate_trip(reader, case):
    from .followups import build_followups

    facts = case["facts"]
    selected = applicable_requirements(facts, case["question_scope"])
    evaluation = Evaluation(reader)
    results = []
    induction = None
    for requirement in selected:
        missing = [f for f in requirement["required_fields"] if value(facts, f) is None]
        conflicting = [c["field"] for c in case["conflicts"]
                       if c["field"] in requirement["required_fields"] + requirement["verification_fields"]]
        row = {"requirement_id": requirement["id"], "label": requirement["label"],
               "family": requirement["family"], "owner": requirement["owner"],
               "status": "unresolved", "execution_state": "not_implemented",
               "reason_codes": ["EVALUATOR_NOT_IMPLEMENTED"], "missing_fields": missing,
               "conflicting_fields": conflicting,
               "verification_needed": requirement["verification_fields"].copy(),
               "reported_absences": [f for f in requirement["required_fields"]
                                     if value(facts, f) is False],
               "source_clause_ids": requirement["source_clause_ids"].copy(),
               "evidence_ids": [], "evidence_basis": "user_reports_and_archived_sources_only",
               "limits": requirement["limits"].copy()}
        if missing:
            row["reason_codes"].append("REQUIRED_FACTS_MISSING")
        if conflicting:
            row["reason_codes"].append("CONFLICTING_REPORTS")
        if requirement["id"] == "trip_context":
            row["execution_state"] = "intake_only"
            row["reason_codes"] = ["TRIP_CONTEXT_INCOMPLETE" if missing else "CONTEXT_RECORDED_NOT_VERIFIED"]
            if conflicting:
                row["reason_codes"].append("CONFLICTING_REPORTS")
        elif requirement["id"] == "apm_induction":
            args = {k: value(facts, k) for k in
                    ("terminal_id", "driver_id", "current_sealink_id", "trip_at", "company_changed")}
            args.update(actor_role=value(facts, "subject_role"), question_scope="induction")
            induction = evaluation.check(args)
            row.update(status=induction["check_status"], execution_state="evaluated",
                       reason_codes=induction["reason_codes"], evidence_ids=induction["evidence_ids"],
                       evidence_basis=induction["evidence_basis"],
                       verification_needed=induction["missing_facts"],
                       limits=requirement["limits"] + induction["limits"])
            if conflicting:
                induction["check_status"] = "unresolved"
                row["status"] = "unresolved"
                row["reason_codes"] = list(dict.fromkeys(row["reason_codes"] + ["CONFLICTING_REPORTS"]))
            report = value(facts, "induction_reported")
            if (type(report) is bool and row["status"] in ("met", "not_met")
                    and report != (row["status"] == "met")):
                induction["check_status"] = "unresolved"
                row["status"] = "unresolved"
                row["reason_codes"].append("REPORT_CONFLICTS_WITH_SYNTHETIC_EVIDENCE")
                row["verification_needed"] = ["synthetic_evidence_reconciliation"]
        results.append(row)

    scope = case["question_scope"]
    requested_status = "unresolved"
    if scope == "induction" and induction is not None:
        requested_status = induction["check_status"]
    elif any(r["status"] == "not_met" for r in results):
        requested_status = "not_met"
    gaps = ["catalog_incomplete", "current_policy_not_verified", "same_day_gate_status_not_verified"]
    if scope == "unknown":
        gaps.append("question_scope_unknown")
    if value(facts, "terminal_id") == "synthetic_other_terminal":
        gaps.append("unsupported_terminal_requirements")
    if scope in ("induction", "terminal_entry"):
        gaps.append("road_vehicle_permit_scope_not_assessed")
    if scope == "route":
        gaps.append("terminal_and_driver_scope_not_assessed")
    versions = {**evaluation.versions, "requirement_catalog": CATALOG_VERSION}
    payload = {"schema_version": "drayage-trip-assessment-v1", "mode": "synthetic_prototype_only",
               "case": public_case(case), "versions": versions, "write_receipt": None,
               "service_status": "available", "requested_scope_status": requested_status,
               "operational_status": "unresolved_not_assessed", "findings": results,
               "coverage": {"complete_trip_check": False, "catalog_complete": False,
                            "selected_requirements": [r["id"] for r in selected],
                            "executed_requirements": [r["requirement_id"] for r in results
                                                      if r["execution_state"] == "evaluated"],
                            "not_executed_requirements": [r["requirement_id"] for r in results
                                                          if r["execution_state"] != "evaluated"],
                            "gaps": gaps},
               "next_questions": build_followups(case, results),
               "limits": LIMITS.copy()}
    payload["assessment_id"] = digest({"case": case, "versions": versions})
    return payload


def validate_arguments(arguments, operation):
    if not isinstance(arguments, dict):
        raise InputError("Arguments must be an object")
    if operation == "assess_trip" and "trip_id" in arguments:
        if set(arguments) != {"trip_id"}:
            raise InputError("To reassess a saved case supply only trip_id; use update_trip_facts for changes")
        return arguments.copy()
    required = {"request_key", "source_message", "facts"}
    allowed = required | {"requester_role", "question_scope"}
    if operation == "update_trip_facts":
        required |= {"trip_id", "expected_revision", "requester_role", "question_scope"}
        allowed |= required | {"replace_conflicts"}
    if set(arguments) - allowed or required - set(arguments):
        raise InputError("Missing required or unexpected trip-tool arguments")
    result = {"requester_role": "unknown", "question_scope": "unknown", **arguments}
    if result["requester_role"] not in ROLES or result["question_scope"] not in SCOPES:
        raise InputError("Unsupported requester_role or question_scope")
    return result


class TripService:
    def __init__(self, graph_store, trip_store=None):
        self.graph_store = graph_store
        self.trip_store = trip_store if trip_store is not None else TripStore(ROOT / ".runtime" / "trips.sqlite3")

    def assess(self, arguments):
        args = validate_arguments(arguments, "assess_trip")
        case = (self.trip_store.get(args["trip_id"]) if "trip_id" in args
                else self.trip_store.create(**args))
        return self._assess_saved(case, written="trip_id" not in args)

    def update(self, arguments):
        args = validate_arguments(arguments, "update_trip_facts")
        return self._assess_saved(self.trip_store.update(**args), written=True)

    def evidence(self, arguments):
        if not isinstance(arguments, dict) or set(arguments) != {"requirement_id"} or not isinstance(arguments["requirement_id"], str):
            raise InputError("Supply only requirement_id")
        return self.graph_store.read(lambda reader: requirement_evidence(reader, arguments["requirement_id"]))

    def _assess_saved(self, case, written=False):
        receipt = {"trip_id": case["trip_id"], "revision": case["revision"]} if written else None
        # Idempotent writes retain their original receipt, but a retry after a
        # later correction must assess the latest assignment, not resurrect an
        # old pass. Read/assessment results always identify their actual revision.
        case = self.trip_store.get(case["trip_id"])
        try:
            payload = self.graph_store.read(lambda reader: evaluate_trip(reader, case))
        except (EvidenceUnavailable, ArchiveError, OSError):
            # A committed fact update must remain recoverable if evidence retrieval
            # fails. Return its receipt, without any prior or invented finding.
            payload = {"schema_version": "drayage-trip-assessment-v1", "mode": "synthetic_prototype_only",
                    "case": public_case(case), "versions": {"requirement_catalog": CATALOG_VERSION},
                    "assessment_id": digest({"case": case, "service_status": "unavailable"}),
                    "service_status": "unavailable", "requested_scope_status": "unresolved",
                    "operational_status": "unresolved_not_assessed", "findings": [],
                    "coverage": {"complete_trip_check": False, "catalog_complete": False,
                                 "selected_requirements": [], "executed_requirements": [],
                                 "not_executed_requirements": [], "gaps": ["evidence_service_unavailable"]},
                    "next_questions": [],
                    "limits": LIMITS + ["Facts were saved at the returned revision. Evidence assessment failed; retry assess_trip with trip_id. No cached finding is returned."]}
        payload["write_receipt"] = receipt
        return payload
