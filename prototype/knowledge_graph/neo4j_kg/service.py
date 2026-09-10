"""Deterministic checks backed by a public graph and synthetic evidence graph."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

from .common import ArchiveError, digest
from .store import Neo4jStore


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


class Evaluation:
    """Frozen induction semantics, using a Neo4j transaction for evidence access.

    The September 6 kg/ package is retained as a byte-identical historical oracle.
    Migration parity tests compare every substantive result field against it.
    """

    def __init__(self, reader):
        self.reader = reader
        self.versions = dict(reader.release["versions"])
        self.versions["graph_release"] = reader.release["revision"]
        paths = [*sorted((ROOT / "neo4j_kg").glob("*.py")),
                 ROOT / "run_neo4j_mcp.py", ROOT / "requirements-neo4j.txt"]
        self.versions["implementation"] = digest({str(p.relative_to(ROOT)):
            hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})

    def targets(self, node_id, relation):
        return self.reader.neighbors(node_id, relation)

    def _citation(self, clause_id):
        clause_node = self.reader.node(clause_id)
        clause = clause_node["record"]
        source = self.reader.record(clause["source_id"])
        return {"clause_id": clause_id, "source_id": source["source_id"],
                "publisher": source["publisher"], "title": source["title"], "url": source["url"],
                "locator": clause["source_locator"], "source_text": clause["source_text"],
                "publication_date": source.get("publication_date"),
                "accessed_date": source.get("accessed_date"),
                "archived_files": source.get("archived_files", []),
                "currentness": "archived_evidence_only_not_verified_for_this_trip",
                **({} if clause_node["archive"] else {"extraction_status": "prototype_not_promoted_to_canonical_archive"})}

    def check(self, arguments: dict) -> dict:
        facts = normalize(arguments)
        check = self.reader.record(CHECK_ID)
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
        citations = sorted(set(self.reader.neighbors(CHECK_ID, "SUPPORTS", incoming=True)))
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
        driver_node = self.reader.node(driver, required=False)
        if driver_node is None or driver_node["kind"] != "synthetic_driver":
            return "unresolved", ["DRIVER_NOT_IN_SYNTHETIC_REGISTRY"], ["synthetic_driver_evidence"], []
        if driver_node["record"]["lookup_status"] != "available":
            return "unresolved", ["EVIDENCE_SERVICE_UNAVAILABLE"], ["completion_verification"], []
        evidence_ids = [obs for obs in self.targets(driver, "HAS_COMPLETION_EVIDENCE")
                        if program in self.targets(obs, "FOR_PROGRAM")]
        if not evidence_ids:
            return "unresolved", ["COMPLETION_EVIDENCE_MISSING"], ["completion_for_current_sealink"], []
        matching = [obs for obs in evidence_ids
                    if facts["current_sealink_id"] in self.targets(obs, "FOR_SEALINK")]
        if not matching:
            return "unresolved", ["SEALINK_EVIDENCE_MISMATCH"], ["completion_for_current_sealink"], evidence_ids
        records = [self.reader.record(obs) for obs in matching]
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
            result.update(self.reader.summary())
        elif topic == "induction":
            result["check"] = copy.deepcopy(self.reader.record(CHECK_ID))
            result["sources"] = [self._citation(c) for c in result["check"]["supporting_clause_ids"]]
        elif topic == "route_directions":
            result["routes"] = self.reader.records_by_kind(("route_family", "route_approach"))
            result["limit"] = "APM-published directions and candidate topology are not legal route designation or clearance."
        elif topic == "port_street":
            result["observations"] = self.reader.records_by_kind(("mutable_observation",))
            result["limit"] = "Archived observations only. No current Port Street restriction, height clearance, permission or prohibition is determined."
        else:
            result["implemented_checks"] = [CHECK_ID]
            result["not_evaluated"] = UNASSESSED.copy()
        return result

class CheckingService:
    """Each call reads Neo4j afresh. Database errors propagate to the MCP error path."""

    def __init__(self, store=None):
        self.store = store if store is not None else Neo4jStore.from_environment()

    def check(self, arguments):
        normalize(arguments)
        return self.store.read(lambda reader: Evaluation(reader).check(arguments))

    def context(self, topic):
        if topic not in ("summary", "induction", "route_directions", "port_street", "coverage"):
            raise InputError("Unsupported graph topic")
        return self.store.read(lambda reader: Evaluation(reader).context(topic))

    def close(self):
        self.store.close()
