# last-mile-drayage-pilot
> A reproducible pilot characterizing the multi-jurisdictional regulatory structure of the
> "last mile" drayage path from the NJDOT-designated truck network to the APM Terminals
> Elizabeth gate, Port of New York & New Jersey.

**Status:** in progress
**Author:** Marvin Ayala
**Supervisor:** Dr. Dan Liu, Kean University
**Contributors:** [assistant initials/roles — no personal details in a public repo]
**Last updated:** Friday, June 19, 2026. 10:24am.

---

## What this is

This repository builds a **coupled physical–regulatory property graph** for one drayage
"last mile" and uses it to characterize where rules from different jurisdictions (NJDOT /
state, municipal, Port Authority, county) layer, conflict, or leave gaps along the path a
truck must travel from the state truck network to the terminal gate.

> **A note on terminology.** What this pilot builds is a *coupled property graph* — nodes,
> edges, and attributes that can be queried and analyzed. It is **not** a full knowledge graph
> in the formal sense (no ontology with logical semantics, no automated reasoning/inference).
> Building the formal knowledge graph with reasoning is future work, not part of this pilot.
> Please keep this distinction accurate in any writeup.

The deliverable is **reproducibility**: someone who was not on the project should be able to
rebuild the coupled graph and arrive at the same finding from this repository alone, using
only the steps in the "How to reproduce" section below.

---

## The finding (fill in when complete)

> A compliant drayage truck traveling from [state-network access point] to the APM Elizabeth
> gate traverses **N** segments across **[3]** jurisdictions. Of these, **K** are not
> municipally designated truck routes despite being the only viable path, and **J** exhibit
> conflicting, ambiguous, or undocumented governing rules.

See `findings/findings.md` for the full characterization and worked examples.

---

## Repository structure

```
.
├── README.md                       ← you are here
├── data/
│   ├── raw/                        ← source material exactly as collected
│   │   ├── documents/              ← rule PDFs/HTML by jurisdiction
│   │   ├── gis/                    ← roadway/centerline files
│   │   └── field/                  ← signage photos (SEE PRIVACY NOTE)
│   ├── processed/                  ← structured outputs (the graph data)
│   │   ├── physical_nodes.geojson
│   │   ├── physical_edges.json
│   │   ├── regulatory_nodes.json
│   │   ├── regulatory_edges.json
│   │   ├── coupling_edges.json
│   │   └── municipal_rules_verified.json
│   └── metadata.json               ← provenance for every source
├── src/                            ← scripts that build/analyze the graph
│   ├── build_graph.py
│   ├── trace_route.py
│   └── analyze.py
├── docs/
│   ├── schema.md                   ← node/edge type definitions
│   ├── data_dictionary.md          ← every field, every file, explained
│   └── provenance_audit.md         ← confirms every record traces to a source
├── benchmark/
│   └── benchmark.json              ← validation questions + expert answers
├── findings/
│   ├── findings.md                 ← the characterization + worked examples
│   └── figures/
└── preliminary_results.md          ← proposal-ready memo
```

---

## How to reproduce

> The goal: a clean checkout of this repo plus the steps below should regenerate the coupled
> graph and the route-trace finding. Fill in real commands as the pipeline is built.

**Prerequisites**
- Python [version]
- Packages: [list — e.g., geopandas, networkx, shapely]. Install: `pip install -r requirements.txt`

**Steps**
1. **Inspect raw data.** Source documents, GIS, and field records are in `data/raw/`.
   Provenance for each is in `data/metadata.json`.
2. **Build the coupled graph:** `python src/build_graph.py`
   - Reads `data/processed/*` and assembles the two-layer coupled property graph.
   - Output: `[graph artifact path]`
3. **Trace the last-mile route(s):** `python src/trace_route.py`
   - Traces the viable path(s) from state-network access to the gate and tags each segment
     (clean / layered / inconsistent / conflicting / gap).
   - Output: `[route-trace table path]`
4. **Run the analysis:** `python src/analyze.py`
   - Produces the quantified characterization and the figures in `findings/figures/`.
5. **Verify against the benchmark:** [how to check answers against `benchmark/benchmark.json`]

---

## Data layers explained

**Physical layer** — the road network of the last mile. Nodes: segments, intersections,
gates, the terminal. Edges: connectivity a truck can travel. Each segment is tagged with its
governing jurisdiction and (where available) physical and volume attributes.

**Regulatory layer** — the rules. Nodes: individual rules from each jurisdiction. Edges:
references between rules (one rule depends on / excepts / implements another).

**Coupling layer** — the links between them. Edges connect each rule to the physical
node(s) it governs, typed by relationship. This coupling is the central object of the pilot.

Full field-by-field definitions are in `docs/data_dictionary.md`.
Node/edge type definitions are in `docs/schema.md`.

---

## Provenance and trust

Every record in `data/processed/` traces to a source recorded in `data/metadata.json` and
audited in `docs/provenance_audit.md`. Sources are one of three kinds:

- **Document** — a public rule/policy document (cited by section/page).
- **Agency response** — confirmation from a municipal or state contact (logged with date).
- **Field observation** — posted signage, captured as a geotagged photo and transcribed.

Where the three disagree for the same segment (e.g., posted signage vs. digitized rule), the
discrepancy is recorded — these disagreements are findings, not errors to be smoothed over.

---

## PRIVACY NOTE (read before making anything public)

The `data/raw/field/` signage photos may capture identifiable people, vehicles, license
plates, or private property.

- **Do not** publish raw field photos without a privacy pass (crop/blur identifiable details).
- Prefer publishing the **transcribed sign data + location** rather than the photo itself.
- Keep any unreviewed photos out of the public repository (e.g., in a private `field/`
  directory excluded by `.gitignore`).
- Do not include contributors' personal information in the public repository.

---

## Scope and limitations

- This is a **feasibility pilot** for one terminal's last mile, not a port-wide system.
- It builds a coupled **property graph**, not a formal knowledge graph (no reasoning/inference).
- It **characterizes** the multi-jurisdictional structure; it does **not** compute optimal routes.
- Municipal rule data may be incomplete or undigitized; gaps are recorded as findings.

---

## Citation / reuse

[How you'd like this repository cited, if applicable.]
Built on public data; intended as open and reproducible.
