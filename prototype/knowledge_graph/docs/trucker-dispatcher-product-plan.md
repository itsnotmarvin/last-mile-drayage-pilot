# From the induction prototype to a trucker and dispatcher assistant

Status: the first saved synthetic trip workflow is implemented; see
[the implementation guide](trip-workflow.md) for the shipped boundary. The larger
plan below retains the starting gaps and future work. This document does not
approve operational policy. The product serves drivers and dispatchers asking ordinary
questions about a specific movement to APM Elizabeth. The research archive and
evidence repository support that product; repository exploration is not its main
user interaction.

## Desired interaction

A user describes a trip in ordinary language. The model extracts only supported
facts, calls the assessment service, asks focused follow-up questions, updates
the same trip, and explains the resulting findings and actions. The service
selects applicable reviewed requirements and computes findings. The model does
not independently issue a broader conclusion than those findings support.

Driver and dispatcher views use the same trip assessment. A dispatcher sees
the assignment, unresolved dependencies, evidence owners, and time-sensitive
actions. A driver sees the relevant personal/vehicle/trip questions and actions.
Changing who asks, or adding urgency, must not change the evidentiary standard.

## Current implementation and concrete gaps

The live `neo4j_kg/` runtime has two read-only tools, a persistent 144-record /
228-relationship release, one synthetic induction evaluator, exact citations,
versioned results, and explicit unchecked coverage. Migration verification
includes 124 local tests, 22 live evaluation cases, five live context topics,
and three actual Claude Desktop tool calls. These establish the bounded
implementation, not full trip assessment.

`neo4j_kg/service.py` accepts only terminal, actor role, synthetic driver,
synthetic SeaLink, timestamp, question scope, and company-change facts. Weight,
dimensions, axle facts, route, cargo, permits, DTR/RFID, TWIC, appointment, and
transaction status cannot be supplied through the checking tool. There is no
trip session, cross-turn fact history, assignment, or follow-up policy.

`actor_role` describes the check's subject and offers only `truck_driver` or
`other`. Add an independent requester role; a dispatcher asking about a driver
must not be represented as an out-of-scope subject. Omitted question scope
currently defaults to induction. Replace that default in a versioned contract;
unknown user intent must not silently narrow a whole-trip question.

The existing static `UNASSESSED` list discloses broad gaps but is not a dynamic
requirement selection or assessment system. Source clauses and project-profile
applicability classifications are evidence, not approved executable checks for
arbitrary trucks. Synthetic fixture dates are test controls, not real credential
expiration policies. Existing fixture identifiers remain in the test adapter.

## Keep

- Neo4j persistence, parameterized queries, release identity, citations, and
  distinctions among original source text, observations, interpretations, and
  findings.
- Explicit missing/conflicting evidence and operational coverage boundaries.
- The existing induction evaluator as one modular check and its frozen cases.
- The historical `kg/` package and experimental captures as reproducible
  baselines. Preserve original findings and add new runs separately.

## Add the trip model and conversation state

Represent the requester separately from the assessed driver, vehicle/trailer,
load, terminal/movement, route, and intended trip time. An assignment binds those
subjects to the movement. Use anonymous case IDs in development; do not remove
the synthetic-only restriction and start accepting real credentials before
appropriate authentication, access controls, retention, and verification exist.

Each fact retains its typed value and units, subject, source utterance or
document locator, who reported it, observation time, verification state, and
validity interval when established. Unknown, explicitly absent, conflicting,
and not-yet-checked are different conditions. A driver statement is recorded as
a statement; it is not upgraded to registry verification. Do not inherit values
from the repository's representative vehicle profiles into a user's trip.

Parse ordinary language, mixed units, corrections, and relative dates with an
explicit time-zone/reference context. Validate extracted values in Python and
ask when a material ambiguity remains. Record corrections as new fact versions.
Changing the assigned driver, truck, route, or date invalidates dependent
findings and triggers reassessment. Never carry a previous assignment's pass
into a new one. Questions should reuse facts already given, prioritize decisive
missing facts, explain why they matter, and identify who can provide them.

## Refactor the decision service

Suggested modules within a new, versioned assessment layer:

- `trip_models.py`: typed trip facts, units, provenance, assignment identity.
- `trip_state.py`: case revisions, corrections, and isolation between cases.
- `requirements.py`: source-backed requirement versions and applicability.
- `checks/`: individual evaluators, starting with the existing induction check.
- `assessment.py`: requirement selection, execution, dependencies, and aggregate
  coverage; preserve blockers and missing information simultaneously.
- `followups.py`: actionable requests for missing facts/evidence, grouped by owner.
- `evidence.py`: source passages, authority/scope, currentness, and external
  verification results.

Each enabled requirement declares applicability conditions, necessary facts,
accepted evidence, evaluator/version, source clauses, review state, and freshness
conditions. Store queryable jurisdiction, terminal, vehicle/cargo scope, units,
and temporal fields in Neo4j alongside lossless source records. Many current
attributes are stored in `record_json`; selectively promote fields needed for
requirement selection instead of scanning JSON or making every text fragment a
graph node.

Per-requirement results can retain `met`, `not_met`, `unresolved`, and
`not_applicable`. Track execution state separately so a check that is not
implemented or whose provider failed cannot appear evaluated. Aggregation must
declare its assessed scope and coverage. A favorable overall result requires
the defined scope's necessary checks and acceptable evidence to be complete;
an incomplete requirement catalog cannot support a whole-trip conclusion.
Future-facing advice must not become conditional permission for an unresolved
present trip. Final gate admission also depends on the terminal's actual state.

## Expand MCP around the user's task

Proposed tools, not currently implemented:

- `assess_trip`: accept validated reported facts or a trip reference, evaluate
  the scoped movement, and return findings, coverage, sources, and next questions.
- `update_trip_facts`: apply explicit corrections/new facts to a versioned case;
  this is a mutation and must not be advertised as read-only.
- `get_requirement_evidence`: retrieve the rule explanation and exact supporting
  passage, original locator, authority, scope, dates, and conflict notices.

Require complete input/output schemas, explicit evidence types, predictable
status fields, tool error handling, and an answer contract that separates the
driver's report from established evidence. Retain the old two-tool interface
for regression comparison while the new contract is developed. User-facing
answers should lead with the assessed finding and next action, with technical
IDs and detailed evidence available on inspection.

## Evidence access, currentness, and delivery

Inventory and index relevant repository content by role: retained sources,
reviewed interpretations, geography, implementation, research results, fixtures,
drafts, and generated visuals. Preserve page/section/line provenance and original
files. Verify extraction quality for tables, scans, and relevant map geometry;
schematic visuals must not become navigable route evidence. Experiment responses
and representative profiles must not become authorities for operational checks.

Develop a reviewed source-to-requirement pipeline: extract candidate clauses,
review scope/exceptions/conflicts and accepted evidence, add evaluator tests,
publish a versioned release, and define when it needs rechecking. Ingestion of
more documents alone does not create new executable checks.

Static sources and changing registry, appointment, release, or road-condition
observations need different freshness policies. Use authorized authoritative
lookups where available; otherwise return the specific unresolved verification
and the appropriate manual action. Do not claim integrations already exist.

For the prototype, Claude Desktop can host the conversation. A trucker-facing
phone interface and dispatcher workspace can later share the same assessment
service. The current local stdio connector and absolute local file paths do not
provide remote/mobile delivery. Before real operations, add authenticated,
appropriately scoped case access, controlled data retention, a restricted
runtime database role, and dependable service operation.

Full database and local archive verification on every current tool call is
reasonable for the bounded migration but should not be the eventual latency
model. Preserve verified immutable release identities while moving bulk checks
to ingestion/deployment and monitored integrity checks, with separate freshness
enforcement for changing observations. Reassess relevant trip facts on updates.

## Implementation sequence and acceptance

1. Build one complete synthetic conversation: ordinary prompt → extracted trip
   facts → scoped requirement coverage → focused follow-up → fact update →
   reassessment → faithful driver/dispatcher answer. Include terminal access,
   weight/dimension/route intake, and explicit unimplemented coverage. Do not
   claim broad readiness just because induction succeeds.
2. Add the six existing scenario families as reviewed assessment modules:
   axle/spacing facts; dimensions and local access; cross-authority permit
   coverage; mutable Port Street conditions; DTR/RFID and unresolved tariff
   conflicts; driver credentials and terminal operations. Stabilize the existing
   induction work within terminal access, but prioritize local-access and
   changing-route-condition handling: these accounted for 13 of the 15 positive
   clearance labels in the frozen 96-response challenge set.
3. Run a new matched evaluation of conversation plus tools. Retain the original
   neutral/pressure prompts and frozen archive unchanged. Verify extraction,
   requirement coverage, follow-up relevance, evidence traceability, outcome,
   and final wording. Include corrections, dispatcher role, identity reassignment,
   unit ambiguity, conflicts, unavailable services, and missing current evidence.
4. Add independently reviewed cases in which sufficient evidence establishes a
   scoped positive result, known failure, or genuine non-applicability. All six
   original scenarios were unresolved cases, so that challenge set alone could
   reward a system that always refuses. Evaluate useful resolution as well as
   withheld unsupported clearance. Neutral and pressured versions with identical
   facts should yield the same evidence-based findings.
5. After the scoped assessment works, add real verification integrations and
   user delivery. Broaden route/vehicle/terminal scope only with corresponding
   reviewed evidence, checks, currentness handling, and tests.

Sources for this plan: the current `neo4j_kg/service.py`, `mcp_server.py`, and
`store.py`; parent processed vehicle/rule records; and the separate Wave4
archive's `README.md`, `docs/GOLD_DISPOSITIONS.md`, six scenario prompt families,
and `analysis/final_tables/by_scenario.csv`. Experiment counts are challenge-set
results, not estimates of real-world failure rates or proof of legal truth.
