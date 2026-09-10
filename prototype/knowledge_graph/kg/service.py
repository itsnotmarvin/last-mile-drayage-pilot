"""Deterministic checks backed by a public graph and synthetic evidence graph."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

import networkx as nx

from .graph import ArchiveError, KnowledgeGraph, digest


ROOT = Path(__file__).resolve().parents[1]
CHECK_ID = "check_apm_induction_v1"
NY = ZoneInfo("America/New_York")
FIELDS = ("terminal_id", "actor_role", "driver_id", "current_sealink_id", "trip_at",
          "question_scope", "company_changed")
UNASSESSED = ["current_policy", "CDL_and_other_driver_requirements", "TWIC",
              "SeaLink_validity_and_TWIC_registration", "DTR_and_RFID",
              "appointment_and_transaction", "same_day_gate_status", "vehicle_and_load",
              "route_dimensions_and_axles", "permits_and_cross_authority_coverage"]


class InputError(ValueError):
    pass


def timestamp(value: str) -> datetime:
    if not isinstance(value, str) or len(value) > 40 or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})", value):
        raise InputError("trip_at must be an ISO timestamp with seconds and timezone, or null")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InputError("Invalid calendar/time value") from exc
    return parsed.astimezone(timezone.utc)


def normalize(arguments: dict) -> dict:
    if not isinstance(arguments, dict):
        raise InputError("Arguments must be an object")
    if set(arguments) - set(FIELDS):
        raise InputError("Unexpected fields; the caller cannot supply evidence or rule overrides")
    normalized = {field: arguments.get(field) for field in FIELDS}
    for field in FIELDS[:-1]:
        value = normalized[field]
        if value is not None and (not isinstance(value, str) or len(value) > 120):
            raise InputError(f"{field} must be a short string or null")
    if normalized["terminal_id"] not in (None, "facility_apm_elizabeth", "synthetic_other_terminal"):
        raise InputError("Only the two documented synthetic terminal IDs are accepted")
    if normalized["actor_role"] not in (None, "truck_driver", "other"):
        raise InputError("actor_role must be truck_driver, other, or null")
    driver = normalized["driver_id"]
    if driver is not None and not re.fullmatch(r"syn-driver-[a-z-]{1,40}", driver):
        raise InputError("Only synthetic driver aliases are accepted; never submit real identifiers")
    sealink = normalized["current_sealink_id"]
    if sealink is not None and not re.fullmatch(r"SYN-SL-[A-Z]{1,8}", sealink):
        raise InputError("Only SYN-SL-* synthetic SeaLink aliases are accepted")
    if normalized["company_changed"] is not None and type(normalized["company_changed"]) is not bool:
        raise InputError("company_changed must be boolean or null")
    if normalized["question_scope"] is None:
        normalized["question_scope"] = "induction"
    if normalized["question_scope"] not in ("induction", "terminal_entry", "trip_dispatch", "route"):
        raise InputError("Unsupported question_scope")
    if normalized["trip_at"] is not None:
        normalized["trip_at"] = timestamp(normalized["trip_at"]).isoformat()
    return normalized


class CheckingService:
    def __init__(self, archive: KnowledgeGraph | None = None):
        self.archive = archive or KnowledgeGraph()
        self.archive.verify_archives()  # Fail closed at startup on missing/corrupt evidence.
        self.model = json.loads((ROOT / "data/model.json").read_text())
        self.fixtures = json.loads((ROOT / "data/synthetic_evidence.json").read_text())
        if self.model.get("operational_use") is not False or self.fixtures.get("synthetic_only") is not True:
            raise ArchiveError("This service accepts only draft models and synthetic evidence")
        self.graph = copy.deepcopy(nx.MultiDiGraph(self.archive.graph))
        self._load_model()
        self._load_fixtures()
        nx.freeze(self.graph)
        self.versions = {"evidence": self.archive.evidence_version,
                         "model": digest(self.model), "synthetic_evidence": digest(self.fixtures),
                         "implementation": digest({p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                                   for p in sorted((ROOT / "kg").glob("*.py"))})}

    def _node(self, node_id, kind, record, layer):
        if node_id in self.graph:
            raise ArchiveError(f"Duplicate prototype node: {node_id}")
        self.graph.add_node(node_id, kind=kind, record=copy.deepcopy(record), layer=layer)

    def _edge(self, start, relationship, end):
        if start not in self.graph or end not in self.graph:
            raise ArchiveError(f"Missing prototype relationship endpoint: {relationship}")
        key = f"prototype:{start}:{relationship}:{end}"
        self.graph.add_edge(start, end, key=key, relationship=relationship, record={})

    def _load_model(self):
        for clause in self.model["supplemental_clauses"]:
            self._node(clause["clause_id"], "source_clause", clause, "prototype_extraction")
            self._edge(clause["source_id"], "CONTAINS_CLAUSE", clause["clause_id"])
        for definition in self.model["checks"]:
            if definition["evaluator"] != "induction_identifier_match_v1":
                raise ArchiveError("Unimplemented evaluator")
            if definition["approval_status"] != "draft_not_human_approved":
                raise ArchiveError("Prototype definitions cannot be promoted through this service")
            node_id = definition["check_id"]
            self._node(node_id, "check_definition", definition, "prototype_rule")
            self._edge(node_id, "APPLIES_AT", definition["scope_terminal_id"])
            self._edge(node_id, "REQUIRES_PROGRAM", definition["program_id"])
            for clause_id in definition["supporting_clause_ids"]:
                if self.graph.nodes[clause_id]["kind"] != "source_clause":
                    raise ArchiveError("A check must be supported by source clauses")
                self._edge(clause_id, "SUPPORTS", node_id)

    def _load_fixtures(self):
        for driver in self.fixtures["drivers"]:
            if not re.fullmatch(r"syn-driver-[a-z-]{1,40}", driver["driver_id"]):
                raise ArchiveError("Non-synthetic driver")
            self._node(driver["driver_id"], "synthetic_driver", driver, "synthetic_private")
        for observation in self.fixtures["observations"]:
            if type(observation["completed"]) is not bool:
                raise ArchiveError("Completion must be an explicit boolean")
            timestamp(observation["observed_at"])
            sealink = observation["sealink_id"]
            if not re.fullmatch(r"SYN-SL-[A-Z]{1,8}", sealink):
                raise ArchiveError("Non-synthetic credential identifier")
            if sealink not in self.graph:
                self._node(sealink, "synthetic_sealink_identifier", {"sealink_id": sealink}, "synthetic_private")
            obs_id = observation["observation_id"]
            self._node(obs_id, "synthetic_completion_observation", observation, "synthetic_private")
            self._edge(observation["driver_id"], "HAS_COMPLETION_EVIDENCE", obs_id)
            self._edge(obs_id, "FOR_SEALINK", sealink)
            self._edge(obs_id, "FOR_PROGRAM", observation["program_id"])

    def targets(self, node_id: str, relation: str) -> list[str]:
        return sorted(end for _, end, attrs in self.graph.out_edges(node_id, data=True)
                      if attrs["relationship"] == relation)

    def _citation(self, clause_id):
        if clause_id in self.archive.graph:
            return self.archive.citation(clause_id)
        clause = self.graph.nodes[clause_id]["record"]
        source = self.archive.record(clause["source_id"])
        return {"clause_id": clause_id, "source_id": source["source_id"],
                "publisher": source["publisher"], "title": source["title"], "url": source["url"],
                "locator": clause["source_locator"], "source_text": clause["source_text"],
                "publication_date": source.get("publication_date"),
                "accessed_date": source.get("accessed_date"),
                "archived_files": source.get("archived_files", []),
                "currentness": "archived_evidence_only_not_verified_for_this_trip",
                "extraction_status": "prototype_not_promoted_to_canonical_archive"}

    def check(self, arguments: dict) -> dict:
        facts = normalize(arguments)
        check = self.graph.nodes[CHECK_ID]["record"]
        terminals = self.targets(CHECK_ID, "APPLIES_AT")
        programs = self.targets(CHECK_ID, "REQUIRES_PROGRAM")
        if len(terminals) != 1 or len(programs) != 1:
            raise ArchiveError("Induction evaluator requires one scoped terminal and one program")
        reasons, missing, evidence_ids = [], [], []
        status = "unresolved"
        applicability = "unresolved"
        if facts["terminal_id"] is None or facts["actor_role"] is None:
            reasons.append("APPLICABILITY_FACT_MISSING")
            missing.extend(k for k in ("terminal_id", "actor_role") if facts[k] is None)
        elif facts["terminal_id"] != terminals[0] or facts["actor_role"] != check["scope_actor_role"]:
            status, applicability = "not_applicable", "not_applicable"
            reasons.append("OUTSIDE_CHECK_SCOPE")
        else:
            applicability = "applicable"
            for field, reason in (("trip_at", "TRIP_TIME_MISSING"),
                                  ("driver_id", "DRIVER_ID_MISSING"),
                                  ("current_sealink_id", "CURRENT_SEALINK_MISSING")):
                if facts[field] is None:
                    reasons.append(reason)
                    missing.append(field)
            if not missing:
                status, reasons, missing, evidence_ids = self._completion(facts, programs[0])
        citations = sorted({start for start, _, attrs in self.graph.in_edges(CHECK_ID, data=True)
                            if attrs["relationship"] == "SUPPORTS"})
        requested = status if facts["question_scope"] == "induction" else "unresolved"
        result = {
            "schema_version": "drayage-check-result-v1", "mode": "synthetic_prototype_only",
            "evaluation_id": digest({"facts": facts, "versions": self.versions, "check_id": CHECK_ID}),
            "versions": self.versions.copy(), "normalized_facts": facts,
            "check_id": CHECK_ID, "approval_status": "draft_not_human_approved",
            "applicability": applicability, "check_status": status,
            "reason_codes": reasons, "missing_facts": missing,
            "evidence_ids": sorted(evidence_ids),
            "evidence_basis": "server_owned_synthetic_records_not_live_driver_verification",
            "requested_scope_status": requested,
            "operational_status": "unresolved_not_assessed",
            "coverage": {"evaluated": ["APM_induction_identifier_match"],
                         "not_evaluated": UNASSESSED.copy(), "complete_trip_check": False},
            "sources": [self._citation(clause_id) for clause_id in citations],
            "limits": ["No dispatch, entry, permit or route clearance is issued.",
                       "Archived policy has not been verified as current for this trip.",
                       "Synthetic evidence assessment dates are test controls, not a training expiry rule.",
                       "An out-of-scope check does not mean the person is exempt from other requirements."],
        }
        return result

    def _completion(self, facts, program):
        driver = facts["driver_id"]
        if driver not in self.graph or self.graph.nodes[driver]["kind"] != "synthetic_driver":
            return "unresolved", ["DRIVER_NOT_IN_SYNTHETIC_REGISTRY"], ["synthetic_driver_evidence"], []
        if self.graph.nodes[driver]["record"]["lookup_status"] != "available":
            return "unresolved", ["EVIDENCE_SERVICE_UNAVAILABLE"], ["completion_verification"], []
        evidence_ids = [obs for obs in self.targets(driver, "HAS_COMPLETION_EVIDENCE")
                        if program in self.targets(obs, "FOR_PROGRAM")]
        if not evidence_ids:
            return "unresolved", ["COMPLETION_EVIDENCE_MISSING"], ["completion_for_current_sealink"], []
        matching = [obs for obs in evidence_ids
                    if facts["current_sealink_id"] in self.targets(obs, "FOR_SEALINK")]
        if not matching:
            return "unresolved", ["SEALINK_EVIDENCE_MISMATCH"], ["completion_for_current_sealink"], evidence_ids
        records = [self.graph.nodes[obs]["record"] for obs in matching]
        trip = timestamp(facts["trip_at"])
        reasons = []
        if any(timestamp(record["observed_at"]) > trip for record in records):
            reasons.append("EVIDENCE_FROM_FUTURE")
        if any(record["verification"] not in ("synthetic_confirmed", "stale") for record in records):
            reasons.append("EVIDENCE_UNVERIFIED")
        if any(record["verification"] == "stale" or record["assessment_date"] != trip.astimezone(NY).date().isoformat()
               for record in records):
            reasons.append("EVIDENCE_NOT_CURRENT_FOR_FIXTURE")
        if len({record["completed"] for record in records}) != 1:
            reasons.append("CONFLICTING_COMPLETION_EVIDENCE")
        if reasons:
            return "unresolved", reasons, ["authoritative_completion_verification_for_current_sealink"], matching
        if records[0]["completed"]:
            return "met", ["MATCHING_COMPLETION"], [], matching
        return "not_met", ["EXPLICIT_NON_COMPLETION"], [], matching

    def context(self, topic: str) -> dict:
        if topic not in ("summary", "induction", "route_directions", "port_street", "coverage"):
            raise InputError("Unsupported graph topic")
        result = {"mode": "synthetic_prototype_only", "topic": topic,
                  "versions": self.versions.copy(), "operational_use": False}
        if topic == "summary":
            result.update(self.archive.summary())
            result["prototype_node_count"] = self.graph.number_of_nodes()
            result["prototype_edge_count"] = self.graph.number_of_edges()
        elif topic == "induction":
            result["check"] = copy.deepcopy(self.graph.nodes[CHECK_ID]["record"])
            result["sources"] = [self._citation(c) for c in result["check"]["supporting_clause_ids"]]
        elif topic == "route_directions":
            result["routes"] = [self.archive.record(node) for node, attrs in self.archive.graph.nodes(data=True)
                                if attrs["kind"] in ("route_family", "route_approach")]
            result["limit"] = "APM-published directions and candidate topology are not legal route designation or clearance."
        elif topic == "port_street":
            result["observations"] = [self.archive.record(node) for node, attrs in self.archive.graph.nodes(data=True)
                                      if attrs["kind"] == "mutable_observation"]
            result["limit"] = "Archived observations only. No current Port Street restriction, height clearance, permission or prohibition is determined."
        else:
            result["implemented_checks"] = [CHECK_ID]
            result["not_evaluated"] = UNASSESSED.copy()
        return result
