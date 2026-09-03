# Last-Mile Drayage Pilot

This repository is the verified evidence base for a multi-jurisdictional study of inbound truck access to APM Terminals Elizabeth. It preserves authoritative physical-network, jurisdictional, regulatory, and terminal-operational data with source provenance.

The scoped movement is a standard five-axle tractor-semitrailer at 80,000 pounds, carrying nonhazardous cargo inbound to the APM terminal gate. The approved processed routes are:

- Path A: New Jersey Turnpike southbound, Exit 13A, North Avenue, McLester Street, and Tripoli Street.
- Path B: U.S. Route 1 & 9 southbound, North Avenue East, North Avenue, McLester Street, and Tripoli Street.

## Repository role

The repository stores evidence and structured data. The coupled knowledge-graph files are one representation of selected records; they are not the entire project. The current verified visual is `visuals/last_mile_regulation_map.png`, generated from the processed files; its road geometry reproduces the approved reference graphic (`visuals/reference/`) and is schematic, not georeferenced.

`main` contains only retained evidence, provenance, minimal documentation, and structured records suitable for reuse. Draft extraction, alternate scenarios, exploratory GIS work, and unresolved research are kept on `fable-audit-review`.

## Data layout

- `data/metadata.json` — source registry with publishers, dates, URLs, archive paths, and hashes.
- `data/raw/documents/` — archived government, roadway-authority, port, and terminal documents.
- `data/raw/gis/official/` — archived official NJOGIS extracts and service metadata.
- `data/processed/vehicle_profiles.json` — the scoped vehicle and movement facts, plus representative drayage truck profiles for rule matching.
- `data/processed/physical_nodes.geojson` — verified route endpoints and intersections.
- `data/processed/physical_edges.json` — ordered, directed roadway corridors for Paths A and B.
- `data/processed/entity_nodes.json` — authorities, jurisdictions, facilities, credentials, and operating systems.
- `data/processed/regulatory_nodes.json` — exact sourced regulatory and operational clauses.
- `data/processed/regulatory_edges.json` — relationships within the regulatory layer.
- `data/processed/coupling_edges.json` — relationships connecting rules and jurisdictions to the scoped vehicle and physical network.
- `data/processed/mutable_conditions.json` — timestamped observations from mutable official pages, isolated from couplings and verified visuals.
- `data/processed/traffic_analysis.json` — NJDOT station comparison, upstream corroboration, corridor operations evidence, limitations, and next-collection requirements.
- `data/raw/observations/` — archived NJDOT traffic-count observations cited by the source registry.
- `docs/data_dictionary.md` — field definitions and relationship meanings.

## Visual

- `visuals/last_mile_regulation_map.png` / `.svg` — "Where does regulation concentrate on the last mile?": the coupled rules drawn on the inbound road network, with jurisdiction coverage bands under each road, rules in force at each corridor point, and a roster of the coupled records grouped by governing authority or operator. Every count is computed from `data/processed/`.
- `visuals/last_mile_reference_lines.json` — the road-line geometry the map draws (slide pixels): exact shape coordinates from the editable reference pptx plus curves traced from its export.
- `visuals/reference/` — the approved reference graphic (PNG and editable pptx) and the line-check images comparing the rendered roads with it.

## Evidence standard

- Archived files are identified in `data/metadata.json` and protected by SHA-256 hashes.
- Regulatory `source_text` is preserved verbatim with a source locator.
- Source statements, applicability classifications, and compliance are stored separately.
- A source may support the broader evidence base without appearing in the final graph visual.
- A map or operational page is used only for the type of fact it actually establishes.
- Unsupported or unresolved claims are not presented as verified data.

## Scope limits

The repository characterizes the selected inbound movement. It does not certify a driver, vehicle, cargo, or trip as compliant, and it does not replace current instructions from the relevant government agency, roadway authority, Port Authority, or terminal operator.
