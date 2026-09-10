"""Exact retained passages for the trip catalog; no caller-supplied Cypher."""

from .requirements import CATALOG_VERSION, applicable_requirements
from .service import Evaluation, InputError


def requirement_evidence(reader, requirement_id):
    requirement = next((r for r in applicable_requirements({}, "trip_dispatch")
                        if r["id"] == requirement_id), None)
    if requirement is None:
        raise InputError("Unknown requirement_id; use an ID returned by assess_trip")
    evaluation = Evaluation(reader)
    sources = []
    for clause_id in requirement["source_clause_ids"]:
        clause = reader.record(clause_id)
        sources.append({**evaluation._citation(clause_id),
                        "authority_entity_id": clause.get("authority_entity_id"),
                        "verbatim": clause.get("source_text_verbatim"),
                        "scope_dimensions": clause.get("keys_on", []),
                        "archive_graph_eligibility": clause.get("graph_eligibility"),
                        "interpretation_status": clause.get("interpretation_status"),
                        "interpretation_boundary": clause.get("interpretation_boundary"),
                        "named_blocker": clause.get("named_blocker"),
                        "scope_basis": "retained_source_locator_and_text_not_user_trip_applicability"})
    return {"schema_version": "drayage-requirement-evidence-v1",
            "mode": "synthetic_prototype_only", "requirement_id": requirement_id,
            "label": requirement["label"], "family": requirement["family"],
            "catalog_version": CATALOG_VERSION, "versions": evaluation.versions,
            "implementation": requirement["implementation"],
            "approval_status": "draft_not_human_approved",
            "sources": sources, "limits": requirement["limits"],
            "evidence_status": "archived_only" if sources else "source_coverage_gap",
            "operational_use": False}
