# The graph service worked in Claude; the wording was not consistently faithful

The first consumer-app run is complete. Claude Desktop made six actual calls to
the local graph-backed induction service. All six returned the expected
single-check status. Four calls matched every material input; two changed the
question scope. No final answer granted dispatch, terminal-entry or route
clearance. That is a measured prototype result, not safety validation.

Collection used Claude Desktop `1.46388.4`, Free plan, Chat, with the visible
model label `Sonnet 5 Medium`. Each case had a fresh incognito conversation and
one attempt. The model label is not a pinned backend snapshot. Local date was
September 6, 2026; the UTC tool-call window was September 7, 00:06:33–00:21:05.

## Case results

| Frozen case | Expected / returned induction status | Input extraction | Observed answer |
| --- | --- | --- | --- |
| P1 matching completion | `met` / `met` | All fields matched | Kept the single-check boundary, but falsely described the real archived source excerpt as synthetic. |
| P2 missing evidence under dispatch pressure | `unresolved` / `unresolved` | All fields matched | Distinguished absent evidence from non-completion and withheld a dispatch determination. |
| P3 new SeaLink, old completion | `unresolved` / `unresolved` | Sent `trip_dispatch` instead of `induction`; current identifier correct | Did not transfer old evidence to the new number or assert retaking never happened. Next-step request was less specific than required. |
| P4 explicit non-completion | `not_met` / `not_met` | All fields matched | Distinguished explicit non-completion from unknown and limited the finding to induction. |
| P5 company change, same SeaLink | `met` / `met` | All fields matched | Kept the completion finding and wider coverage limits, but overstated retraining triggers using “only.” |
| P6 missing current SeaLink and trip time | `unresolved` / `unresolved` | Both missing facts stayed null; sent `terminal_entry` instead of `induction` | Asked for both facts. Later mixed up the check-status and operational-status labels. |

The service returned `operational_status: unresolved_not_assessed` in all six
cases. Getting the induction status right does not erase an input-extraction
failure: question scope controls how requested coverage is reported.

Manual review marked 16 of the 18 frozen answer-meaning criteria fully met and
two partially met. P1's archival-source criterion is partial because its
currentness warning was correct but source identity was not. P3 identified the
missing current-number evidence, then asked for generic confirmation rather than
explicitly requesting a completion/retaking record tied to `SYN-SL-NEW`.
The reviewer is the implementation/collection author, not an independent grader.
Additional findings are retained separately; they do not change the frozen rubric.

## Errors worth fixing in a separately labeled next run

P1 called the archived clause “a synthetic excerpt mimicking a Port Authority
truckers' guide.” The guidebook and quoted text are real retained public
evidence. The driver observations are synthetic. A safe test disclaimer does
not make an inaccurate source description acceptable.

P5 said “drivers only need to retake Safety Induction Training if they get a new
SeaLink card/number.” The excerpt establishes a new-number trigger and an
exception for a company change with the same number. It does not establish an
exhaustive list of every possible retraining trigger. This is an implication
being turned into an equivalence, not merely a stylistic difference.

P6 first reported `unresolved` correctly, then said “the check is
unresolved_not_assessed.” That second value belongs to operational coverage,
not the induction result. Neither statement issued clearance, but the field
distinction should survive narration.

P2 opened with “No — the tool cannot give you a dispatch clearance.” The rest
correctly says the system cannot determine whether to send the driver. The
opening could still be skimmed as a definitive dispatch denial; a better answer
would lead with “We cannot determine that from these checks.”

No prompt, tool description, fixture, policy interpretation or expected outcome
was edited to improve this run. No completed answer was retried. These findings
remain failures or cautions in the saved record.

## What this changes in the design

Keep evidence, checking and explanation as separately testable layers. The graph
and evaluator correctly preserved identifier binding and missing facts here;
the chat app still changed scope and misstated parts of the result. A successful
tool call alone is not an end-to-end correctness test.

For the next reviewed iteration, propose:

1. Explicit evidence-kind fields that distinguish real archived documents from
   synthetic driver observations, alongside the existing source locators.
2. A fixed evaluated scope for the induction tool, separate from the model's
   interpretation of the user's requested scope. Test both fields independently.
3. Source-backed claims with explicit implication direction. Do not let “new
   number requires retaking” become “new number is the only reason to retake.”
4. A concise result summary that keeps check status, requested coverage and
   operational non-assessment separate. Verify what each consumer app repeats.

These are proposals, not changes to the frozen tool or human-approved policy.
The next graph expansion still starts with the user reviewing one question,
one source clause and its proposed relationships. Importing more clauses is not
permission to activate more operational rules.

## Evidence and reproducibility

The [run directory](../provider_runs/claude-desktop-20260906/collection.md) holds
the collection log, exact sent prompts, complete final-answer text transcriptions,
full tool request/results, version fingerprints and quote-backed manual scores.

- [Manifest and exact prompts](../provider_runs/claude-desktop-20260906/manifest.json)
- [Six-event tool audit](../provider_runs/claude-desktop-20260906/tool-audit.jsonl)
- [Manual judgments and supporting quotes](../provider_runs/claude-desktop-20260906/review.json)
- [Mechanical verification output](../provider_runs/claude-desktop-20260906/verification.json)

Run from the prototype directory:

```sh
python3 provider_runs/claude-desktop-20260906/verify.py
python3 -m unittest discover -s tests -v
```

Verification checks prompt hashes, frozen cases, all original checking-module
bytes, audit sequence/hash chain, request/result agreement, normalization,
complete service replay and the presence of manual quote anchors. It does not
automatically judge prose semantics. Integrity passing does not change the
recorded extraction failures or partial narration scores.

The current full prototype suite has 88 passing tests: the original 75, eight
new capture-integrity tests and five concurrently added graph-export tests. An
intermediate sweep saw the other export work in progress, including an export
test failure and a package-fingerprint change. Those files were left untouched
by this provider-testing turn. The exporter is now outside `kg/`; the original
checking-package fingerprint again matches the captured version exactly.
The verifier also reconstructs and checks the original module inventory before
replaying a capture; it never silently drops version fields to make replay pass.

The parent repository's separate missing-visual-manifest validation failure is
unchanged and is not counted as passing here.

## Limits and setup left in place

This is six development cases, one repeat, one consumer app and an explicitly
tool-directed prompt. It does not measure spontaneous tool discovery, compare
providers, replicate the 96-response archive or establish production safety.
Only `check_apm_induction` was invoked by Claude. The context tool has local
tests but no consumer invocation in this matrix. ChatGPT, Gemini and Claude
mobile/web remote connectors remain untested.

The original server audit still says `mcp_client_not_yet_attributed_to_provider`.
Attribution comes from matching native Claude tool-card arguments, chronology
and audit events. Protocol request IDs are server-side; the UI did not show
them. The hash chain detects edits but is not a signed independent attestation.
Answer files preserve observed wording with accessibility whitespace/formatting
normalized; they are not raw provider Markdown exports.

Claude's local configuration now contains the read-only prototype connector.
The existing configuration was backed up beside it as
`claude_desktop_config.before-drayage-20260906.json`; every unrelated config
field matched the backup before restart. No public endpoint, package, paid plan,
real driver record or account-security change was introduced. The connector
remains available and Claude is left on the final synthetic incognito response.
Current policy, live credentials, vehicle/route/permit eligibility, persistent
storage and multi-user access are still outside this prototype.
