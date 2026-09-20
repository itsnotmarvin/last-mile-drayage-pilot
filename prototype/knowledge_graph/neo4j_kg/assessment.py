"""Versioned trip conversation service over Neo4j evidence and local case state.

Reports advance intake. Only server-owned evidence can establish a check result.
Every request evaluates its saved revision against a fresh graph read.
"""

from __future__ import annotations

import copy

from .reported_checks import evaluate_reported_checks, unavailable as unavailable_reported_checks
from .reported_checks import CATALOG_VERSION as REPORTED_CHECK_CATALOG, ENGINE_VERSION as REPORTED_CHECK_ENGINE
from .common import ArchiveError, EvidenceUnavailable, ROOT, digest
from .evidence import requirement_evidence, trip_evidence
from .requirements import CATALOG_VERSION, applicable_requirements
from .route_context import build_route_context
from .service import Evaluation, InputError
from .trip_state import TripStore
from .input_review import input_review
from .decision_brief import decision_brief
from .answer_guidance import answer_guidance
from .verification import admit, evaluate_requirement, restrict_evidence_to_segments
from .verification import REQUIRED_KINDS, CONTRACT_VERSION, ENGINE_VERSION
from .verification_store import VerificationStore
from .source_supplements import source_coverage_gaps


SCOPES = ("unknown", "induction", "terminal_entry", "trip_dispatch", "route")
ROLES = ("unknown", "driver", "dispatcher", "other")
LIMITS = [
    "Synthetic development cases only; no operational entry or dispatch clearance.",
    "Reported facts are not authoritative verification, even when a reporter says verified.",
    "The catalog is incomplete; current policy, CDL, gate state and other duties remain outside executable coverage.",
    "Archived directions and bulletins do not establish legal access or current road conditions.",
    "Bounded draft evaluators use server-owned synthetic records; missing verification, source gaps and exceptions remain unresolved.",
]


def value(facts, field):
    return facts.get(field, {}).get("value")


def public_case(case):
    """Return current provenance and conflicts without unbounded historical turns."""
    return {k: copy.deepcopy(v) for k, v in case.items() if k != "history"}


def evaluate_trip(reader, case, verification_snapshot=None, now=None, terminal_status=None):
    from .followups import build_followups

    review = input_review(case)
    rejected_fields = {i['field'] for i in review['issues']}
    # Older persisted cases may predate write-time extraction checks. Preserve
    # their history, but never evaluate a known inconsistent value as fact.
    facts = {k: v for k, v in case["facts"].items() if k not in rejected_fields}
    selected = applicable_requirements(facts, case["question_scope"])
    evaluation = Evaluation(reader)
    if verification_snapshot is None:
        verification_snapshot = {'version': digest({'empty_verifications': True, 'case': case['trip_id']}),
                                 'receipts': [], 'revoked_ids': []}
    admission = admit(verification_snapshot, case, evaluation.versions['graph_release'], now)
    route_context = build_route_context(evaluation.reader, value(facts, 'route_id'),
                                        evaluation.versions['graph_release'])
    if route_context['status'] == 'resolved_from_pinned_graph':
        # Segment-bearing receipts must reference the trip's resolved route.
        # Anything else fails closed instead of evaluating the wrong road.
        admission = restrict_evidence_to_segments(
            admission, [s['segment_id'] for s in route_context['segments']])
    evidence_package = trip_evidence(evaluation, selected, facts, case['conflicts'],
                                     terminal_status=terminal_status, route_context=route_context)
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
               "reported_absences": [f for f in dict.fromkeys(requirement["required_fields"] + requirement["verification_fields"])
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
        elif requirement['id'] in REQUIRED_KINDS:
            evaluated = evaluate_requirement(requirement['id'], facts, admission, value(facts, 'trip_at'))
            kinds = REQUIRED_KINDS[requirement['id']]
            has_evidence = any(admission['evidence'].get(k) for k in kinds)
            row.update(status=evaluated['status'],
                       execution_state='evaluated' if has_evidence else 'verification_required',
                       reason_codes=evaluated['reason_codes'] or ['BOUNDED_SYNTHETIC_PREDICATES_MET'],
                       evidence_ids=evaluated['used_receipt_ids'],
                       evidence_basis='operator_owned_synthetic_verification',
                       checks=evaluated['checks'],
                       limits=requirement['limits'] + evaluated['limits'],
                       verification_needed=[] if evaluated['status']=='met' else ['operator_verification_resolution'])
            rejected = [r for r in admission['rejected'] if r['kind'] in kinds]
            row['rejected_evidence'] = rejected
            if rejected and not has_evidence:
                row['reason_codes'] = list(dict.fromkeys(row['reason_codes'] + [c for r in rejected for c in r['reason_codes']]))
            if missing or conflicting:
                # Unknown assignment/applicability never disappears because an
                # unrelated predicate failed or a partial fixture was available.
                row['status'] = 'unresolved'
                row['reason_codes'] += (['REQUIRED_FACTS_MISSING'] if missing else []) + (['CONFLICTING_REPORTS'] if conflicting else [])
            source_gaps = source_coverage_gaps(requirement, evidence_package, evaluation.versions['graph_release'])
            if source_gaps:
                row['status'] = 'unresolved'
                row['reason_codes'] = [code for code in row['reason_codes']
                                       if code != 'BOUNDED_SYNTHETIC_PREDICATES_MET'] + ['SOURCE_COVERAGE_INCOMPLETE']
                row['verification_needed'] = list(dict.fromkeys(row['verification_needed'] + ['source_coverage_resolution']))
                row['checks'].append({'id': 'source_coverage', 'status': 'unresolved',
                                      'detail': 'Required supporting evidence is missing or changed: ' + ', '.join(source_gaps)})
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
    versions = {**evaluation.versions, "requirement_catalog": CATALOG_VERSION,
                "reported_check_catalog": REPORTED_CHECK_CATALOG, "reported_check_engine": REPORTED_CHECK_ENGINE,
                "verification_contract": CONTRACT_VERSION, "requirement_engine": ENGINE_VERSION,
                "verification_snapshot": admission['snapshot_version'],
                "verification_admission": admission['admission_version']}
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
               "next_questions": build_followups(case, results, evidence_package.get("route_context")),
               "evidence_package": evidence_package,
               "limits": LIMITS.copy()}
    payload['verification_evidence'] = {
        'status': 'available', 'mode': 'synthetic_only',
        'snapshot_version': admission['snapshot_version'],
        'accepted_receipts': [r for rs in admission['evidence'].values() for r in rs],
        'rejected_receipts': admission['rejected'], 'revoked_ids': admission['revoked_ids'],
        'limits': ['Provider aliases are synthetic adapter fixtures, not authenticated real issuers.',
                   'Intervals are start-inclusive/end-exclusive; observations cannot occur after the trip or assessment.',
                   'User or model statements cannot create, amend, or revoke operator verification records.']}
    versions['draft_source_supplements'] = digest(payload['evidence_package']['draft_supplements'])
    payload['reported_fact_checks'] = evaluate_reported_checks(case, payload['evidence_package'], versions, selected, rejected_fields)
    payload["input_review"] = review
    if rejected_fields:
        payload['requested_scope_status'] = 'unresolved'
        payload['coverage']['gaps'].append('input_text_conflict')
        payload['next_questions'] = [
            {'field': i['field'], 'question': i['message'], 'owner': 'requester',
             'reason': 'The recorded value conflicts with its supplied source text.',
             'requirement_ids': [], 'kind': 'extraction_correction'} for i in review['issues'][:3]]
    payload["assessment_id"] = digest({"case": case, "versions": versions})
    payload['decision_brief'] = decision_brief(payload)
    payload['answer_guidance'] = answer_guidance(payload)
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
    def __init__(self, graph_store, trip_store=None, verification_store=None,
                 terminal_status_fetcher=None):
        self.graph_store = graph_store
        self.verification_store = verification_store if verification_store is not None else VerificationStore()
        self.trip_store = trip_store if trip_store is not None else TripStore(ROOT / ".runtime" / "trips.sqlite3")
        self.terminal_status_fetcher = terminal_status_fetcher

    def _terminal_status(self):
        """Current terminal operating context, fetched outside the graph read.

        Live fetch is env-gated so offline suites stay network-free. Any
        outcome, including disabled/unavailable, is explanatory context only.
        """
        if self.terminal_status_fetcher is not None:
            try:
                return self.terminal_status_fetcher()
            except Exception:
                from .terminal_status import unavailable as _unavailable
                return _unavailable("fetch_error:fetcher")
        import os
        if os.environ.get("DRAYAGE_TERMINAL_STATUS_LIVE") == "1":
            from .terminal_status import fetch as _fetch
            return _fetch()
        from .terminal_status import unavailable as _unavailable
        return _unavailable("live_fetch_disabled")

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
        from .terminal_status import current_observation
        terminal_status = current_observation(self._terminal_status())
        try:
            def assess_reader(reader):
                snapshot = self.verification_store.snapshot(case, reader.release['revision'])
                return evaluate_trip(reader, case, snapshot, terminal_status=terminal_status)
            payload = self.graph_store.read(assess_reader)
            current = self.verification_store.snapshot(case, payload['versions']['graph_release'])
            if current['version'] != payload['versions']['verification_snapshot']:
                raise EvidenceUnavailable('Verification changed during assessment; retry')
            if self.trip_store.get(case['trip_id'])['revision'] != case['revision']:
                raise EvidenceUnavailable('Trip changed during assessment; retry')
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
                    "evidence_package": {"schema_version": "drayage-trip-evidence-v1",
                            "status": "unavailable", "sources": [], "draft_supplements": [],
                            "requirement_links": [], "observations": [],
                            "route_context": None, "current_terminal_status": None,
                                         "port_street_selection": "evidence_service_unavailable",
                                         "limits": ["Evidence retrieval failed; no cached passages or observations are returned."]},
                    "limits": LIMITS + ["Facts were saved at the returned revision. Evidence assessment failed; retry assess_trip with trip_id. No cached finding is returned."]}
        if 'verification_evidence' not in payload:
            payload['verification_evidence'] = {'status': 'unavailable', 'mode': 'synthetic_only',
                'snapshot_version': '', 'accepted_receipts': [], 'rejected_receipts': [], 'revoked_ids': [],
                'limits': ['Verification unavailable; no prior positive record is returned.']}
        if 'reported_fact_checks' not in payload:
            payload['reported_fact_checks'] = unavailable_reported_checks()
        if 'input_review' not in payload:
            payload['input_review'] = input_review(case)
            payload['decision_brief'] = decision_brief(payload)
        payload['answer_guidance'] = answer_guidance(payload)
        payload["write_receipt"] = receipt
        return payload
