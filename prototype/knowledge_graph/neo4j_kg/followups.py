"""Bounded, deterministic follow-up questions for a trip assessment."""

from __future__ import annotations

from .requirements import applicable_requirements


MAX_FOLLOWUPS = 3

# Context first when it is absent, then the exact route, loaded dimensions, and
# mutable road conditions that dominated the frozen challenge failures.  The
# remaining order advances weight, permit, and terminal-entry intake without
# presenting a driver with the entire catalog as one giant questionnaire.
_FIELD_PRIORITY = (
    "terminal_id",
    "trip_at",
    "route_id",
    "route_description",
    "port_street_in_route",
    "width",
    "height",
    "semitrailer_length",
    "route_conditions_checked_at",
    "overall_length",
    "gross_weight",
    "axle_weights",
    "axle_spacings",
    "axle_count",
    "permit_type",
    "container_sealed",
    "load_divisible",
    "permit_route_reported",
    "turnpike_approval_reported",
    "local_approval_reported",
    "port_approval_reported",
    "terminal_approval_reported",
    "subject_role",
    "driver_id",
    "current_sealink_id",
    "twic_reported",
    "sealink_registered_reported",
    "induction_reported",
    "vehicle_id",
    "engine_model_year",
    "dtr_reported",
    "rfid_reported",
    "appointment_reported",
    "transaction_release_reported",
    "trailer_id",
    "cargo_hazardous",
)
_PRIORITY = {field: position for position, field in enumerate(_FIELD_PRIORITY)}


_VERIFICATION_QUESTIONS = {
    "gross_weight": "Verify the reported loaded gross weight from a current scale or authoritative load record.",
    "axle_weights": "Verify the reported axle and axle-group weights from a current scale or authoritative load record.",
    "axle_spacings": "Verify the reported axle spacings for the assigned equipment.",
    "width": "Verify the reported loaded width from a current measurement or authoritative load record.",
    "height": "Verify the reported loaded height from a current measurement or authoritative load record.",
    "overall_length": "Verify the reported loaded overall length from a current measurement or authoritative equipment record.",
    "semitrailer_length": "Verify the reported semitrailer length for the assigned trailer.",
    "route_id": "Confirm the exact route and every roadway jurisdiction with the carrier and responsible road authorities.",
    "route_description": "Confirm the full road sequence, including terminal access, against the permit and responsible road authorities.",
    "route_conditions_checked_at": "Recheck current postings, closures, lane widths, detours, escorts, and restrictions with each responsible road authority for this trip.",
    "permit_type": "Verify the reported permit identity, terms, validity window, vehicle, and load with the issuing authority.",
    "permit_route_reported": "Verify with the issuing authority that the permit covers this exact route and trip.",
    "turnpike_approval_reported": "Verify the reported toll-road approval directly with the responsible tolling authority.",
    "local_approval_reported": "Verify the reported county and local approvals with each responsible road authority.",
    "port_approval_reported": "Verify the reported Port Authority approval directly with the Port Authority.",
    "terminal_approval_reported": "Verify the reported terminal handling approval directly with the terminal.",
    "dtr_reported": "Verify the reported DTR status for this truck through an authorized registry source.",
    "rfid_reported": "Verify that the assigned truck has a current, correctly associated RFID tag through an authorized source.",
    "twic_reported": "Verify the reported TWIC through an authorized credential source for the intended access.",
    "sealink_registered_reported": "Verify the current SeaLink and its TWIC registration through an authorized Port Authority source.",
    "induction_reported": "Verify induction for this driver and current SeaLink through the implemented synthetic check or an authorized source.",
    "appointment_reported": "Verify the appointment for this exact gate move through an authorized terminal source.",
    "transaction_release_reported": "Verify the same-day transaction release and gate state directly with the terminal before entry.",
}


def _value(facts: dict, field: str):
    if not isinstance(facts, dict):
        return None
    record = facts.get(field)
    return record.get("value") if isinstance(record, dict) else None


def _rank(field: str) -> tuple[int, str]:
    return (_PRIORITY.get(field, len(_PRIORITY)), field)


def _add_candidate(candidates: dict, *, field: str, requirement: dict,
                   kind: str, question: str, reason: str) -> None:
    """Merge one field across requirements without duplicating its question."""
    candidate = candidates.get(field)
    if candidate is None:
        candidates[field] = {
            "field": field,
            "question": question,
            "owner": requirement["owner"],
            "reason": reason,
            "requirement_ids": [requirement["id"]],
            "kind": kind,
        }
        return
    if requirement["id"] not in candidate["requirement_ids"]:
        candidate["requirement_ids"].append(requirement["id"])
    if kind == "verification" and requirement["owner"] == "authority":
        candidate["owner"] = "authority"


def build_followups(case: dict, findings: list[dict]) -> list[dict]:
    """Return at most three relevant fact, conflict, or verification actions.

    Known values are never asked for again as missing facts.  User-reported
    values can still produce a separately worded verification action because a
    report is not authoritative evidence.  Conflicts take precedence, followed
    by missing facts and then verification work.
    """
    if not isinstance(case, dict) or not isinstance(findings, list):
        return []
    facts = case.get("facts") if isinstance(case.get("facts"), dict) else {}
    requirements = {
        item["id"]: item for item in applicable_requirements(
            facts, case.get("question_scope"),
        )
    }
    finding_by_id = {
        finding.get("requirement_id"): finding for finding in findings
        if isinstance(finding, dict) and isinstance(finding.get("requirement_id"), str)
    }

    conflicts = {}
    missing = {}
    verification = {}
    for requirement_id, requirement in requirements.items():
        finding = finding_by_id.get(requirement_id)
        if finding is None:
            continue
        if finding.get("status") in ("met", "not_applicable"):
            continue
        templates = requirement["question_templates"]

        for field in finding.get("conflicting_fields", []):
            if field not in templates:
                continue
            _add_candidate(
                conflicts,
                field=field,
                requirement=requirement,
                kind="conflict_resolution",
                question=f"The reports for {field.replace('_', ' ')} conflict. What is the explicit corrected value?",
                reason="Conflicting reports keep this fact unresolved until an explicit correction is recorded.",
            )

        for field in finding.get("missing_fields", []):
            if field not in templates or field in conflicts or _value(facts, field) is not None:
                continue
            _add_candidate(
                missing,
                field=field,
                requirement=requirement,
                kind="missing_fact",
                question=templates[field],
                reason="This fact is needed to determine requirement applicability or evidence readiness.",
            )

        for field in finding.get("verification_needed", []):
            if (field not in templates or field in conflicts or field in missing
                    or _value(facts, field) is None):
                continue
            reported_value = _value(facts, field)
            reason = (
                "The current report says this item is absent; it needs resolution and authoritative confirmation."
                if reported_value is False else
                "The value is user-reported and still needs authoritative verification for this trip."
            )
            _add_candidate(
                verification,
                field=field,
                requirement=requirement,
                kind="verification",
                question=_VERIFICATION_QUESTIONS.get(
                    field,
                    f"Verify the reported {field.replace('_', ' ')} with the responsible evidence owner.",
                ),
                reason=reason,
            )

        # The implemented induction evaluator can have every user-supplied fact
        # and still lack usable server-owned synthetic evidence (missing,
        # mismatched, stale, conflicting, future-dated, or unavailable).  Those
        # evaluator tokens are deliberately not accepted trip fact fields.  Give
        # the caller one evidence-resolution action instead of asking the user to
        # repeat a known driver, SeaLink, date, or self-report.
        induction_evidence_fields = [
            field for field in finding.get("verification_needed", [])
            if field not in templates
        ]
        if (requirement_id == "apm_induction"
                and finding.get("status") == "unresolved"
                and not finding.get("missing_fields")
                and not finding.get("conflicting_fields")
                and induction_evidence_fields):
            evidence_field = induction_evidence_fields[0]
            _add_candidate(
                verification,
                field=evidence_field,
                requirement={**requirement, "owner": "authority"},
                kind="evidence_resolution",
                question=(
                    "Resolve the unavailable, non-matching, stale, or conflicting "
                    "server-owned synthetic induction evidence for the assigned "
                    "driver and current SeaLink, then reassess this saved trip."
                ),
                reason=(
                    "The implemented induction check is unresolved even though "
                    "its user-supplied inputs are present; this prototype has no "
                    "live training-provider lookup."
                ),
            )

    ordered = []
    for bucket in (conflicts, missing, verification):
        ordered.extend(bucket[field] for field in sorted(bucket, key=_rank))
    return ordered[:MAX_FOLLOWUPS]
