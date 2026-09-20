# Bounded requirement evaluators

Eleven executable predicates over admitted synthetic verification receipts:
five road/permit (`neo4j_kg/road_evaluators.py`), six terminal/driver
(`neo4j_kg/terminal_evaluators.py`). They answer narrow source-backed
subchecks for one saved trip revision. None of them issues entry, dispatch,
or clearance permission; the engine-policy evaluator cannot return met by
construction. Driver and dispatcher wording runs the same predicates; the
[terminal policy review](../audits/eleven-evaluators-2026-09-15/terminal-policy-review.md)
checks every terminal constant against its retained clause.

## Admission before evaluation

`neo4j_kg/verification.py admit()` binds each operator-seeded receipt to the
case before any predicate runs: same trip and revision, matching case
fingerprint, pinned graph release, validity interval covering the trip time
(start-inclusive/end-exclusive), observation not in the future, every binding
field equal to the saved facts, and no revocation. Anything else is rejected
with reason codes; rejected receipts never reach the evaluators.
`evaluate_requirement()` additionally forces the whole requirement unresolved
when two admitted receipts for the same kind disagree — except `approval` and
`conditions`, whose segmented observations are compared per segment/authority
inside the road evaluator (`_segment_evidence`), with the same
disagreement-stays-unresolved outcome.

Reports cannot defeat a trusted negative: when a predicate returns met but a
saved user report says false for the same prerequisite (DTR, permit route,
TWIC, SeaLink, appointment, transaction, RFID-in-scope), the result is forced
unresolved with `REPORT_CONFLICTS_WITH_SYNTHETIC_VERIFICATION`. Missing facts,
case conflicts, and source-coverage gaps force unresolved one layer up in
`assessment.evaluate_trip`, which also never resolves the requested scope on a
partial pass.

## Road evaluators

- `axle_weight_evidence`: individual-axle scale record plus verified complete
  route sequence. Per-segment bridge evaluation (`bridge_math.evaluate_axles`),
  posted gross/single/tandem comparisons, no tolerance or exception inferred.
  Permits never alter this baseline. Non-Interstate bridge/tandem applicability
  is a stated source-scope gap.
- `dimensions_and_route`: 102in width, 162in height, 636in semitrailer caps on
  non-terminal regimes; terminal/unknown regimes get no generic clearance rule.
  102-inch local-access and over-48ft trailer rules require their own verified
  observations. Explicit postings are still checked per segment.
- `permit_eligibility`: NJ single-trip and ocean-container-annual types only,
  NJ issuer, valid status, satisfied conditions, stated-envelope comparisons.
  Ocean-container permits additionally require legal dimensions (a nested
  `dimensions_route` run). Load-report contradictions stay unresolved.
- `cross_authority_coverage`: per-segment responsible-authority approval or
  explicit not-required, with authority-mismatch and overlapping-observation
  conflict detection. A state permit is not approval for other segments.
- `current_route_conditions`: per-segment condition-category observations,
  operating status, and current postings against saved measurements. Archived
  bulletins never establish current conditions; no live feed is connected.

## Terminal evaluators

- `dtr_registration_and_rfid`: DTR scope, active registration predating the
  local entry date, change-amended-within-ten-calendar-days, then the Class 8
  RFID branch (assigned, valid, properly mounted) only when in scope.
- `dtr_engine_policy`: 34-1101 registration branch (July 2, 2023 12:01 AM
  threshold, 2014 emissions standard — year alone never suffices) alongside the
  34-1140 entry branch (2023/1998, 2027/1999, 2028/2000 blocks). The retained
  release leaves the branches in tension, so the evaluator always returns
  unresolved with `UNRESOLVED_DTR_TARIFF_CONFLICT`. Alternative-truck clause
  (c) has no reviewed predicate.
- `driver_twic`: unescorted secure-area scope, no claimed exception, valid
  credential, trip strictly before expiry, physical possession.
- `sealink_registration`: active case-bound record with TWIC registered on it.
- `apm_appointment`: APM Elizabeth scope, confirmed status, trip inside the
  start-inclusive/end-exclusive slot for the admitted move.
- `transaction_release`: import-pickup moves only (draft supplement, not a
  promoted clause), explicit full availability, all five modeled hold fields
  explicit and false.

## Verification surfaces

Unit: `tests/test_requirement_evaluators.py`, `test_terminal_evaluators.py`,
plus `test_verification_review_regressions.py` and
`test_terminal_review_regressions.py` for reviewed failure modes. Live:
`tools/verify_requirement_evaluators.py` seeds synthetic receipts as operator
(not through client endpoints), runs positives, eleven targeted negatives,
revocation, reassignment, and caller-injection rejection over stdio MCP and the
local HTTP app against the pinned Neo4j release — see the
[final September 15 audit](../audits/eleven-evaluators-final-2026-09-15/README.md).
34 assessments captured, all service available, all operational permission not
issued, driver/dispatcher semantics equal.

## What this does not establish

Current policy beyond the retained clauses, CDL or credentialing outside the
named predicates, gate state, live road conditions, alternative-truck status,
non-import transaction types, non-APM terminals, or any operational permission.
Missing verification, source gaps, and exceptions remain unresolved by design.
Production stays blocked per [production-readiness](production-readiness.md).

## September 16 review closeout

The [closeout audit](../audits/evaluator-closeout-2026-09-16/README.md) adds
`tests/test_source_supplements.py`: every required extraction is individually
removed; altered text, mappings, source IDs, locators, release IDs and duplicate
entries are rejected; source-byte changes and provider failures cannot reuse a
passing result. Output-schema checks accompany the assessment regressions.
Forbidden approval metadata is rejected by the loader and wire schema, and the
finding guard also remains unresolved when a test bypasses the loader.

The September 15 live capture used a Python environment with NetworkX installed.
Its sealed README's claim of absence is corrected by the closeout addendum;
`.venv-neo4j` remains NetworkX-free. The existing driver screenshots are now
preserved, but their original runtime identity was not recorded. No new browser
or model acceptance run is claimed by preservation.
