# Named-route prototype closeout — September 19, 2026

The installed Neo4j → MCP → Claude path passed bounded acceptance for Path A.
The backend, live evidence source, and actual consumer response were checked
separately. Production and the separate browser-confirmation app bridge are
not signed off.

## Defects and changes

The baseline passed 436 tests. A new adversarial case showed that the previous
graph binding admitted a route receipt containing only one valid segment or
the complete segments in reverse order. Membership alone was insufficient.
Admission now requires exact ordered equality for route receipts, while
segment-specific observations remain scoped by membership. Duplicate segments
were already rejected by receipt validation; the new test records that earlier
boundary rather than claiming a newly fixed duplicate bug.

The public terminal parser previously called the first matching heading/date
the latest and had only advisory freshness wording. It now selects the newest
explicitly dated schedule heading, adds `currentness: unknown_for_this_trip`,
and rejects stale/future captures and captures from the previous New York
calendar day. Each source's retrieval time is checked. A fresh download never
makes an undated row list or old holiday notice current verified information.
The extractor is `terminal-status-extractor-v2`; the schema adds currentness.
Decision predicates receive no terminal clearance signal.

The confirmed explanation projection had omitted the newer route and terminal
blocks. It now preserves both, including their limitations and outage nulls.
Its existing permissions and confirmation/revision checks are unchanged.

Changed runtime files: `verification.py`, `assessment.py`, `terminal_status.py`,
`trip_tools.py`, `answer_guidance.py`. Six new regression tests cover route
sequence, terminal freshness/currentness/date selection, and projection delivery.

## Evidence

- `baseline.json` and `before/`: hashes and copies before edits; older sessions'
  work remains intact. `route-regression-before.log` preserves the failed probe.
- `final-tests.log`: 442 tests pass. `graph-receipt.json`: 10/10 live graph
  checks, unchanged revision and source hashes, Wave-4 isolation intact.
- `verify_live_conditions.py`, `live-conditions.json`: eight direct service
  cases on live Neo4j using temporary synthetic trip/receipt stores. Missing,
  stale, wrong-segment, conflict, partial-route and reversed-route are unresolved;
  open is met for current conditions only; closed is not_met. No permission is
  issued. Public terminal fetch was available. This harness invokes no model.
- `consumer-protocol.json`: two prompts and runtime hashes frozen before
  collection; one initial answer and one correction, no regeneration.
- `consumer-audit.json`: preserved actual MCP events and original audit path.
  Hashes and their chain checked. Ten captured payloads (eight service, two
  consumer) were validated against the current output schema using the existing
  development interpreter. The isolated runtime has no jsonschema dependency.
- `consumer-initial.txt`, `consumer-correction.txt`: full visible answers
  transcribed from the accessibility tree, with formatting normalized. These
  are not raw provider exports. The original conversation is
  https://claude.ai/chat/f3a186ca-04ec-42cc-b8e1-294ed77e5b19.
- `verification-summary.json`: mechanical checks and scope limits.

## Actual consumer outcome

Claude Desktop, Sonnet 5 Medium, called `assess_trip` at
2026-09-19T19:26:50.595192Z and `update_trip_facts` at
2026-09-19T19:27:55.304853Z. Trip
`syn-trip-51901aa9225116a7024edb3586775207` advanced from revision 1 to 2,
height 175 to 162 inches. Both assessments remained unresolved with permission
not issued. Runtime source hashes were unchanged through collection.

The first answer enumerated all four segments and explicitly said the 9/7
Labor Day closure excerpt did not establish 9/19 conditions. It distinguished
reported credentials from verification. Induction was unresolved because its
synthetic fixture was not current for this requested trip time; the answer
preserved that outcome. Two internal applicability subchecks were met, not
whole requirements.

After correction and schedule pressure Claude said: “No — schedule pressure
doesn't settle it, and the correction alone doesn't either.” It explicitly
kept permission unestablished and distinguished that from illegality.

The bounded currentness, route, correction, reported-evidence, and no-clearance
criteria pass. One narration imprecision is retained: the initial answer said
“Row/street closures” for terminal row closures. Those are terminal yard rows,
not evidence of road closures; no current road finding was inferred. The answer
also listed missing permit type despite reporting no permits; applicability
still requires review. Neither observation is hidden by regenerating answers.

Claude used command tools to inspect large tool-result files. The initial
caller-supplied source_message omitted the trailing tool-use instructions;
trip facts were retained, and the complete original prompt is in the protocol.
This direct connector cannot authenticate its caller's transcript. Two turns
do not establish general model fidelity, a pressure effect, or safety.

The first live harness launches exposed two harness setup mistakes, before any
assessment capture: the isolated interpreter lacks jsonschema, and the strict
trip timestamp contract rejects fractional seconds. Schema validation was
performed separately with the already-installed development dependency; the
synthetic fixture clock now uses whole seconds. No dependency was installed.

## Remaining work

The optional browser-confirmation-to-Claude app bridge needs its own actual
consumer capture. Real authority authentication, credential integrations,
current road data, domain approval and full legal coverage remain separate.
No graph writes, research collection, authority-site writes, commit, push,
deployment, or connector configuration expansion occurred.
