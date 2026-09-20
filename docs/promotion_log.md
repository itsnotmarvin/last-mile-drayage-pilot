# Evidence promotion log

Records enter `main` only after their retained source bytes, locator, date semantics, applicability boundary, and graph/visual eligibility have been rechecked against the `main` evidence registry. Interpretive unresolved research remains on `fable-audit-review`.

## 2026-08-24 — Permit-currentness and PA-10 evidence hardening

- Base `main` commit reviewed: `0fd261b`.
- Branch promotion: none. New records were derived directly from official sources archived on 2026-08-24; no audit-branch conclusion was copied into `main`.
- New retained sources: NJPASS portal snapshot, NJPASS-hosted N.J.A.C. 13:18 rule copy, NJDOT truck-routing regulations page, New Jersey Register 16:32 readoption/adoption notice, and PANYNJ facilities map.
- Point-in-time byte checks: the live January 2024 NJ size-and-weight guidebook, NJDOT 16:32 courtesy copy, and PA-10 tariff effective May 1, 2026 matched their retained SHA-256 hashes.
- Currentness boundaries: portal currency is stored separately from publication and effective dates; official code-of-record comparisons remain explicitly incomplete where not archived.
- Applicability changes: the single-trip and ocean-container permit records were changed from negative determinations to `indeterminate_missing_rule_keyed_facts`.
- PA-10 34-1140: all three deadline blocks were transcribed from the tariff retained on `main`; only the bounded `unresolved_internal_text_tension` notice was retained. No audit-branch reference to absent Subrule 34-1120 was promoted.
- Spatial change: `couple_terminal_weight_gate` was removed because retained text establishes Marine Terminal Highway scope, not an APM gate-node coupling.
- Visual status: the prior infographic was marked stale rather than silently treated as current.
- Verification command: `python3 tools/validate_records.py`.
