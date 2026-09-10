# Synthetic driver and dispatcher trip workflow

The MCP now accepts a trip conversation, retains facts between turns, and
reassesses the saved assignment after changes. Claude extracts facts from an
ordinary statement. Python validates the supplied values, saves their provenance,
queries the pinned Neo4j evidence release, and returns scoped findings plus up
to three follow-up questions.

This increment provides intake and evidence-readiness coverage for the six study
families. APM induction remains the only executable requirement check, using the
existing server-owned synthetic fixtures. Weight, dimensions, permits, road
conditions, DTR/RFID, TWIC, appointment, and transaction reports never become
verified legal findings just because the fields are filled in.

## Conversation contract

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

`get_requirement_evidence` returns exact retained passages and locators,
publisher, authority, archive dates, file hashes, source interpretation limits,
and named blockers. Structured and dated passages retain their original shape.
An empty source list explicitly identifies a source-coverage gap. No tool accepts
arbitrary Cypher, caller-created verification, or rule overrides.

## Code and storage

| Responsibility | Implementation |
| --- | --- |
| Typed values, explicit units, and report provenance | `neo4j_kg/trip_models.py` |
| Saved cases, revisions, conflicts, assignment invalidation, retry handling | `neo4j_kg/trip_state.py` |
| Thirteen requirement entries covering six study families | `neo4j_kg/requirements.py` |
| Bounded questions and verification actions | `neo4j_kg/followups.py` |
| Fresh evidence reads, scoped findings, coverage, and outage receipts | `neo4j_kg/assessment.py` |
| Lossless source retrieval and interpretation boundaries | `neo4j_kg/evidence.py` |
| Complete new MCP schemas and model instructions | `neo4j_kg/trip_tools.py` |
| Five-tool stdio transport | `neo4j_kg/mcp_server.py` |

Neo4j remains the primary graph store. Mutable synthetic conversation state lives
in private local SQLite at `.runtime/trips.sqlite3`, separate from the immutable
public evidence release. Every assessment performs a fresh Neo4j read and archive
integrity check. A provider failure returns the saved case revision and no cached
findings. Programming defects propagate to the MCP error handler.

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

This is still a local, synthetic prototype. There are no live credential,
appointment, registry, permit, road-condition, or gate integrations. The catalog
does not cover every legal duty, compute bridge formulas, or produce navigable
truck routes. Source ingestion and human approval of executable policy remain
separate work. Authenticated mobile access, dispatcher workspaces, retention
controls, operational monitoring, and a restricted database role are also future
work. The tool never returns whole-trip clearance.
