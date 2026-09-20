# Drayage knowledge-graph prototype

Today's driver experience uses the existing **Claude Desktop
drayage-kg-prototype connector**. It now receives a prepared source-linked
answer, a detailed evidence briefing and the full structured assessment.
See [how to use it](docs/driver-experience.md).

**450 local tests pass. The four-turn driver presentation acceptance did not
fully pass.** The live walkthrough preserved the same-trip height correction,
separate Path B case and exact routes, and useful evidence while current
conditions remained unknown. Claude still dropped terminal links from a
follow-up and shortened an access-rule qualification. These are outstanding
experience defects, not missing sources. The new Path B move also selected a
narrower route scope. See the [current state](CURRENT_STATE.md) and
[driver experience review](audits/driver-experience-2026-09-19/README.md).
511NJ and the separate browser/app bridge are not gates for this local version.

The underlying engineering checkpoint has eleven bounded requirement evaluators plus the
existing synthetic induction check. Operator-owned synthetic receipts supply the
measurements, credentials, permits and conditions; user reports cannot verify
these facts. Missing or conflicting evidence remains unresolved. Production
remains blocked and operational permission is never issued.

**442 local tests passed** at the earlier September 19 core checkpoint. The installed
Claude Desktop connector passed a two-turn named-route acceptance check:
four ordered Path A segments, terminal-source currentness kept unknown,
175→162-inch correction on the same saved trip, and no permission issued.
Eight fresh live-Neo4j operator-condition cases and the ten-check graph
validation also passed. See [current state](CURRENT_STATE.md) and the
[September 19 closeout](audits/core-closeout-2026-09-19/README.md).

The [confirmed-assessment explanation bridge](docs/confirmed-advice-bridge.md)
adds qualified answer guidance and a separately authorized read of the latest
user-confirmed assessment. Its live HTTP/stdio capture is complete; actual Claude
use of this new app bridge remains unverified. The preserved paired Claude run
found archived-currentness narration failures. No production acceptance is claimed.

The [September 16 closeout](audits/evaluator-closeout-2026-09-16/README.md)
corrects the capture-environment claim, preserves the existing browser screenshots,
adds eight source-delivery regression tests and reconciles current documentation.
The [September 15 live audit](audits/eleven-evaluators-final-2026-09-15/README.md)
contains 28 stdio and six HTTP assessments against the pinned Neo4j release.
Its recorded environment had NetworkX installed; the audit README's claim of
NetworkX absence is incorrect. The isolated `.venv-neo4j` environment remains
NetworkX-free. Presence in the capture environment does not establish runtime
use of NetworkX as the graph store.

The preserved browser images support a synthetic driver walkthrough through
Describe, Review and Assess. They lack an original runtime binding and complete
action transcript; full client acceptance remains open. See the
[evaluator contract](docs/requirement-evaluators.md) and
[current production gates](docs/production-readiness.md).

The earlier [individual axle intake and release review](docs/release-engineering.md)
adds explicit per-axle measurements, count/gross reconciliation, source-change
impact reports and verification-capture binding to code and graph release.
At the September 13 checkpoint, **300 local tests passed**, with 27 live Neo4j/MCP assessments, one rejected
inconsistent request and two confirmed application HTTP assessments. See the
[final engineering audit](audits/release-engineering-final-2026-09-13/README.md).
At that checkpoint, browser acceptance was unverified. Production remains blocked.

The earlier [source-bound reported-fact checks](docs/reported-fact-checks.md)
explain numerical differences and reported prerequisite problems, then prioritize
specific resolution actions. The catalog has 23 draft checks tied to 19 clauses;
these do not expand the legal evaluator coverage beyond synthetic induction.
At that checkpoint, **273 local tests passed**, with 20 live Neo4j/MCP assessments across ten matching
driver/dispatcher pairs. See the [final September 13 audit](audits/reported-checks-final-2026-09-13/README.md).

Separate implementation: the [integrated driver and dispatcher workspace](docs/integrated-trip-workspace.md)
captures original statements, requires user review of proposed facts, enforces
local conversation access, and displays fresh Neo4j assessments and citations.
It includes a restricted MCP proposal bridge with an optional confirmed-assessment read and verified local backup
and restore. This is a local synthetic application; browser and actual client/model
acceptance remain incomplete. The [production release requirements](docs/production-readiness.md)
remain open; stakeholder presentation is deferred at the user's request.

The earlier [input consistency and controlled reports](docs/input-review.md)
remain underneath this application and in the existing Neo4j connector.

The [September 12 evidence fix](audits/evidence-fix-2026-09-12/README.md)
repairs the two missing clause mappings identified in the
[September 10 audit](audits/evidence-2026-09-10/README.md). Trip assessments now
include supporting passages, requirement links, separate dated route observations,
and source-extraction review notes. At that checkpoint, 216 local tests passed; all 24 fresh live
Neo4j/MCP broad assessments deliver their expected passages. Claude answer
validation remains incomplete. Historical counts below describe earlier checkpoints.

The updated runtime has also been
[loaded by Claude Desktop](docs/evidence-fix-activation-2026-09-12.json): the
connector is enabled and startup/tool discovery succeeded. No new model response
was collected during activation.

## Driver and dispatcher trip workflow

The current MCP also supports a saved synthetic trip conversation: `assess_trip`,
`update_trip_facts`, and `get_requirement_evidence`. It keeps reported facts and
corrections, selects requirements across the six study families, rechecks the
assignment against Neo4j, and asks up to three focused follow-up questions.
Read the [workflow and code guide](docs/trip-workflow.md). Eleven additional
bounded evaluators execute when matching operator verification records are
available. Their exact scopes and remaining gaps are documented in the
[evaluator contract](docs/requirement-evaluators.md).

## Current MCP: Neo4j

The current MCP runtime is `run_neo4j_mcp.py`, backed by a pinned Neo4j evidence
release and an isolated environment without NetworkX. Read the
[migration and setup guide](docs/neo4j-migration.md) for architecture, installation,
import, verification, configuration, rollback, and remaining limits.
The [validation record](docs/neo4j-validation/README.md) includes 124 passing
local tests, 27 live stdio comparisons, and three actual Claude Desktop calls.

The `kg/` package and `run_mcp.py` below are preserved historical NetworkX
fixtures used by the original provider capture, tests, and offline exports.
They are not the Neo4j runtime. The two existing MCP tool contracts are preserved
alongside the three new trip tools; whole-repository retrieval is separate work.

## Explore the entire populated graph

Open [the whole graph](output/evidence-graph/index.html): all 121 connected public
nodes and 345 relationships, with zoom, full labels, evidence inspection, and
JSON/GraphML exports. The separate neighborhood explorer supports full-record
search. Rebuild with `python3 export_graph.py`; see [explorer notes](docs/explorer.md)
for scope and verification. The latest view follows six drayage topics, with topic navigation, plain-language
relationships and ordered route segments; [organization notes](docs/graph-organization.md).

This is a queryable local graph and an experimental checking service, not an
operational clearance system. Its first executable requirement is APM Elizabeth
safety induction. All model interpretations remain draft until human review.

The parent repository holds the source evidence. The historical prototype imports it
read-only into a NetworkX directed multigraph. It does not install or claim to
run TypeDB, Neo4j, or a production database. That historical statement applies
to `kg/`, not the new `neo4j_kg/` runtime. NetworkX 3.6.1 is already available
in the current Python 3.11 environment; no packages were installed.

## Run the checks

From this directory:

```sh
python3 -m unittest discover -s tests -v
```

Read `docs/design.md` for the graph model, `GOAL_BRIEF.md` for scope and completion
criteria, and `PROGRESS.md` for verified results and remaining work.

The parent repository's existing `python3 tools/validate_records.py` fails on
the missing `visuals/visual_manifest.json`. That pre-existing failure is not
fixed, hidden, or counted as a passing prototype test.

## Historical prototype capabilities

- Connected evidence graph: 121 nodes and 345 relationships, including 32 source
  records and 31 retained source clauses. Five mutable observations are
  quarantined and now link only to their archived source. The enrichment connects
  33 of 34 formerly isolated records and adds the retained historical traffic
  analysis. The unlinked facilities map remains in the separate source inventory
  and complete archive export (122 records). See [the connection audit](docs/connectivity.md).
- Frozen service archive baseline: 121 nodes and 202 relationships.
- Prototype overlay: 144 nodes and 228 relationships in total, including the
  induction check, one supplemental source extraction, and synthetic evidence.
- One deterministic induction evaluator with source citations, input/version
  fingerprints, missing-fact reporting and explicit unchecked coverage.
- Two read-only MCP tools: `check_apm_induction` and
  `get_drayage_graph_context`; local stdio transport only.
- 108 tests pass in the current shared prototype: the original 75, eight
  provider-capture integrity tests, five graph-export tests, seven explicit-reference tests, six presentation tests, and seven organized-view tests. The original
  suite includes 22 frozen outcome cases and a separate-process tool handshake.
- Six frozen cases collected through actual Claude Desktop incognito Chat:
  six tool calls, six expected induction statuses, four fully matching inputs.
  Two scope-extraction failures and narration/source errors are retained.

Read [the provider results](docs/claude-provider-results.md) for what worked,
what failed, complete saved answers and reproducible artifact checks. This is
one small development run, not a safety certification.

Inspect the graph:

```sh
python3 -m kg context summary
python3 -m kg context induction
python3 -m kg context route_directions
python3 -m kg context port_street
```

For a check, provide a JSON file with synthetic facts:

```sh
python3 -m kg check --input examples/matching-induction.json
```

No package installation is needed in the inspected environment. Another machine
must provide Python 3.11 and NetworkX 3.6.1; dependency installation is not part
of this prototype's setup automation. NetworkX uses a BSD 3-Clause license;
source-document reuse permissions remain separate from the library license.

## Historical test limits

ChatGPT/Gemini or other clients; Claude's context-tool use and spontaneous tool
discovery; real credential checkers; live policy freshness; route/permit/vehicle
eligibility; persistent storage and multi-user authentication. The imported
31 clauses do not mean 31 executable checks exist.

Neo4j persistence and the migrated connector are covered by the separate
[migration validation](docs/neo4j-migration.md). The other limits still apply.

See `docs/provider-test.md` for the completed Claude setup and collection plan. This prototype
is not operational, even when a synthetic single-requirement result is `met`.
