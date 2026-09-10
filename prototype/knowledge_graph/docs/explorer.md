# Connected drayage graph

Current view: [topic organization](graph-organization.md), with 121 connected
nodes. The complete archive still contains 122 records. The 2020 facilities
map is available in the source inventory, outside the main view.

The user's September 6 request is a complete, populated graph to explore, with
the entire graph shown together. The whole-graph view is the default.

Open `output/evidence-graph/index.html` in a browser. It shows all 121 connected public
evidence nodes and all 345 directed relationships, including five quarantined observations with source-provenance links. Fit shows everything; zoom,
drag, and Readable size let the reader inspect the full labels. Selecting a
node highlights its relationships and dims unrelated records without removing them. A native
record selector provides another way to reach any node. Complete records and
an enumeration of all 345 relationships are expandable below the graph.

The preceding September 7 readability revision followed the user's second reference: one
white canvas, small colored dots, compact names outside the nodes, and quiet
arrows. Six colors identify existing record kinds; a legend explains them.
No grouping nodes or taxonomy edges are introduced. Every original node and
arrow remains in the default overview. Relationship labels appear on node
selection or through the all-label toggle. Full labels remain in the selector,
SVG titles, accessibility names and evidence panel. Quarantined observations
retain dashed outlines and visible status labels. The isolate is explicitly
marked “No supported connection.”

Graphviz sfdp, already installed on the authoring machine, generated the saved
positions in `presentation/`. The stdlib exporter checks the topology fingerprint
before reading them; Graphviz is not an export/runtime requirement. Unseen graph
topologies use a clearly identified circular fallback. The optional
`python3 tools/author_graph_layout.py` command regenerates positions if Graphviz
is already available; it never installs packages. A deterministic rectangle
separation pass reserves space for outside labels.

Fit displays the whole topology. At a narrow browser width, fitting 122 labeled
nodes necessarily makes the text small; use Readable size (14px labels at 1:1),
zoom, or the record selector. Fit resets selection and restores all context.
The saved PNG is a whole-graph overview, not a claim that every label is readable
at a 1139px browser fit. See [the independent review](visual-review.md).

`explorer.html` supplies the separate searchable neighborhood view. Searches
include the complete record text. Incoming and outgoing relationships retain
their direction and original attributes; source text and provenance are
available in the detail panel.

## Rebuild

From `prototype/knowledge_graph`:

```sh
python3 export_graph.py
python3 -m unittest discover -s tests -v
```

The exporter verifies all 40 retained archive files before generating outputs.
It requires only the prototype's existing NetworkX and standard-library setup.
It lives outside `kg/*.py` so presentation exports do not alter the service
implementation fingerprint used to replay frozen provider captures.

## Files

- `index.html` and `readable-graph.html`: portable offline whole-graph page; no remote scripts or fetches.
- `readable-graph-preview.png`: latest small-node overview.
- `before-readability-review.png`: previous diagram for comparison.
- `entire-graph.html`: the whole-graph conversation fragment.
- `entire-graph.svg`: full-resolution vector graph, all node labels included.
- `explorer.html`: search and neighborhood inspection.
- `graph-archive.json`: all 122 retained records, including the unlinked map.
- `source-inventory.html`: every source document and its retained record.
- `organized-graph.html`: the current topic-arranged main view.
- `graph.json`: every connected public node, edge, original record, input hash,
  and the list of hash-verified archives.
- `connectivity-audit.json`: every formerly isolated record, added links with
  exact input paths and JSON pointers, and remaining gaps.
- `graph.graphml`: the same graph for graph software. Nested attributes are
  preserved as JSON in `record_json`; parallel-edge IDs are retained.

The export includes all records imported from the nine baseline graph inputs,
plus the retained `traffic_analysis.json` record and explicit-reference links.
See [the connectivity audit](connectivity.md) for the 143 added relationships. It
does not mean every possible drayage law has been collected. This snapshot
excludes the service's synthetic driver/check overlay. No new policy decisions,
active restrictions, real driver records, or trip-clearance conclusions are
introduced. The facilities map remains in `graph-archive.json` and `source-inventory.html`.
The main view excludes it; all 121 visible records belong to one component.

## Verification

The exporter tests verify exact node/edge membership, all nested record values,
GraphML and embedded-JSON round trips, baseline quarantine isolation, provenance-only enriched observation links, SVG node/edge
membership and complete accessibility labels, independent copies, and embedded
source-text escaping. The full suite passed with 108 tests at completion,
including the concurrently completed provider-capture tests. Browser inspection
was blocked by the browser tool's local-file URL policy; interactive rendering
has not been visually verified in that browser. The September 7 SVG was rendered
with the installed `rsvg-convert` and visually inspected as a PNG; this checks
the exported diagram's appearance, not browser interactions.
