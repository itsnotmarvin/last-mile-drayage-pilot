# Data dictionary

The repository is an evidence base for the scoped inbound drayage movement. The processed files provide a graph-compatible physical layer, regulatory layer, and explicit links between them. The static visual uses selected records from these files; the graph is not the entire evidence collection.

## Source-text rule

Regulatory `source_text` values are verbatim transcriptions from the cited source and locator. Applicability and compliance are stored in separate fields. A missing credential, vehicle fact, or observation is not converted into a claim.

## data/metadata.json

Canonical registry for retained source evidence. Some sources support the broader study without producing a node or edge in the static visual.

| Field | Meaning |
|---|---|
| source_id | Stable source key referenced by processed records. |
| title | Official or publisher-displayed title. |
| publisher | Issuing body or service. |
| source_type | Official, operational, GIS, code, or third-party observation class. |
| publication_date | Date or month displayed by the published source; never replaced by a later access date. |
| effective_date / amendments_effective_date / readoption_effective_date | Source-stated date on which a tariff, rule, amendment, or readoption takes effect. |
| expiration_date | Source-stated sunset or expiration date; it does not by itself prove that no intervening amendment or repeal occurred. |
| accessed_date | Calendar date on which the repository retrieved or accessed the source. `retrieval_date` is deprecated. |
| observed_at | Timestamp at which mutable webpage content was observed. |
| currentness_check.checked_at | Timestamp of a separate point-in-time currentness check. |
| currentness_check.status / verification_basis / verification_limit | What the check established, the evidence used, and what it did not establish. A live portal link is publication-currency evidence, not an authority upgrade. |
| url | Source page or service. |
| archived_files | Files held in `data/raw/` for the source, each with a `role`, repository `path`, and SHA-256 hash. |

## data/processed/physical_nodes.geojson

Ten canonical route nodes: the original route starts and intersections, plus the northbound Exit 13A start, authority-to-state ramp transition, and North Avenue approach merge.

Each feature contains `node_id`, `node_type`, `name`, `path_ids`, `incident_edge_ids`, source references, and the coordinate method.

## data/processed/physical_edges.json

Nine ordered, directed roadway corridors. Path A has a default operator-published southbound approach and a candidate northbound approach assembled from directed official centerlines.

| Field | Meaning |
|---|---|
| paths | Paths A and B with ordered edge IDs and verbatim APM directions. |
| approaches | Direction-specific Path A realizations, verification status, and ordered edge IDs. The northbound approach is explicitly marked as not truck-route verified. |
| edges | Canonical roadway corridors. |
| from_node / to_node | Directed physical topology. |
| official_feature_ids | NJOGIS road-centerline features used by the corridor. |
| official_list_names | Exact `LST_PNAME` name variants from the archived NJOGIS features. |
| official_sri_ids | Exact NJOGIS Standard Route Identifiers (`SRI`) used by the corridor. |
| official_shield_types_raw / official_shield_numbers_raw | Unchanged NJOGIS route-shield attributes used for route-number joins. |
| official_oneway_raw | Unchanged NJOGIS `ONEWAY` values. |
| jurisdiction_code_raw | Unchanged NJOGIS `JURISDICTN` value. |
| official_nhs_designations | Federal National Highway System status for the edge from the archived current FHWA shapefile extract: raw code, FHWA's official code meaning, and the deterministic match basis. Edges absent from the FHWA data carry no designation record. |
| geometry_reference | Archived source path, endpoints, and topology method. |
| sequence_source_id | APM source supporting street order. |

`FT` means travel from the source feature start node to end node, `B` means travel in both directions, and `TF` means travel from end node to start node, exactly as decoded by the NJOGIS layer schema.

## data/processed/vehicle_profiles.json

Contains three profiles. The scoped profile is project-supplied — an inbound, nonhazardous, standard five-axle tractor-semitrailer at 80,000 pounds traveling to APM Terminals Elizabeth — and stores only supplied facts and their confirmed classifications; its `properties_not_supplied` field lists rule-keyed properties that were never supplied. These now include axle and axle-group weights, axle spacing, dimensions, engine and fuel type, DTR verification, divisibility and seal status, permit status, and trip timing. Gross weight and axle count alone do not establish bridge-formula, dimensional, permit, or route-specific compliance. The two representative profiles (older-engine drayage, OS/OW ocean container) are defined constructs for rule-to-profile matching: their `defined_facts` are values chosen from thresholds in extracted rules, not observations, and each `rule_interactions` entry restates what the cited rule's text says about the defined value. Their interactions do not inherit the canonical profile's applicability status. No profile record is a compliance claim.

## data/processed/entity_nodes.json

Contains authorities, jurisdictions, the terminal, credentials, registration, operating systems, training, and the four exact NJOGIS jurisdiction-domain values referenced by graph edges.

## data/processed/regulatory_nodes.json

Contains retained exact source-text clauses. Verified graph records, currentness-limited reference text, and interpretively unresolved text are distinguished by `applicability_status` and `graph_eligibility`; not every retained clause may enter the graph or visual.

| Field | Meaning |
|---|---|
| rule_id | Stable rule node key. |
| label | Source section heading or citation. |
| authority_entity_id | Issuing authority node. |
| source_id / source_locator | Exact trace to the source registry and source location. |
| source_text | Verbatim official text or table value. |
| keys_on | Rule-key categories tested by the text. Current values include weight, axles, axle_weights, axle_spacings, engine_model_year, fuel_powertrain_type, dimensions, container_seal_status, load_divisibility, trip_timing, route_geometry, and permit_credential_status. Empty when the rule tests no profile or trip property. |
| applicability_status | Separate classification for the scoped movement. |
| matching_scope_facts | Project facts used for that classification. |
| applicability_profile_id | Profile to which the applicability classification applies when explicit disambiguation is needed. |
| required_profile_facts / missing_profile_facts | Facts needed for a vehicle- or trip-level determination and the subset absent from the named profile. |
| currentness_limit | Boundary on use of exact source text whose official current code-of-record status was not fully verified. |
| interpretation_status / interpretation_boundary / named_blocker | Bounded handling for genuine source-text tensions. These fields preserve uncertainty and cannot establish denial, compliance, contradiction, enforcement, or route feasibility. |
| compliance_status | `not_a_compliance_claim`; the graph records requirements and does not assert that a particular driver or vehicle satisfies them. |
| graph_eligibility | Whether the node may appear in the verified visual. |

The three exact N.J.A.C. 13:18 nodes from the rule copy currently served by NJPASS are excluded from verified visuals because the PDF metadata dates to 2010 and the official code of record was not independently compared. PA-10 Subrule 34-1140 preserves all three deadline blocks verbatim but is also excluded: its clause (c) remains internally unreconciled with the retained diesel DTR registration pathway in Subrule 34-1101.

## data/processed/regulatory_edges.json

Relationships within the regulatory layer, including authority-to-rule, rule-to-credential, and rule-to-operational-system edges. These edges do not assign rules to roads.

## data/processed/coupling_edges.json

Links rules and jurisdictions to physical corridors, the observed APM entrance node, or the scoped vehicle.

| Relationship | Meaning |
|---|---|
| GOVERNS | The cited rule applies to the linked roadway corridor. |
| GOVERNS_ENTRY_AT / GOVERNS_GATE_MOVE_AT / GOVERNS_ACCESS_AT / GOVERNS_PORT_ENTRY_MOVEMENT_AT / GOVERNS_UNESCORTED_SECURE_ACCESS_AT | The cited requirement applies at the linked entrance node. |
| APPLIES_TO / CLASSIFIES | The rule applies to or classifies the scoped vehicle profile. |
| HAS_NJOGIS_JURISDICTION_CATEGORY | Direct mapping from the edge's raw `JURISDICTN` code. |
| LOCATED_WITHIN | Mechanical all-vertices-in-polygon result using the archived official boundary. |
| OVERLAPS_PART_OF | The exact local code location overlaps only part of the coarser corridor edge. |
| ROUTE_NUMBER_NOT_LISTED_IN_APPENDIX_C | The edge's raw NJOGIS shield number was compared with the route numbers printed in N.J.A.C. 16:32 Appendix C and was absent. This relationship records network classification only, not a truck prohibition. |
| STREET_NOT_LISTED_IN_RESTRICTION_TABLE | The edge's official street-name variants were compared with every street name in the cited restriction table and were absent. This relationship records absence from the table only, not a permission grant. |
| TRUCK_ROUTE_SCHEDULE_RESERVED | The cited authority's truck-route designation schedule contains no entries ("Reserved"). This relationship records the authority's designation status for the linked corridor only, not a restriction or permission. |

Road-specific couplings include a `road_segment_match` object. It records the official name variants, SRI or shield number, matched feature IDs, and any source-stated intersection offsets used for the deterministic join. Derived coordinates identify the matched extent and state their calculation method; they are not transcribed source text.
Every coupling edge lists its supporting source IDs and source-supported applicability status. Compliance is not inferred.

The Elizabeth 10.16.050 relationship remains `OVERLAPS_PART_OF` with `confirmed_geographic_overlap_only`. It does not authorize entry into the Port Authority overweight corridor. The former `couple_terminal_weight_gate` relationship was removed because PA-10 34-045 and 34-046 govern designated Marine Terminal Highways, while the retained sources do not lock that scope to the APM gate node. No NJ public-road permit-to-PANYNJ-zone authorization relationship is stored.

## data/processed/mutable_conditions.json

Timestamped source-text observations from mutable official pages. `source_stated_duration_text` preserves wording such as "until further notice" without turning it into a continuing boolean. Every file-level and record-level status prevents these observations from entering coupling edges or verified visuals, and `must_recheck_before_any_operational_use` is always true.

## visuals/visual_manifest.json

Lists the record IDs and relationship counts represented by each retained evidence visual. A visual with invalidated representations is marked stale and cannot be the `current_verified_artifact_id`. The retained primary graphic is currently stale because it places PA-10 34-046 at the gate and reports the retired 102-edge coupling count.

## tools/validate_records.py

Standard-library validation for archive hashes, count fields, unique IDs, source and graph references, canonical-profile negative determinations, missing-fact declarations, complete PA-10 34-1140 block retention, exclusion of unresolved records from couplings and visual manifests, mutable-condition isolation, and visual-manifest consistency.

## data/processed/traffic_analysis.json

Source-triangulated traffic evidence for the inbound North Avenue corridor. The file separates the historical same-year station comparison from later corroborating evidence so publication date, count year, location, and method are not conflated.

| Field | Meaning |
|---|---|
| station_comparison | 2018 NJDOT comparison between upstream station 3-3-024 and station 182001 immediately before the complete approach merge. |
| latest_upstream_corroboration | Published 2020–2022 records plus the 2024 annual-file record at station 3-3-024, with comparisons to the 2018 upstream median and 2022 value. |
| current_public_data_check | Result of checking the official 2024 annual AADT file for stations 3-3-024 and 182001, with the boundary that NJDOT's current interactive system still requires manual review. |
| corridor_operations_cross_check | City of Elizabeth seven-day and turning-movement count program, LOS findings, and pandemic-adjustment qualification. |
| county_context_cross_check | Union County's identification of the 29,973-AADT CR 624 segment as the highest-volume county roadway in its inventory. |
| secondary_cross_check | FHWA HPMS segment comparison, retained as directional evidence rather than an exact station validation. |
| decision | Supported monitoring implication and explicit statement that a path ranking is not yet supported. |
| limitations | Location, year, method, truck-classification, and gate-delay constraints that bound the findings. |
| next_collection | Measurements required to produce current truck-specific reliability and path-ranking metrics. |
