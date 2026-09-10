# Independent readability review — September 7, 2026

The user requested a subagent comparison with a sparse biomedical graph. An
independent GPT 5.6 Sol reviewer inspected the old large-circle image, the user
reference and the revised render. Its verdict: “The collision-adjusted revision
is good enough to ship.” It attributed the improvement to small colored nodes,
outside labels, quiet arrows and Graphviz sfdp positioning. It recommended
stopping further spreading because larger bounds shrink everything at fit.

The revision retains all 122 nodes, 345 edges and weak components of sizes
[121, 1]. The remaining dense center reflects real hubs and cross-connections.
The reviewer recommended selected relationship labels, the all-label toggle,
unique short names with complete original labels available, and visible status
for the lone unconnected source. These changes affect presentation only.

The review also recommended at least 9 CSS-pixel aliases at a 1139px fitted view.
**That target is not met by the all-graph fit:** the 2815×1807 world uses 14-unit
labels, which fit to about 5.5 CSS pixels at that width. Readable size and
selector navigation use 1:1 scale. Increasing every label at full fit would
reintroduce collisions. This remains an overview/detail tradeoff, not a passed
legibility claim. Browser interactions were not exercised because local-file
navigation was rejected earlier in this session.

## Verified

- All 101 tests pass, including unchanged frozen provider-capture replay.
- All 40 archived files retain their verified hashes; graph evidence is unchanged.
- Complete node/edge membership and exact original labels remain in the SVG/data.
- Zero intersections among conservative node-plus-label rectangles; no box clipping.
- Unique display aliases; 12-unit-radius dots and 46-unit hit targets at 1:1.
- Every relationship label remains in the SVG, hidden by default and available
  through incident selection or the all-label toggle.
- Reciprocal and parallel relationships have separate curves.
- Saved Graphviz coordinates are matched against node IDs and unordered adjacency.
- Both generated HTML pages pass JavaScript syntax checks. The PNG was visually
  inspected independently; these checks are not a browser interaction test.

## Files

- [Latest graph](../output/evidence-graph/readable-graph.html)
- [Latest overview](../output/evidence-graph/readable-graph-preview.png)
- [Previous overview](../output/evidence-graph/before-readability-review.png)
- `graph_presentation.py`: rendering, palette, topology validation and label spacing.
- `presentation/labels.json`: presentation aliases, separate from evidence records.
- `presentation/*.dot` and `*.json`: source graphs and saved layout coordinates.
- `tools/author_graph_layout.py`: optional authoring command for an existing Graphviz install.
