# Trip workflow validation — September 10, 2026

The final implementation passes 200 local tests and 60 live Neo4j tool calls.
Claude Desktop also completed one actual `assess_trip` call from an ordinary
dispatcher prompt. Its free-plan quota then prevented a final answer and the
remaining follow-up turns. Consumer conversation validation is incomplete.

The tested runtime fingerprint is
`fa9d32e74a73958c8182b1d88878f37c52ca6c45c9a0f5a3f322c8f26e4cc019`.
The pinned evidence release remains
`f5dffe0f7a32b5144920efb5a644f8c4dc9f20def76b4217c38b0cdbc454cf5c`.

## Local and live checks

- `unit-tests.txt`: all 200 tests passed. This includes the preserved 124-test
  baseline and 76 new trip tests. A separate reviewer also ran all 200 tests and
  inspected conflict, retry, schema, provider-failure, and catalog-integrity edges.
- `trip-verification.json` and `trip-stdio-transcript.json`: 33 actual stdio tool
  calls through the isolated Python runtime with NetworkX absent. These cover
  creation, dispatcher correction, idempotent retry, saved-case reassessment,
  six family controls with unchanged-facts pressure variants, scoped positive,
  negative, non-applicable and unknown-scope controls, and all 13 evidence entries.
- `legacy-parity/`: all 22 frozen check cases and five graph context topics match
  their original substantive results. Historical captures were not overwritten.
- `captured-schema-validation.json`: the arguments and outputs of all 33 new live
  tool calls and the actual consumer call validate against the final MCP schemas.

These are synthetic implementation controls, not a new matched run of the
original 96-response Wave4 experiment or human approval of operational policy.

## Actual Claude Desktop capture

`consumer-plan.json` retains the three prompts and expectations written before
submission. `claude-tool-audit.jsonl` contains the full executed request and tool
response with a validated event hash. `consumer-results.json` records attribution,
field extraction, the returned assessment, and the quota boundary separately.

The visible client was Claude Desktop, incognito chat, Sonnet 5 Medium. The native
tool card showed the new assessment tool and arguments matching the local audit:
dispatcher requester, truck-driver subject, APM Elizabeth, the supplied synthetic
aliases, the explicit trip timestamp, 80,000 lb, five axles, and reported TWIC and
SeaLink registration. No tool name or JSON arguments were required in the prompt.

The tool created case `syn-trip-f664835de1f360be06850db0a7d07ce4`, revision 1.
Its assessment identified 13 requirements, returned narrow synthetic induction
`met`, and kept the whole-trip result `unresolved`. It supplied questions about
the exact route, travel sequence, and whether Port Street is included.

Claude abridged `source_message` while preserving the material facts and reporting
qualifications. That field is model-supplied provenance; it is not a verbatim
capture of the user's UI utterance. The complete original prompt is retained in
the test plan. Final-answer fidelity cannot be graded because the app stopped
after the successful tool response.

The app displayed: **“You are out of free messages until 4:30 AM.”** Its modal
specified the 5-hour message limit. The observation was September 10 in the
America/New_York environment. No upgrade or billing change was made. Prompts 2
and 3 remain unsubmitted in the final run; their unit/stdio counterparts do not
count as consumer-app validation.

An earlier preliminary permission request was stopped before tool execution so
the final reviewed runtime could be loaded. It is not counted as a completed
consumer call. The final audit and both live verification receipts use the same
runtime fingerprint.

## Remaining validation

After the provider quota resets, resume the incognito case if it is still
available, or start a fresh capture using the retained plan. Record the model's
fact updates, the same-case revisions, SeaLink invalidation, evidence lookup, and
final wording. Keep any failures as measured results. The source catalog remains
draft, and no live legal, registry, road-condition, appointment, or gate checks
have been established by this run.
