# Regulatory Provenance Audit

Audit date: 2026-07-16
Scope: every rule in `data/processed/regulatory_nodes.json`, verified against the archived local sources only. No web research.

## Method

For each rule: (1) confirm `local_path` exists and hash-matches `data/raw/metadata.json`; (2) extract the cited page/section from the archived PDF and compare against `rule_summary`; (3) classify language force (mandatory / prohibitory / permissive / advisory / descriptive / operational / reference-only / definitional); (4) separate **text verification** ("the archived document says this") from **current legal force** ("this governs on the audit date"); (5) note where a more authoritative archived source exists for the same subject; (6) record applicability precision. Unknown values evaluate as unknown, never as compliant. Layout-aware extraction was used where clause structure mattered (tariff Subrule 34-1140).

This round independently page-verified: APM hours PDF pp.1–2; APM appointment PDF pp.1–2; PANYNJ guidebook PDF pp.3–4 and the APM-specific section (printed pp.18–19, PDF p.11); N.J.A.C. 16:32 cover and §§1.1–1.5; NJ size/weight guidebook pp.10, 12–15; eCFR §§1572.1/1572.3/1572.5; tariff PA-10 pp.55–56. The 2026-07-15 audit's matrix was used as a checklist and spot-checked (no citation errors found), not adopted blind.

## Audit table

| Rule ID | Source verified | Citation verified | Authority type | Rule force | Applicability precision | Problems or limitations |
|---|---|---|---|---|---|---|
| rule_001 | yes | yes — hours p.1, M–F 6:00 a.m. opening | Terminal operator (APM) | operational | terminal area | Mutable page; Wayback only in `data/metadata.json` |
| rule_002 | yes | yes — hours p.1 cutoff table, 4:00 p.m. | Terminal operator | operational | terminal area | Saved page includes an expired temporary 5 p.m. alert; cite the table, not the alert |
| rule_003 | yes | yes — hours p.1, 3:30 p.m. OOG | Terminal operator | operational | terminal area | OOG loads only; must not be applied to non-OOG profiles |
| rule_004 | yes | yes — hours pp.1–2 | Terminal operator | operational | terminal area | Schedule mutable |
| rule_005 | yes | yes, as a system description | Terminal operator | descriptive | terminal area | `compliance_effect` overstates the cited page; the mandatory statement is rule_041 |
| rule_006 | yes | yes | Terminal operator | descriptive | terminal area | System capability, not an access rule |
| rule_007 | yes | yes — appointment p.2 | Terminal operator | operational | terminal area | Mutable |
| rule_008 | yes | yes — guidebook p.3 | Port authority (guidebook) | advisory-phrased | terminal area | "Applicable marine terminal" is vague; APMT-specific mandate is rule_041 |
| rule_009 | yes | yes — guidebook p.3 | Port authority (guidebook) | advisory-phrased checklist | terminal area | Guidebook shows no publication date (applies to all guidebook rules) |
| rule_010 | yes | yes — guidebook p.3 | Federal, via PANYNJ summary | mandatory (as summarized) | secure/restricted areas | Secondary summary; archived Part 1572 (rule_032) is credentialing law, not itself the complete facility-access rule |
| rule_011 | yes | yes — guidebook p.3 | Federal via guidebook | mandatory | secure/restricted areas | Same summary limitation |
| rule_012 | yes | yes — guidebook p.4, "mandatory for all truckers" | Port authority | mandatory | port-wide | Undated guidebook |
| rule_013 | yes | yes — guidebook p.4 | Port authority | mandatory | port-wide | Undated guidebook |
| rule_014 | yes | yes — guidebook p.4 | Port authority | mandatory | terminal gates | Tariff Subrules 34-1080/-1121 are the current controlling text (now rule_038/rule_040) |
| rule_015 | yes | yes — guidebook p.4, "No tag, no entry" | Port authority | prohibitory | terminal gates | Same |
| rule_016 | yes | yes — guidebook p.4 | Port authority | mandatory | terminal gates | Same |
| rule_017 | yes | yes — guidebook p.4 | Port authority | prohibitory | terminal gates | Guidebook footnote defers to tariff; tariff 34-1140(b) (rule_035) confirms the 1998 threshold now, tightening to 1999 on 2027-05-01 and 2000 on 2028-05-01 |
| rule_018 | yes | yes — guidebook p.4 | Port authority | mandatory (registration) | DTR registration | Tariff 34-1101 (rule_037) is the current controlling text; registration ≠ gate entry |
| rule_019 | yes | yes — guidebook p.4 | Port authority | prohibitory | terminal gates | Same tariff-supersession note |
| rule_020 | yes | yes — guidebook p.3 | Port authority | advisory-phrased checklist | carrier-level | Applies to the motor carrier, not the vehicle |
| rule_021 | yes | yes — §16:32-1.1 | State (NJDOT) | regulatory (text) | network-wide | Archived copy is a courtesy copy stating "Expires on July 2, 2022"; current force unresolved for rule_021–026 |
| rule_022 | yes | yes — §16:32-1.2 | State | regulatory with exception | path | Same currentness problem |
| rule_023 | yes | yes — §16:32-1.5 | State | regulatory exception | local segments | Same; path directness never computed |
| rule_024 | yes | yes — §16:32-1.2(e) | State | savings clause | municipal segments | Same; and no municipal/county rules exist in the repository to test |
| rule_025 | yes | yes — §16:32-1.3 (Route 81, I-95 Elizabeth → US 1) | State | designation | Route 81 | Same; no Route 81 edge exists in the physical network |
| rule_026 | yes | yes — §16:32-1.5(c) | State | permissive (documentation *may* demonstrate) | path | `compliance_effect` reads stronger than the permissive text |
| rule_027 | yes | yes — size/weight p.13, 96″/102″ | State | mandatory size limit | segment-designation-dependent | Per-segment designation unverified; key un-coupled rule |
| rule_028 | yes | yes — p.14, 13′6″ | State | mandatory | all roads | No clearance data on edges |
| rule_029 | yes | yes — p.15, 53′/48′ | State | mandatory | designation-dependent | Same coupling gap |
| rule_030 | yes | yes — p.12 + FAQ | State | mandatory | statewide | OS/OW profile lacks a concrete load |
| rule_031 | yes | yes — FAQ p.10 | State | mandatory limitation | Turnpike (Path A approach) | No Turnpike edges modeled |
| rule_032 | yes | yes — §§1572.1/.3 present | Federal (TSA/DHS) | regulatory | credentialing | eCFR snapshot "up to date as of 6/23/2026"; mutable; no Wayback |
| rule_033 | yes | yes — §1572.5 | Federal | regulatory | credentialing | Same |
| rule_034 | yes | partially — map is graphical, not text-verifiable this round | State | reference-only | reference | N.J.A.C. §16:32-1.7: maps do not supersede textual descriptions; keep `confidence: medium` |
| rule_035 | yes | yes — tariff p.56, Subrule 34-1140(a)–(b), layout-verified | Port authority (tariff) | prohibitory | terminal gates | Effective 2026-05-01 per document; repository cannot prove no later amendment |
| rule_036 | yes | yes — tariff p.56, Subrule 34-1140(c), layout-verified | Port authority (tariff) | prohibitory text, interpretation unresolved | terminal gates | Literal reading conflicts with 34-1101 and operational reality; plausible drafting error; requires agency review; confidence low |
| rule_037 | yes | yes — tariff p.56, Subrule 34-1101 | Port authority (tariff) | mandatory (registration) | DTR registration | Governs registration, a different act from gate entry |
| rule_038 | yes | yes — tariff p.56, Subrule 34-1121 | Port authority (tariff) | mandatory on terminal operator | terminal gates | Obligation on the terminal, not the truck |
| rule_039 | yes | yes — tariff p.55, Subrule 34-1060 | Port authority (tariff) | definitional | terminal area | Definition only |
| rule_040 | yes | yes — tariff p.55, Subrule 34-1080 | Port authority (tariff) | definitional | terminal area | Definition only |
| rule_041 | yes | yes — guidebook printed pp.18–19 (PDF p.11), "ALL GATE MOVES AT APMT REQUIRE AN APPOINTMENT" | Port authority / APM (guidebook) | mandatory | APM gate | Undated guidebook; corroborated by APM appointment page |
| rule_042 | yes | yes — same section, Mandatory Trucker Training | Port authority / APM (guidebook) | mandatory | APM gate | Undated guidebook; induction status surfaced in TERMPoint (appointment PDF p.2) |

## Cross-source hierarchy notes

- The guidebook's own footnote (PDF p.4) directs readers to "confirm registration and entry requirements … in the most current Port Authority Marine Tariff" — the tariff is the controlling text over the guidebook for DTR/engine/gate rules.
- The N.J.A.C. courtesy copy's own cover states the official Administrative Code governs and that the copy expired 2022-07-02; text verification of rule_021–026 is therefore decoupled from current legal force.
- rule_010/011 (TWIC) are PANYNJ summaries; the archived eCFR Part 1572 (rule_032/033) is the federal credentialing source, but the complete federal facility-access authority (e.g., the MTSA facility-security regulations) is not archived.

Do not write conclusions from this table into `docs/provenance_audit.md` without David's separate approval; that file remains empty by design pending review.
