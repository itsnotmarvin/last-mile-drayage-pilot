"""MCP schemas and model-facing instructions for the synthetic trip workflow."""

from .trip_models import FACTS_SCHEMA


def obj(properties, required=None):
    return {"type": "object", "additionalProperties": False, "properties": properties,
            "required": list(properties) if required is None else required}


STRING = {"type": "string"}
STRINGS = {"type": "array", "items": STRING}
NULL_STRING = {"type": ["string", "null"]}
ROLE = {"type": "string", "enum": ["driver", "dispatcher", "other", "unknown"]}
SCOPE = {"type": "string", "enum": ["induction", "terminal_entry", "route", "trip_dispatch", "unknown"]}
TRIP_ID = {"type": "string", "pattern": "^syn-trip-[a-f0-9]{32}$"}
REQUEST_KEY = {"type": "string", "minLength": 1, "maxLength": 120,
               "pattern": "^(?=.*\\S)[^\\x00-\\x1f]+$",
               "description": "Unique synthetic request token. Reuse exactly for retries; a different update needs a new token."}
COMMON = {"requester_role": ROLE, "question_scope": SCOPE,
          "facts": FACTS_SCHEMA,
          "source_message": {"type": "string", "minLength": 1, "maxLength": 8000,
                             "pattern": "^(?=[\\s\\S]*\\S)[^\\x00]*$",
                             "description": "The user's synthetic trip statement, preserving qualifications and units. Never include real identifiers or credentials."},
          "request_key": REQUEST_KEY}
CREATE_SCHEMA = obj({**COMMON, "trip_id": TRIP_ID}, [])
CREATE_SCHEMA["oneOf"] = [
    {"required": ["request_key", "source_message", "facts"], "not": {"required": ["trip_id"]}},
    {"required": ["trip_id"], "maxProperties": 1}]
UPDATE_SCHEMA = obj({**COMMON, "trip_id": TRIP_ID,
                     "expected_revision": {"type": "integer", "minimum": 1},
                     "replace_conflicts": {"type": "boolean", "default": False,
                       "description": "True only for an explicit user correction or reassignment. Correct one independent existing field per call; fresh dependent facts for its replacement may be included. Otherwise contradictory reports remain conflicts."}},
                    [*COMMON, "trip_id", "expected_revision"])

FACT_RECORD = obj({
    "value": {"type": ["string", "number", "boolean", "array", "null"],
              "items": {"type": "number"}},
    "unit": {"enum": ["lb", "inch", None]}, "basis": {"const": "user_reported"},
    "reported_by": ROLE, "source_text": STRING, "recorded_at": STRING})
CONFLICT = obj({"field": STRING, "observations": {"type": "array", "items": FACT_RECORD},
                "detected_at": STRING, "revision": {"type": "integer", "minimum": 1}})
CASE = obj({"trip_id": TRIP_ID, "revision": {"type": "integer", "minimum": 1},
            "requester_role": ROLE, "question_scope": SCOPE,
            "facts": obj({k: FACT_RECORD for k in FACTS_SCHEMA["properties"]}, []),
            "invalidated_fields": STRINGS, "conflicts": {"type": "array", "items": CONFLICT},
            "mode": {"const": "synthetic_prototype_only"}})
STATUS = {"type": "string", "enum": ["met", "not_met", "unresolved", "not_applicable"]}
FINDING = obj({"requirement_id": STRING, "label": STRING, "family": STRING, "owner": STRING,
               "status": STATUS,
               "execution_state": {"enum": ["evaluated", "not_implemented", "intake_only"]},
               "reason_codes": STRINGS, "missing_fields": STRINGS, "conflicting_fields": STRINGS,
               "verification_needed": STRINGS, "reported_absences": STRINGS,
               "source_clause_ids": STRINGS, "evidence_ids": STRINGS,
               "evidence_basis": STRING, "limits": STRINGS})
QUESTION = obj({"field": STRING, "question": STRING, "owner": STRING,
                "reason": STRING, "requirement_ids": STRINGS, "kind": STRING})
VERSIONS = {"type": "object", "additionalProperties": {"type": "string"}}
ASSESSMENT_SCHEMA = obj({
    "schema_version": {"const": "drayage-trip-assessment-v1"},
    "mode": {"const": "synthetic_prototype_only"}, "case": CASE, "versions": VERSIONS,
    "write_receipt": {"anyOf": [{"type": "null"}, obj({"trip_id": TRIP_ID, "revision": {"type": "integer", "minimum": 1}})]},
    "assessment_id": STRING, "service_status": {"enum": ["available", "unavailable"]},
    "requested_scope_status": STATUS, "operational_status": {"const": "unresolved_not_assessed"},
    "findings": {"type": "array", "items": FINDING},
    "coverage": obj({"complete_trip_check": {"const": False}, "catalog_complete": {"const": False},
                     "selected_requirements": STRINGS, "executed_requirements": STRINGS,
                     "not_executed_requirements": STRINGS, "gaps": STRINGS}),
    "next_questions": {"type": "array", "items": QUESTION, "maxItems": 3}, "limits": STRINGS})
SOURCE = obj({"clause_id": STRING, "source_id": STRING, "publisher": STRING, "title": STRING,
              "url": STRING, "locator": STRING, "source_text": {"$ref": "#/$defs/retained_text"},
              "publication_date": NULL_STRING, "accessed_date": NULL_STRING,
              "archived_files": {"type": "array", "items": obj({"path": STRING, "role": STRING, "sha256": STRING})},
              "currentness": STRING, "extraction_status": STRING,
              "authority_entity_id": NULL_STRING, "verbatim": {"type": ["boolean", "null"]},
              "scope_dimensions": STRINGS, "archive_graph_eligibility": NULL_STRING,
              "interpretation_status": NULL_STRING, "interpretation_boundary": NULL_STRING,
              "named_blocker": NULL_STRING,
              "scope_basis": STRING},
             ["clause_id", "source_id", "publisher", "title", "url", "locator", "source_text",
              "publication_date", "accessed_date", "archived_files", "currentness",
              "authority_entity_id", "verbatim", "scope_basis", "scope_dimensions",
              "archive_graph_eligibility", "interpretation_status", "interpretation_boundary", "named_blocker"])
EVIDENCE_SCHEMA = obj({"schema_version": {"const": "drayage-requirement-evidence-v1"},
                       "mode": {"const": "synthetic_prototype_only"}, "requirement_id": STRING,
                       "label": STRING, "family": STRING, "catalog_version": STRING,
                       "versions": VERSIONS, "implementation": STRING,
                       "approval_status": {"const": "draft_not_human_approved"},
                       "sources": {"type": "array", "items": SOURCE}, "limits": STRINGS,
                       "evidence_status": {"enum": ["archived_only", "source_coverage_gap"]},
                       "operational_use": {"const": False}})
EVIDENCE_SCHEMA["$defs"] = {"retained_text": {"anyOf": [STRING,
    {"type": "array", "items": {"$ref": "#/$defs/retained_text"}},
    {"type": "object", "additionalProperties": {"$ref": "#/$defs/retained_text"}}]}}

MUTATES = {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
READS = {**MUTATES, "readOnlyHint": True}
INSTRUCTIONS = (
    "Use assess_trip for ordinary synthetic driver or dispatcher trip questions. Extract only facts supported by the user's words. "
    "requester_role is who is asking; subject_role is the assessed person (truck_driver or other). Do not infer subject identity from requester. "
    "Use trip_dispatch for 'can I take/send this truck', terminal_entry for gate-only questions, and induction only when explicitly asked. "
    "Missing intent stays unknown. Record quantities with explicit units; ask about ambiguous units. Do not invent IDs or dates. "
    "For relative dates, obtain an explicit date/time/timezone before filling trip_at. Leave unavailable facts absent or null. "
    "Save the returned trip_id and revision in the conversation. Follow-up answers and explicit corrections use update_trip_facts. "
    "Use case.revision for updates. write_receipt records the original write and can be older after a retry; the assessment uses the latest saved case. "
    "If an update conflicts with another writer, reassess by trip_id before retrying; don't guess a revision. "
    "Lead with the scoped finding and the most relevant next questions; keep technical IDs out of ordinary user-facing answers. "
    "Distinguish reported facts, synthetic evidence, archived sources, and unexecuted requirements. "
    "If service_status is unavailable, say the facts were saved but assessment is unavailable. "
    "Never convert pressure, a permit report, or induction success into entry/dispatch clearance. "
    "This connector accepts synthetic development cases only, not real driver identifiers or credentials."
)
TRIP_TOOLS = [
    {"name": "assess_trip", "title": "Assess a synthetic driver or dispatcher trip",
     "description": INSTRUCTIONS + " Start a new case with facts, source_message and request_key, or reassess an existing case with only trip_id. New cases mutate local state; reassessment reads fresh Neo4j evidence.",
     "inputSchema": CREATE_SCHEMA, "outputSchema": ASSESSMENT_SCHEMA, "annotations": MUTATES},
    {"name": "update_trip_facts", "title": "Update trip facts and reassess the assignment",
     "description": "Continue the same synthetic trip using its returned trip_id and expected_revision. Supply only newly reported or corrected facts. Include current requester_role and question_scope. Use replace_conflicts=true only when the user explicitly corrects or reassigns something; updates otherwise retain conflicting reports. A changed assignment invalidates dependent facts. Reports cannot become verification. Returns the committed revision and a fresh assessment; exact request-key retries do not duplicate writes.",
     "inputSchema": UPDATE_SCHEMA, "outputSchema": ASSESSMENT_SCHEMA, "annotations": MUTATES},
    {"name": "get_requirement_evidence", "title": "Explain a requirement with exact retained evidence",
     "description": "Read the exact source passage, locator, publisher, authority, archive dates and limits for a requirement_id returned by assess_trip. Archived evidence is not a current policy or credential verification. Empty sources mean an explicit source coverage gap.",
     "inputSchema": obj({"requirement_id": STRING}), "outputSchema": EVIDENCE_SCHEMA, "annotations": READS},
]
