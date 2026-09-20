# Individual axle intake and release review

Current status, September 16: [eleven bounded evaluators](requirement-evaluators.md)
now supplement induction. See the [closeout](../audits/evaluator-closeout-2026-09-16/README.md)
for source regressions, the capture-environment correction and preserved browser
evidence. Production remains blocked. The individual axle sections below retain
the September 13 implementation checkpoint.

## Individual axle reports

The MCP and application accept `axle_layout`: one weight and one position for
**each individual axle**, measured from the first axle in front-to-back order.
The first position must be zero, later positions must strictly increase, weights
must be positive, and every quantity needs a unit. Up to 32 rows are supported.
For example:

```json
{
  "axle_layout": {
    "axles": [
      {"position": {"value": 0, "unit": "ft"}, "weight": {"value": 12000, "unit": "lb"}},
      {"position": {"value": 12, "unit": "ft"}, "weight": {"value": 17000, "unit": "lb"}},
      {"position": {"value": 16, "unit": "ft"}, "weight": {"value": 17000, "unit": "lb"}},
      {"position": {"value": 48, "unit": "ft"}, "weight": {"value": 17000, "unit": "lb"}},
      {"position": {"value": 52, "unit": "ft"}, "weight": {"value": 17000, "unit": "lb"}}
    ]
  }
}
```

This synthetic example reports five axles, an 80,000 lb total and a 624-inch
first-to-last span. Those values describe the submitted measurements; they are
not a legal finding. The normalized record uses `position_inches` and `weight_lb`.
Different rows may use different supported units (`ft`/`in`, `lb`/`kg`).
`null` means unknown. The form preserves each row's units during review.

The service rejects malformed ordering, extra/group fields and count/gross
contradictions submitted together. If a later correction disagrees with an
existing layout, the assessment requests correction and suppresses affected
comparisons. Vehicle or trailer reassignment invalidates the layout. Conflicting
assignments suppress derived layout measurements. Disputed gross/count reports
are not used for reconciliation; the independently reported layout total can
still be displayed. Corrupt saved measurements
cannot produce totals. The implementation bounds are input limits, not legal
weight or dimension limits; no scale tolerance is assumed.

Legacy `axle_weights` and `axle_spacings` remain available for historical reports.
Their group semantics are ambiguous. Neither MCP nor application splits a tandem
total into invented individual axle weights or guesses missing positions. The
axle requirement now asks for an explicit layout; a driver who only has group
totals can leave it unknown.

The authoritative response is `input_review.axle_layout`. Its status is
`not_supplied`, `reported_only` or `input_review_required`; its total, span and
reconciliation issues remain separate from requirement findings and reported
source comparisons. There is still no bridge-formula, axle-group, tire-load,
road-applicability or legal-weight evaluator. Driver and dispatcher roles use
the same measurement and legal coverage rules.

## Read-only source and release commands

Run these from the prototype directory. They use the standard library and do
not connect to Neo4j, read credentials, change the graph or activate a release.
Without `--output`, the report goes to stdout. An output file must be new and is
created with owner-only permissions. The parent directory must already exist.

```sh
python3 tools/review_release.py inventory
python3 tools/review_release.py packet --output .runtime/source-review-packet.json
python3 tools/review_release.py compare \
  --baseline data/neo4j_release.json \
  --candidate .runtime/candidate-release.json
python3 tools/review_release.py readiness \
  --capture audits/release-engineering-final-2026-09-13
```

`inventory` reports all 33 source records in the pinned release, their retained
files, publication/access dates, clauses, archived observations, dependent
requirements and reported checks. Reviewers remain unassigned. The
`transaction_release` requirement has no retained governing clause; the command
reports this gap explicitly.

`packet` includes the exact stored clause records, all 13 requirement definitions,
the 23 draft reported checks and their bindings, and review instructions. A
packet for a candidate also states whether the reported-check catalog is bound
to that candidate. Complete original sources, applicability and exceptions still
need review; an excerpt collection is not a completeness certificate.

`compare` first validates both content-addressed releases. Text, locator and
source metadata changes identify dependent requirements. Changed archived bytes
also identify their source and dependent clauses, even if a clause excerpt is
unchanged. Relationship, graph classification/order/context, release metadata,
and unattributed file changes require broad review. Removed required clauses
remain explicit. No-change means the supplied snapshots match; it does not mean
that law or gate conditions have stayed unchanged outside those snapshots.

This is a review aid, not an automatic watcher or publisher. Obtain candidate
material, review material changes, build a candidate in the authorized evidence
workflow, compare it, then validate its checks and rollback before separately
authorized activation. See [the migration workflow](neo4j-migration.md). The parent
archive stays read-only in this implementation task.

`readiness` checks the full draft scope, retained source bytes, actual evaluator
coverage, catalog/release binding and an optional artifact capture. Its exit code
is **2 for blocked readiness**, **1 for invalid inputs**, and **0 for other
successfully produced reports**. Exit 2 is expected for the current synthetic
runtime and must not be reinterpreted as production approval.

The capture checker verifies the expected graph release, manifest-bound artifact hashes and the exact current
runtime file map, including the MCP runner, application, catalogs and review
command. Missing, changed or removed runtime files make a capture stale;
altered artifacts, an unbound summary or escaping paths make it invalid. Hashes
bind bytes to a capture; they do not authenticate reviewers or prove adequate
test coverage. Old immutable captures remain valid historical records while
being stale for this changed implementation.

## Rule changes and operating conditions

Stable rule review should respond to material source changes, corrections,
reported errors and applicability questions. A freshly downloaded document is
not automatically a newly reviewed rule. Source publication date, access date,
version and review decision stay distinct.

Appointments, credential status, permit validity, gate state and road conditions
need evidence suitable for the particular move. An archived bulletin cannot
provide that verification. Source owners must define accepted evidence and
change triggers for each supported requirement, separately from rule review.

The official bridge-equation image retained under
`data/source_candidates/2026-09-13/` is an **inactive candidate**. Its receipt
records origin, retrieval time, byte hash and a draft visual transcription. The
current eCFR page displayed title-wide dates; those dates do not establish when
section 658.17 last changed. Variable definitions, rounding, applicability and
exceptions have not completed review. The image does not activate a calculator,
change the graph or fill the remaining legal coverage gap.

## Concrete release dependencies

`data/release_scope.json` proposes APM Elizabeth, driver and dispatcher workflows,
and the existing six study families plus shared trip context. The two study
routes are candidate context; their identities are not approved legal roadway
coverage. All 13 requirements remain in the scope. Narrowed profiles or a changed
approval label cannot make the readiness command report a passing grade.

| Accountable role | Required deliverable |
| --- | --- |
| Product and domain reviewers | Approved terminal, road, vehicle/cargo and decision scope, exclusions and escalation ownership. |
| Domain reviewers and engineering | Complete governing clauses, reviewed applicability/exceptions/conflicts, accepted verification contracts, and positive/negative/missing/conflicting acceptance cases for every evaluator. Eleven bounded implementations now exist beyond induction; complete legal/operational coverage and domain acceptance remain open. |
| Data owners and integration operators | Authorized verification services or accepted human procedures for credentials, registry, appointments, permits and operating conditions. |
| Client acceptance reviewers | Actual released browser/MCP/model workflow captures and scored final answers, including correction, pressure and outage cases. A synthetic driver walkthrough is preserved; full released-client acceptance remains incomplete. |
| Identity/security owners | Selected production hosting/identity boundary, threat and privacy review, retention/key policy and security acceptance. |
| Service operator | Agreed load/cost targets, monitoring, RPO/RTO, tested recovery, incident response and operational ownership. |
| Release owner | A decision bound to the reviewed implementation, source release and accepted evidence. |

These roles are proposed responsibilities, not named or consenting reviewers.
The readiness report is an engineering review tool. There is no production
serving mode or independent launch-authority system in this local prototype;
a JSON approval-like field cannot create one.

## Verification and code

At the September 13 checkpoint, the full suite passed 300 tests. Sixteen new release-review tests cover changed
text/locators/files/metadata/context, removed clauses, malformed/tampered releases,
stale or altered captures, scope narrowing and command behavior. Eleven axle tests
cover intake, reconciliation, invalidation, role equality and form read logic.
The small DOM substitute verifies form logic; it does not establish browser
rendering, accessibility or interaction acceptance.

The [final local capture](../audits/release-engineering-final-2026-09-13/README.md) records
real stdio and HTTP exchanges against the pinned Neo4j release. No language model
was invoked. The restricted application proposal bridge remains unattached.

| File | Responsibility |
| --- | --- |
| `neo4j_kg/axle_layout.py` | Strict individual layout normalization and defensive reconciliation. |
| `neo4j_kg/trip_models.py`, `trip_state.py`, `input_review.py` | Accepted facts, assignment invalidation and correction handling. |
| `neo4j_kg/trip_tools.py`, `requirements.py`, `followups.py` | MCP schema, requirement intake and questions. |
| `trip_app/static/app.js` | Individual row editor and controlled report display. |
| `neo4j_kg/source_review.py` | Inventory, exact review packet and candidate impact analysis. |
| `neo4j_kg/release_readiness.py`, `tools/review_release.py` | Scope, source integrity and capture binding review. |
| `tools/verify_release_engineering.py` | Reproducible live synthetic capture, including prior reported checks. |
