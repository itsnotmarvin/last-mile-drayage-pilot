"""MCP schemas and model-facing instructions for the synthetic trip workflow."""

from .trip_models import FACTS_SCHEMA
from .axle_layout import NORMALIZED_SCHEMA as AXLE_VALUE_SCHEMA, REVIEW_SCHEMA as AXLE_REVIEW_SCHEMA


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
COMMON = {"requester_role": ROLE, "question_scope": {**SCOPE,
          "description": "Use trip_dispatch for a complete move to a terminal, including 'Can I use this route with this truck?' when the driver supplies an APM arrival and credential/appointment facts. route is only for an explicitly road-only question excluding terminal entry; mentioning a route does not narrow a complete move. Use terminal_entry for gate-only questions and induction for induction-only questions. Preserve the same scope for corrections."},
          "facts": FACTS_SCHEMA,
          "source_message": {"type": "string", "minLength": 1, "maxLength": 8000,
                             "pattern": "^(?=[\\s\\S]*\\S)[^\\x00]*$",
                             "description": "The user's exact complete synthetic trip message, including qualifications, questions and units; do not summarize it. Never include real identifiers or credentials."},
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

# A complete move has fixed scope; operation branches cannot accept each other's fields.
MOVE_SCHEMA = obj({'action': {'enum': ['create', 'update', 'read']},
                   **{k: v for k, v in COMMON.items() if k != 'question_scope'},
                   'trip_id': TRIP_ID,
                   'expected_revision': UPDATE_SCHEMA['properties']['expected_revision'],
                   'replace_conflicts': UPDATE_SCHEMA['properties']['replace_conflicts']}, ['action'])
MOVE_SCHEMA['oneOf'] = [
    {'properties': {'action': {'const': 'create'}},
     'required': ['facts', 'source_message', 'request_key'],
     'not': {'anyOf': [{'required': [k]} for k in ('trip_id', 'expected_revision', 'replace_conflicts')]}},
    {'properties': {'action': {'const': 'update'}},
     'required': ['trip_id', 'expected_revision', 'requester_role', 'facts', 'source_message', 'request_key']},
    {'properties': {'action': {'const': 'read'}}, 'required': ['trip_id'], 'maxProperties': 2},
]

FACT_RECORD = obj({
    "value": {"anyOf": [{"type": ["string", "number", "boolean", "array", "null"],
              "items": {"type": "number"}}, AXLE_VALUE_SCHEMA]},
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
               "execution_state": {"enum": ["evaluated", "not_implemented", "intake_only", "verification_required"]},
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
              "provenance_review": {"anyOf": [{"type": "null"}, obj({
                  "review_status": STRING, "reviewed_release": STRING, "review_record": STRING,
                  "issue": STRING, "recommended_locator": STRING, "quotation_form": STRING,
                  "note": STRING})]},
              "scope_basis": STRING},
             ["clause_id", "source_id", "publisher", "title", "url", "locator", "source_text",
              "publication_date", "accessed_date", "archived_files", "currentness",
              "authority_entity_id", "verbatim", "scope_basis", "scope_dimensions",
              "archive_graph_eligibility", "interpretation_status", "interpretation_boundary", "named_blocker"])
OBSERVATION = obj({
    "condition_id": STRING, "source_id": STRING, "publisher": STRING, "title": STRING,
    "url": STRING, "publication_date": NULL_STRING, "accessed_date": NULL_STRING,
    "archived_files": SOURCE["properties"]["archived_files"],
    "record": {"type": "object", "additionalProperties": {"$ref": "#/$defs/retained_json"}},
    "currentness": {"const": "archived_observation_not_verified_for_this_trip"},
    "operational_use": {"const": False}})
ROUTE_JURISDICTION = obj({"id": STRING, "kind": STRING, "name": NULL_STRING})
ROUTE_SEGMENT = obj({
    "sequence": {"type": "integer", "minimum": 1},
    "segment_id": STRING, "name": NULL_STRING, "aliases": STRINGS,
    "starts_at": STRING, "starts_at_name": NULL_STRING,
    "ends_at": STRING, "ends_at_name": NULL_STRING,
    "jurisdictions": {"type": "array", "items": ROUTE_JURISDICTION},
    "njogis_categories": STRINGS, "governing_clause_ids": STRINGS,
    "candidate_requirement_ids": STRINGS})
ROUTE_CONTEXT = obj({
    "status": {"enum": ["resolved_from_pinned_graph", "unavailable_route_not_graph_backed",
                        "unavailable_graph_inconsistency"]},
    "route_id": NULL_STRING, "route_kind": NULL_STRING, "route_name": NULL_STRING,
    "graph_release": STRING,
    "segments": {"type": "array", "items": ROUTE_SEGMENT},
    "candidate_requirement_ids": STRINGS, "limits": STRINGS})
STATUS_SOURCE = obj({"page": STRING, "url": STRING, "retrieved_at": STRING,
                       "content_sha256": STRING, "extractor": STRING})
CURRENT_TERMINAL_STATUS = obj({
    "schema_version": {"const": "terminal-status-observation-v1"},
    "status": {"enum": ["available", "unavailable"]},
    "currentness": {"const": "unknown_for_this_trip"},
    "unavailable_reason": NULL_STRING, "terminal_id": STRING, "retrieved_at": STRING,
    "sources": {"type": "array", "items": STATUS_SOURCE},
    "row_closures_text": NULL_STRING, "row_closures_effective": NULL_STRING,
    "gate_status_text": NULL_STRING,
    "gate_indicators": obj({"live_cameras": {"type": "boolean"},
                            "turn_times": {"type": "boolean"},
                            "happiness_index": {"type": "boolean"}}),
    "latest_notice_heading": NULL_STRING, "latest_notice_date": NULL_STRING,
    "closure_notice_text": NULL_STRING, "extractor_version": STRING,
    "freshness_hours": {"type": "integer", "minimum": 1},
    "operational_use": {"const": False}, "limits": STRINGS})
EVIDENCE_PACKAGE = obj({
    "schema_version": {"const": "drayage-trip-evidence-v1"},
    "status": {"enum": ["available", "unavailable"]},
    "sources": {"type": "array", "items": SOURCE},
    "requirement_links": {"type": "array", "items": obj({
        "requirement_id": STRING, "source_clause_ids": STRINGS, "condition_ids": STRINGS})},
    "observations": {"type": "array", "items": OBSERVATION},
    "route_context": {"anyOf": [ROUTE_CONTEXT, {"type": "null"}]},
    "current_terminal_status": {"anyOf": [CURRENT_TERMINAL_STATUS, {"type": "null"}]},
    "port_street_selection": {"enum": ["reported_or_unknown_route_membership", "reported_outside_route",
                                        "outside_requested_scope", "evidence_service_unavailable"]},
    "limits": STRINGS})
ASSESSMENT_SCHEMA["properties"]["evidence_package"] = EVIDENCE_PACKAGE
ASSESSMENT_SCHEMA["required"].append("evidence_package")
EVIDENCE_SCHEMA = obj({"schema_version": {"const": "drayage-requirement-evidence-v1"},
                       "mode": {"const": "synthetic_prototype_only"}, "requirement_id": STRING,
                       "label": STRING, "family": STRING, "catalog_version": STRING,
                       "versions": VERSIONS, "implementation": STRING,
                       "approval_status": {"const": "draft_not_human_approved"},
                       "sources": {"type": "array", "items": SOURCE}, "limits": STRINGS,
                       "observations": {"type": "array", "items": OBSERVATION},
                       "evidence_status": {"enum": ["archived_only", "source_coverage_gap", "prototype_extraction_only"]},
                       "operational_use": {"const": False}})
EVIDENCE_SCHEMA["$defs"] = {"retained_text": {"anyOf": [STRING,
    {"type": "array", "items": {"$ref": "#/$defs/retained_text"}},
    {"type": "object", "additionalProperties": {"$ref": "#/$defs/retained_text"}}]},
    "retained_json": {"anyOf": [{"type": ["string", "number", "boolean", "null"]},
        {"type": "array", "items": {"$ref": "#/$defs/retained_json"}},
        {"type": "object", "additionalProperties": {"$ref": "#/$defs/retained_json"}}]}}
ASSESSMENT_SCHEMA["$defs"] = EVIDENCE_SCHEMA["$defs"]
ASSESSMENT_SCHEMA['properties']['input_review'] = obj({
    'schema_version': {'const': 'drayage-input-review-v1'},
    'text_origin': {'const': 'caller_supplied_not_authenticated_transcript'},
    'consistency_status': {'enum': ['issues_detected', 'no_detected_conflict']},
    'issues': {'type': 'array', 'items': obj({'field': STRING, 'code': STRING, 'message': STRING})},
    'axle_layout': AXLE_REVIEW_SCHEMA,
    'confirmation_status': {'const': 'not_independently_confirmed'},
    'unconfirmed_fields': STRINGS, 'limits': STRINGS})
ASSESSMENT_SCHEMA['properties']['decision_brief'] = obj({
    'schema_version': {'const': 'drayage-decision-brief-v1'}, 'trip_id': TRIP_ID,
    'revision': {'type': 'integer', 'minimum': 1}, 'assessment_id': STRING,
    'status': {'enum': ['assessment_unavailable', 'input_correction_required', 'not_cleared']},
    'headline': STRING, 'summary': STRING, 'operational_permission': {'const': 'not_issued'},
    'scope': SCOPE, 'scoped_result': STATUS,
    'fact_confirmation': {'const': 'not_independently_confirmed'},
    'next_steps': STRINGS, 'limits': STRINGS})
ASSESSMENT_SCHEMA['required'].extend(['input_review', 'decision_brief'])

REPORTED_CHECKS = obj({
    'schema_version': {'const':'drayage-reported-checks-v1'}, 'catalog_version': STRING,
    'engine_version': STRING, 'status': {'enum':['available','unavailable']},
    'approval_status': {'const':'draft_not_human_approved'}, 'operational_permission': {'const':'not_issued'},
    'checks': {'type':'array','items':obj({
        'check_id':STRING,'requirement_id':STRING,'title':STRING,'kind':{'enum':['numeric','prerequisite','manual']},
        'status':{'enum':['manual_review_required','source_review_required','input_review_required','missing_facts','attention_required','comparison_only','reported_unverified']},
        'field_names':STRINGS,'missing_fields':STRINGS,'conflicting_fields':STRINGS,
        'source_clause_ids':STRINGS,'source_text_sha256':VERSIONS,
        'comparison':{'anyOf':[{'type':'null'},obj({'field':STRING,'reported':{'type':'number'},'reference':{'type':'number'},
             'unit':{'enum':['inch','lb']},'relation':{'enum':['above','at','below']},'difference':{'type':'number'}})]},
        'summary':STRING,'context':STRING,'next_action':STRING,'owner':STRING,'reason_codes':STRINGS,
        'reported_inputs':{'type':'array','items':obj({'field':STRING,'value':FACT_RECORD['properties']['value'],
                                                    'unit':FACT_RECORD['properties']['unit']})}})},
    'priority_actions':{'type':'array','maxItems':3,'items':obj({'check_id':STRING,'requirement_id':STRING,'owner':STRING,
         'action':STRING,'status':{'enum':['attention_required','input_review_required','source_review_required']}})},
    'not_run_check_ids':STRINGS,'reason_codes':STRINGS,'limits':STRINGS})
ASSESSMENT_SCHEMA['properties']['reported_fact_checks'] = REPORTED_CHECKS
ASSESSMENT_SCHEMA['required'].append('reported_fact_checks')


from .verification_models import receipt_schema
REJECTED_RECEIPTS = {'type':'array','items':obj({'id':STRING,'kind':STRING,'reason_codes':STRINGS})}
FINDING['properties']['checks'] = {'type':'array','items':obj({'id':STRING,'status':STATUS,'detail':STRING})}
FINDING['properties']['rejected_evidence'] = REJECTED_RECEIPTS
SUPPLEMENT = obj({**{k:STRING for k in ('id','source_id','source_file_path','source_file_sha256','locator','source_text',
                                       'interpretation_boundary','publisher','title','url','graph_release','supplement_sha256')},
                  'requirement_ids':STRINGS,'publication_date':NULL_STRING,'accessed_date':NULL_STRING,
                  'approval_status':{'const':'draft_not_human_approved'},
                  'extraction_status':{'const':'prototype_extraction_only'},
                  'archive_graph_membership':{'const':False},'operational_use':{'const':False}})
for _schema in (EVIDENCE_PACKAGE, EVIDENCE_SCHEMA):
    _schema['properties']['draft_supplements']={'type':'array','items':SUPPLEMENT}
    _schema['required'].append('draft_supplements')
ASSESSMENT_SCHEMA['properties']['verification_evidence']=obj({
    'status':{'enum':['available','unavailable']},'mode':{'const':'synthetic_only'},
    'snapshot_version':STRING,'accepted_receipts':{'type':'array','items':receipt_schema()},
    'rejected_receipts':REJECTED_RECEIPTS,'revoked_ids':STRINGS,'limits':STRINGS})
ASSESSMENT_SCHEMA['required'].append('verification_evidence')


ANSWER_GUIDANCE = obj({
    'schema_version': {'const':'drayage-answer-guidance-v1'}, 'assessment_id':STRING,
    'trip_id':TRIP_ID, 'revision':{'type':'integer','minimum':1},
    'service_status':{'enum':['available','unavailable']}, 'opening':STRING,
    'operational_permission':{'const':'not_issued'},
    'reported_comparisons':{'type':'array','items':obj({
        'check_id':STRING,'requirement_id':STRING,'status':STRING,
        'comparison':REPORTED_CHECKS['properties']['checks']['items']['properties']['comparison'],
        'statement':STRING,'qualification':STRING,'next_action':STRING,'source_clause_ids':STRINGS,
        'claim_type':{'const':'reported_fact_comparison_not_legal_finding'}})},
    'open_requirements':{'type':'array','items':obj({'requirement_id':STRING,'label':STRING,
        'status':{'const':'unresolved'},'missing_fields':STRINGS,'reason_codes':STRINGS,'limits':STRINGS})},
    'historical_context':{'type':'array','items':obj({'condition_id':STRING,'source_id':STRING,
        'archived_at':NULL_STRING,'current_status':{'const':'unknown_for_this_trip'},
        'statement':STRING,'next_action':STRING})},
    'next_questions':{'type':'array','items':QUESTION,'maxItems':3},'boundaries':STRINGS})
ASSESSMENT_SCHEMA['properties']['answer_guidance'] = ANSWER_GUIDANCE
ASSESSMENT_SCHEMA['required'].append('answer_guidance')


MUTATES = {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
READS = {**MUTATES, "readOnlyHint": True}
INSTRUCTIONS = (
    "Assessment tools return a prepared driver answer as the first text block, detailed source briefing second, and full JSON last. Present the prepared answer faithfully with its source links and qualifications; do not add speculative legal conclusions or dates. The full structuredContent and final text block remain available for detailed inspection. "
    "Read answer_guidance first when explaining an assessment: its qualified comparisons and historical currentness are the supported claims. Never turn unresolved into either permission or a finding of illegality. A rough route helps clarify, not verify. "
    "Use assess_driver_move for ordinary complete synthetic driver or dispatcher moves and their corrections. Use assess_trip only for explicitly narrow questions or full evidence inspection. Extract only facts supported by the user's words. "
    "requester_role is who is asking; subject_role is the assessed person (truck_driver or other). Do not infer subject identity from requester. "
    "Drivers and dispatchers use the same workflow and evidence standard. Infer requester_role only when clear; unknown is allowed, so do not require a role-selection step. "
    "Use trip_dispatch for a complete move to APM, including 'can I use this route with this truck' with arrival and credential/appointment facts. Use route only for an explicitly road-only question excluding terminal entry; mentioning a route does not narrow the complete move. Use terminal_entry for gate-only questions, and induction only when explicitly asked. "
    "For a saved-trip follow-up asking about current road/gate conditions, dates, or what findings remain useful, use get_trip_conditions_answer. It freshly reassesses the saved trip and returns a compact answer with citations, without offloading the full assessment into the conversation. Present its links beside the date claims and keep its scope qualifications. "
    "Missing intent stays unknown. Record quantities with explicit units; ask about ambiguous units. Do not invent IDs or dates. "
    "Record the user's supplied road sequence in route_description as well as the matching named route_id. Explicit no-Port-Street statements set port_street_in_route=false; absence from a stored sequence alone does not. "
    "For relative dates, obtain an explicit date/time/timezone before filling trip_at. Leave unavailable facts absent or null. "
    "Use axle_layout only for explicitly supplied individual axle weights and positions measured from the first axle. Never split group totals or infer positions. Legacy axle_weights/axle_spacings remain ambiguous reports. Review input_review.axle_layout for count or gross-weight inconsistencies; its totals are not bridge or legal calculations. "
    "Save the returned trip_id and revision in the conversation. Follow-up facts and explicit corrections to a complete move use assess_driver_move action=update; narrow cases use update_trip_facts. Keep trip IDs and revisions internally, not in the driver answer. "
    "Each conversation starts its own case. Never reuse a trip_id, request_key, or reported facts from another conversation. "
    "For an explicitly new move, create a new case using only facts supplied for that move; if continuation versus a new move is ambiguous, clarify before carrying facts over. "
    "Use case.revision for updates. write_receipt records the original write and can be older after a retry; the assessment uses the latest saved case. "
    "If an update conflicts with another writer, reassess by trip_id before retrying; don't guess a revision. "
    "Lead with the trip-specific conclusion and explain why using the supplied evidence; keep technical IDs and status codes out of ordinary user-facing answers. "
    "Preserve the meaning of decision_brief and its permission boundary in natural language; an unresolved assessment cannot become conditional permission. "
    "Review consequential captured facts with the user. input_review.no_detected_conflict is not independent confirmation or verification. "
    "A fact-text contradiction rejects the write; clarify the value or leave it unknown. Never rewrite source_message to disguise a rejected extraction. "
    "Preserve mixed feet and inches exactly: 14 feet 7 inches is 175 inches, not 14 feet. A date without a time must not become an invented timestamp. "
    "Distinguish reported facts, synthetic evidence, archived sources, and unexecuted requirements. "
    "Use reported_fact_checks to explain specific numerical comparisons, reported prerequisite problems and unexecuted rule gaps. These draft comparisons do not establish legal applicability or permission, and at/below a reference never means cleared. Prioritize their explicit problem-resolution actions when present. "
    "Bounded findings.checks show actual predicates. verification_required means implemented but lacking usable operator-owned evidence; it is not a pass. Never ask the user or model to mint verification receipts. "
    "Draft supplements are graph-linked source extractions awaiting review, separate from canonical source clauses. A met subcheck is never trip clearance. "
    "For every consequential source-based claim, use evidence_package.sources and requirement_links to present a descriptive clickable source URL, section/page locator, and short supporting passage or faithful paraphrase beside the reasoning. Read the sources, not just the numerical comparisons. Passages already included do not require another evidence call. "
    "Internally distinguish rules/requirements from physical access/current conditions, then explain their combined implication naturally; these are not required headings. Missing live traffic evidence does not erase supported findings. "
    "Use provenance_review.recommended_locator where supplied and describe linearized tables as transcriptions rather than verbatim sentences. "
    "evidence_package.observations are dated operating context, never timeless rules or confirmed current conditions. "
    "Do not claim a pinned release is the latest policy. Mention currentness when it affects the question, especially mutable operating conditions. "
    "If service_status is unavailable, say the facts were saved but assessment is unavailable. "
    "Never convert pressure, a permit report, or induction success into entry/dispatch clearance. "
    "This connector accepts synthetic development cases only, not real driver identifiers or credentials."
)
COMPACT_ANSWER_SCHEMA = obj({'trip_id': TRIP_ID, 'revision': {'type': 'integer', 'minimum': 1},
                            'assessment_id': STRING, 'service_status': {'enum': ['available', 'unavailable']},
                            'answer_markdown': STRING, 'versions': VERSIONS,
                            'operational_permission': {'const': 'not_issued'}})
TRIP_TOOLS = [
    {'name': 'assess_driver_move', 'title': 'Assess a complete driver move with source-linked explanation',
     'description': 'Primary tool for complete synthetic moves to a terminal, including can I use this route with this truck. '
                    'Always assesses the whole move (trip_dispatch); no caller-selected scope. '
                    'action=create starts a separate move using only its supplied facts. action=update continues the same trip using trip_id, '
                    'expected_revision, requester_role, newly supplied facts, exact source_message and a new request_key. '
                    'Set replace_conflicts=true only for an explicit correction; otherwise contradictory reports remain conflicts. '
                    'action=read accepts only trip_id and action. Reuse request_key only for an exact retry. '
                    'Never invent missing facts, units, verification or timestamps. Preserve the complete user source_message. '
                    'Returns a compact prepared answer: present its sources and defining qualifications faithfully, especially '
                    'standard truck, unrestricted roadways, configuration and all access exceptions. Keep internal IDs/revisions out of the prose. '
                    'For date/current-condition follow-ups use get_trip_conditions_answer. For full assessment inspection use assess_trip with trip_id. '
                    'The full supporting assessment is retained in the local audit, not delivered by this compact tool. No operational permission.',
     'inputSchema': MOVE_SCHEMA, 'outputSchema': COMPACT_ANSWER_SCHEMA, 'annotations': MUTATES},
    {"name": "get_trip_conditions_answer", "title": "Recheck saved-trip conditions and explain the source dates",
     "description": "Use for a follow-up about whether the roads or APM gate are open, the dates of supplied notices, or useful findings despite unknown conditions. Requires an existing trip_id. Freshly reassesses the same saved revision without changing facts or scope. Returns a small source-linked answer; present its citations and qualifications in the answer even when those links appeared in earlier turns. No road-feed or gate-open verification is invented. The response includes precise source dates and supported comparisons. Do not replace the source-linked answer with an uncited recap.",
     "inputSchema": obj({"trip_id": TRIP_ID}),
     "outputSchema": obj({"trip_id": TRIP_ID, "revision": {"type": "integer", "minimum": 1},
                          "assessment_id": STRING, "service_status": {"enum": ["available", "unavailable"]},
                          "answer_markdown": STRING, "versions": VERSIONS,
                          "operational_permission": {"const": "not_issued"}}),
     "annotations": READS},
    {"name": "assess_trip", "title": "Assess a synthetic driver or dispatcher trip",
     "description": "Full assessment inspection or explicitly narrow questions. For ordinary complete moves and corrections use assess_driver_move. " + INSTRUCTIONS + " Start a new case with facts, source_message and request_key, or reassess an existing case with only trip_id. New cases mutate local state; reassessment reads fresh Neo4j evidence.",
     "inputSchema": CREATE_SCHEMA, "outputSchema": ASSESSMENT_SCHEMA, "annotations": MUTATES},
    {"name": "update_trip_facts", "title": "Update trip facts and reassess the assignment",
     "description": "For complete moves prefer assess_driver_move action=update. This legacy/full-output tool can continue the same synthetic trip using its returned trip_id and expected_revision. Supply only newly reported or corrected facts. Include current requester_role and question_scope. Use replace_conflicts=true only when the user explicitly corrects or reassigns something; updates otherwise retain conflicting reports. A changed assignment invalidates dependent facts. Reports cannot become verification. Returns the committed revision and a fresh assessment; exact request-key retries do not duplicate writes.",
     "inputSchema": UPDATE_SCHEMA, "outputSchema": ASSESSMENT_SCHEMA, "annotations": MUTATES},
    {"name": "get_requirement_evidence", "title": "Explain a requirement with exact retained evidence",
     "description": "Read retained source passages, locators, provenance review notes, publisher, authority, archive dates and limits for a requirement_id returned by assess_trip. Trip assessments already include an evidence_package; use this tool for focused follow-up inspection. Current-route evidence includes a separately labeled dated Port Street observation. Archived evidence is not current policy or credential verification. Empty sources mean an explicit source coverage gap.",
     "inputSchema": obj({"requirement_id": STRING}), "outputSchema": EVIDENCE_SCHEMA, "annotations": READS},
]
