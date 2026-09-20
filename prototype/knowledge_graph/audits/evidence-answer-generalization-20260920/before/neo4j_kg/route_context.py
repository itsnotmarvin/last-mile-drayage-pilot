"""Graph-derived candidate route structure for trip assessments.

Read-only. Resolves one of the existing named routes into its ordered road
segments with jurisdiction and governing-clause context from the pinned
release, using only the reader's bounded node/neighbor lookups.

Candidate structure only: discovering topology never satisfies a
requirement, verifies no fact, and assumes no currentness. Measurement,
approval, and condition predicates still require admitted operator
verification receipts. ``other`` and free-text routes stay unbacked.
"""

from __future__ import annotations


GRAPH_BACKED_ROUTES = ("path_a_exit13a_to_apm", "path_b_us1_9_to_apm")

GOVERNANCE_RELS = (
    "GOVERNS",
    "OVERLAPS_PART_OF",
    "STREET_NOT_LISTED_IN_RESTRICTION_TABLE",
    "ROUTE_NUMBER_NOT_LISTED_IN_APPENDIX_C",
    "TRUCK_ROUTE_SCHEDULE_RESERVED",
    "GOVERNS_ACCESS_AT",
    "GOVERNS_ENTRY_AT",
    "GOVERNS_GATE_MOVE_AT",
    "GOVERNS_PORT_ENTRY_MOVEMENT_AT",
    "GOVERNS_UNESCORTED_SECURE_ACCESS_AT",
)

CANDIDATE_LIMITS = [
    "Graph-derived candidate structure only; it requires trip-specific verification and never satisfies a requirement.",
    "Stored topology and clause references are archived evidence, not legal route designation, permission, or current conditions.",
    "A road's presence here, or its absence from a restriction table, establishes neither permission nor prohibition.",
    "Segment measurements, approvals, and current postings still require admitted operator verification for this trip.",
]


def clause_requirement_map():
    """Static clause -> requirement mapping from the catalog (no graph read)."""
    from .requirements import REQUIREMENTS
    mapping: dict[str, list[str]] = {}
    for requirement in REQUIREMENTS:
        for clause_id in requirement["source_clause_ids"]:
            mapping.setdefault(clause_id, []).append(requirement["id"])
    return {clause: sorted(ids) for clause, ids in mapping.items()}


def _name(record: dict, kind: str) -> str | None:
    if not isinstance(record, dict):
        return None
    if kind == "physical_location":
        properties = record.get("properties")
        if isinstance(properties, dict) and isinstance(properties.get("name"), str):
            return properties["name"]
        return None
    name = record.get("name")
    return name if isinstance(name, str) else None


def _aliases(record: dict) -> list[str]:
    if not isinstance(record, dict):
        return []
    seen: list[str] = []
    for key in ("official_feature_names", "official_list_names"):
        values = record.get(key)
        if isinstance(values, list):
            for value in values:
                if isinstance(value, str) and value not in seen:
                    seen.append(value)
    return seen


def _unavailable(route_value, graph_release, reason: str) -> dict:
    return {
        "status": reason,
        "route_id": route_value,
        "route_kind": None,
        "route_name": None,
        "graph_release": graph_release,
        "segments": [],
        "candidate_requirement_ids": [],
        "limits": list(CANDIDATE_LIMITS),
    }


def build_route_context(reader, route_value, graph_release: str) -> dict:
    """Resolve a named route to candidate segment structure, or explain why not."""
    if route_value not in GRAPH_BACKED_ROUTES:
        return _unavailable(route_value, graph_release, "unavailable_route_not_graph_backed")
    try:
        return _resolve(reader, route_value, graph_release)
    except (KeyError, TypeError, ValueError, AttributeError):
        # Inconsistent release content must stay explanatory, never fail the
        # assessment or invent topology. The assessment remains available.
        return _unavailable(route_value, graph_release, "unavailable_graph_inconsistency")


def _resolve(reader, route_id: str, graph_release: str) -> dict:
    route_node = reader.node(route_id)
    if route_node["kind"] != "route_family":
        raise ValueError("Named route is not a route_family record")
    record = reader.record(route_id)
    ordered = record.get("ordered_edge_ids")
    if not isinstance(ordered, list) or not ordered or len(set(ordered)) != len(ordered):
        raise ValueError("Route has no usable ordered segment list")
    linked = reader.neighbors(route_id, "HAS_ORDERED_SEGMENT")
    if sorted(linked) != sorted(ordered):
        raise ValueError("Route segment links differ from the ordered segment list")
    clause_reqs = clause_requirement_map()
    segments = []
    for sequence, segment_id in enumerate(ordered, 1):
        segments.append(_segment(reader, segment_id, sequence, clause_reqs))
    candidate_requirements = sorted({req for segment in segments
                                     for req in segment["candidate_requirement_ids"]})
    return {
        "status": "resolved_from_pinned_graph",
        "route_id": route_id,
        "route_kind": route_node["kind"],
        "route_name": _name(record, "route_family"),
        "graph_release": graph_release,
        "segments": segments,
        "candidate_requirement_ids": candidate_requirements,
        "limits": list(CANDIDATE_LIMITS),
    }


def _segment(reader, segment_id: str, sequence: int, clause_reqs: dict) -> dict:
    node = reader.node(segment_id)
    if node["kind"] != "road_segment":
        raise ValueError(f"Route member is not a road segment: {segment_id}")
    record = reader.record(segment_id)
    starts = reader.neighbors(segment_id, "STARTS_AT")
    ends = reader.neighbors(segment_id, "ENDS_AT")
    if len(starts) != 1 or len(ends) != 1:
        raise ValueError(f"Segment lacks unique endpoints: {segment_id}")
    if starts[0] != record.get("from_node") or ends[0] != record.get("to_node"):
        raise ValueError(f"Segment edges differ from record endpoints: {segment_id}")
    jurisdictions = []
    for jurisdiction_id in sorted(reader.neighbors(segment_id, "LOCATED_WITHIN")):
        jurisdiction = reader.node(jurisdiction_id)
        jurisdictions.append({
            "id": jurisdiction_id,
            "kind": jurisdiction["kind"],
            "name": _name(reader.record(jurisdiction_id), jurisdiction["kind"]),
        })
    governing = sorted({clause_id for rel in GOVERNANCE_RELS
                        for clause_id in reader.neighbors(segment_id, rel, incoming=True)})
    candidate_requirements = sorted({req for clause_id in governing
                                     for req in clause_reqs.get(clause_id, [])})
    return {
        "sequence": sequence,
        "segment_id": segment_id,
        "name": _name(record, "road_segment"),
        "aliases": _aliases(record),
        "starts_at": starts[0],
        "starts_at_name": _name(reader.record(starts[0]), "physical_location"),
        "ends_at": ends[0],
        "ends_at_name": _name(reader.record(ends[0]), "physical_location"),
        "jurisdictions": jurisdictions,
        "njogis_categories": sorted(reader.neighbors(segment_id, "HAS_NJOGIS_JURISDICTION_CATEGORY")),
        "governing_clause_ids": governing,
        "candidate_requirement_ids": candidate_requirements,
    }
