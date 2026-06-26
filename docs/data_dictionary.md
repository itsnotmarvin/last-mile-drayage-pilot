

---

## regulatory_nodes.json

Purpose: Stores extracted state, Port Authority/APM, and federal rules that may affect whether a truck can legally or operationally use a last-mile segment.

Location: data/processed/regulatory_nodes.json

Top-level fields:

| Field | Type | Description |
|---|---|---|
| schema_version | string | Version of this draft schema. |
| description | string | Plain-English description of the file. |
| status | string | Draft/final status. |
| rules | array | List of extracted regulatory rule objects. |

Rule fields:

| Field | Type | Required | Description |
|---|---|---|---|
| rule_id | string | yes | Unique rule ID, such as rule_001. |
| rule_name | string | yes | Short readable name for the rule. |
| jurisdiction | string | yes | Authority level: state, port_authority, federal, or related value. |
| authority | string | yes | Specific authority or publisher, such as NJDOT, PANYNJ, APM Terminals, eCFR/TSA. |
| source_doc | string | yes | Source document name. |
| source_section | string | yes | Section, page, heading, table, or page area where the rule appears. |
| source_url | string | yes | Original live source URL. |
| local_path | string | yes | Local saved copy in the repository. |
| rule_summary | string | yes | Plain-English summary of the rule. |
| vehicle_property_keys | array | yes | Truck/vehicle properties the rule depends on, such as weight, axles, dimensions, engine_model_year, permit_status, twic_status, rfid_status, appointment_status, or load_type. |
| applies_to_segments_or_paths | array | yes | Candidate path(s), segment(s), or location(s) the rule may apply to. |
| compliance_effect | string | yes | What the rule affects: allowed, prohibited, credential_required, appointment_required, permit_required, time_window, etc. |
| confidence | string | yes | high, medium, or low, based on source clarity. |
| notes | string | no | Clarifications, uncertainty, or extraction notes. |

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
