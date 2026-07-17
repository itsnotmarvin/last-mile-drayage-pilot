# Evidence-First Regulatory Audit

Audit date: 2026-07-15  
Scope: repository contents only  
Regulatory dataset: `data/processed/regulatory_nodes.json` (34 rules)  
Physical dataset: `data/processed/physical_edges.json` and `data/processed/physical_nodes.geojson`  
Vehicle dataset: `data/processed/vehicle_profiles.json`

## Executive result

The repository supports evidence-backed **layered**, **conditional**, **blocking**, and **unresolved** findings. It does **not** currently support a potential-contradiction finding.

The strongest supported result is that the same physical terminal approach has different operational outcomes by vehicle profile:

- A source-backed standard 5-axle profile remains conditionally usable at terminal entry only when appointment, time-window, credential, carrier, DTR, and RFID requirements are satisfied (`rule_001`-`rule_003`, `rule_007`-`rule_009`, `rule_012`-`rule_016`, and `rule_020`).
- A 1998-engine drayage profile is blocked at Port Authority terminal entry by the engine/DTR access rules (`rule_017` and `rule_019`). The archived 2026 PANYNJ tariff independently corroborates this outcome at Subrule 34-1140, although that tariff is not currently cited by those rule records.
- An oversize/overweight/out-of-gauge profile is conditional on actual dimensions, weight, permits, toll-authority approval where applicable, and the APM OOG cutoff (`rule_003` and `rule_027`-`rule_031`). Because the profile intentionally lacks a specific load configuration, no route-level pass/fail result is supported.
- State terminal-access routing remains unresolved as a current legal conclusion because the archived N.J.A.C. 16:32 PDF is a courtesy copy that states it expired July 2, 2022 (`rule_021`-`rule_026`). Its cited text supports the extracted summaries, but the repository does not contain a newer authoritative copy establishing present validity.

No two repository rules currently establish incompatible outcomes for the same physical edge, vehicle, time, and circumstance. `data/processed/coupling_edges.json` is empty, municipal rules are absent, every physical edge has null `from_node` and `to_node`, and the rule records refer mostly to broad path or terminal labels rather than exact edge IDs.

## Method

### Pass 1 - provenance verification

For every rule, this audit checked:

1. the local source path exists;
2. the cited section appears in the archived source and supports the summary;
3. the rule's source URL and issuing authority are internally consistent;
4. the source is covered by `data/raw/metadata.json` and `data/metadata.json`;
5. limitations affecting present-day use are recorded; and
6. every field currently used by `regulatory_nodes.json` is documented in `docs/data_dictionary.md`.

### Pass 2 - applicability and findings

A result is classified as:

- **layered**: multiple requirements can be satisfied together;
- **conditional**: access depends on one or more stated conditions;
- **blocking**: a verified rule denies the selected profile under the stated circumstance;
- **unresolved**: the repository lacks current, sufficiently precise, or connected evidence; or
- **potential contradiction**: two verified rules govern the same location, vehicle, time, and circumstance but impose incompatible outcomes.

The audit does not treat multiple authorities or multiple requirements as a contradiction by themselves.

## Pass 1 findings

### Repository-wide provenance checks

- All 34 rule records point to local files that exist.
- All cited local files have records in both metadata files.
- The file sizes and SHA-256 hashes in `data/raw/metadata.json` match the archived files.
- `data/raw/metadata.json` has 12 source records and checksum coverage. `data/metadata.json` has 10 curated source records and mutable-source/Wayback fields. The repository does not identify which metadata file is canonical.
- The rule URLs exactly match at least one metadata record for every rule. In `data/raw/metadata.json`, the URLs for `rule_027`-`rule_031` and `rule_034` point to general landing pages rather than the exact URLs stored in the rules; `data/metadata.json` contains the exact URLs.
- APM Wayback snapshots are recorded in `data/metadata.json`, but not in `data/raw/metadata.json`.
- `docs/provenance_audit.md` and `docs/schema.md` are empty.
- The data dictionary documents all 14 fields used by regulatory rule records: `rule_id`, `rule_name`, `jurisdiction`, `authority`, `source_doc`, `source_section`, `source_url`, `local_path`, `rule_summary`, `vehicle_property_keys`, `applies_to_segments_or_paths`, `compliance_effect`, `confidence`, and `notes`.
- The data dictionary does not define an audit/findings artifact, evidence status, applicability precision, or the five classifications used here.

### Rule-by-rule provenance matrix

Status meanings:

- **verified**: the archived passage supports the recorded summary.
- **verified-description**: the passage supports an operational description, but not the stronger compliance effect currently assigned.
- **text-verified/currentness-unresolved**: the passage supports the summary, but the archived source does not establish present legal force.
- **verified/reference-only**: the source supports use as a reference, not as a standalone legal rule.

| Rule | Provenance result | Authority and section check | Metadata | Current limitation |
|---|---|---|---|---|
| `rule_001` | verified | APM, hours page p.1 states weekday opening at 6:00 a.m. | both | Mutable page; Wayback only in `data/metadata.json`. |
| `rule_002` | verified | APM, cutoff table p.1 supports 4:00 p.m. standard cutoffs. | both | Mutable page; saved page also contains a temporary alert, so the cutoff table must remain the cited element. |
| `rule_003` | verified | APM, cutoff table p.1 supports 3:30 p.m. OOG cutoff. | both | Mutable page; Wayback only in `data/metadata.json`. |
| `rule_004` | verified | APM, pp.1-2 states weekend/holiday hours may vary. | both | Operational schedule may change. |
| `rule_005` | verified-description | APM p.1 establishes TERMPoint as an appointment-management system. | both | The cited page describes the system but does not, by itself, prove that every move requires an appointment. The APM section of the archived PANYNJ guidebook provides that stronger statement. |
| `rule_006` | verified-description | APM p.1 supports simultaneous import/export scheduling. | both | This is a system capability, not a standalone access rule; `compliance_effect` overstates the cited passage. |
| `rule_007` | verified | APM p.2 states availability may change with closures and e-alert notice. | both | Mutable operational information. |
| `rule_008` | verified | PANYNJ guidebook p.3 says applicable terminal visitors should have an appointment. | both | “Applicable” is broad; the same guidebook's APM section states all APMT gate moves require an appointment. |
| `rule_009` | verified | PANYNJ guidebook p.3 lists license, TWIC, and SeaLink before gate arrival. | both | Guidebook has no visible publication date in the archived front matter. |
| `rule_010` | verified | PANYNJ guidebook p.3 states federal TWIC requirement for secure/restricted maritime areas. | both | This is a PANYNJ summary of federal law; `rule_032` is the archived federal source. |
| `rule_011` | verified | PANYNJ guidebook p.3 requires original TWIC for unescorted secure-area access. | both | Same guidebook-date limitation. |
| `rule_012` | verified | PANYNJ guidebook p.4 says SeaLink is mandatory for port truckers. | both | Same guidebook-date limitation. |
| `rule_013` | verified | PANYNJ guidebook p.4 requires SeaLink holders to have and register TWIC. | both | Same guidebook-date limitation. |
| `rule_014` | verified | PANYNJ guidebook p.4 requires Class 8 drayage trucks to be in DTR with valid RFID. | both | Current tariff is stronger/current corroboration but is not cited in this rule. |
| `rule_015` | verified | PANYNJ guidebook p.4 states “No tag, no entry.” | both | Guidebook evidence; no separate current-tariff citation in rule. |
| `rule_016` | verified | PANYNJ guidebook p.4 supports one RFID tag per unique vehicle. | both | Same guidebook-date limitation. |
| `rule_017` | verified | PANYNJ guidebook p.4 denies 1998-and-older engine models. | both | Corroborated by archived 2026 tariff Subrule 34-1140; tariff citation should replace or supplement the guidebook in a future rule revision. |
| `rule_018` | verified | PANYNJ guidebook p.4 states 2014 EPA engine standard for DTR registration. | both | Corroborated by archived 2026 tariff Subrule 34-1101; current tariff also changes the 2027 gate threshold, so time scope is essential. |
| `rule_019` | verified | PANYNJ guidebook p.4 lists DTR, approval, and pre-1999 denial reasons. | both | Current tariff corroborates DTR/engine denial; exact rule should carry an effective-time field. |
| `rule_020` | verified | PANYNJ guidebook p.3 lists UIIA, insurance, and steamship-line credit evidence. | both | Same guidebook-date limitation. |
| `rule_021` | text-verified/currentness-unresolved | NJDOT courtesy copy §16:32-1.1 states the three-level hierarchy. | both | PDF states “Expires on July 2, 2022” and says the official NJ Administrative Code governs. |
| `rule_022` | text-verified/currentness-unresolved | Courtesy copy §16:32-1.2(b) supports National Network use and terminal-access exception. | both | Same expiration/current-authority problem. |
| `rule_023` | text-verified/currentness-unresolved | Courtesy copy §16:32-1.5(a) supports necessary/direct terminal access. | both | Same expiration/current-authority problem; directness has not been computed for either path. |
| `rule_024` | text-verified/currentness-unresolved | Courtesy copy §16:32-1.2(e) preserves state, municipal, and county restrictions. | both | Same expiration problem; municipal/county rules are absent from the repository. |
| `rule_025` | text-verified/currentness-unresolved | Courtesy copy §16:32-1.3(a)(5) lists Route 81 from I-95 to US 1. | both | Same expiration problem; `physical_edges.json` contains no Route 81 edge. |
| `rule_026` | text-verified/currentness-unresolved | Courtesy copy §16:32-1.5(c) lists acceptable routing documentation. | both | Same expiration/current-authority problem; `compliance_effect` should be read as supporting compliance, not necessarily mandatory documentation. |
| `rule_027` | verified | January 2024 NJ guidebook p.13 supports 96/102-inch route-dependent limits. | both | Guidebook disclaimer says rules may change; exact URL differs in `data/raw/metadata.json`. |
| `rule_028` | verified | January 2024 NJ guidebook p.14 supports 13 ft 6 in maximum unless otherwise identified. | both | Guidebook disclaimer; route clearances are not encoded in physical edges. |
| `rule_029` | verified | January 2024 NJ guidebook pp.15 and 20-21 supports 53 ft on network/access routes and 48 ft on other routes. | both | Guidebook disclaimer; physical route designation is incomplete. |
| `rule_030` | verified | January 2024 NJ guidebook p.12 and permit section support special permits when limits are exceeded. | both | Exact load is absent for the OS/OW profile; permit eligibility also depends on load divisibility. |
| `rule_031` | verified | January 2024 NJ guidebook FAQ p.10 requires toll-authority approval for listed facilities. | both | Path A uses a Turnpike access label but has no Turnpike/Route 81 edges connected to the modeled corridor. |
| `rule_032` | verified | eCFR §§1572.1 and 1572.3 support TWIC credentialing/security-assessment scope. | both | Saved eCFR says current through June 23, 2026; mutable and no valid Wayback snapshot. |
| `rule_033` | verified | eCFR §1572.5 supports denial/invalidation standards. | both | Same mutable-source limitation. |
| `rule_034` | verified/reference-only | Archived 2024 map is a route-designation reference for the large-truck network. | both | N.J.A.C. courtesy copy §16:32-1.7 says maps do not supersede textual regulatory descriptions; Path B/US 1&9 and North Ave status are not resolved by an explicit repository coupling. |

## Pass 2 findings

The machine-readable form of these findings is `data/processed/evidence_findings.json`.

### Supported findings

1. **Conditional - standard profile at APM terminal access.** The standard profile must satisfy current gate windows and appointment conditions (`rule_001`-`rule_003`, `rule_007`, and `rule_008`). Applicability is terminal-area/path-level, not exact-edge-level.
2. **Layered - standard profile at APM terminal access.** License/TWIC/SeaLink, RFID/DTR, unique tag, and carrier-documentation requirements can apply together (`rule_009`, `rule_012`-`rule_016`, and `rule_020`). These are compatible cumulative requirements, not a contradiction.
3. **Blocking - 1998-engine profile at Port Authority terminal entry.** `rule_017` and `rule_019` deny the profile at terminal entry. The archived 2026 tariff independently corroborates the result.
4. **Conditional - OS/OW/OOG profile.** Entry and route use depend on APM OOG time window, actual dimensions/weight, state permit, and toll-authority approval where relevant (`rule_003` and `rule_027`-`rule_031`). The absence of a specific load prevents a route-level verdict.
5. **Unresolved - state terminal-access legality for Path A and Path B.** `rule_021`-`rule_026` describe terminal access, but the archived source states it expired in 2022 and the repository has not computed direct-route compliance.
6. **Unresolved - exact edge applicability and route continuity.** Rules use broad labels such as `Path A`, `Path B`, and `APM terminal access candidate`; they do not cite edge IDs. All 74 physical edges have null `from_node` and `to_node`. The 74 edges cover North Avenue/North Avenue East, McLester Street, and Tripoli Street and are assigned to both paths; no Route 81, Turnpike, or US 1&9 edge is present.
7. **Unresolved - local restrictions.** `rule_024` says other state, municipal, and county restrictions may apply, but the repository contains no municipal regulatory nodes and no field-signage evidence.

### Contradiction assessment

**No potential contradiction is supported by the current repository.**

The closest research question is the interaction between terminal-access permission in `rule_022`/`rule_023` and possible local restrictions preserved by `rule_024`. That is an unresolved evidence gap, not a contradiction, because:

- the state source's present validity is unresolved;
- no municipal/county restriction has been extracted;
- no rule-to-edge coupling exists; and
- no same-vehicle, same-time incompatible pair can be identified.

## Exact append-only data-dictionary proposal

Do not replace `docs/data_dictionary.md`. If the project approves `evidence_findings.json` as a maintained artifact, append the following section exactly (or review and revise it before appending):

```markdown
---

## evidence_findings.json

Purpose: Stores evidence-backed audit findings derived from existing regulatory rules, physical network records, and representative vehicle profiles. A finding records what the current repository supports; it does not make a final legal determination.

Location: data/processed/evidence_findings.json

Top-level fields:

| Field | Type | Required | Description |
|---|---|---|---|
| schema_version | string | yes | Version of the evidence-findings schema. |
| audit_date | string | yes | ISO date of the repository-only audit. |
| evidence_boundary | string | yes | States that only repository contents were used. |
| contradiction_supported | boolean | yes | True only when at least one finding meets the potential-contradiction test. |
| classification_definitions | object | yes | Definitions of layered, conditional, blocking, unresolved, and potential_contradiction. |
| findings | array | yes | Evidence-backed finding records. |

Finding fields:

| Field | Type | Required | Description |
|---|---|---|---|
| finding_id | string | yes | Stable unique finding identifier. |
| classification | string | yes | One of layered, conditional, blocking, unresolved, or potential_contradiction. |
| title | string | yes | Short human-readable finding title. |
| vehicle_profile_ids | array | yes | Vehicle profiles evaluated; empty only for a structural data finding. |
| path_ids | array | yes | Exact candidate path IDs implicated by the finding. |
| physical_edge_ids | array | yes | Exact physical edge IDs when supported; empty when applicability is only path/area-level. |
| location_scope | string | yes | Human-readable physical scope. |
| rule_ids | array | yes | Regulatory rule IDs supporting the finding. |
| explanation | string | yes | Plain-English explanation of the supported outcome. |
| evidence_files | array | yes | Repository files used to support the finding. |
| applicability_precision | string | yes | One of exact_edge, path, terminal_area, jurisdiction_area, or unresolved. |
| evidence_status | string | yes | One of verified, verified_with_limitation, or unresolved. |
| limitations | array | yes | Known limitations that constrain interpretation. |
| requires_human_review | boolean | yes | Whether authoritative or expert review is required before operational use. |
```

Future coupling definitions should be proposed separately only after the project decides how rules will reference exact edges, areas, time scopes, and evidence. The current empty `coupling_edges.json` should not be populated without an approved dictionary definition.

## Recommended next evidence tasks

1. Establish one canonical metadata file or formally document the distinct purpose of `data/metadata.json` and `data/raw/metadata.json`.
2. Obtain and archive a current authoritative N.J.A.C. 16:32 source before using `rule_021`-`rule_026` for present-day legality.
3. Add the archived 2026 PANYNJ tariff as the primary or corroborating source for DTR/engine rules, with effective dates.
4. Verify and extract Elizabeth/Union County rules and field-signage evidence before testing a state-versus-local contradiction.
5. Complete physical topology and include approach edges for Route 81/Turnpike and US 1&9 before claiming path-level continuity or directness.
6. Propose, approve, and append a `coupling_edges.json` schema before creating rule-to-edge records.


---

## Addendum — 2026-07-16 verification round

A second repository-only round independently re-verified this audit's provenance matrix (spot checks across five archived sources found no citation errors) and made the following corrections and additions. The machine-readable findings file was updated in place.

**Corrections**

1. `finding_001` previously applied `rule_003` (the 3:30 p.m. OOG cutoff) to the standard non-OOG profile. Removed; the standard cutoff's exact window remains conditional on load type.
2. `contradiction_supported: false` was stated as a determination. Replaced with the tri-state value `not_determinable`: the current repository does not contain enough connected and verified evidence to determine whether a contradiction exists.

**Additions**

3. `finding_008` (unresolved): archived tariff PA-10 Subrule 34-1140(c) literally denies terminal access to any drayage truck that is not an Alternative Drayage Truck (Subrule 34-1060: LNG/CNG/electric/hybrid only). Confirmed as genuine document text via layout-aware extraction. A literal reading would make clauses (a)–(b) and Subrule 34-1101 surplusage, so a drafting error is plausible; interpretation requires agency review. Not classified as a contradiction.
4. `finding_009` (layered): the guidebook's APM-specific section (printed pp. 18–19) contains two previously unextracted mandatory rules — "ALL GATE MOVES AT APMT REQUIRE AN APPOINTMENT" and mandatory online safety induction for terminal access — now extracted as `rule_041` and `rule_042`.
5. The tariff's operative subrules (34-1060, 34-1080, 34-1101, 34-1121, 34-1140) were extracted as `rule_035`–`rule_040`, carrying `modality` and `effective_from`/`effective_to` fields, addressing this audit's recommendation 3.
6. The curated metadata file `data/metadata.json` now records the tariff and the OSM GeoJSON and documents the two metadata files' complementary roles, addressing recommendation 1.

The full second-round outputs are in `docs/audits/repository_completeness_audit.md`, `docs/audits/regulatory_provenance_audit.md`, and `docs/audits/missing_evidence_inventory.md`, with machine-readable artifacts `data/processed/rule_applicability.json`, `data/processed/coupling_edges.json`, `data/processed/route_evaluations.json`, and `data/processed/rule_pair_evaluations.json`.
