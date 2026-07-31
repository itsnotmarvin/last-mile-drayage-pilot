# Last-Mile Drayage Pilot

This repository is the verified evidence base for a multi-jurisdictional study of inbound truck access to APM Terminals Elizabeth. It preserves authoritative physical-network, jurisdictional, regulatory, and terminal-operational data with source provenance.

The scoped movement is a standard five-axle tractor-semitrailer at 80,000 pounds, carrying nonhazardous cargo inbound to the APM terminal gate. The approved processed routes are:

- Path A: New Jersey Turnpike southbound, Exit 13A, North Avenue, McLester Street, and Tripoli Street.
- Path B: U.S. Route 1 & 9 southbound, North Avenue East, North Avenue, McLester Street, and Tripoli Street.

## Repository role

The repository stores evidence and structured data. The coupled knowledge-graph files are one representation of selected records; they are not the entire project. The Friday static visual is produced from the verified data but is not stored here.

`main` contains only retained evidence, provenance, minimal documentation, and structured records suitable for reuse. Draft extraction, alternate scenarios, exploratory GIS work, and unresolved research are kept on `fable-audit-review`.

## Data layout

- `data/metadata.json` — source registry with publishers, dates, URLs, archive paths, and hashes.
- `data/raw/documents/` — archived government, roadway-authority, port, and terminal documents.
- `data/raw/gis/official/` — archived official NJOGIS extracts and service metadata.
- `data/processed/vehicle_profiles.json` — the scoped vehicle and movement facts.
- `data/processed/physical_nodes.geojson` — verified route endpoints and intersections.
- `data/processed/physical_edges.json` — ordered, directed roadway corridors for Paths A and B.
- `data/processed/entity_nodes.json` — authorities, jurisdictions, facilities, credentials, and operating systems.
- `data/processed/regulatory_nodes.json` — exact sourced regulatory and operational clauses.
- `data/processed/regulatory_edges.json` — relationships within the regulatory layer.
- `data/processed/coupling_edges.json` — relationships connecting rules and jurisdictions to the scoped vehicle and physical network.
- `docs/data_dictionary.md` — field definitions and relationship meanings.

## Evidence standard

- Archived files are identified in `data/metadata.json` and protected by SHA-256 hashes.
- Regulatory `source_text` is preserved verbatim with a source locator.
- Source statements, applicability classifications, and compliance are stored separately.
- A source may support the broader evidence base without appearing in the final graph visual.
- A map or operational page is used only for the type of fact it actually establishes.
- Unsupported or unresolved claims are not presented as verified data.

## Scope limits

The repository characterizes the selected inbound movement. It does not certify a driver, vehicle, cargo, or trip as compliant, and it does not replace current instructions from the relevant government agency, roadway authority, Port Authority, or terminal operator.
