# Input consistency and controlled trip reports

The current trip tools reject recognized contradictions between extracted facts
and the supplied source text before writing a case or request receipt. A rejected
update leaves the prior revision and history intact. After clarification, the
caller can retry the rejected request key because no write was committed.

`neo4j_kg/input_review.py` currently recognizes:

- Labeled height, width, overall length, and semitrailer length in feet/inches,
  including mixed values. A recorded 14 feet conflicts with “14 feet 7 inches
  high”; 175 inches preserves that measurement. Several labeled values require
  clarification rather than selection of a convenient value. The comparison
  allows only 0.00001 inch for numeric conversion roundoff.
- A timestamp paired with a recognized date but no stated clock time, or a
  date/time without a recognized explicit timezone. These require clarification.
- Certain explicit unknown approval statements converted to true or false,
  lack of verification converted to absence, and certain permit-need questions
  converted to a report of no permit. An explicit positive possession report
  may remain a report even when the user says it is unverified.

These checks are deliberately bounded. They are not a natural-language parser,
date resolver, general verifier of claims, or proof that facts match the actual
user conversation. Another time elsewhere in a message can satisfy the clock
check; temporal association is not established. Qualifications, negation, other
subjects, unsupported expressions, and omissions require fuller application
review. Several measurements may describe different subjects; the guard asks
for clarification instead of assuming which one is the current truck.

Both facts and `source_message` still come from the MCP caller. Changing both can
evade a consistency check. Every assessment therefore includes `input_review`
with `text_origin = caller_supplied_not_authenticated_transcript`,
`confirmation_status = not_independently_confirmed`, and all concrete fields in
`unconfirmed_fields`. `no_detected_conflict` is never promoted to verified
extraction. There is no model-callable confirmation flag.

`normalize_facts` enforces the write guard for create and update paths. On
reassessment, `assessment.py` independently checks old saved records, excludes
known inconsistent fields from evaluation, reports an unresolved result, and
asks for correction. It preserves original facts and history for review. Failed
evidence reads still return the saved revision without cached findings.

## Decision display

Every trip assessment/update also includes a server-generated `decision_brief`.
It binds the brief to the trip, revision, assessment, scope, and scoped result.
It never issues operational permission. A synthetic induction match remains
visible as a scoped result while the trip's permission boundary stays explicit.
Input problems and evidence outages receive distinct headlines.

`neo4j_kg/decision_brief.py` renders a service result as inert HTML. The renderer
rebuilds its headline and status; it ignores arbitrary `assistant_answer` text
or a substituted brief. It escapes all reported facts and evidence content,
loads no external resources or scripts, and shows source dates/currentness.
This enforces the report's presentation, not Claude Desktop's separate prose.
The renderer does not authenticate an arbitrary externally supplied JSON object.

Export directly from a fresh assessment of a saved local synthetic case:

```sh
.venv-neo4j/bin/python tools/export_trip_report.py \
  --trip-id SYNTHETIC_CASE_ID_FROM_THE_SERVICE \
  --credentials-file /path/outside/repository/neo4j.env \
  --revision VALIDATED_GRAPH_RELEASE \
  --output .runtime/new-trip-report.html
```

The command uses `.runtime/trips.sqlite3` by default, accepts an explicit
`--state-file`, writes a private file, and refuses to overwrite an existing
report. It accepts no model answer or assessment JSON input. A report is a
revision-specific snapshot, not a live dashboard or an authorization token.
Reassess after corrections; the consumer application still needs to enforce
which current revision is displayed.

## Validation and boundaries

Run the full suite with `python3 -m unittest discover -s tests -v`. The focused
`tools/verify_input_review.py` uses actual saved Claude arguments against a fresh
stdio MCP process, an isolated synthetic case database, and live Neo4j. It does
not invoke a model or modify the original experiment. Its new output directory
contains exact responses, input capture hashes, runtime hashes, corrected
driver/dispatcher assessments, and a report from the saved current revision.

The [production release requirements](production-readiness.md) remain open.
Original user-message capture, application-owned confirmation, authenticated
ownership, a driver-facing controlled interface, broader evaluators, operational
verification, and deployed-client acceptance are not implemented by this increment.
