# Finished local driver experience — September 19, 2026

**The agreed four-interaction Claude Desktop driver experience passed.** [Read the actual conversation](https://claude.ai/chat/0ce6f46c-fd0d-484f-b544-bb0d0dfaa5ef) and the [consumer review](consumer-review.md). [Usage guide](../../docs/driver-experience.md).

Complete moves and corrections now use `assess_driver_move`, which fixes full-trip scope and returns a compact prepared source-linked answer. Date/current-condition follow-ups use `get_trip_conditions_answer`. Existing full-assessment/evidence tools remain available. Full supporting assessments are retained in the local audit; compact delivery does not claim to deliver all 26 source records to the model.

## Evidence

- `protocol.json`: unchanged four prompts and 36 frozen runtime-file hashes.
- `consumer-audit.json`: five actual connector events, including one rejected request-key collision and four successful assessments. No pasted tool results or harness substituted for the app.
- `consumer-verification.json`: schema, JSON/rendered-text parity, event chain, scope, source binding, route and revision checks passed.
- `consumer-excerpts.md` / `consumer-review.md`: actual observed final prose and acceptance assessment, distinct from `service-answer-*.md` prepared tool output.
- `tests.log`: **462 tests passed**, 35.718 seconds.
- `adversarial-qa.json`: nested verification injection, stale revision, contradictory height extraction and missing-report controls passed.
- `implementation.diff`: isolated changes since r3; `completion.diff` includes the cumulative r2–r4 repair and documentation closeout.
- `manifest.json`: local artifact and delivered-file checksums.

Reproduce connector evidence verification from this directory's frozen final runtime:

```sh
python3 audits/driver-experience-2026-09-19-r4/verify_capture.py
```

Earlier failed attempts remain preserved in the original, r2 and r3 checkpoint directories. They are superseded as current experience status, not rewritten as passes. The final code does not change source records, evaluators, verification authority, pinned graph or connector configuration. No dependencies, commit, push or deployment were added.

The supported result is an evidence-backed explanation for synthetic moves, including honest unresolved answers. It is not real-world dispatch authorization. A future model/version change should rerun the same bounded consumer walkthrough.
