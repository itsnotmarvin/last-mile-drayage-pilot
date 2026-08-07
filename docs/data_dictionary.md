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
| publication/effective/current/access date | Date supplied by the source or date of access. |
| url | Source page or service. |
| archived_files | Files held in `data/raw/` for the source, each with a `role`, repository `path`, and SHA-256 hash. |

## data/processed/physical_nodes.geojson

Seven canonical route nodes: the two route starts, the Route 1 & 9/North Avenue turn, the shared merge, two shared intersections, and the observed APM entrance coordinate.

Each feature contains `node_id`, `node_type`, `name`, `path_ids`, `incident_edge_ids`, source references, and the coordinate method.

## data/processed/physical_edges.json

Six ordered, directed roadway corridors.

| Field | Meaning |
|---|---|
| paths | Paths A and B with ordered edge IDs and verbatim APM directions. |
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

Contains one project-supplied profile: an inbound, nonhazardous, standard five-axle tractor-semitrailer at 80,000 pounds traveling to APM Terminals Elizabeth. Only supplied facts and their confirmed classifications are stored.

## data/processed/entity_nodes.json

Contains authorities, jurisdictions, the terminal, credentials, registration, operating systems, training, and the four exact NJOGIS jurisdiction-domain values referenced by graph edges.

## data/processed/regulatory_nodes.json

Contains the verified source-text clauses used in the graph.

| Field | Meaning |
|---|---|
| rule_id | Stable rule node key. |
| label | Source section heading or citation. |
| authority_entity_id | Issuing authority node. |
| source_id / source_locator | Exact trace to the source registry and source location. |
| source_text | Verbatim official text or table value. |
| keys_on | Vehicle property categories the rule's text tests: weight, axles, engine_model_year, dimensions, or permit_credential_status. Empty when the rule tests no vehicle property. |
| applicability_status | Separate classification for the scoped movement. |
| matching_scope_facts | Project facts used for that classification. |
| compliance_status | `not_a_compliance_claim`; the graph records requirements and does not assert that a particular driver or vehicle satisfies them. |
| graph_eligibility | Whether the node may appear in the verified visual. |

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

Road-specific couplings include a `road_segment_match` object. It records the official name variants, SRI or shield number, matched feature IDs, and any source-stated intersection offsets used for the deterministic join. Derived coordinates identify the matched extent and state their calculation method; they are not transcribed source text.
Every coupling edge lists its supporting source IDs and source-supported applicability status. Compliance is not inferred.
