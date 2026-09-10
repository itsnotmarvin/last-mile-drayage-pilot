# Neo4j runtime migration

The live drayage MCP uses a pinned, immutable Neo4j release. Its two tool names,
synthetic induction semantics, exact source quotations, missing-fact behavior,
and operational coverage limits are preserved. The original `kg/` package and
`run_mcp.py` remain byte-identical historical fixtures for September 6 capture
replay, offline exports, and migration comparisons. They are not the new runtime.

## Runtime and data flow

```text
Claude Desktop
  → run_neo4j_mcp.py (isolated .venv-neo4j)
  → neo4j_kg/mcp_server.py
  → neo4j_kg/service.py (defined synthetic checks)
  → neo4j_kg/store.py (parameterized Cypher, Neo4j read transactions)
  → DrayageRecord nodes and native relationship types in Neo4j
```

`requirements-neo4j.txt` contains the runtime dependencies. NetworkX appears
only in `requirements-dev.txt`; the runtime neither imports `networkx` nor
imports the historical `kg` package. The small evaluator was ported into the
new package to preserve the historical implementation fingerprint. Full-result
parity tests constrain that port; new behavior belongs in the new runtime.

Neo4j is the graph query store. Original documents and structured input files
remain the retained evidence. Before each tool answer, the runtime verifies
the complete database release against its content-addressed revision and
checks all 51 recorded local input/archive hashes. Source changes require a new
validated release. These hashes establish integrity, not semantic completeness
or present-day legal authority.

Every invocation uses a new read transaction and parameterized node and
relationship queries. There is no cached successful answer or automatic fallback
to NetworkX. Missing/corrupted releases, missing/changed source bytes, connection
failures, and timeouts return a tool error without a check status or clearance.
Records may be cached only within the current invocation.

## Dataset isolation and updates

The drayage dataset is `last-mile-drayage-pilot`. Its initial release contains
144 records and 228 relationships, including the original 121-record,
202-relationship archive and the synthetic overlay. This preserves the evaluator
baseline; it does not silently substitute the separately enriched visualization
graph or import the whole repository.

`DrayageRecord` identity is `(dataset, revision, id)`. `DrayageRelease` identity
is `(dataset, revision)`. The original IDs, kinds, layers, archive membership,
record order, and lossless `record_json` are stored on nodes. Native relationship
types preserve existing relationship names; edge IDs, order, membership, and
lossless records are retained as properties. Unique constraints prevent duplicate
record/release identities. The importer also validates edge identities and
endpoints.

The existing `Wave4Entity` experiment is separate. Import commands never delete
or modify it. Each new drayage release is created in one transaction, compared
against every source node/property/relationship before commit, and retained
alongside earlier releases. Existing releases are compared rather than overwritten;
identical reimports are idempotent and differing content is rejected.

The optional `DrayageDataset.active_revision` pointer changes only with
`--apply --activate`. The MCP always uses the explicit
`DRAYAGE_NEO4J_REVISION` configuration, so an import cannot silently change a
running client's evidence. Activate only after validation; update the client
revision and restart it to adopt a new release. Rollback selects a previously
verified revision; no data deletion is necessary.

## Reproduce the migration

Create a development environment with `requirements-dev.txt` for the baseline
suite, snapshot builder, and historical exports. Create a separate runtime
environment with only `requirements-neo4j.txt`:

```sh
python3 -m venv .venv-neo4j
.venv-neo4j/bin/python -m pip install -r requirements-neo4j.txt

# Run using the development Python with NetworkX installed:
python3 tools/build_neo4j_snapshot.py \
  --oracle-output .runtime/neo4j-oracle.json
python3 -m unittest discover -s tests -v

# Credentials remain outside the checkout:
.venv-neo4j/bin/python tools/import_neo4j.py --apply \
  --credentials-file /path/outside/repo/neo4j.env
.venv-neo4j/bin/python tools/verify_neo4j_migration.py \
  --oracle .runtime/neo4j-oracle.json \
  --credentials-file /path/outside/repo/neo4j.env \
  --output .runtime/neo4j-verification
.venv-neo4j/bin/python tools/verify_neo4j_import.py \
  --credentials-file /path/outside/repo/neo4j.env \
  --receipt .runtime/neo4j-import-verification.json
```

After the live parity checks pass, repeat the import with `--apply --activate`.
Configure Claude using `claude_desktop_config.neo4j.example.json`, substituting
the checkout, runtime Python, protected credential-file path, and verified
revision. Preserve unrelated connector configuration. Audit files are private
under `.runtime/`; captured validation artifacts contain public evidence and
synthetic records only.

TLS certificate verification is required (`neo4j+s://`). No arbitrary Cypher,
write tool, file reader, shell execution, or database-administration tool is
exposed to Claude. Runtime queries use Neo4j read access mode, timeouts, and fixed
query templates. The existing credential has not been replaced or assigned a
new database role; application-level read-only behavior is not a claim that
the credential itself has restricted database permissions.

## Validation boundaries

`docs/neo4j-validation/` records live stdio comparisons and the separate Claude
Desktop check. Expected migration differences are the implementation fingerprint,
graph-release identity, derived evaluation ID, and summary engine description.
All other returned fields must match the historical evaluator.

The original six-case consumer capture and its documented narration/input errors
remain unchanged. The migration intentionally preserves the existing default
of induction when `question_scope` is omitted; improving that contract requires
a separately versioned behavior change and its own test expectations.

Whole-repository search, arbitrary record/graph lookup, visual/document reading,
and additional policy evaluators remain outside this migration. The root
repository validator still references the missing visual manifest and absent
historical experiment trees (`elizabeth-pilot`, `elizabeth-browser-pilot`, and
`elizabeth-wave2`). No replacement evidence was invented, and that validator is
not reported as passing. The migration verifies its actual input/archive bytes,
complete graph, frozen behavior, transport, and existing Wave4 data separately.
