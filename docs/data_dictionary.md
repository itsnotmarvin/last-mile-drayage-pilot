# Data dictionary

The processed repository represents a coupled property graph with a physical layer, a regulatory layer, and explicit links between them. The static visual reads only the canonical arrays documented below.

## Source-text rule

Regulatory `source_text` values are verbatim transcriptions from the cited source and locator. Applicability and compliance are stored in separate fields. A missing credential, vehicle fact, or observation is not converted into a claim.

## data/metadata.json

Canonical registry for every `source_id` used by the processed graph.

| Field | Meaning |
|---|---|
| source_id | Stable source key referenced by processed records. |
| title | Official or publisher-displayed title. |
| publisher | Issuing body or service. |
| source_type | Official, operational, GIS, code, or third-party observation class. |
| publication/effective/current/access date | Date supplied by the source or date of access. |
| url | Source page or service. |
| locally_archived | Whether the source is held in `data/raw/`. |
| local_path | Archived file path, or null. |
| sha256 | Hash of the archived file, or null. |

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
| official_oneway_raw | Unchanged NJOGIS `ONEWAY` values. |
| jurisdiction_code_raw | Unchanged NJOGIS `JURISDICTN` value. |
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
| GOVERNS_ENTRY_AT / GOVERNS_GATE_MOVE_AT / GOVERNS_ACCESS_AT | The cited requirement applies at the linked entrance node. |
| APPLIES_TO / CLASSIFIES | The rule applies to or classifies the scoped vehicle profile. |
| HAS_NJOGIS_JURISDICTION_CATEGORY | Direct mapping from the edge's raw `JURISDICTN` code. |
| LOCATED_WITHIN | Mechanical all-vertices-in-polygon result using the archived official boundary. |
| OVERLAPS_PART_OF | The exact local code location overlaps only part of the coarser corridor edge. |
Every coupling edge lists its supporting source IDs and source-supported applicability status. Compliance is not inferred.
