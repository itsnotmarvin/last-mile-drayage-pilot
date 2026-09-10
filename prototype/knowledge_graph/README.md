# Drayage knowledge-graph prototype

## Driver and dispatcher trip workflow

The current MCP also supports a saved synthetic trip conversation: `assess_trip`,
`update_trip_facts`, and `get_requirement_evidence`. It keeps reported facts and
corrections, selects requirements across the six study families, rechecks the
assignment against Neo4j, and asks up to three focused follow-up questions.
Read the [workflow and code guide](docs/trip-workflow.md). Only induction has an
executable synthetic evaluator; the other families expose evidence needs and
unimplemented coverage explicitly.

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
