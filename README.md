# Last-Mile Drayage Pilot

This repository is the verified evidence base for a multi-jurisdictional study of inbound truck access to APM Terminals Elizabeth. It preserves authoritative physical-network, jurisdictional, regulatory, and terminal-operational data with source provenance.

The scoped movement is a standard five-axle tractor-semitrailer at 80,000 pounds, carrying nonhazardous cargo inbound to the APM terminal gate. The processed corridor routes are:

- Path A: New Jersey Turnpike Exit 13A, North Avenue, McLester Street, and Tripoli Street. The southbound approach is operator-published; the northbound Exit 13A approach is a centerline-connected candidate and is not truck-route verification.
- Path B: U.S. Route 1 & 9 southbound, North Avenue East, North Avenue, McLester Street, and Tripoli Street.

## Repository role

The repository stores evidence and structured data. The coupled knowledge-graph files are one representation of selected records; they are not the entire project. The current verified visual is `visuals/last_mile_regulation_map.png`, generated from the processed files; its road geometry reproduces the approved reference graphic (`visuals/reference/`) and is schematic, not georeferenced.

`main` contains retained evidence, provenance, minimal validation tooling, and structured records suitable for reuse. Draft extraction, alternate scenarios, exploratory GIS work, and interpretive unresolved research are kept on `fable-audit-review`. A verbatim source clause may remain on `main` with an inert conflict notice only when it is explicitly excluded from couplings, compliance conclusions, and verified visuals.

## Data layout

- `data/metadata.json` — source registry with publishers, dates, URLs, archive paths, and hashes.
- `data/raw/documents/` — archived government, roadway-authority, port, and terminal documents.
- `data/raw/gis/official/` — archived official NJOGIS extracts and service metadata.
- `data/raw/observations/` — archived NJDOT traffic-count observations cited by the source registry.
- `data/processed/vehicle_profiles.json` — the scoped vehicle and movement facts, plus representative drayage truck profiles for rule matching.
- `data/processed/physical_nodes.geojson` — verified route endpoints and intersections.
- `data/processed/physical_edges.json` — ordered, directed roadway corridors for Paths A and B.
- `data/processed/entity_nodes.json` — authorities, jurisdictions, facilities, credentials, and operating systems.
- `data/processed/regulatory_nodes.json` — exact sourced regulatory and operational clauses.
- `data/processed/regulatory_edges.json` — relationships within the regulatory layer.
- `data/processed/coupling_edges.json` — relationships connecting rules and jurisdictions to the scoped vehicle and physical network.
- `data/processed/mutable_conditions.json` — timestamped official-page observations that must be rechecked before operational use and cannot enter the verified graph.
- `data/processed/traffic_analysis.json` — historical station comparison, newer upstream corroboration, corridor operations evidence, limitations, and next-collection requirements.
- `docs/data_dictionary.md` — field definitions and relationship meanings.
- `visuals/last_mile_regulation_map.png` / `.svg` — "Where does regulation concentrate on the last mile?": the coupled rules drawn on the inbound road network, with jurisdiction coverage bands under each road, rules in force at each corridor point, and a roster grouped by governing authority or operator. Every count is computed from `data/processed/`.
- `visuals/last_mile_reference_lines.json` — the road-line geometry the map draws (slide pixels): exact shape coordinates from the editable reference pptx plus curves traced from its export.
- `visuals/reference/` — the approved reference graphic (PNG and editable pptx) and the line-check images comparing the rendered roads with it.
- `tools/validate_records.py` — narrow repository exception for validating source hashes, record counts, references, unresolved-record isolation, mutable-condition isolation, and visual eligibility.
- `experiments/elizabeth-pilot/` — invalidated CLI-based protocol-development pilot retained for provenance; it used the wrong model surface and cannot support the canonical browser-application finding.
- `experiments/elizabeth-browser-pilot/` — canonical Chrome consumer-application pilot using the frozen prompt and rubric with fresh, temporary, private, or signed-out AI sessions; six responses are preserved, independently scored, and adjudicated, while one application was unavailable.

## Evidence standard

- Archived files are identified in `data/metadata.json` and protected by SHA-256 hashes.
- Regulatory `source_text` is preserved verbatim with a source locator.
- Source statements, applicability classifications, and compliance are stored separately.
- A source may support the broader evidence base without appearing in the final graph visual.
- A map or operational page is used only for the type of fact it actually establishes.
- Unsupported or unresolved claims are not presented as verified data.
- Publication, effective, accessed, observed, expiration, and currentness-check dates retain separate meanings.
- A current portal serving an older document proves only what the portal served at the check time; it does not silently update the document's publication date or authority level.
- Mutable bulletins are retained as dated observations, not continuing-validity claims.

## Validation

Run the retention checks from the repository root:

```bash
python3 tools/validate_records.py
```

The validator uses only the Python standard library. It checks every retained archive hash, source and node reference, declared record count, negative permit determination, unresolved-record coupling and visual exclusion, mutable-condition isolation, and the visual manifest.

## Scope limits

The repository characterizes the selected inbound movement. It does not certify a driver, vehicle, cargo, or trip as compliant, and it does not replace current instructions from the relevant government agency, roadway authority, Port Authority, or terminal operator.
