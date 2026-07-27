

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
