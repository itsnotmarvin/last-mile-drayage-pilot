# Source-bound reported-fact checks

September 13, 2026. Implemented in the local Neo4j MCP and trip application.
The catalog contains **23 draft reported-fact checks bound to 19 retained
clauses**: 11 numerical comparisons, seven reported prerequisites, and five
explicit manual gaps. These are not 23 completed legal evaluators. Only the
existing synthetic induction evaluator produces executable requirement findings;
the requirement coverage and broad unresolved trip status are unchanged.

## What a driver or dispatcher gets

For a reported loaded height of **175 inches**, the service retrieves the
retained NJ guide clause, compares the report with its **162-inch** reference,
and explains the **13-inch excess**. It separately compares the same report
with the terminal's **195-inch** approval reference. Being below that terminal
reference does not resolve the roadway issue. The first action is to confirm
the loaded height and resolve the actual route, applicable exceptions and
required oversize authorization with the carrier and road authorities.

A reported missing appointment or RFID produces a specific prerequisite problem
and next action. A matching report remains unverified. Unknown values remain
unknown. Drivers and dispatchers receive the same comparisons and evidence for
the same trip facts; role does not lower the evidence standard.

The new `reported_fact_checks` package is additive to the existing assessment.
It includes the source bindings, reported inputs, reference and signed difference,
status, scope context, next action and responsible party. Up to three deduplicated
actions prioritize input/source corrections and then known reported problems
before general missing-fact questions. The original `next_questions` list remains
available separately. The local application and controlled HTML export display
these results with source titles and locators.

## Status contract

| Status | Meaning |
| --- | --- |
| `attention_required` | A reported number exceeds the cited reference, or a reported boolean does not match the described prerequisite. Applicability and exceptions remain unresolved. |
| `comparison_only` | A number is at or below the reference. This does not mean the requirement is met. |
| `reported_unverified` | A boolean report matches the prerequisite; no authoritative verification occurred. |
| `missing_facts` | A required reported fact is unknown; no comparison occurred. |
| `input_review_required` | Conflicting, inconsistent or invalid input suppresses the comparison. |
| `source_review_required` | A clause, source identifier, locator or source-text digest no longer matches the frozen catalog; the comparison is suppressed. |
| `manual_review_required` | The required interpretation, calculation or authoritative verification remains unimplemented. |

The package itself is `available` or `unavailable`. An evidence outage returns
no checks or priority actions from cached evidence. A different graph release
returns `UNREVIEWED_GRAPH_RELEASE`, even if some quoted text is unchanged.
Every package carries `approval_status: draft_not_human_approved` and
`operational_permission: not_issued`. No comparison promotes an existing
requirement to `met`, issues terminal entry, or authorizes dispatch.

## Evidence and execution boundaries

The catalog is pinned to graph release
`f5dffe0f7a32b5144920efb5a644f8c4dc9f20def76b4217c38b0cdbc454cf5c`.
Each binding preserves the clause's source ID, raw locator and source-text digest
calculated with `neo4j_kg.common.digest`. Evaluation uses the evidence package
already retrieved for the selected requirements. It does not issue arbitrary
queries, search the whole repository, or fetch current law from the web.

Inputs use the trip service's normalized units. Arithmetic uses `Decimal` and
requires positive finite measurements. It does not infer a roadway category,
resolve conflicting reports, or interpret missing values as false. Permit-specific
comparisons run only for the explicitly reported permit category. Selecting a
category does not establish that the permit exists or covers this move.

Several distinctions are necessary before further evaluators can be enabled:

- **Axles and bridges:** the retained federal clause introduces the bridge
  formula but omits its equation and complete grouping/exception rules. The
  existing axle array accepts individual axles or axle groups. No bridge or
  individual-axle calculation is derived from that ambiguous input.
- **Road access:** 96- and 102-inch width references remain separate; route IDs
  and graph topology do not establish legal road classification. The 48-foot
  semitrailer comparison is an access trigger, not a general length prohibition.
  Lower bridge limits and separate authority approvals remain relevant.
- **Terminal limits:** terminal dimension/weight references do not establish
  roadway permission. The 128,000-pound comparison retains container applicability
  and manufacturer working-load qualifications; those are not evaluated.
- **DTR:** the retained tariff interpretation conflict remains unresolved.
  Engine year alone never produces eligibility or a categorical rejection.
- **Verification and conditions:** reported TWIC, SeaLink, DTR, RFID and
  appointments are not registry lookups. A timestamp or archived bulletin does
  not establish current route or gate conditions. Transaction-release checking
  still lacks a retained governing clause and authoritative verification.

Rule freshness and operating-condition freshness are separate. Stable rules can
remain on a reviewed pinned release until a material change is identified;
operating conditions need suitable timely evidence for the move. This increment
implements source binding and suppression on changed inputs/releases, not a
source-monitoring service or a guarantee that the archived law is current.

## Code map

| File | Responsibility |
| --- | --- |
| [`data/reported_checks.json`](../data/reported_checks.json) | Frozen definitions, references, conditions, scope context, actions, owners and exact source bindings |
| [`neo4j_kg/reported_checks.py`](../neo4j_kg/reported_checks.py) | Source validation, comparison arithmetic, report statuses, suppression and priority actions |
| [`neo4j_kg/assessment.py`](../neo4j_kg/assessment.py) | Adds the package to fresh assessments and evidence-outage responses; versions the catalog and engine |
| [`neo4j_kg/trip_tools.py`](../neo4j_kg/trip_tools.py) | Strict MCP output schema and model-use instructions |
| [`neo4j_kg/decision_brief.py`](../neo4j_kg/decision_brief.py) | Action ordering and controlled HTML presentation |
| [`trip_app/static/app.js`](../trip_app/static/app.js) | Browser rendering through DOM text nodes |
| [`tests/test_reported_checks.py`](../tests/test_reported_checks.py) | Numeric boundaries, prerequisites, conflicts, source changes, scope and schema controls |
| [`tools/verify_reported_checks.py`](../tools/verify_reported_checks.py) | Captures separate-process stdio assessments against live Neo4j with source files held unchanged |

## Verification and review

**273 local tests pass.** The final live capture contains **20 assessments across
ten matching driver/dispatcher pairs** through stdio MCP and live Neo4j. This is
backend verification with synthetic facts; no language model was invoked.
The [final audit](../audits/reported-checks-final-2026-09-13/README.md) records the
exact requests, responses, runtime hashes, HTTP check and connector activation.

The [source-to-check review matrix](reported-check-review-matrix.md) lists every
definition, source locator and remaining scope or verification issue. The matrix
is generated from the draft catalog; it is a review aid, not human approval.
Browser interaction, accessibility, responsive layout, actual released model
behavior and the [production requirements](production-readiness.md) remain open.
