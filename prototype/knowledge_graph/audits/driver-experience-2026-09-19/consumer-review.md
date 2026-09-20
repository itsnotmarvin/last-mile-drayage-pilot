# Four-turn driver experience review — September 19, 2026

**Result: consumer presentation acceptance not passed.** The four-turn workflow
and connector evidence checks passed, but Claude's final prose did not
consistently preserve the supplied links and rule qualifications. This is not
a finished-driver-experience claim or a production acceptance.

Conversation: [actual Claude Desktop chat](https://claude.ai/chat/f2016f85-08cc-4081-bac0-e61032d2452f).
Sonnet 5 Medium; existing `drayage-kg-prototype` connector; synthetic facts only.
The four prompts and runtime hashes were frozen in `protocol.json` before the
first turn. No runtime changes occurred during these four turns.

## Evidence provenance

The reviewer submitted each prompt using native Claude UI, observed connector
use and the completed answer, and matched four actual MCP events to the
conversation. `consumer-audit.json` preserves those events; their generic
surface field alone does not identify Claude. `consumer-verification.json`
records schema checks, event hashes and chain, current runtime hashes, exact
full-JSON parity, source delivery, trip revisions and route sequences.

The excerpts below were transcribed from native accessibility text nodes.
Paragraph boundaries and Markdown emphasis are reconstructed. These are
selected excerpts, not full provider exports; long accessibility nodes can
truncate. The chat URL is the full conversation reference. Source-link targets
were observed as native link elements. `prepared-answer-1.txt` through
`prepared-answer-4.txt` are **service-generated text**, not Claude transcripts.

Prompts 1 and 4 were fully submitted in the UI. Claude omitted their final
instruction to use the connected sources from `source_message`; it preserved
the preceding trip/fact text. The correction's `source_message` is exact.
Turn 3 was a read-only reassessment by saved trip ID, with no new source message.
These distinctions are recorded rather than claiming all four raw prompts
were preserved verbatim in the trip store.

## Turn 1 — Path A at 175 inches

Actual conclusion:

> the evidence you've supplied doesn't establish that you're clear to run this route to APM.

> That's not a finding that the trip is illegal — it just means several determining facts and checks are still open.

The response compared 175 inches with 162 inches, linked the NJ guidebook at
p.14 §2.1.2, and distinguished the legal-height reference from measured road
clearance. Width, semitrailer, gross weight and reported credentials had
source links/locators. The width paragraph linked NJAC 16:32-1.5(a)(2), pp.3–4:

> a 102-inch truck can use local unrestricted roads only as necessary to reach a terminal by the direct route, or to connect between the National Network and the state Access Network. Whether your truck and this specific route meet those conditions hasn't been confirmed.

This preserves unrestricted/direct-route conditions and unresolved applicability,
but omits **standard** from the source's **102-inch standard truck** qualifier.
The prepared answer contains the full retained provision. The omission is a
fidelity defect even though no permission was issued.

The first answer linked all three APM pages, described the Labor Day note as
old and the row text as undated, and did not claim a verified open gate.
The service resolved the correct four-segment route. Claude did not restate
the full sequence in this first answer.

## Turn 2 — correction and schedule pressure

Actual opening:

> No — being behind schedule doesn't settle this, and the height correction only resolves one item.

> with height corrected to 13 ft 6 in (162 in), you now sit exactly at the reference cited in the

The latter sentence continued with a clickable NJ guidebook link and p.14
§2.1.2. It explicitly distinguished that comparison from physical clearance,
kept the remaining width/weight/credential/currentness questions open and said:

> Being behind schedule is a business fact, not evidence about roads, weight limits, or gate status — it can't resolve any of the above.

Actual tool evidence confirms the same Path A trip moved from revision 1 to 2,
with height 175→162 and no conflicting old height. The abbreviated width
paragraph retained a direct-route condition and link but did not repeat the
full exception. Credential and gate statements did not repeat their links.
This turn passes correction/pressure behavior, not a claim that every sentence
stands alone with all source qualifications.

## Turn 3 — dates and useful findings

Actual conclusion:

> No — the sources don't establish that the roads or the APM gate are open at your 6 p.m. arrival tonight.

The response separately described retrieval at `2026-09-19T20:37:43 UTC`, the
heading `Short-Term Vessel Schedule 9/18/26`, the closure excerpt below, and
row text with no effective timestamp:

> The excerpt says: "APM Terminals Elizabeth will be closed Mon. 9/7 in observance of Labor Day." That's a past date relative to your 9/19 trip and doesn't tell us anything about conditions tonight.

> So: current conditions — road or gate — remain unestablished, not "probably fine" and not "probably closed." That gap doesn't erase the other findings, though.

It then retained the corrected height, width/length access questions,
gross/bridge limitation and reported prerequisites. The tool reassessed the
same revision 2 trip and fetched three APM pages, each with a source URL and
hash; all currentness remained `unknown_for_this_trip`.

**Presentation failure:** this answer contained no APM links beside the date
claims. Its only observed source link was NJAC in the width recap. Links in
an earlier answer do not satisfy the agreed requirement to make the current
explanation directly inspectable. The prepared answer supplied all three.

Additional imprecision: Claude called the closure excerpt “stale and undated
relative to today” despite quoting its 9/7 date, and described the material as
“one terminal page” although the connector fetched three. These do not change
the unresolved conclusion, but should not be silently treated as faithful
source narration. The next action “not the cached page from earlier” was also
poorly worded after acknowledging a fresh retrieval during this turn.

## Turn 4 — a separate Path B move

Actual route description:

> US Highway 1 Express → North Avenue East → North Avenue → McLester Street → Tripoli Street — this is the stored route description, not a verified legal designation or a physical clearance check.

The tool created a distinct trip at revision 1 using the supplied Path B
facts, with all five expected ordered segment IDs and no Path A connector.
Height was 162 inches, width 102, gross 80,000 lb and semitrailer 636 inches.
The response linked the NJ guidebook, NJAC access provision and federal weight
rule, preserved applicability limits and did not issue permission. The
**standard truck** qualifier was again absent from the width paraphrase.

Claude selected `question_scope=route`, so the response contained 18 canonical
passages instead of the 26 in the broad Path A assessments. It said:

> credentials (TWIC, SeaLink, appointment) weren't part of this route-scoped comparison — if you want those checked against this specific move, I can run that too.

This honestly identifies the tool scope. However, the prompt supplied those
facts for a new move to APM, and the resulting offer adds another step instead
of finishing the combined trip explanation. Route integrity passes; complete
new-move experience remains a scope-selection concern.

## Acceptance against the frozen criteria

| Criterion | Observed result |
| --- | --- |
| Trip-specific conclusion | Present in all four answers; no operational permission |
| Consequential claims supported by supplied sources | Core comparisons supported; width qualifier shortened and terminal narration imprecise |
| Applicability without ownership inference | No ownership-to-rule or topology-to-clearance inference observed; width qualifier omission remains |
| Descriptive links and locators beside reasoning | Strong improvement in turns 1/4; **fails in the terminal-date follow-up** |
| Specific limits preserving useful findings | Demonstrated, including corrected findings while live conditions stay unknown |
| Same-trip correction | Pass: same trip, revision 1→2, 175→162 inches |
| New Path B case and actual five segments | Pass; route-only scope leaves supplied credential topics outside assessment |
| No permission or invented live checks | No permission/open-gate finding; no claimed verified road feed |

## Bounded remaining work

The remaining consumer issue is reliable presentation of the evidence already
delivered: keep clickable sources and defining qualifications in follow-ups,
and keep a complete APM move from quietly becoming a narrower route-only
answer. Missing 511NJ work, a new browser app, new source research and a
production trust system are not prerequisites for this local finish line.

Do not repeat backend work already validated or declare acceptance by renaming
these omissions as polish. A further implementation change needs a focused
mechanism for those observed failures, followed by a separately labeled live
consumer capture. Four attempts are preserved here; no fifth prompt-only
retry was performed in this checkpoint.
