

---

## regulatory_nodes.json

Purpose: Stores extracted state, Port Authority/APM, and federal rules that may affect whether a truck can legally or operationally use a last-mile segment.

Location: data/processed/regulatory_nodes.json

Top-level fields:

| Field | Type | Description |
|---|---|---|
| schema_version | string | Version of the clause-consolidated schema. |
| description | string | Plain-English description of the file. |
| status | string | Evidence and analytical status. |
| scope | object | Geographic scope, node grain, and consolidation policies. |
| source_registry | array | One copy of source metadata and the source URL for each logical source. |
| source_count | integer | Number of logical sources in `source_registry`. |
| unique_source_url_count | integer | Number of distinct non-empty source URLs. |
| rules | array | Clause-level regulatory nodes. |
| rule_count | integer | Number of clause-level regulatory nodes. |
| nested_requirement_count | integer | Number of retained atomic requirements across all nodes. |
| requirement_to_rule_index | object | Maps a nested legacy requirement ID to its clause-level `rule_id`. |
| consolidation_summary | object | Before/after counts for the clause-level consolidation. |

Rule fields:

| Field | Type | Required | Description |
|---|---|---|---|
| rule_id | string | yes | Stable ID for the clause-level rule. |
| rule_name | string | yes | Short readable name for the rule. |
| definition | string | yes | Source-grounded definition assembled from the retained proposition(s). |
| source_id | string | yes | Foreign key into `source_registry`; source URLs are not repeated on rules. |
| source_sections | array | yes | Section, page, heading, table, or page area supporting the rule. |
| requirement_count | integer | yes | Number of atomic requirements represented by this node. |
| requirement_ids | array | yes | IDs of the retained atomic requirements. |

---

## vehicle_profiles.json

Purpose: Stores representative drayage truck profiles used later to test which route segments a given truck can legally or operationally use.

Location: data/processed/vehicle_profiles.json

Top-level fields:

| Field | Type | Description |
|---|---|---|
| schema_version | string | Version of this draft schema. |
| description | string | Plain-English description of the file. |
| status | string | Draft/final status. |
| profiles | array | List of representative vehicle profiles. |

Profile fields:

| Field | Type | Required | Description |
|---|---|---|---|
| profile_id | string | yes | Unique profile ID, such as standard_5_axle_drayage_truck. |
| profile_name | string | yes | Human-readable vehicle profile name. |
| description | string | yes | Plain-English description of the truck type. |
| weight_lbs | number or string | yes | Approximate gross vehicle weight or unknown/pending_source. |
| axles | number or string | yes | Number of axles if known. |
| engine_model_year | number or string | yes | Engine model year or category if relevant. |
| dimensions | object | yes | Length, width, height if available or unknown. |
| permit_status | string | yes | Whether OS/OW permit is required, not required, or pending. |
| credential_status | object | yes | TWIC, RFID, SeaLink, appointment, or other credential assumptions. |
| rule_property_keys | array | yes | Properties that link this profile to extracted rules. |
| notes | string | no | Any uncertainty or source notes. |

### vehicle_profiles.json verification fields

| Field | Type | Required | Description |
|---|---|---|---|
| verification_status | string | yes | Explains whether the profile is source-backed, assumed, or pending more evidence. |
| source_evidence | array | yes | List of source-backed evidence for each important profile property. |
| source_evidence.property | string | yes | The profile property being verified, such as weight_lbs, axles, engine_model_year, twic, rfid, or permit_status. |
| source_evidence.value | string/number/object | yes | The value used in the profile. |
| source_evidence.source_doc | string | yes | Source document supporting the value. |
| source_evidence.source_section | string | yes | Page, section, heading, or table supporting the value. |
| source_evidence.rule_ids | array | no | Related rule IDs from regulatory_nodes.json. |

---

## regulatory_nodes.json — additional optional rule fields (added 2026-07-16)

Rules `rule_035` onward may carry these optional fields. Existing rules and fields are unchanged.

| Field | Type | Required | Description |
|---|---|---|---|
| modality | string | no | Language force of the cited text: mandatory, prohibitory, permissive, advisory, descriptive, operational, definitional, reference_only, or a qualified variant (e.g., prohibitory_text_interpretation_unresolved). |
| effective_from | string or null | no | ISO date the provision takes effect, when stated by the source. |
| effective_to | string or null | no | ISO date the provision ends or is superseded, when stated by the source; null when open-ended. |

---

## evidence_findings.json

Purpose: Stores evidence-backed audit findings derived from existing regulatory rules, physical network records, and representative vehicle profiles. A finding records what the current repository supports; it does not make a final legal determination.

Location: data/processed/evidence_findings.json

Top-level fields:

| Field | Type | Required | Description |
|---|---|---|---|
| schema_version | string | yes | Version of the evidence-findings schema. |
| audit_date | string | yes | ISO date of the original repository-only audit. |
| last_updated | string | no | ISO date of the most recent correction or addition. |
| evidence_boundary | string | yes | States that only repository contents were used. |
| contradiction_supported | string | yes | Tri-state: supported, not_determinable, or no_contradiction_verified. |
| contradiction_supported_values | object | no | Definitions of the three states. |
| classification_definitions | object | yes | Definitions of layered, conditional, blocking, unresolved, and potential_contradiction. |
| findings | array | yes | Evidence-backed finding records. |

Finding fields:

| Field | Type | Required | Description |
|---|---|---|---|
| finding_id | string | yes | Stable unique finding identifier. |
| classification | string | yes | One of layered, conditional, blocking, unresolved, or potential_contradiction. |
| title | string | yes | Short human-readable finding title. |
| vehicle_profile_ids | array | yes | Vehicle profiles evaluated; empty only for a structural data finding. |
| path_ids | array | yes | Exact candidate path IDs implicated by the finding. |
| physical_edge_ids | array | yes | Exact physical edge IDs when supported; empty when applicability is only path/area-level. |
| location_scope | string | yes | Human-readable physical scope. |
| rule_ids | array | yes | Regulatory rule IDs supporting the finding. |
| explanation | string | yes | Plain-English explanation of the supported outcome. |
| evidence_files | array | yes | Repository files used to support the finding. |
| applicability_precision | string | yes | One of exact_edge, path, terminal_area, jurisdiction_area, or unresolved. |
| evidence_status | string | yes | One of verified, verified_with_limitation, or unresolved. |
| limitations | array | yes | Known limitations that constrain interpretation. |
| requires_human_review | boolean | yes | Whether authoritative or expert review is required before operational use. |

---

## rule_applicability.json

Purpose: One normalized applicability record per rule in regulatory_nodes.json: modality, actor, action, canonical spatial target, validity interval, per-profile results, and multi-dimensional confidence. Missing values never default to compliant.

Location: data/processed/rule_applicability.json

Top-level fields:

| Field | Type | Required | Description |
|---|---|---|---|
| schema_version | string | yes | Schema version. |
| generated | string | yes | ISO date the file was generated. |
| description | string | yes | Semantics, including the profile_results definitions. |
| evidence_boundary | string | yes | States that only repository contents were used. |
| records | array | yes | One record per rule. |

Record fields:

| Field | Type | Required | Description |
|---|---|---|---|
| rule_id | string | yes | Links to regulatory_nodes.json. |
| provenance_status | string | yes | text_verified or weaker statuses as defined in the provenance audit. |
| currentness | string | yes | current_per_document_text, current_operational, undated_source, or currentness_unresolved. |
| modality | string | yes | Language force (see regulatory_nodes optional fields). |
| actor | string | yes | Who the rule binds: vehicle, driver, carrier, terminal_operator, jurisdictions, road_segment, n_a. |
| action | string | yes | Operative act: gate_entry, gate_entry_timing, registration, road_travel, secure_area_access, permit_trigger, etc. |
| spatial_target | object | yes | target_type (node, path, area), target_ids (canonical IDs), label. |
| circumstance | string | yes | Compliance-effect / operating circumstance carried from the rule record. |
| valid_from / valid_to | string or null | yes | Effective interval when stated by the source. |
| exceptions | array | yes | Express exceptions with the mechanism identified. |
| profile_results | object | yes | profile_id → applies, does_not_apply, or indeterminate. applies = predicate triggered by the profile; does_not_apply = not triggered or non-operative; indeterminate = required property, designation, or current force unknown. |
| applicability_precision | string | yes | exact_edge, path, terminal_area, jurisdiction_area, or unresolved. |
| confidence | object | yes | Separate ratings for text, authority, currentness, spatial. |
| limitations | array | yes | Constraints on interpretation. |

---

## coupling_edges.json

Purpose: Rule-to-physical couplings — the coupling layer of the property graph. Only evidence-supported couplings are recorded; exact-edge couplings are deliberately absent until per-segment designation and jurisdiction evidence exists.

Location: data/processed/coupling_edges.json

Top-level fields:

| Field | Type | Required | Description |
|---|---|---|---|
| schema_version | string | yes | Schema version. |
| generated | string | yes | ISO date generated. |
| description | string | yes | Coupling policy and precision rationale. |
| known_omissions | array | yes | Couplings that cannot yet be made and why. |
| couplings | array | yes | Coupling records. |

Coupling fields:

| Field | Type | Required | Description |
|---|---|---|---|
| coupling_id | string | yes | Stable unique coupling identifier. |
| rule_id | string | yes | Links to regulatory_nodes.json. |
| target_type | string | yes | node, path, edge, or area. |
| target_ids | array | yes | Canonical physical IDs (node_*, anchor_*, path ids, osm_edge_*). |
| relationship | string | yes | governs, requires, denies, or excepts. |
| applicability_predicate | string | yes | Compliance-effect predicate carried from the rule. |
| valid_interval | object | yes | from/to ISO dates or null. |
| circumstance | string | yes | Operative act the coupling concerns. |
| evidence_citation | string | yes | Source document and section supporting the coupling. |
| spatial_precision | string | yes | terminal_area, path, exact_edge, or jurisdiction_area. |
| confidence | string | yes | high, medium, or low. |
| notes | string | no | Limitations. |

---

## route_evaluations.json

Purpose: Profile-by-path evaluation outcomes under the repository-only audit. Records what the evidence supports (classification, blocking rules, unresolved inputs); never a legal conclusion.

Location: data/processed/route_evaluations.json

Top-level fields:

| Field | Type | Required | Description |
|---|---|---|---|
| schema_version | string | yes | Schema version. |
| generated | string | yes | ISO date generated. |
| description | string | yes | Evaluation policy. |
| overall_statement | string | yes | The determinability statement for the contradiction question. |
| evaluations | array | yes | Evaluation records. |

Evaluation fields:

| Field | Type | Required | Description |
|---|---|---|---|
| evaluation_id | string | yes | Stable unique identifier. |
| profile_id | string | yes | Links to vehicle_profiles.json. |
| path_id | string | yes | Canonical candidate path ID. |
| as_of | string | yes | ISO evaluation date. |
| timezone | string | yes | IANA timezone for time-window rules. |
| load_circumstance | string | yes | Load type/circumstance evaluated, or unspecified. |
| per_edge_results | array | yes | Exact-edge results; empty while edge-level coupling is unsupported. |
| per_edge_results_note | string | no | Why per-edge results are empty. |
| gate_result | string | yes | conditional, blocking, or unresolved at the terminal gate. |
| classification | string | yes | Overall: layered, conditional, blocking, unresolved, potential_contradiction, or a compound (e.g., conditional_and_unresolved). |
| rule_ids | array | yes | Rules driving the evaluation. |
| blocking_rule_ids | array | yes | Rules that independently deny the profile. |
| unresolved_inputs | array | yes | Missing facts that prevent a verdict. |
| contradiction_pair_ids | array | yes | pair_ids from rule_pair_evaluations.json meeting the contradiction test; empty when none. |
| explanation | string | yes | Plain-English evidence-based explanation. |
| requires_human_review | boolean | yes | Whether expert/agency review is required. |

---

## rule_pair_evaluations.json

Purpose: Auditable disposition of every rule pair (n choose 2) for the contradiction scan. A pair is potential_contradiction only when both rules are verified and currently applicable and their outcomes are incompatible for the same segment/area, truck property, time, and circumstance.

Location: data/processed/rule_pair_evaluations.json

Top-level fields:

| Field | Type | Required | Description |
|---|---|---|---|
| schema_version | string | yes | Schema version. |
| generated | string | yes | ISO date generated. |
| description | string | yes | Disposition vocabulary and adjudication method. |
| potential_contradictions | array | yes | pair_ids meeting the four-condition test; empty when none. |
| summary_counts | object | yes | Count of pairs per disposition. |
| pairs | array | yes | Pair records. |

Pair fields:

| Field | Type | Required | Description |
|---|---|---|---|
| pair_id | string | yes | Stable unique identifier. |
| left_rule_id / right_rule_id | string | yes | Links to regulatory_nodes.json. |
| disposition | string | yes | compatible, layered, exception_relationship, different_scope, different_time_circumstance, blocking_not_contradictory, unresolved_missing_evidence, or potential_contradiction. |
| rationale | string | yes | Evidence-based reason for the disposition. |
| adjudication | string | yes | hand (individually reviewed) or rule_based_first_pass (documented category logic; reviewable). |

---

## Phase A additions (appended 2026-07-16; earlier sections unchanged)

### scenarios.json

Purpose: Concrete vehicle-movement scenarios binding a representative profile to the full fact set the contradiction test requires (fuel type, engine year, dimensions, weight, credentials, permit status, appointment status, route, timestamp). Unknown facts are recorded as "unresolved" and never default to compliant.

Location: data/processed/scenarios.json

Scenario fields: scenario_id, profile_id, optional profile_variant, fuel_or_powertrain_type, engine_model_year, meets_epa_my2014_standard, dimensions, weight_lbs, axles, credentials (per-credential state), permit_status, appointment_status, load_type, route (path_id, edges, destination), datetime_local (ISO 8601 with offset), optional purpose.

### municipal_rules_verified.json (now populated)

Populated 2026-07-16 from the official Municode publication of the Elizabeth City Code (Supplement 31, codified through Ord. 6138, 2025-06-24). Adds fields beyond the regulatory_nodes base schema: `act` (roadway_operation | parking | registration | terminal_entry — acts are distinct and non-conflicting across categories), and a top-level `corridor_negative_finding` block recording that no corridor street appears in any Elizabeth weight/truck-route exclusion schedule. Municipal rules also appear in regulatory_nodes.json as rule_043–rule_046 so the pair scan covers them.

### physical_edges.json additions

New edges lrs_edge_101–lrs_edge_104 (official NJDOT LRS approach segments: NJ 81 mainline, NJ Turnpike/I-95 at Exit 13A, US 1&9 port-area segment, Rt 81/North Ave ramp complex). New per-edge fields: `network_designation` (national_network: bool, nj_access_network: bool, category, basis — derived from the current N.J.A.C. 16:32 text), `njdot_lrs_sri`, optional `municipal_overlays`, optional `geometry_note` (LRS edges reference geometry in the raw LRS file rather than duplicating it). Jurisdiction values upgraded from OSM-derived labels to `municipal_city_of_elizabeth_per_njdot_lrs` with basis notes. OSM edges keep null from_node/to_node (documented limitation; same-location testing uses street/edge identity).

### rule_applicability.json additions

New per-record fields where relevant: `act` (distinct-act discipline), `legal_addressee` (e.g., container_terminal_facility for PA-10 34-1140, per the actor-separation guardrail), `regulated_actor_or_object`, `outcome`. New currentness values: `current_official_text` (state text with verified force and expiration), `current_confirmed_2026_07_16` (byte-identical live check), `current_per_supplement_31` (municipal code publication currency).

### rule_pair_evaluations.json vocabulary mapping (Phase B)

The Phase B scan uses the taxonomy: compatible, layered, exception_relationship, different_scope, different_time_circumstance, blocking_not_contradictory, unresolved, contradiction_supported. Mapping from the original vocabulary: `unresolved_missing_evidence` → `unresolved`; `potential_contradiction` → `contradiction_supported`. Pair IDs are stable; re-adjudicated pairs carry `adjudication: "phase_b_2026_07_16"` and retain their prior rationale in `prior_rationale` when changed.

### contradiction_conclusion.json

Purpose: The single terminal conclusion of the contradiction analysis. Exactly one of: `contradiction_supported` (with the pair shown side-by-side and all four conditions proven), `no_contradiction_within_scope` (only when every scan cell is resolved), or `not_determinable_named_source_unavailable` (with the exact named blocker). Produced by `src/analyze.py`; no competing conclusion may exist elsewhere in the repository.

### New raw directories

- `data/raw/documents/municipal/` — Elizabeth City Code Title 10 API captures (Supp. 31).
- `data/raw/gis/state/` — official NJDOT LRS corridor extract.
- `data/raw/gis/boundaries/` — NJGIN municipal boundaries (non-legal-boundary disclaimer applies).
