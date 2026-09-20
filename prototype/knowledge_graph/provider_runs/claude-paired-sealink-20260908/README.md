# One synthetic SeaLink comparison in Claude Desktop

**Result: this experiment does not establish that the model needs the MCP tool to perform the core check.** Both no-tool answers identified the identifier mismatch, requested current-number evidence, and withheld broader clearance. The defined-status follow-up produced `unresolved` in both conditions. There is a narrower observed difference in the follow-up: the no-tool answer suggested an unsupported alternative to a completion record; the tool-assisted answer did not. The initial tool-assisted answer also suggested an unsupported alternative, so tool access did not consistently prevent this error.

## Case and method

A synthetic driver has induction completion recorded under `SYN-SL-A`, but the current SeaLink identifier is `SYN-SL-NEW`. Both conditions received the same archived PANYNJ guidebook quotations and the complete relevant synthetic driver record. The expected prototype result, frozen before collection, is `unresolved`: evidence tied to the old identifier does not establish completion under the current identifier, and missing evidence is not explicit non-completion.

Four fresh incognito chats in Claude Desktop consumer Chat, Free plan, visible label **Sonnet 5 Medium**. One completed first response per condition per pair; no regenerations. Initial order A then B; separately frozen follow-up B then A. These orders were fixed, not randomized. All unrelated connectors and web search were disabled during collection; the drayage connector was enabled only for B. Initial twelve enabled connectors and web search were restored afterward.

The first pair did not define status labels. Because its no-tool answer used `not_met` while otherwise correctly identifying insufficient evidence, a second pair supplied identical explicit status definitions to both conditions. The original pair remains preserved and reported. No new case was selected after observing results.

## Results

| Pair | No tool | With graph checker through MCP |
| --- | --- | --- |
| Initial, labels undefined | `not_met`; correct mismatch and evidence request; terminology confound prevents a strong reasoning-failure claim | `unresolved`; checker output correct, but invented `company_changed=false` and suggested an unsupported reissue exception |
| Follow-up, labels defined | `unresolved`; correct mismatch and uncertainty; suggested unsupported alternative evidence | `unresolved`; correct mismatch, uncertainty and current-number evidence request; `company_changed=null` |

The follow-up no-tool answer says: “it's also not \"not_met,\" since nothing explicitly states the induction wasn't completed under SYN-SL-NEW; it's simply absent.” This is the correct core distinction. However, it asks for “an induction record (or confirmation of no new SeaLink card issuance) specifically under SYN-SL-NEW.” The alternative is not a supported way to establish current-identifier completion in the frozen prototype. The case uses the word “alias,” so uncertainty about physical card issuance is understandable; do not describe this as granting clearance or proving general reasoning inability.

The initial tool-assisted answer asks for “documentation that SYN-SL-NEW/SYN-SL-A are the same underlying credential, if this was a reissue rather than a true new card.” That exception is also unsupported by the supplied packet/checker. Its false company-change argument was not supplied by the user; it did not change this particular check result.

The follow-up tool-assisted answer requests “a completion record (or confirmation) showing the induction was completed under SYN-SL-NEW specifically.” Its actual service response is `unresolved`, with reason `SEALINK_EVIDENCE_MISMATCH` and missing fact `completion_for_current_sealink`.

Both follow-up answers exceeded the requested 180 words under a whitespace-token count (187 without the tool; 201 with it). Both initial answers were within the limit (168 and 175). This format check is recorded separately from the substantive rubric. No answer issued broader entry or dispatch clearance.

## Inspect the evidence

- [Initial protocol](protocol.json), [no-tool prompt](A-no-tool.prompt.txt), [no-tool answer](A-no-tool.answer.md), [tool prompt](B-with-tool.prompt.txt), [tool answer](B-with-tool.answer.md), [actual tool event](B-tool-audit.jsonl).
- [Follow-up protocol](defined-status-followup/protocol.json), [no-tool prompt](defined-status-followup/A-no-tool.prompt.txt), [no-tool answer](defined-status-followup/A-no-tool.answer.md), [tool prompt](defined-status-followup/B-with-tool.prompt.txt), [tool answer](defined-status-followup/B-with-tool.answer.md), [actual tool event](defined-status-followup/B-tool-audit.jsonl).
- [Structured author review](review.json), [follow-up collection notes](defined-status-followup/collection.json), [initial collection incidents](collection-events.jsonl).

Answers were transcribed from visible accessibility text with formatting/whitespace normalized, not exported as raw provider Markdown. UI observations are in the assistant tool transcript; no screenshot files are bundled. Expanded tool cards showed the arguments; exact server audit events preserve requests and responses. Server request IDs are not provider message IDs. The connector runs from the original local checkout; its five kg modules were compared byte-for-byte with this repo before collection.

A free-plan limit dialog appeared after the final submission. Dismissing it revealed the completed answer. No response was retried. An interim claim that collection was blocked was corrected. Rapid preference-restoration toggles also hit UI rate limiting; individual toggles were subsequently verified restored. These restoration actions occurred after response collection.

## Limits and defensible claim

One deliberately selected synthetic case, one visible model label (no pinned backend snapshot), two protocols, four first responses, fixed order, and non-independent author scoring. The follow-up was motivated by the first pair and is exploratory. Both conditions already had the relevant source and records, so this tests interpretation/checking with an optional tool, not retrieving otherwise unavailable data. The checker embodies draft deterministic policy semantics; it is not a human-approved operational authority.

Supported statement: **The MCP-connected checker produced reproducible, source-linked structured results in actual Claude chats. Claude could also identify this evidence gap without it; tool access did not consistently eliminate unsupported narration.** This is not proof of general model superiority, MCP necessity, or a graph-specific advantage over equivalent deterministic code/data exposed another way.

Run `python3 provider_runs/claude-paired-sealink-20260908/verify.py` from `prototype/knowledge_graph` to verify the artifact manifest, frozen protocols/prompts, audit-event hashes and exact service replay. Hashes detect later drift; they do not independently authenticate UI provenance. New experiment artifacts are local and have not been published.
