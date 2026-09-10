# A graph that can explain what is still missing

Status: prototype design, September 6, 2026. Not user-approved operational policy.

The first question is narrow: what does the supplied evidence establish about
this driver's APM Elizabeth induction? The broader questions about dispatch,
licenses, permits, and Port Street define the model's expansion path, but this
first evaluator does not pretend to answer all of them.

## Public evidence and private trip facts

```text
Source document ─contains─> Source clause ─supports─> Requirement version
       │                         │                        │
 publisher + dates        exact text + locator       applies within scope
                                                         │
Trip ─assigned─> Driver ─uses─> SeaLink identifier          │
 │                │                  │                    │
route          Induction evidence ─for identifier─────────┘
 │                │
ordered        program + result + checked time + provenance
segments                          │
 │                         Deterministic evaluation
authorities                  result + missing facts
                            + sources + coverage limits
```

The public graph contains authorities, terminal facilities, route families,
directed segments, document versions, exact clauses, scope relationships, and
prototype check definitions. Public source text never contains private driver
credentials. A future authenticated adapter supplies private, time-bounded
driver, vehicle, trip, permit, and observation records. Evaluation results are
new records, never edits to a requirement or source clause.

An induction record belongs to the program, driver and SeaLink identifier used
for that record. A change of company does not by itself invalidate it. Evidence
for an old number does not establish completion for a new number, but also does
not establish that the driver failed to retake it. No training expiry duration
is invented.

## What each relationship can establish

| Relationship | Meaning and boundary |
| --- | --- |
| Document CONTAINS_CLAUSE clause | Exact retained evidence, not a compliance result. |
| Authority/operator ATTRIBUTED_REQUIREMENT requirement | Rule attribution; distinct from the document publisher. |
| Clause SUPPORTS check definition | Explicit, versioned prototype interpretation requiring human review. |
| Route HAS_ORDERED_SEGMENT segment | Direction and order, not truck permission. |
| APM PUBLISHES_DIRECTIONS_FOR route | APM lists the route; not a legal designation or a clearance certificate. |
| Requirement APPLIES_WITHIN scope | Applicability predicate evaluated from trip facts, not inherited from the old project profile. |
| Observation ABOUT subject | Time-bounded evidence with provenance, not a timeless boolean. |
| Evaluation USED evidence/version | An auditable result tied to exact facts and versions. |

The importer preserves the archive's existing relationships and attributes in
an archive layer. They are available for inspection, not automatic runtime rule
activation. In particular, existing `PUBLISHES` edges do not overwrite the
registry's document publisher. `graph_eligibility` remains a visual/archive
classification and is not a service permission flag. Mutable conditions remain
in a quarantined layer with no executable restriction edges.

## Checking contract

Every result separates applicability, evidence sufficiency, factual assessment,
and operational coverage. The four factual outcomes are:

- `met`: required supplied facts establish this one prototype check.
- `not_met`: supplied evidence explicitly establishes a missing requirement.
- `unresolved`: applicability/evidence is missing, stale, conflicting, unavailable,
  or associated with the wrong subject/identifier.
- `not_applicable`: the known facts are outside this check's explicit scope.

Missing destination or role is unresolved, not not-applicable. An unsupported
terminal is outside this check, not exempt from all terminal requirements.
Conflicting evidence stays unresolved; neither an LLM nor a last-write-wins rule
may select a convenient answer. Inputs are validated strictly, unknown fields
are rejected, and evidence/rule versions accompany results.

The prototype uses synthetic, server-owned evidence fixtures. A chat model can
identify the synthetic driver and trip facts; it cannot mint a verified
completion record or change the rules. This tests the trust boundary before
real credential integrations exist. Fixture IDs are not real SeaLink numbers.

Even a `met` result is a synthetic, single-requirement finding. The response
must separately say that current policy and the other trip requirements remain
unchecked. No `safe_to_dispatch` or broad `can_enter=true` field exists.

## Coverage beyond induction

The existing six scenario families are design requirements, not six completed
evaluators. The 96 archived responses are repeated measurements of those six
families, not 96 independent trips. All six are unresolved cases.

| Family | Relationships and missing facts the graph must represent |
| --- | --- |
| S1 axle facts | Vehicle/load, individual and grouped axle weights, spacing, road regime, permit scope. Gross weight alone is insufficient. |
| S2 route dimensions | Loaded dimensions, direction-specific segments, legal route classification, terminal access, current postings. Absence from a list is neither prohibition nor permission. |
| S3 permit handoff | Permit version, issuing authority, permitted vehicle/load/time/route, and separate county/toll/port/terminal approvals. |
| S4 Port Street | Observation time, source-stated start, direction, affected segment, vehicle scope, live status and approvals. No universal height rule inferred from a bulletin. |
| S5 DTR conflict | Vehicle/engine, registration event, active record, ownership change, RFID, temporal tariff blocks and explicit unresolved interpretation. |
| S6 terminal access | Driver credentials, SeaLink/TWIC registration, induction tied to identifier, appointment tied to move, same-day gate state. |

Adding each evaluator requires a reviewed clause-to-check mapping, source
currentness strategy, positive and negative fixtures, and missing/conflicting
evidence tests. A generic question outside induction returns a coverage gap,
not an inferred answer from similar text. The graph does not compute navigable
truck routes or certify bridge clearance.

## Storage and chat integration

NetworkX is an actual in-memory attributed multigraph with traversal queries.
The canonical JSON archive remains the durable evidence source. This prototype
does not provide durable private records, concurrent transactions, access
control, migrations, backup, or a graph database query endpoint. Those are
production requirements, not hidden capabilities.

TypeDB remains a candidate for a later persistent schema with role-based
relations. No vendor choice was approved. LangChain or another agent framework
can wrap the service later, but it must not become the authority for deciding
requirements or erasing conflicts.

One transport-neutral service owns normalization and checking. A read-only MCP
tool exposes it to a chat provider. Consumer-app verification must capture the
app's tool call, service result and final answer. Manually pasting a JSON result
into a chat only tests narration. API testing tests that API harness, not the
consumer app. App availability/account requirements must be checked separately.

## Human decisions still open

Approve or revise the induction evidence model; choose an operational evidence
verification/freshness policy; choose persistent graph storage and hosting;
choose any additional consumer-app connector/hosting setup; review each new
consequential rule interpretation before enabling real trip checks.

## First provider findings

The [Claude Desktop run](claude-provider-results.md) exercised the complete
consumer-app → local tool → graph service → answer path on six frozen synthetic
cases. The evaluator returned the expected induction outcome each time, but the
model changed the requested scope in two calls. It also confused real source
evidence with synthetic driver data once, overstated the exclusivity of a
retraining trigger, and mixed status-field labels in an answer.

These observations support keeping input extraction, deterministic evaluation
and answer fidelity as separate checks. They do not prove a graph is necessary
or sufficient for safe trips. Proposed output-contract improvements are recorded
in that report for review; no provider failure was hidden by revising this run's
prompts, tool descriptions, fixtures or expected outcomes.
