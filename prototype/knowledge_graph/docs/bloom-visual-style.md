# Bloom reference-style view

The saved `Trucker & Dispatch — Knowledge Graph` scene uses Coordinate layout,
with `viz_x` and `viz_y` as its axes, and light Aura theme. Display captions use
`viz_caption`; the unique-values color rule uses `viz_category`. Topic membership
is available as `viz_topic`. These five presentation properties are added only to
144 DrayageRecord nodes in the pinned prototype release. Existing record JSON,
relationships, and release identity are unchanged (verified before and after).

`tools/style_neo4j_bloom.py` reapplies the display properties from the authored
six-topic layout. This is a database write limited to those presentation fields.
The Bloom scene and perspective settings are saved through the Neo4j UI.

The node arrangement follows the reference, with extra prototype records below
terminal entry. Bloom's rendering is not an exact copy of the SVG: its labels
appear according to zoom level, and the six standalone section headings have
not been added. No heading nodes were inserted into the evidence graph.
