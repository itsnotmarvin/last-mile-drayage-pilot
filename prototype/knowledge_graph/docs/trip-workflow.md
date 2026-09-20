# Synthetic driver and dispatcher trip workflow

Current application integration: [driver and dispatcher workspace](integrated-trip-workspace.md).
It adds original-statement capture, explicit review, local identities/sharing and
controlled results above the existing trip/Neo4j service. Historical limitations
below describe their original checkpoint unless explicitly updated.

The MCP now accepts a trip conversation, retains facts between turns, and
reassesses the saved assignment after changes. Claude extracts facts from an
ordinary statement. Python validates the supplied values, saves their provenance,
queries the pinned Neo4j evidence release, and returns scoped findings plus up
to three follow-up questions. Each assessment now includes the supporting
passages and their requirement links in `evidence_package`.

Current coverage includes induction and [eleven bounded receipt-backed
evaluators](requirement-evaluators.md) across the six study families. Their
operator-owned synthetic records are separate from user reports. Filling in
weight, dimension, permit, condition, DTR/RFID, TWIC, appointment or transaction
fields cannot establish verification. See the [September 16 closeout](../audits/evaluator-closeout-2026-09-16/README.md)
for current verification evidence and its limits.

## Conversation contract

The [input consistency guard](input-review.md) rejects recognized contradictions
before a write. Assessments include explicit unconfirmed-extraction review and a
deterministic `decision_brief`; old saved inconsistencies are excluded from
evaluation and returned for correction. A private report exporter renders the
service status directly. This does not control Claude Desktop's separate prose.

Drivers and dispatchers use the same evidence standard and conversational flow.
The model can leave requester role unknown; there is no role-selection gate.
Each conversation starts a separate case. Follow-ups retain that case; an
explicitly new move starts another case with only the facts supplied for it.
The model must clarify an ambiguous continuation and must not copy trip IDs,
request keys, or reports from another conversation.

This is a model instruction backed by separate local case records, not an
authenticated multi-user boundary. The server does not bind a case to a logged-in
person or enforce conversation ownership. Case IDs and request keys are not
authorization credentials. A shared driver/dispatcher deployment still needs
server-enforced ownership and authorized sharing.

`assess_trip` creates a synthetic case from `facts`, the original
`source_message`, and a unique `request_key`. The requester can be a driver,
dispatcher, other person, or unknown. `subject_role` separately describes the
person being assessed. Omitted scope is `unknown` and selects broad coverage;
only an explicit induction question receives a narrow induction assessment.
The model supplies the extracted facts and source-message field; the service
cannot independently guarantee a verbatim UI transcript. The consumer capture
retains the original prompt separately and records Claude's abridged provenance.

`update_trip_facts` takes the returned `trip_id`, `expected_revision`, current
requester/scope, and new or corrected facts. Exact retries with the same request
key do not write twice. A conflicting revision fails with the current revision
in its error. A retried old write returns its original `write_receipt` while the
assessment uses the latest `case.revision`; it cannot restore a superseded pass.
Contradictory reports stay in the case until explicitly corrected. One update
can correct one independent existing fact and include fresh dependent facts for
that replacement. Separate unrelated corrections use separate updates.
The full local history retains previous observations and corrections; MCP
responses include current provenance and active conflicts without repeating the
entire history.

`assess_trip` and `update_trip_facts` return one deduplicated evidence package
from the same Neo4j read transaction as the findings. `sources` contains the
selected catalog's passages; `requirement_links` maps each finding to those
passages. The selection is a static, versioned requirement mapping, not a
dynamic determination that every cited rule applies to this trip. The model
can explain the assessment using the included evidence without a second call.

`get_requirement_evidence` remains available for a focused requirement. It returns exact retained passages and locators,
publisher, authority, archive dates, file hashes, source interpretation limits,
and named blockers. Structured and dated passages retain their original shape.
An empty source list explicitly identifies a legal-source coverage gap. No tool accepts
arbitrary Cypher, caller-created verification, or rule overrides.

The Port Street bulletin is returned separately in `observations`, preserving
its complete original record, direction-specific text, source-stated effective
date, observation time, and currentness limits. Broad route assessments include
it when Port Street membership is reported, unknown, or conflicted. An
unconflicted report that Port Street is outside the route omits it; a narrow
scope also omits it. Neither choice establishes route permission. The focused
`current_route_conditions` endpoint also includes the bulletin.

Two release-scoped `provenance_review` annotations identify a corrected PDF
page locator and a table transcription previously labeled verbatim. The model
is instructed to use the reviewed locator and describe the table accurately.
Original source fields remain intact for replay. These development review notes
do not amend the archive or approve executable policy.

## Code and storage

| Responsibility | Implementation |
| --- | --- |
| Typed values, explicit units, and report provenance | `neo4j_kg/trip_models.py` |
| Saved cases, revisions, conflicts, assignment invalidation, retry handling | `neo4j_kg/trip_state.py` |
| Thirteen requirement entries covering six study families | `neo4j_kg/requirements.py` |
| Bounded questions and verification actions | `neo4j_kg/followups.py` |
| Fresh evidence reads, scoped findings, coverage, and outage receipts | `neo4j_kg/assessment.py` |
| Lossless source retrieval and interpretation boundaries | `neo4j_kg/evidence.py` |
| Release-scoped extraction review annotations | `neo4j_kg/provenance_notes.py` |
| Complete new MCP schemas and model instructions | `neo4j_kg/trip_tools.py` |
| Five-tool stdio transport | `neo4j_kg/mcp_server.py` |

Neo4j remains the primary graph store. Mutable synthetic conversation state lives
in private local SQLite at `.runtime/trips.sqlite3`, separate from the immutable
public evidence release. Every assessment performs a fresh Neo4j read and archive
integrity check. An evidence-service failure returns the saved case revision,
an unavailable evidence package, and no cached findings or passages. Programming
defects propagate to the MCP error handler.

A fresh database read uses the pinned evidence release; it does not automatically
fetch the latest law. Source changes need review and a new release. Stable rules
can retain their reviewed version, while a dated road bulletin requires a check
of current conditions for a real move. This patch does not add change monitoring.

The runtime remains `.venv-neo4j/bin/python run_neo4j_mcp.py`, without NetworkX.
The historical `kg/` package and original captures remain unchanged. The existing
two tools preserve their result contracts; the three trip tools use new versioned
schemas. The two state-writing tools advertise that they mutate local data.

## Verification and limits

Run `python3 -m unittest discover -s tests -v` from the prototype directory.
The new schema test uses `jsonschema` already installed in the development Python;
the MCP runtime does not import it or require it. The live stdio proof uses
`tools/verify_trip_workflow.py` with the isolated runtime and protected credentials
file. Captures and measured consumer behavior are recorded in `trip-validation/`.

The six scenario-family controls are new synthetic implementation tests. They
do not replace or regrade the frozen 96-response Wave4 experiment. Scoped positive,
negative, and non-applicable induction controls test useful resolution as well
as unresolved outcomes.

The [September 12 evidence fix](../audits/evidence-fix-2026-09-12/README.md)
passed 216 local tests and a fresh live Neo4j/stdio audit: all 24 broad assessment
responses contain the frozen cases' expected passages, and eight controls pass.
This verifies backend delivery, not Claude's extraction or final wording. Broad
responses currently carry 26 passages, approximately 51 KB of evidence JSON;
performance and model context costs remain optimization work.

This is still a local, synthetic prototype. There are no live credential,
appointment, registry, permit, road-condition, or gate integrations. The catalog
does not cover every legal duty, compute bridge formulas, or produce navigable
truck routes. Source ingestion and human approval of executable policy remain
separate work. Authenticated mobile access, dispatcher workspaces, retention
controls, operational monitoring, and a restricted database role are also future
work. The runtime retrieves the pinned evidence subset, not the entire GitHub
repository or every PDF. The tool never returns whole-trip clearance.
