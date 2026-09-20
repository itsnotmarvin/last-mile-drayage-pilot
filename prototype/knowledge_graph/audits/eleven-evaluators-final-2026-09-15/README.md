# Eleven bounded evaluators — final live audit, September 15, 2026

Live capture of all eleven requirement evaluators through the MCP (stdio) and
the local driver/dispatcher app (HTTP) against the pinned Neo4j release
`f5dffe0f...` (144 prototype records, 228 relationships). The Aura instance was
PAUSED at handoff and resumed before this run; the secure handshake and release
readback were verified first. No model prompts, no browser acceptance, no new
dependencies, no NetworkX in the runtime, no commit or push.

An earlier capture the same day (`../eleven-evaluators-2026-09-15/`) ran green
on every assertion but could not finish its saves: the verifier wrote
`operator-fixture-events.json` twice with exclusive-create and crashed after
all checks passed. That directory is preserved as the intermediate checkpoint
(completed manually from its transcripts, with a capture note). The verifier
was fixed (stdio events now save under their own name) and this is the clean
re-run: every file below comes from a single invocation.

## Measured results

| Check | Result |
| --- | --- |
| Live stdio assessments | 28, all service available |
| Live HTTP assessments (driver + dispatch) | 6, all service available |
| Post-seed positives, 10 of 11 evaluators | met (driver == dispatcher semantics) |
| `dtr_engine_policy` on every assessment | unresolved (`UNRESOLVED_DTR_TARIFF_CONFLICT`) |
| Eleven targeted negatives (weight, height, revoked permit, denied approval, closed conditions, RFID, engine, TWIC, SeaLink, appointment, transaction) | not_met (engine: unresolved by construction) |
| Revocation recheck (stdio + HTTP) | unresolved, new assessment id |
| Load reassignment | old receipts rejected, none accepted |
| Caller-supplied verification injection | rejected with error |
| Served `app.js` vs runtime hash | match |
| Runtime hashes before vs after | unchanged |
| Operational permission on all 34 assessments | not_issued |
| Local unit suite at capture | 387 passed, 480 subtests passed |

## Independent reviews closed in this increment

- [Terminal policy review](../eleven-evaluators-2026-09-15/terminal-policy-review.md):
  every hardcoded terminal constant (34-1101 threshold and 2014 standard,
  34-1140 year blocks, 10-day amendment, pre-entry registration, Class 8 RFID,
  TWIC scope/expiry/possession, SeaLink registration, APM slot, import-pickup
  holds) checked against its retained clause text. No contradictions; adapter
  semantics are disclosed in their check details and fail toward unresolved.
- Contradictory-evidence review: disagreeing admitted receipts force unresolved
  at `evaluate_requirement` (all non-segmented kinds) and per segment/authority
  in `_segment_evidence`; conflicting user reports, missing facts, and
  source-coverage gaps force unresolved in `evaluate_trip`. No pass-on-conflict
  case in the current tree; regression tests pin the reviewed modes.

## Files

`summary.json` (counts, hashes, surface limits), `assessments.json` (34),
`mcp-transcript.json`, `http-transcript.json`, `operator-fixture-events.json`
(complete) plus `operator-fixture-events-stdio.json`, `tools.json`,
`transaction-evidence.json`, `sample-trip-report.html`, `stdio-stderr.txt`.

## Limits

Synthetic fixtures only; the operator seeds receipts outside client endpoints.
Browser acceptance was not run (prior `ERR_BLOCKED_BY_CLIENT` unresolved).
No model answer-fidelity test. The eleven evaluators do not cover current
policy, CDL, gate state, live conditions, alternative-truck status, non-import
moves, or non-APM terminals. Production remains blocked per
[production-readiness](../../docs/production-readiness.md), and the full
evaluator contract is in [requirement-evaluators](../../docs/requirement-evaluators.md).
