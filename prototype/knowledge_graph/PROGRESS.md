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
