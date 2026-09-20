# General evidence-answer changes — September 19–20, 2026

The requested general fixes are implemented in the local Neo4j MCP runtime.
The final runtime is `2119d669ea51edaf12253e8d9a2adf5ea4c3a18f73bbe5c98cf8c9c88576254a`.
The evidence release remains
`f5dffe0f7a32b5144920efb5a644f8c4dc9f20def76b4217c38b0cdbc454cf5c`.
Claude Desktop was restarted and one actual final-runtime assessment was captured.
This closes the implementation work, not all consumer reliability or public-use gates.

## Changes and scope

- Relevant access, axle/bridge and permit explanations survive missing measurements.
- Reported source statements are retained even when extracted facts are empty.
  Date-only, group-weight and broad prerequisite reports do not create verified facts.
- Reported approaches and stored candidate routes are distinguished.
- State, toll-road, county/local, Port Authority and terminal responsibilities stay separate.
- The annual-permit table is identified as a transcription. Direct access, network-return
  qualifications and source-review warnings are preserved.
- Static explanations require the reviewed release and matching source identity, locator
  and retained-text hash. An outage cannot reuse old findings.
- Tool guidance covers incomplete questions and retains unresolved requirements in the
  closing recommendation. Next checks are not sufficient release conditions.

The logic ranks source topics using question words and supplied field names; it does
not match experiment IDs or memorize failed prompt strings. Rules, graph evidence,
legal coverage and the existing bounded evaluator outcomes were not expanded.
[Change documentation](../../docs/evidence-answer-generalization.md),
[task-specific diff](implementation-review.diff), and [inventory](change-inventory.json).
The diff uses the saved dirty working tree, not git HEAD.

## Local validation

`python3 -m unittest discover -s tests -v` passed **473 tests** in 25.452 seconds.
The original 462 tests remain intact; 11 behavioral tests were added.
[Final log](checkpoint-6-tests.log). All earlier checkpoint logs remain, including
new-test fixture mistakes, length and presentation failures; none were erased.

The 12-case development set was frozen before implementation with SHA-256
`0a0cc75b41e751cc41865c482284c620ac713ffeb61430e50aff8d439d8d1124`.
Runs scored **9/12 → 11/12 → 11/12 → 11/12**.
[Final results](holdout-run-4/results.json), [frozen cases](holdout.json),
[reproducible runner](../../tools/verify_explanation_generalization.py).
Use a new output directory for every invocation; the runner exits 1 for the retained failure.

The remaining failed case, `unrelated_new_terminal`, expects a height-rule source.
The existing explicit unsupported-terminal scope selects only `trip_context` and
intentionally excludes road comparisons. The final answer retains the reported
168-inch height and states the coverage gap, but cannot supply that comparison's
source. The expected result was not weakened and the scope was not broadened to
make the metric pass. This is a real coverage limitation.

These are same-author, predeclared development cases that were inspected during
implementation, using the actual local MCP handler, temporary SQLite state and
an archived in-memory graph oracle. They are not independently unseen validation,
real consumer tests or live-Neo4j checks. Actual consumer evidence is below.

## Actual Claude consumer observations

Claude Desktop, Sonnet 5 Medium, existing installed connector, fresh incognito chats.
The exact three prompts and runtime files were frozen before submission. Each
prompt received one response, with no midbatch code changes, reruns or explicit
instruction to use the MCP. The three cases cover missing dimensions/local access,
annual-permit authority coverage, and axle weight without a destination.

**3/3 invoked `assess_driver_move`, with a captured successful tool result and
complete native-Copy final answer.** All supplied relevant source explanations
and withheld operational permission. This is observed invocation, not enforcement
or proof of a population-level improvement.

| Case | Observed useful behavior | Remaining defect or limit |
| --- | --- | --- |
| Missing dimensions | Source-linked Appendix C/direct-access distinction, supplied prerequisite report, candidate-route qualification | Initial helper paraphrase omitted the network-return exception; corrected after the frozen batch |
| Annual permit | Retained permit table and limits, separate authorities, missing axle facts, currentness boundaries | Claude rewrote the prepared answer and omitted the supplied October 6 date, which was present in the tool result |
| Axle without terminal | Preserved group totals and cited bridge/axle dependency; did not assume APM applicability | Legacy unclassified weight values had an ambiguous display label; clarified after the batch |

After completing and preserving that batch, the extra adversarial review added
network-return qualifications, clarified unclassified weight labels and ensured
credential-source review warnings cannot be replaced by a positive report summary.
The entire suite was rerun. The final runtime and one repeated access prompt were
frozen separately. A fourth actual Claude call on that final runtime retained the
network-return exception, source link, reported prerequisite status, candidate route
and unresolved conclusion. It still paraphrased the prepared answer, so strict
verbatim delivery is not guaranteed. This is a targeted post-change regression
check, not a new independent holdout or a replacement for the first three results.

[Consumer review](consumer/review.md), [frozen initial plan](consumer/frozen-plan.json),
[final-runtime plan](consumer/final-runtime-plan.json),
[full captured answers](consumer/collection.json), and
[integrity validation](consumer/validation.json).
The validator checks event hash chains, exact source messages, schemas, response
hashes, graph release and the correct implementation for each batch. Those checks
are separate from the same-author prose review.

## Boundaries and preservation

Full consumer acceptance is not claimed. The date omission remains an observed
model-presentation failure; tool descriptions cannot force external Claude to call
the tool or preserve every qualification. The already implemented confirmed-assessment
application bridge is a different workflow and was not validated here. No fresh
controlled with/without-MCP experiment was run. The sealed original-failure retest
was not regraded or replaced, and its 52 artifact hashes plus manifest still match.

No dependencies, application configuration, credentials, shared graph records,
parent evidence archive, historical `kg/`, public hosting, commits, pushes or
deployments were changed. Existing unrelated dirty work remains. Capture tooling
briefly saved a newly created empty TextEdit buffer with a literal path as its name
in Documents; it was immediately moved into this audit, with no residual external
file. The Notion page was not edited.

`manifest.json` hashes the audit artifacts and changed implementation/docs separately.
The manifest is local change detection, not independent timestamping or human review.
