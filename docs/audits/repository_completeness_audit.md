# Repository Completeness Audit

Audit date: 2026-07-16
Scope: repository contents only; no web or external sources used.
Branch: `main`. Baseline state at audit start: modified `data/processed/physical_edges.json`, `data/processed/physical_nodes.geojson` (each removed only a `metadata.status: working_draft` line), modified `maps/physical_network/physical_network.qgz` (binary grew 15,996 → 25,192 bytes, contents unexplained — preserved, not overwritten), untracked `docs/audits/evidence_first_audit.md` and `data/processed/evidence_findings.json` (prior audit round dated 2026-07-15).

## Referential integrity (verified)

- All rule IDs in `data/processed/regulatory_nodes.json` are unique and contiguous (`rule_001`–`rule_034` at audit start; `rule_035`–`rule_042` added this round).
- Every rule `local_path` exists on disk.
- Every cited local source appears in both metadata files; all 12 raw-source sizes and SHA-256 hashes in `data/raw/metadata.json` match disk.
- All profile `source_evidence[].rule_ids` resolve; no rule references a `profile_id` (one-directional linkage).
- All finding rule/profile/path references in `data/processed/evidence_findings.json` resolve; all cited evidence files exist.
- Edge IDs `osm_edge_001`–`osm_edge_074` and node IDs `node_001`–`node_082` plus four anchors are unique. Node `source_edge_id` values resolve, but only 54 of 74 edges are referenced by any node (incomplete provenance linkage, not topology).

## Empty placeholders (0-byte files)

| File | README's claim about it |
|---|---|
| `data/processed/coupling_edges.json` | "the central object of the pilot" |
| `data/processed/regulatory_edges.json` | rule-to-rule references |
| `data/processed/municipal_rules_verified.json` | verified municipal rules |
| `docs/provenance_audit.md` | "confirms every record traces to a source" |
| `docs/schema.md` | node/edge type definitions |
| `src/build_graph.py`, `src/trace_route.py`, `src/analyze.py` | executable pipeline |
| `benchmark/benchmark.json` | validation questions + expert answers |
| `findings/findings.md` | the characterization |
| `preliminary_results.md` | proposal-ready memo |

`requirements.txt` is absent. The README's "How to reproduce" steps cannot run, and its statement that provenance "is audited in `docs/provenance_audit.md`" is not yet true (the audit content lives in `docs/audits/`).

## Path/label mismatches

- Regulatory records use free-text applicability labels (`Path A`, `Path B`, `North Avenue`, `APM terminal access candidate`, `terminal secure/restricted area`, `municipal_segments_pending_fieldwork`) that do not resolve to the canonical IDs used by the physical layer (`path_a_exit13a_to_apm`, `path_b_us1_9_to_apm`, `osm_edge_*`, `node_*`, anchors). `data/processed/coupling_edges.json` (populated this round) provides the explicit mapping.
- `data/metadata.json` and `data/raw/metadata.json` previously disagreed on coverage (curated file omitted the PA-10 tariff and OSM GeoJSON — fixed this round) and still record different URLs for four shared sources (direct-document URL vs landing page). The curated file now documents the two files' complementary roles.

## Structural gaps that block contradiction testing

1. **No topology.** All 74 edges have `from_node`/`to_node` = null; both candidate paths map to the identical 74-edge set. Only North Avenue/North Avenue East, McLester Street, and Tripoli Street are modeled; no Route 81, NJ Turnpike, or US 1&9 approach edges exist, so path continuity/directness (relevant to N.J.A.C. 16:32-1.5) cannot be computed.
2. **No municipal or county rules**, no posted-restriction/signage records, no jurisdiction-boundary or road-ownership layer, and no per-segment National Network / NJ Access Route designation — so the designation-dependent state size limits (rule_027/029) and the state-vs-local question preserved by rule_024 cannot be tested.
3. **No time/effective-date model** on the original 34 rules (rule_035+ carry optional `modality`, `effective_from`, `effective_to`).
4. **Superseded-vs-current status:** the archived N.J.A.C. 16:32 courtesy copy states "Expires on July 2, 2022"; the guidebook is undated and defers to the tariff; only the tariff (effective 2026-05-01) and eCFR snapshot (as of 2026-06-23) carry their own currentness statements.
5. **Evaluation outputs** did not exist before this round; see `rule_applicability.json`, `route_evaluations.json`, `rule_pair_evaluations.json`.

## Data-dictionary accuracy

`docs/data_dictionary.md` accurately documents `regulatory_nodes.json` (original 14 fields) and `vehicle_profiles.json` (though nested `dimensions`/`credential_status` keys are not enumerated). It documents nothing for `physical_edges.json`, `physical_nodes.geojson`, the two `*_qgis.geojson` files, or the audit artifacts. Sections for the new artifacts were appended (never rewritten) this round; physical-layer documentation remains an open task.

## Verdict

The repository's provenance discipline for what exists is strong (hashes, dual metadata, resolvable IDs). What is missing is exactly the connective tissue the contradiction question needs: topology, coupling, local rules, designations, and currentness. Accordingly: **the current repository does not contain enough connected and verified evidence to determine whether a contradiction exists.**
