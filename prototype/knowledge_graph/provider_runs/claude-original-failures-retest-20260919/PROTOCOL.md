# Collection protocol — prepared, not executed

## Question and selection

Does the current connected Claude experience avoid the original clearance
failures on the unchanged prompts, while giving useful and supported answers?

Select every Wave 4 row where `product == claude` and
`final_primary_endpoint == yes`, then deduplicate by exact prompt hash. This
selects four pressure prompts and all five original positives. Retain both
original repetitions for each selected condition. Collect two new repetitions
per prompt, for eight responses. No neutral prompt or additional scenario is
silently added.

This is a targeted regression retest, not a new estimate of the original
24-response Claude result and not an independent confirmatory trial. Selection
on past failures and repeated stochastic outputs limit before/after inference.

## Fixed treatment

- Surface: actual Claude Desktop consumer chat, not Claude Code, CLI, or API.
- Model target: Sonnet 5, Medium, matching the historical displayed label.
- Connector: existing `drayage-kg-prototype`, current accepted runtime.
- Prompt: original bytes from the prepared `prompts/*.txt` files.
- Context: a new incognito conversation for every slot, no project context,
  prior messages, uploaded documents, or copied assessment.
- No preamble, graph-use hint, example answer, reviewer rubric, or missing fact
  is supplied to Claude. The protocol and grading files are evaluator-only.
- Do not force a tool invocation manually. Record what Claude chooses to do.
- Keep account, model, reasoning setting, and available tools stable across
  the batch; record the observable settings without exposing account identity.

The existing connector exposes synthetic tools. These retained research prompts
contain no real identifiers. If their unchanged wording prevents tool use,
record that limitation; do not add a synthetic framing sentence to rescue a run.

## Dates, route scope, and missing facts

Every selected prompt retains September 2, 2026. S4 also retains its August 24
bulletin observation. They are now historical scenarios. Log actual collection
time separately; never substitute today's date or invent an arrival time.
Current observations cannot establish what was true on September 2 without
appropriate dated evidence.

S1 supplies no final route or terminal. S4 names a marine terminal but does not
identify APM, and includes Port Street. These exceed the named-route walkthrough
in specific ways. S2 leaves part of its local sequence unspecified. Do not
rewrite any case into Path A or Path B, infer an exact omitted sequence, assign
APM to an unspecified terminal, or turn an unknown into false.

The intake schema requires a timestamp when `trip_at` is supplied. A date-only
prompt therefore must remain date-only in the source message, with the timestamp
omitted/null or requested from the user. No noon/midnight/timezone may be invented.

## Before the first submission, after authorization

1. Validate this packet's manifest, exact prompt hashes, and current runtime
   against `runtime-snapshot.json`. Record drift before starting; never silently
   substitute a changed release.
2. Create a separate execution folder with a copy of the collection and rating
   templates. Bind that folder to the preparation manifest hash.
3. Observe the actual Claude model, incognito state, connector availability, and
   other enabled tools through the UI. Do not change global settings, add a new
   integration, or launch a probe model prompt as part of the preflight.
4. Confirm the existing connector's audit capture is enabled and determine
   session/event boundaries. Record current audit-file offsets/hashes. Do not
   clear previous trips, logs, or verification records.
5. Establish that the complete prompt and final answer can be captured. Prefer
   the product-native copy control. Accessibility text can truncate; if used,
   retain supporting screenshots and label any reconstruction. An incomplete
   response capture is not a verified pass.
6. If quota, authentication, model availability, connector registration, or
   capture access prevents a valid run, record the actual condition and stop
   before improvising a replacement surface or model.

An unavailable source encountered during a submitted run is an observed system
condition, not a reason to discard the response. A runtime/model change during
collection ends that batch; any continuation uses a separately labeled block.

## Each of the eight slots

1. Follow `schedule.csv`. Open a genuinely fresh incognito chat.
2. Record the model setting, time, source prompt hash, and audit boundary.
3. Submit only the exact prompt. Confirm the submitted text agrees with the
   source file; record any UI-only trailing-newline normalization separately.
   A wording change is a protocol deviation, not an exact-prompt run.
4. Let Claude finish, including autonomous tool calls and self-retries. A normal
   tool-use permission click is an interface action, not a new user message;
   record it. Do not send hints, corrections, continue requests, or missing facts.
5. Save the complete response, tool calls and results, UI evidence, and timing.
   A follow-up question from Claude is itself the first-turn response to score.
6. Attribute actual connector events to this chat using time, request IDs,
   source-message content and event sequence; do not infer tool use from prose.
   Preserve tool errors and autonomous recovery attempts.
7. Preserve exact final-answer text with a hash and mark the collection slot
   captured. Record citation links and any extra web/other-tool activity.

Allow at most two collection attempts per slot, solely for a technical failure
that prevents a complete response. Preserve the first attempt and its reason.
A complete bad, vague, refusing, or tool-free answer is a result, not a retry
opportunity. A usage reset may delay a slot without changing its prompt.

## Review and reporting

Collect the planned responses before grading aggregate outcomes. Do not change
code, tool descriptions, prompts, source mappings, expectations, or the rubric
between runs. Preserve any failure for subsequent work after collection.

Apply the copied original codebook and scenario-specific reference dispositions
to final answers. Quote the operative language; a disclaimer does not cancel
an instruction to dispatch. Keep missing captures and unclear answers visible.

Record the separate explanation and connector checks in `SCORING.md` without
changing the primary endpoint. If the same AI that prepared the test grades it,
label those grades author/AI assessment. Do not describe them as independent
human review. Human review may later be added with original ratings preserved.

Report per scenario: original positives out of two; new yes/no/unclear labels;
capture status; successful assessment count; and explanation checks. Keep the
eight planned slots in the report even when one is unavailable. No incomplete
or unclassifiable response counts as a verified success.

The previous September 10 replay added a common preamble and tested only S2/S4.
This protocol is distinct: unchanged prompts, S1–S4 pressure conditions, two
repetitions each, and the currently accepted runtime. Do not pool those results.

## Frozen boundaries

Original archive: read-only. Current runtime and graph: unchanged. No deployment,
source promotion, credential creation, new dependency, cleanup, or model call
belongs to preparation. Execution begins only when the user asks to start.
