# Organize by the questions a reader is trying to answer

The main graph now contains **121 connected nodes and 345 relationships**. The
user approved removing the unlinked 2020 Port Authority facilities map from the
main view. Its original record and archived file remain in the source inventory
and complete archive export. No relationship was deleted. If the map acquires a
relationship, export fails rather than silently hiding that new connection.

Six topic areas give the graph an explicit reading order. The top row follows
vehicle/driver facts, approaches/roads and APM entry. The bottom row groups permit
questions, road rules/jurisdiction and historical traffic context. Topic buttons
zoom to the corresponding area and explain what its records establish and what
remains unchecked. These are presentation annotations, not organizing-principle
nodes, instance-data sections or new knowledge-graph relationships.

The road area places existing route and segment nodes in a schematic of their
recorded approaches and common corridor. Other topics use saved Graphviz layouts.
Selecting a route lists its actual `ordered_edge_ids` in order; selecting any
node lists incident relationships as readable source–verb–target statements.
Source wording is available separately from the relationship explanation. Full
evidence records remain inspectable. Cross-topic arrows are quiet in the overview
and emphasized on node selection; all 345 arrows remain in the SVG.

## Topic membership

| Topic | Nodes | Purpose |
| --- | ---: | --- |
| Vehicle & driver | 11 | Representative profiles, CDL and federal weight records. |
| Approaches & roads | 25 | Route families, approaches, segments, locations and route/geometry sources. |
| Terminal entry | 30 | APM gate, terminal/operator, credentials, entry clauses and cited sources. |
| Permits & dated notices | 13 | Permit clauses and quarantined NJPASS observations. |
| Road rules & jurisdiction | 35 | State/local/toll rules, authorities, jurisdiction and their sources. |
| Historical traffic context | 7 | The retained analysis and its six historical sources. |

Membership is explicit in `presentation/topics.json`. Each visible node appears
exactly once. Placement identifies a reading topic; it does not establish a
legal applicability claim or an exclusive category. The saved layout validates
both graph topology and the topic manifest before use.

## Files and verification

- [Current graph](../output/evidence-graph/organized-graph.html)
- [Whole overview image](../output/evidence-graph/organized-graph-preview.png)
- [Source inventory](../output/evidence-graph/source-inventory.html)
- [Complete retained archive](../output/evidence-graph/graph-archive.json)
- `graph.json` and `graph.graphml`: connected view, 121 nodes / 345 edges.
- `graph-archive.json`: complete retained evidence, 122 nodes / 345 edges.
- `connectivity-audit.json`: audit of the complete retained archive, including its isolate.

All 108 tests pass. Checks preserve the frozen service and provider replay,
validate exclusion without edge loss, test refusal to hide a newly connected
map, partition every visible node exactly once, verify 121 SVG nodes / 345 SVG
edges, check node-label bounds and intersections, and reject stale topic layouts.
The whole SVG was rendered and visually inspected. Both page scripts pass syntax
checks. Browser interactions remain unverified under the earlier local-file
navigation rejection. Full-fit text is still small; topic navigation and zoom
provide detail. Tests establish preservation and layout checks, not a guarantee
that every reader will understand the graph without explanation.
