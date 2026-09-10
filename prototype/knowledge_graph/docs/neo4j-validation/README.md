# Neo4j migration verification

Verified September 9, 2026 (America/New_York; receipts use September 10 UTC).

The live Claude Desktop connector now runs `run_neo4j_mcp.py` in the isolated
`.venv-neo4j` environment, with no NetworkX installed. The release is
`f5dffe0f7a32b5144920efb5a644f8c4dc9f20def76b4217c38b0cdbc454cf5c`.

| Check | Observed result | Evidence |
| --- | --- | --- |
| Complete local suite | 124 tests passed: original 112 plus 12 migration tests | [receipt](local-suite.json), [complete test log](local-suite.txt) |
| Graph import | All 144 nodes, 228 relationships, records, types, order, and provenance matched | [activation.json](activation.json) |
| Live stdio MCP | All 22 frozen evaluation cases and all five context topics matched every substantive baseline result field | [verification.json](verification.json), [complete transcript](stdio-transcript.json) |
| Runtime dependencies | NetworkX absent; `pip check` passed | Runtime environment used by the live verifier |
| Reimport and rollback | Repeat import created no duplicates; injected post-write verification failure left zero probe records | [import-adversarial.json](import-adversarial.json) |
| Existing Wave4 graph | All 824 nodes and 1,872 relationships retained the same complete-data fingerprint | [import-adversarial.json](import-adversarial.json) |
| Actual Claude Desktop | Three actual tool calls: summary and two induction cases; all supplied arguments and expected statuses preserved | [manifest](claude-manifest.json), [tool audit](claude-tool-audit.jsonl), [observed response](claude-response.md) |
| Historical evidence | Original `kg/`, legacy entry point, and original consumer capture retained byte-identically | Historical capture tests and pre-migration file-hash comparison |

The final live runtime implementation fingerprint is
`25e1b4363066e788e35bc4fccf2f964069029b0b5a60a0ced7295ffbc03c89f8`.
All 27 stdio calls and all three actual Claude tool calls used that fingerprint.
The expected differences from the historical evaluator are this implementation
identity, the pinned graph-release identity, derived evaluation IDs, and the
summary engine string. No checking semantics or source text was changed.

Claude's observed answer correctly reported the Neo4j engine and counts,
distinguished real archived policy from synthetic driver records, preserved the
induction/dispatch scopes, and withheld wider clearance. This was one explicitly
tool-directed conversation in incognito Chat using the visible model label
Sonnet 5 Medium. The implementation author reviewed narration; there was no
independent grading or spontaneous-discovery test. Earlier recorded Claude
failures remain in the separate September 6 capture.

Claude configuration was backed up before replacement. Only the existing
`drayage-kg-prototype` server entry changed. The app was restarted, and its live
process was confirmed to run the new entry point. Credentials are retained
outside Git; no new database user or permission grant was created.

The parent repository validator remains blocked by missing historical artifacts.
It is not counted as passing. Whole-repository reading/search and new evaluators
are separate work. See the [migration guide](../neo4j-migration.md) for exact
scope, installation, release activation, and rollback.
