# Progress and verification

## 2026-09-06: baseline

- Created this isolated prototype; parent evidence and Wave 4 archive untouched.
- Imported all 31 clauses plus existing entities, route topology, scope links,
  source metadata, and quarantined mutable observations into NetworkX.
- Seven baseline tests pass, including all retained registry archive hashes.
- Parent archive validation fails before checks on a missing visual manifest.
- TypeDB, Docker and cloudflared are unavailable on PATH. No installation.
- Browser-harness requires Chrome's remote-debugging consent. No provider
  prompt, tool connection, or provider evaluation has happened yet.
- Consumer-app vs API-first preference was requested; no reply at baseline.

Next: freeze synthetic acceptance cases, build deterministic checks and tool
transport, run adversarial tests, and resolve the provider setup boundary.

## 2026-09-06: local service and transport

- Native bounded goal activated after the seven-test baseline was passing.
- Public graph has 121 nodes / 202 relationships. Prototype rule and synthetic
  evidence overlay brings the total to 144 nodes / 228 relationships.
- Frozen 22 acceptance cases before implementing the evaluator. Their hash is
  `7f973f1cb48af3fd4a953a00a56fb7fa971101808d503ec0a4453339034656ee`.
- Implemented four distinct induction outcomes with applicability, sources,
  versioned normalized inputs, coverage gaps, and no operational clearance.
- Implemented local MCP lifecycle/tools and validated synthetic audit logs.
- Frozen six provider cases before collection. Their hash is
  `1743836d1a817c4240a5f711d451b2e6ea8088d49a38ff2a954eb5d594d0339b`.
- 75 local tests pass. This includes a subprocess stdio handshake and tool
  invocation, not a language-model/provider invocation.
- Adversarial QA added checks for real-identifier rejection, evidence injection,
  future/stale/conflicting evidence, Unicode byte limits, invalid UTF-8, duplicate
  JSON keys, explicit null request IDs, archive path escape and checksum failure.
- A final regression test reproduced a crash on array/object tool names; fixed
  input validation so malformed names return protocol errors. No expectation
  files were edited to pass tests.
- Inspected Claude Desktop through its native UI: signed in, Free plan, Chat,
  visible model `Sonnet 5 Medium`, app `1.46388.4`, no local MCP servers added.
- No consumer-provider prompts submitted, config changed, credentials used,
  public service started, or new packages installed.

Remaining boundary: user approval to add the local read-only MCP configuration
and restart Claude for the six synthetic cases. Only public retained excerpts
and synthetic records would be sent to Claude/Anthropic as tool results.
The provider-test condition remains unmet; do not mark the goal complete.

## 2026-09-06: blocked audit

The original build turn and two automatic continuations reached the same
consent boundary: approval to add the local tool to Claude Desktop and restart
the app. The latest read-only check confirms that Claude's configuration still
has no `drayage-kg-prototype` entry. No approval was supplied in those
continuations. The preceding continuation made no implementation progress and
was not a wait on a live job.

All remaining provider paths require that approval or a separately authorized
change of test surface/hosting. No safe in-scope action can complete actual
provider testing now. Mark the native goal blocked, not complete. Resume after
the user approves the local connector setup; preserve the frozen cases and
collect the actual app/tool/answer evidence described in `docs/provider-test.md`.

## 2026-09-06: resumed consumer-app collection

The user said "continue" after the explicit local-connector approval request.
This authorizes that described config addition, restart and synthetic test, not
new hosting, spend, real credentials or unrelated access. The native goal API
has no agent-controlled resume operation; keep its existing objective/accounting
and evaluate completion against the same stop condition.

The 75-test baseline passes again. Quit Claude, copied its existing config to
`claude_desktop_config.before-drayage-20260906.json` beside the original, and
added only `mcpServers.drayage-kg-prototype`. A JSON comparison confirmed every
other config field was unchanged before restart. Claude Developer settings now
show the server as `Running`; the Chat connector menu lists it. Collection uses
fresh incognito Chat sessions, the observed `Sonnet 5 Medium` label, and app
version `1.46388.4` on the Free plan. UTC collection date is September 7; local
America/New_York date is September 6. Frozen scenario timestamps remain unchanged.

## 2026-09-06: actual provider run and verification complete

- Captured six actual Claude Desktop incognito Chat cases, one attempt each.
  The native app used `check_apm_induction` six times. Full successful tool
  exchanges are in `provider_runs/claude-desktop-20260906/tool-audit.jsonl`.
- Exact sent prompts, normalized-input comparisons, full answer transcriptions,
  app/version labels, audit mapping and manual quote-backed judgments are saved.
- All six service statuses match the frozen expectations. Four calls match
  every material input; P3 changed scope to `trip_dispatch`, P6 to
  `terminal_entry`. Both supplied/omitted identifiers were otherwise preserved.
- Manual review: 16/18 frozen answer meanings fully met, two partial. No broad
  clearance observed. Source-identity error, unsupported exclusivity wording,
  a generic follow-up request and a status-field conflation remain documented.
- No prompt/tool/model/fixture edits or completed-answer retries during the
  matrix. Public evidence version and all original checking-module hashes match
  every captured response. All 40 registered archive files still verify.
- Added eight artifact-integrity tests. An intermediate full run encountered
  concurrently edited export files and an export test failure. Those files were
  left untouched by this turn. The exporter moved outside `kg/` during the other
  work, restoring the original package fingerprint; all five export tests now
  pass. The current complete suite is 88/88 passing.
- The run verifier retains full-payload replay and reconstructs the original
  inventory fingerprint before using it. It does not ignore version fields or
  convert measured provider failures into passing behavior.
- Updated README, design limits, collection instructions and
  `docs/claude-provider-results.md`. The prior parent visual-manifest validation
  failure and dirty-worktree edits remain untouched. No operational policy
  promotion, real credential use, new dependency, paid service or hosting.

Completion audit: a real graph and bounded evaluator exist; model/limits are
documented; frozen local tests pass; actual consumer-provider tool use is captured
and scored, including failures. This meets the bounded prototype goal, not the
broader goal of a safe operational drayage product. Further rule activation and
live-evidence policies remain human decisions.

## 2026-09-06: complete retained-evidence explorer

User requested a populated graph to explore, then explicitly requested the entire graph together. Added an offline whole-graph default view, full-resolution SVG, searchable neighborhood view, and lossless JSON/GraphML exports. All 121 retained public nodes and 202 edges are included; 40 archived files hash-verify. No service or source-data changes. Export code is outside the fingerprinted service module directory. Full suite: 88 tests pass; embedded JavaScript syntax checks pass. Browser visual inspection was blocked by the local-file URL policy, so browser interaction is not claimed as tested. See `docs/explorer.md`.

## 2026-09-07: reference-style circular graph

Applied the corrected image reference: white canvas, beige circles, yellow authority/operator/terminal nodes, black directed arrows, and visible stored relationship names. No organizing-principles/instance-data bands, extra type nodes, or inferred edges. All 121 nodes and 202 edges preserved; selected circles retain full names and records. Added cursor-anchored wheel zoom and label toggle. 88 tests pass, including exact SVG node membership, circular marks, every relationship label, and export round trips. JavaScript syntax checks pass. Rendered the SVG with installed rsvg-convert and inspected its PNG; browser interaction remains unverified due to the existing local-file URL restriction.

## September 7 — supported connections for disconnected records

- Added the separately versioned `evidence_graph.py` exploration graph; baseline
  `kg/*.py`, evidence archive and provider captures remain unchanged.
- Added 143 auditable relationships and one retained historical-analysis record.
  Exports now contain 122 nodes / 345 edges; isolated records fall from 34 to 1.
- Kept the 2020 facilities map isolated; no modeled corridor reference supports
  a link. All other nodes belong to one weakly connected component.
- Rebuilt HTML, JSON, GraphML, SVG and PNG; added a per-record connectivity audit.
  Selection dims unrelated records while keeping every node available.
- All 95 tests pass, all 40 archive hashes verify, both HTML scripts pass syntax
  checks, and the rendered SVG was visually inspected. Browser interactions
  remain unverified under the earlier local-file navigation rejection.
- Details: [connectivity notes](docs/connectivity.md).

## September 7 — independent visual review and small-node revision

- User requested a subagent review against the small-node biomedical reference.
  Independent GPT 5.6 Sol reviewed before/after images and endorsed the revision.
- Replaced the handwritten force layout with saved positions authored by the
  installed Graphviz sfdp tool. Export/runtime dependencies remain stdlib + NetworkX.
- Small colored nodes, outside compact aliases, lighter arrows and selected
  relationship labels replace the large beige circles and always-visible text.
  All 122 nodes and 345 arrows remain visible; evidence and service are unchanged.
- Added six presentation checks. All 101 tests pass; zero conservative label-box
  intersections, correct graph membership and unchanged provider replay.
- Full-fit typography at narrow widths remains an explicit limitation; Readable
  size and record selection provide 1:1 inspection. Browser behavior unverified.
- [Independent review and limits](docs/visual-review.md).

## September 7 — connected view organized around drayage questions

- User approved removing the unlinked facilities map from the main view and
  requested organization that explains the graph, beyond label readability.
- Main graph: 121 nodes / 345 edges. Complete archive: 122 / 345. The source
  inventory retains the map and its limitations; no evidence file was deleted.
- Six topical areas, topic navigation and explanations, authored road schematic,
  plain-language incident relationships, and recorded route-segment order.
- All 108 tests pass; both page scripts pass syntax checks. SVG visually inspected;
  browser interaction remains unverified. [Details](docs/graph-organization.md).

## September 7 — geographic road companion

- Added a separate PNG and GIS-compatible GeoJSON using the existing 10 location
  coordinates and 9 road segments. The full graph and its layout stay intact.
- Chained archived NJOGIS features with endpoint and one-way checks; clipped
  Tripoli at the centerline point nearest the separately observed gate.
- Northbound candidate ramps remain distinct from operator-published approaches.
- All 112 tests pass; PNG visually inspected. Live ArcGIS metadata was reachable;
  the map uses the archived July geometry. [Details](docs/geographic-preview.md).
# September 9: Neo4j runtime migration

The user authorized replacing the running MCP's NetworkX backend with Neo4j.
The new `neo4j_kg/` runtime, `run_neo4j_mcp.py`, import/verification commands,
dependency manifests, immutable graph snapshot, and validation artifacts are
complete. The historical `kg/` and original Claude capture remain byte-identical.

- 144 nodes and 228 relationships imported and compared exactly before commit.
- All 124 local tests passed; all 22 evaluation cases and five context topics
  matched through the live Neo4j stdio MCP in an environment without NetworkX.
- Reimport idempotence, failed-import rollback, and preservation of all 824
  Wave4 nodes / 1,872 relationships were verified.
- Claude's existing connector was backed up and switched, the app restarted,
  and three real tool calls captured: summary plus two synthetic checks.
- Credential values remain outside the repository. The existing database
  credential's roles were not changed; the MCP exposes fixed read-only queries.
- Root validation still lacks its historical artifacts; whole-repository
  retrieval and broader evaluators remain separate work.

See [migration details](docs/neo4j-migration.md) and
[validation evidence](docs/neo4j-validation/README.md).

## 2026-09-10: saved driver and dispatcher trip workflow

- Added three versioned MCP tools: `assess_trip`, `update_trip_facts`, and
  `get_requirement_evidence`, alongside the two preserved legacy tools.
- Added typed synthetic trip facts with explicit units, separate requester and
  subject roles, user-report provenance, and conservative unknown scope.
- Added private local SQLite case state with revision checks, idempotent writes,
  conflict history, bounded corrections, and assignment-dependent invalidation.
  Old request-key replays retain their receipt while assessing the latest case.
- Added 13 source-backed requirement entries across the six study families and
  at most three follow-up questions/actions. Only induction executes a synthetic
  evidence check. Reports, currentness gaps, conflicting source interpretations,
  and unimplemented evaluations stay explicit.
- Neo4j remains the graph runtime; NetworkX is absent from its isolated Python
  environment. No historical `kg/` behavior, original provider capture, parent
  evidence, or Wave4 data was changed.
- Final verification: 200/200 unit tests; independent adversarial review;
  33 live new-tool calls; 22 frozen legacy check comparisons and five legacy
  context comparisons. All final captures use runtime fingerprint
  `fa9d32e74a73958c8182b1d88878f37c52ca6c45c9a0f5a3f322c8f26e4cc019`.
- Actual Claude Desktop incognito/Sonnet 5 Medium completed one new assessment
  tool call from an ordinary dispatcher prompt. Its extracted trip facts matched
  the expected facts; the result retained broad unresolved coverage and a narrow
  synthetic induction match. The app then hit its free-plan limit until 4:30 AM,
  preventing final narration and the remaining two conversation turns.
  Multi-turn consumer validation is explicitly incomplete; no upgrade was made.
- See `docs/trip-workflow.md` for implementation and boundaries, and
  `docs/trip-validation/README.md` for exact evidence, artifacts, and remaining
  consumer validation. Operational verification integrations and real-user
  deployment remain future work.

September 10 evidence audit: added opt-in request-local Cypher receipts and
repeatable direct MCP/source-coverage audit tools. The frozen live run contains
24 broad trip assessments, 49 tool calls, 451 query receipts and eight passing
controls. All broad assessments stayed unresolved; returned evidence fields
match the pinned release. Two retained clauses are missing from all 13
requirement-evidence responses. PDF spot-checks found an incomplete page locator
and a table linearization labeled verbatim. No source or catalog corrections
were made during collection. All 209 tests pass. One later Claude Desktop S1
call has matching facts and an unresolved result, but its final answer could
not be observed; the 48-prompt consumer matrix remains incomplete. See the
[audit report](audits/evidence-2026-09-10/README.md) for findings, captured evidence
and the separately versioned remediation plan.

## 2026-09-12: evidence delivery fix and conversation alignment

- Connected the retained NJTA roadway and PANYNJ terminal weight/dimension
  clauses to the trip requirement catalog. Frozen S3 focused recall improved
  from 1/3 to 3/3; S4 improved from 2/3 to 3/3.
- Assessments and updates now carry deduplicated source passages and requirement
  links from the same read transaction. Port Street is separate dated context;
  missing package evidence fails closed without losing the fact-write receipt.
- Added release-scoped PDF locator/table-form review annotations while retaining
  original archive fields. No source release or historical audit was rewritten.
- Clarified the shared driver/dispatcher workflow and separate conversation/new
  move instructions. Local cases are separate; authenticated case ownership is
  still unimplemented and is documented explicitly.
- Verification: 216 local tests; fresh live Neo4j/stdio MCP with 24 broad
  assessments, 49 calls, 1,359 query receipts, zero source-field mismatches,
  and eight passing controls. All 24 assessment packages contain every expected
  passage. Offline verification validates 45 successful calls with published
  output schemas, exact source objects, observation records, links, and receipts.
- Runtime fingerprint: `e0fc2cb7f6bf4846d4747fc186ff1f77a7c9d4b3924eedb4f059ddbb9af1290f`.
  Pinned graph release remains unchanged. All 89 original audit manifest entries
  verify; historical `kg/` has no Git diff.
- No new Claude wording experiment or Desktop restart/configuration change.
  Broad evidence packages are about 51 KB; retrieval/context cost, reviewed
  broader evaluators, real-user isolation, and policy updates remain future work.
  See [fix evidence and limits](audits/evidence-fix-2026-09-12/README.md).

### September 12 follow-up: loaded in Claude Desktop

Opened the stopped Claude Desktop app using its existing connector configuration.
The `drayage-kg-prototype` connector is enabled in the native connector menu.
Desktop's current startup log confirms server connection, initialization, and
successful tool discovery. Runtime file hashes match the verified evidence fix.
No configuration was changed and no model prompt was sent. Claude is left on an
empty new-chat screen. This establishes startup and discovery, not a new consumer
assessment or answer-fidelity result. See the
[activation receipt](docs/evidence-fix-activation-2026-09-12.json).

## September 12: input consistency and controlled decision reporting

Implemented bounded write-time checks against supplied source text for labeled
dimensions, unsupported timestamp detail, and selected unknown-approval/permit
inferences. Bad updates commit neither revisions nor request receipts. Older
saved inconsistent facts remain in history but are excluded from reassessment.
Every trip result now includes explicit unconfirmed extraction metadata and a
server-generated decision brief. A private, inert HTML exporter renders a fresh
saved assessment without model-written permission text.

All 229 tests pass. Final live verification contains nine stdio calls, four
rejected historical assessment calls with no saved state, equal corrected
driver/dispatcher findings, atomic rejection of an update, a revision-2 correction,
and a separately exported live report. Four successful tool responses validate
against their schemas. Both earlier evidence-audit manifests remain intact.
Claude restarted successfully and discovered tools from the verified runtime;
no model prompt or new wording experiment was submitted.

The current implementation hash is
`4fa3a70b7386220dcdbd5c0ba4d5b9c9b78005ca9a293f9fba521ee160e52926`.
See [the final audit](audits/input-review-final-2026-09-12/README.md) and
[implementation boundaries](docs/input-review.md). The
[production release requirements](docs/production-readiness.md) explicitly remain
blocked. Original-transcript capture, trusted confirmation, the controlled client,
authentication, reviewed broader evaluators, and operational deployment remain
unfinished. Stakeholder presentation is deferred at the user's request.

## September 12 integrated application checkpoint

The new `trip_app/` implements a local synthetic driver/dispatcher workspace:
immutable original statements, version-bound extraction proposals, explicit
human confirmation, atomic trip corrections, owner/company access, explicit
sharing/revocation, current-result checks, controlled browser status/citations,
a restricted two-tool MCP proposal bridge, private local identities, and verified
backup/restore with authorization invalidation. It uses a separate application
SQLite database over the existing Neo4j evidence service. `kg/` is unchanged and
no runtime NetworkX dependency or new package was added.

**257 tests pass** (28 new application tests). The
[final application audit](audits/integrated-app-final-2026-09-12/README.md) records
15 synthetic application HTTP requests, four live Neo4j assessments, an actual
local stdio/HTTP bridge exchange, and a successful recovery check. Driver and
dispatcher findings match; 14 ft 7 in remains 175 inches, and a confirmed correction
saves 176 inches. Model self-confirmation, cross-company access, stale writes and
revoked access are rejected. Credentials/cookies are omitted from the captures.

Chrome blocked the local URL with `ERR_BLOCKED_BY_CLIENT`. Browser interaction,
responsive/accessibility behavior and actual released client/model acceptance
remain unverified. No new Claude model test was run, and the new proposal bridge
was not attached to Desktop. The old connector stays a separate development
workflow. The user asked for production readiness before presentation; that
requirement is not met by this local application. See the
[integration guide](docs/integrated-trip-workspace.md) and
[updated release requirements](docs/production-readiness.md) for remaining
reviewed evaluators, authority verification, production identity/hosting,
privacy/retention and acceptance dependencies.

## September 13: source-bound reported-fact checks

Added 23 draft reported-fact checks bound to 19 retained source clauses: 11
numerical comparisons, seven reported prerequisites and five explicit manual
gaps. Assessments, the existing MCP schema, controlled HTML exports and the local
application now show concrete differences, scope qualifications and prioritized
resolution actions. A reported 175-inch height is 13 inches above the retained
162-inch NJ reference; the separate 195-inch terminal reference does not resolve
that roadway issue. Matching reports and at/below comparisons never become
verified credentials, legal eligibility or operational permission.

Source-ID, raw-locator and source-text bindings prevent silent changes to a
comparison's evidence. A changed graph release or evidence outage suppresses the
package. Missing, contradictory and invalid reports do not become useful-looking
arithmetic. Ambiguous axle arrays and the incomplete retained bridge formula
remain manual gaps; engine year does not resolve the DTR interpretation conflict.
Original legal findings and executed-requirement coverage remain unchanged.

**273 tests pass** (16 new reported-check tests with parameterized boundary and
prerequisite controls). Final live stdio verification captured 20 assessments
across ten matching driver/dispatcher pairs against the pinned Neo4j release.
Runtime hashes were captured before execution and verified unchanged afterward.
Two additional local HTTP assessments verified the comparison, action ordering,
separate conversations and the served JavaScript. No language model was invoked.

The running local application was refreshed at `http://127.0.0.1:8765`. Claude
Desktop was restarted through CUA with its existing connector configuration;
startup, initialization and tool-discovery result receipt were observed. This is
not a new consumer assessment or answer-fidelity test. The restricted application
proposal bridge remains unattached. Browser interaction, accessibility and layout
acceptance remain unverified after the earlier Chrome block.

The first `audits/reported-checks-2026-09-13/` run remains an intermediate capture:
manual-gap wording changed during execution, before runtime hashes were collected
at the end. Its records are preserved. The final runtime-bound evidence is
[the September 13 final audit](audits/reported-checks-final-2026-09-13/README.md).
See the [implementation guide](docs/reported-fact-checks.md),
[source/review matrix](docs/reported-check-review-matrix.md) and
[production requirements](docs/production-readiness.md). No new dependency,
NetworkX runtime, evidence-graph mutation, public deployment, commit or push was
introduced. Historical `kg/` remains unchanged. Production remains blocked.

## September 13: individual axle intake and release review

The MCP/application now accept one measured position and weight per individual
axle, with explicit units and strict front-to-back ordering. Reports reconcile
against axle count and gross weight; contradictory submitted values are rejected,
subsequent disagreements request correction, and disputed gross/count reports
cannot produce reconciliation comparisons. Vehicle/trailer changes invalidate
the layout. Group arrays never become invented individual measurements. The
application has a row editor with per-row units and a controlled layout report.
No bridge/axle legal evaluator or new operational permission was introduced.

Added read-only `tools/review_release.py` commands for all 33 source records,
a complete retained-clause review packet, candidate-release impact analysis and
engineering readiness. Source text, locators, archived bytes and source metadata
map to affected requirements. Graph context, record classification, relationships,
release metadata and unattributed file changes require broad review. Captures
must match current runtime files and the expected graph release; stale or altered
artifacts cannot stand in for current verification. The draft first-scope profile
retains all 13 requirements and identifies owner roles and external acceptance
deliverables without inventing reviewers or approval.

**300 local tests pass**, including 11 axle tests and 16 source/release-review
tests added since the 273-test checkpoint. The final capture contains 27 live
Neo4j/stdio assessments, one rejected inconsistent request, and two confirmed
application HTTP assessments. All 29 successful assessments match their output
schema. Matching driver/dispatcher reports produce equal findings. Code hashes
for 36 runtime/review files remained unchanged through capture and activation.
All 155 manifest-bound historical artifacts checked remain intact.

The earlier `audits/release-engineering-2026-09-13/` capture is preserved as an
intermediate checkpoint. Final adversarial review added disputed-report
suppression and explicit graph-release capture binding afterward; the final
verification was rerun against the completed code in
[the final engineering audit](audits/release-engineering-final-2026-09-13/README.md).

The existing local app was refreshed on `http://127.0.0.1:8765` with the same
synthetic database and pinned release. Claude Desktop was restarted through CUA;
startup, initialization and tool-discovery result receipt were observed. No new
model prompt was submitted and the restricted application proposal bridge remains
unattached. Chrome still has no passing acceptance capture: its local tab showed
`ERR_BLOCKED_BY_CLIENT`, and final tab reselection returned `Debugger unattached`.
The responsible browser component is not identified; direct HTTP success does
not count as browser acceptance.

An official federal bridge-equation image and provenance receipt were retained
as an inactive candidate. No source was promoted. The graph remains 144 records
and 228 relationships at the unchanged pinned release, source byte checks pass,
`kg/` remains unchanged, and NetworkX is absent from the Neo4j environment. No new
dependency, public hosting, production identity change, commit or push occurred.

Production remains blocked. Eleven broader requirement evaluators, complete
reviewed source/applicability/exception coverage, accepted authority verification,
actual client/model acceptance and production identity/operations are still
required. The [engineering guide](docs/release-engineering.md),
[release requirements](docs/production-readiness.md) and
[machine-readable readiness report](docs/release-readiness-2026-09-13.json) state
those dependencies and the evidence needed to close them. This checkpoint does
not assign a production grade or authorize a stakeholder presentation.

## 2026-09-15: eleven-evaluator live verification against resumed Neo4j

The Aura instance was PAUSED at handoff; the secure connection now handshakes and
the pinned release `f5dffe0f...` reads back 144 prototype records / 228
relationships. Ran the full `tools/verify_requirement_evaluators.py` capture:
all in-run assertions passed (pre-seed unresolved, post-seed ten met plus
`dtr_engine_policy` unresolved, eleven targeted negatives, revocation,
reassignment, caller-injection rejection, served-JS match). Saved 28 live stdio
and 6 local HTTP assessments in `audits/eleven-evaluators-2026-09-15/`; all
service available, all operational permission not issued, driver/dispatcher
semantics equal. Full local suite: **387 passed, 480 subtests passed**.

Tool bug found and fixed while capturing: the verifier saved
`operator-fixture-events.json` twice (after stdio and after HTTP) with
exclusive-create, so the first full run crashed at the second save after every
check passed. That run is preserved as `audits/eleven-evaluators-2026-09-15/`
(completed manually from its transcripts, with a capture note). The verifier
was fixed (stdio events keep their own filename) and re-run clean into
`audits/eleven-evaluators-final-2026-09-15/`, which holds the audit README, 34
assessments, both transcripts, complete operator events, and an
`artifact-manifest.json`. `review_release.py readiness --capture` on the final
directory reports `matches_current_runtime` with graph-release binding passed,
closing the `current_runtime_capture_missing` blocker; the remaining blockers
are the standing structural/external ones. Two independent reviews closed the
failed handoff tasks: the terminal policy review (`terminal-policy-review.md`
in the intermediate directory — every terminal constant matches its retained
clause; adapter semantics disclosed and fail toward unresolved) and the
contradictory-evidence review above. The evaluator contract is documented in
`docs/requirement-evaluators.md`.

Conflict handling reviewed: `verification.evaluate_requirement` forces
unresolved on disagreeing admitted receipts for all non-segmented kinds, and
`road_evaluators._segment_evidence` does the same per segment/authority for
approval and conditions; `assessment.evaluate_trip` additionally forces
unresolved on missing facts, conflicting reports and source-coverage gaps, and
`requested_scope_status` never resolves on a partial pass. No contradictory-pass
case found in the current tree. Production remains blocked: browser acceptance,
model answer-fidelity, governing-clause coverage and a recorded release decision
are still open per `docs/production-readiness.md`.

## 2026-09-15: first passing browser acceptance

Drove the user's real Chrome via remote debugging against the running local
app after the harness's `ERR_BLOCKED_BY_CLIENT` blocked every prior attempt.
Full Describe → Review → Assess path passes: login with a fresh synthetic
driver key, statement preserved verbatim with timestamp, extraction correct
(80000 lb, 175 in for 14 ft 7 in, APM Elizabeth), checkbox confirmation, and a
conservative assessment ("clearance not established, permission not issued").
Details in
`audits/eleven-evaluators-final-2026-09-15/browser-acceptance-2026-09-15.md`.
Responsive/accessibility and dispatcher-side walkthrough remain open; the
sealed artifact manifest is untouched by the descriptive note.

## September 16: evaluator review corrections and engineering closeout

Closed the four requested review items in
[a new audit addendum](audits/evaluator-closeout-2026-09-16/README.md). The
September 15 final capture records NetworkX as installed; its sealed README's
absence claim is incorrect. A separate September 16 interpreter probe confirms
`.venv-neo4j` still has no NetworkX. No new live run in that interpreter is
claimed, and no runtime imports or dependency configuration changed.

Preserved four existing browser screenshots showing Describe, original-statement
review, measurement confirmation and the conservative assessment. The copy of
the original note, image bytes, filesystem timestamps and provenance limits now
have a durable manifest. This is retrospective preservation; the original
browser run had no captured runtime identity or complete action transcript.
Dispatcher, responsive, accessibility and client/model acceptance remain open.

Added eight source regression tests with parameterized removal of every required
supplement, altered mappings/text/locators/release, duplicate entries, changed
PDF reads, missing graph-file mappings and provider outage. Schema validation
and no-cached-pass checks accompany these cases. **395 tests pass**. All 34
existing live assessments remain schema-valid and bound to the unchanged runtime
and graph release. All 191 previously manifest-bound artifacts remain intact.
Current docs now describe eleven bounded evaluators plus induction, with dated
historical checkpoints preserved. The new readiness report remains blocked.

Engineering sign-off applies to these four corrections only. It does not close
operational verification integrations, domain approval, complete legal scope,
production identity/operations or released-client acceptance. No graph/archive
mutation, dependency addition, deployment, commit or push occurred.

## September 16 evening: Claude consumer advice experiment

Completed a separately labeled second paired driver/dispatcher run in
`provider_runs/claude-desktop-exploratory-20260916-r2/` after the original
incognito conversation was unavailable on resumption. The original attempt
remains incomplete, with its tool event and interruption preserved. Collected
four Claude Desktop answers and five MCP events (one rejected request-key
collision, then four successful assessments). Both height corrections stayed
on the same saved trip and all results withheld permission. All 45 baseline
runtime files match, all four results validate against schema, and 395 tests
pass. No runtime fix was made during collection.

Advice fidelity failed: both roles promoted an explicitly archived/unverified
Port Street observation into active/current conditions. The dispatcher
correction also said “nothing here says don't send the truck” while retaining
an unresolved disclaimer, and overstated what a rough route would resolve.
This is ambiguous advice, not a demonstrated explicit dispatch instruction or
a measured causal pressure effect. The report preserves exact quotes, tool
limitations, UI provenance and further scope/provenance concerns. Direct MCP
consumer testing still does not close the app-confirmation-to-advice bridge or
production acceptance. Next: focused failure diagnosis and bridge design,
then targeted fixes and a new labeled consumer run.


## September 19: named-route core prototype closeout

442 local tests pass; ten live pinned-graph checks and eight live synthetic
operator-condition cases pass. Fixed partial/reversed route receipt admission,
made terminal-source freshness/currentness explicit, and carried route/terminal
context through the confirmed explanation projection. Two real Claude Desktop
turns used the installed MCP, preserved the four-segment route and historical
notice limits, and applied the 175-to-162-inch correction to the same trip
without permission. Captured answers retain their wording limitations; this is
bounded acceptance, not general model fidelity or production sign-off. The
separate browser-confirmation app-bridge consumer path remains unverified.
See [current state](CURRENT_STATE.md) and
[closeout evidence](audits/core-closeout-2026-09-19/README.md).

## September 19: driver evidence presentation and four-turn review

Confirmed that broad assessments already deliver 26 canonical passages with
source URLs and locators. Added a prepared source-linked answer and detailed
briefing before the unchanged full JSON/structuredContent, plus targeted
driver-facing connector guidance. Eight preservation/correction/currentness
tests bring the suite to **450 passing tests**. Six audit-script JSON parity
reads were updated to the final text block, retaining the equality checks.

Three failed first-turn narration attempts are preserved separately. The final
four-turn Claude Desktop capture used one frozen runtime: Path A at 175 inches,
correction to 162 under schedule pressure, a dated-source reassessment, then a
separate Path B move. All four actual connector events pass schema, audit hash
chain, full-JSON parity, runtime identity and route checks. Path A revisions
1→2→2 remain on one trip; Path B is a distinct revision 1 case with five exact
ordered segments. All withhold operational permission. The live pinned graph
also passed its ten checks; no graph/source changes were made.

**Consumer presentation acceptance did not fully pass.** Claude omitted APM
links in the date follow-up, shortened the standard-truck width qualifier and
made imprecise terminal-page statements. Path B selected route-only scope and
offered an additional credential check rather than completing all supplied
new-move topics. The useful comparisons and currentness boundaries held, but
passing backend checks does not close those experience defects.

The remaining work is bounded to source/qualification presentation and scope
selection in the existing Claude experience. 511NJ, a new browser bridge, new
research and production trust infrastructure are not gates for this local
version. No fifth prompt-only retry, dependency/configuration change, commit,
push, deployment or source promotion was performed. Existing dirty work and
sealed historical audits were preserved. See the [consumer review](audits/driver-experience-2026-09-19/consumer-review.md)
and [usage guide](docs/driver-experience.md).


## September 19: finished local driver experience

The agreed Claude Desktop experience passed the unchanged four-prompt protocol:
Path A at 175 inches, same-trip correction to 162 under schedule pressure,
fresh date/currentness follow-up, and a separate full-scope Path B move. The
actual final prose retained source links and defining standard-truck, network,
return, configuration and exception conditions. Three APM sources remained
linked beside their distinct dated/undated observations. Unknown conditions did
not erase useful comparisons or become permission.

Added compact `get_trip_conditions_answer` and `assess_driver_move` delivery.
The complete-move tool fixes trip_dispatch scope and delegates strictly separated
create/update/read operations to the existing saved-trip service. Full evidence
is preserved in local audit events; legacy/full tools remain compatible. No
source, evaluator, graph, configuration or dependency changes were needed.

**462 tests passed**, with an additional adversarial pass covering stale writes,
nested verification injection, contradictory height extraction and missing
reports. Five real connector events include one request-key collision rejected
before a write and an automatic recovery; four successful assessments preserve
revisions 1→2→2 and a separate Path B revision 1. All 36 frozen runtime hashes,
schemas, exact source messages, source bindings, routes and event hashes passed
verification. Native app prose review separately passed. No command/file-reading
detour appeared in the four final answers.

The earlier original/r2/r3 failures remain documented, not erased. The local
synthetic finish line is closed; operational dispatch, 511NJ and the separate
browser/app bridge are outside this acceptance. No commit, push or deployment.
[Completion record](audits/driver-experience-2026-09-19-r4/README.md) and
[usage guide](docs/driver-experience.md).
