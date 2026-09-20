# Driver experience checkpoint — September 19, 2026

**Implementation and four-turn consumer capture complete; driver presentation
acceptance not passed.** The remaining gap is Claude's source/qualification
presentation, with an additional scope-selection concern on the new Path B
move. Do not equate backend success with the user's finished experience.

Read the [consumer review](consumer-review.md) and
[actual Claude conversation](https://claude.ai/chat/f2016f85-08cc-4081-bac0-e61032d2452f).
The [usage guide](../../docs/driver-experience.md) documents the existing local
connector and current limitations.

## What changed

The supplied evidence was already available. Broad Path A assessments deliver
26 canonical passages, source URLs, locators and qualification notes. The
large MCP payload was difficult for Claude to present faithfully.

Added a prepared source-linked answer and a detailed source briefing ahead of
the full assessment JSON. The short answer connects the reported truck facts
to retained provisions and distinguishes rule applicability, physical
clearance and the separate APM notice/retrieval dates. The detailed briefing
preserves every selected canonical passage; full per-finding details and
draft supplements remain in the unchanged JSON and `structuredContent`.

Updated connector guidance for natural driver explanations, same-trip
corrections, supplied road sequences and source links beside claims.
Compatibility assertions in tests and six audit scripts now read the final
text block for full-JSON equality; these checks were retained, not weakened.
No evaluator, source policy, verification admission, graph or application
configuration was changed by this presentation work.

## Verification

- **450 local tests passed** after the final runtime change (`tests.log`).
  The final checkpoint rerun also passed all 450 in 23.026 seconds
  (`tests-final.log`); `git diff --check` passed.
  Eight added tests cover passage/qualification preservation, correction and
  Path B order, conflicting reports/history, outage, width access, missing
  reports, separate terminal dates and narrow-scope fallback.
- **10/10 live pinned-graph checks passed** (`graph-receipt.json`), including
  exact source/graph equality and separate Wave-4 isolation. This check
  predates the final presentation edit; graph/evaluator data did not change.
- **Four actual Claude connector events** validate against their schemas,
  reproduce the prepared/detailed text, preserve exact full-JSON parity and
  form a verified audit hash chain. All 34 frozen runtime files still match.
  Path A revisions are 1→2→2; Path B is a new trip at revision 1 with five
  segments. Every result keeps terminal currentness unknown and permission
  not issued. See `consumer-verification.json` and `verify_capture.py`.
- Native Chrome opened the supplied 68-page NJ guidebook PDF; the cited
  height and semitrailer sections were visible. This is an accessibility
  check of one source, not an audit of every live publisher page.
- Extra adversarial review inspected source omission, date conflation,
  shortened access conditions, unavailable-service behavior, scope fallback,
  cross-trip fact handling and full-payload compatibility. The consumer
  defects are retained in `consumer-review.md` rather than scored as passes.

## Preserved attempts and artifact meaning

`attempt-1-*`, `attempt-2-*` and `attempt-3-*` preserve three failed first-turn
captures. They exposed missing links, legal-sounding overstatements, inferred
missing facts and conflated terminal dates. They are separate experiments,
not extra passing turns in the final conversation.

`protocol.json` is the fourth attempt's frozen prompts and runtime identity.
Its originally null conversation URL is intentionally unchanged; the actual
URL is recorded in the consumer verification and review. `consumer-audit.json`
contains the real connector events. `prepared-answer-*.txt` are service text,
not model transcripts. The consumer review contains selected native UI
excerpts with explicit transcription limits. Earlier previews are development
artifacts, not acceptance evidence.

`baseline.json` and `before/` preserve this session's starting dirty files.
`session-changes.patch` isolates this session's changes; `runtime-changes.patch`
contains only its runtime edits. `artifact-manifest.json` binds the checkpoint
artifacts after documentation is finalized. Historical sealed audits are
unchanged.

## Scope and status

This is the existing local synthetic Claude Desktop experience. 511NJ and the
separate browser/confirmed-assessment bridge are outside this finish line.
Full legal/operational coverage and production release are separate matters.
No commit, push, public deployment, new dependency, source promotion or real
driver data was introduced. The multi-session dirty worktree was preserved.

The narrow next repair must address the observed final-answer omissions and
scope choice. More source collection or another repeat of the passing graph
checks would not close this consumer acceptance failure.
