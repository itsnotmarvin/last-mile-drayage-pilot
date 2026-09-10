# Explicit connections added September 7, 2026

The explorer now contains **122 nodes and 345 relationships**. The former graph
had 121 nodes, 202 relationships and 34 isolated records. Explicit retained
references connect 33 of those isolated records. There is one component of 121
nodes and one isolated source: `panynj_facilities_map_2020`. Its geometry-only
use limit does not identify a modeled corridor, so no connection was guessed.

| Added relationship | Count | Evidence and meaning |
| --- | ---: | --- |
| CITES_SOURCE | 99 | Explicit source ID fields, including geometry, directions and archived currentness checks; no independent validation claim. |
| ATTRIBUTED_TO_AUTHORITY | 31 | Each retained clause's authority_entity_id; distinct from source publisher. |
| HAS_RECORDED_RULE_INTERACTION | 6 | Two representative profiles' rule_interactions; not live vehicles or compliance findings. |
| OBSERVED_IN_SOURCE | 5 | Shared source_id in mutable_conditions.json; observations remain quarantined with coupling prohibited. |
| GATE_OF_TERMINAL | 1 | APM gate's terminal_entity_id. |
| RECORDED_OPERATOR | 1 | APM gate's operator_entity_id. |

The extra node preserves `data/processed/traffic_analysis.json` verbatim. It
connects to its six explicitly cited sources. Its historical dates, station
limitations, missing current merge count and unsupported path ranking remain
inspectable. No organizing-principle nodes, instance-data sections, artificial
hub, TYPE_OF links or inferred permissions were added.

`evidence_graph.EvidenceGraph` is a queryable NetworkX graph used by both HTML
views and JSON, GraphML and SVG exports. `kg.graph.KnowledgeGraph` and the checking
service retain their frozen baseline so earlier provider captures still replay.
The enrichment has its own fingerprint over all ten input hashes and its builder
code. Every new edge records the input filename, exact JSON pointer, referenced
ID, relationship meaning and non-operational status. Duplicate source references
for the same endpoints share one edge with multiple evidence pointers.

## Inspect and reproduce

```python
from evidence_graph import EvidenceGraph
kg = EvidenceGraph()
kg.related('node_apm_inbound_gate')
kg.related('representative_older_engine_drayage')
kg.audit()
```

- [Per-record connection audit](../output/evidence-graph/connectivity-audit.json)
- [Entire graph](../output/evidence-graph/index.html)
- [Searchable neighborhood explorer](../output/evidence-graph/explorer.html)
- [Full graph data](../output/evidence-graph/graph.json)

## Verification and limits

All 95 tests pass, including frozen provider-capture replay. New tests check
unchanged baseline records/edges, evidence-pointer resolution, reference target
types, source-only observation links, representative rule references, honest
remaining isolation, deterministic versions and enriched SVG membership. The
adversarial fixture inserts an unknown source ID and gives an entity the map's
ID as its name: the unknown reference is reported and no name-based edge appears.
All 40 archived-file hashes verify. GraphML and embedded JSON preserve records;
both HTML pages pass JavaScript syntax checking. The rebuilt SVG was rendered
and visually inspected. Browser interaction remains unverified because the
browser tool rejected local-file navigation earlier in this session.
