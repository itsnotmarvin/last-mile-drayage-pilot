"""Exact retained passages for the trip catalog; no caller-supplied Cypher."""

from .requirements import CATALOG_VERSION, applicable_requirements
from .route_context import build_route_context
from .service import Evaluation, InputError
from .provenance_notes import provenance_review
from .source_supplements import draft_supplements


PORT_STREET_OBSERVATION = "njpass_port_st_oversize_restrictions_2026_08_03"


def clause_evidence(evaluation, clause_id):
    clause = evaluation.reader.record(clause_id)
    return {**evaluation._citation(clause_id),
            "authority_entity_id": clause.get("authority_entity_id"),
            "verbatim": clause.get("source_text_verbatim"),
            "scope_dimensions": clause.get("keys_on", []),
            "archive_graph_eligibility": clause.get("graph_eligibility"),
            "interpretation_status": clause.get("interpretation_status"),
            "interpretation_boundary": clause.get("interpretation_boundary"),
            "named_blocker": clause.get("named_blocker"),
            "provenance_review": provenance_review(evaluation.versions["graph_release"], clause_id),
            "scope_basis": "retained_source_locator_and_text_not_user_trip_applicability"}


def port_street_observation(evaluation):
    """Preserve the quarantined observation separately from legal source clauses."""
    observation = evaluation.reader.record(PORT_STREET_OBSERVATION)
    source_id = observation["archive_context"]["source_id"]
    source = evaluation.reader.record(source_id)
    return {"condition_id": PORT_STREET_OBSERVATION, "source_id": source_id,
            "publisher": source["publisher"], "title": source["title"], "url": source["url"],
            "publication_date": source.get("publication_date"),
            "accessed_date": source.get("accessed_date"),
            "archived_files": source.get("archived_files", []),
            "record": observation,
            "currentness": "archived_observation_not_verified_for_this_trip",
            "operational_use": False}


def trip_evidence(evaluation, selected, facts, conflicts, terminal_status=None, route_context=None):
    """One package, within the assessment transaction, with no repeated passages.

    Unknown Port Street membership retains the bulletin as candidate context.
    An explicit false report can omit it, unless that field is conflicted.
    Neither inclusion nor omission establishes route eligibility.
    """
    clauses = list(dict.fromkeys(cid for r in selected for cid in r["source_clause_ids"]))
    has_conditions = any(r["id"] == "current_route_conditions" for r in selected)
    port_value = facts.get("port_street_in_route", {}).get("value")
    port_conflict = any(c["field"] == "port_street_in_route" for c in conflicts)
    include_port = has_conditions and (port_value is not False or port_conflict)
    selection = ("reported_or_unknown_route_membership" if include_port
                 else "reported_outside_route" if has_conditions else "outside_requested_scope")
    route_context = build_route_context(evaluation.reader, facts.get("route_id", {}).get("value"),
                                        evaluation.versions["graph_release"]) if route_context is None else route_context
    return {"schema_version": "drayage-trip-evidence-v1", "status": "available",
            "sources": [clause_evidence(evaluation, cid) for cid in clauses],
            "draft_supplements": draft_supplements(evaluation, [r["id"] for r in selected]),
            "requirement_links": [
                {"requirement_id": r["id"], "source_clause_ids": r["source_clause_ids"].copy(),
                 "condition_ids": [PORT_STREET_OBSERVATION]
                 if r["id"] == "current_route_conditions" and include_port else []}
                for r in selected],
            "observations": [port_street_observation(evaluation)] if include_port else [],
            "port_street_selection": selection,
            "route_context": route_context,
            "current_terminal_status": terminal_status,
            "limits": [
                "Selected passages support explaining requirements; they do not establish trip applicability or clearance.",
                "User reports remain in the trip record and never amend shared graph evidence.",
                "The pinned release is not a promise of the latest law or policy. Publication, access and effective dates are distinct.",
                "Dated operating observations require current-condition verification for a real move.",
            ]}


def requirement_evidence(reader, requirement_id):
    requirement = next((r for r in applicable_requirements({}, "trip_dispatch")
                        if r["id"] == requirement_id), None)
    if requirement is None:
        raise InputError("Unknown requirement_id; use an ID returned by assess_trip")
    evaluation = Evaluation(reader)
    sources = [clause_evidence(evaluation, cid) for cid in requirement["source_clause_ids"]]
    supplements = draft_supplements(evaluation, [requirement_id])
    return {"schema_version": "drayage-requirement-evidence-v1",
            "mode": "synthetic_prototype_only", "requirement_id": requirement_id,
            "label": requirement["label"], "family": requirement["family"],
            "catalog_version": CATALOG_VERSION, "versions": evaluation.versions,
            "implementation": requirement["implementation"],
            "approval_status": "draft_not_human_approved",
            "sources": sources, "draft_supplements": supplements, "limits": requirement["limits"],
            "observations": [port_street_observation(evaluation)]
            if requirement_id == "current_route_conditions" else [],
            "evidence_status": "prototype_extraction_only" if supplements else "archived_only" if sources else "source_coverage_gap",
            "operational_use": False}
