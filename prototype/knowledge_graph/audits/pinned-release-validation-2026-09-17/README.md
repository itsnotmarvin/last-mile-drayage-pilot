# Pinned-release validation — 2026-09-17

Critical-path step 4. Read-only proof that the operational graph behind the
installed `drayage-kg-prototype` connector is internally consistent and
source-traceable.

- Revision: `f5dffe0f7a32b5144920efb5a644f8c4dc9f20def76b4217c38b0cdbc454cf5c`
- Dataset: `last-mile-drayage-pilot`, database `neo4j` (Aura)
- Result: **PASS 10/10** — see `receipt.json`

## Files (all isolated to this directory)

- `validate_pinned_release.py` — read-only suite (MATCH-only Cypher via
  READ_ACCESS `execute_read`; no `execute_write`, no import, no TripStore writes)
- `queries.cypher` — exact query templates used
- `receipt.json` — immutable receipt: revision, database, snapshot/script/query
  hashes, UTC timestamps, per-check PASS/FAIL, counts, Wave-4 observation

## Rerun

From `prototype/knowledge_graph`:

```sh
.venv-neo4j/bin/python audits/pinned-release-validation-2026-09-17/validate_pinned_release.py \
  --receipt audits/pinned-release-validation-2026-09-17/receipt.json
```

Credentials resolve from `--credentials-file`, else `NEO4J_CREDENTIALS_FILE`,
else `~/.config/drayage-mcp/neo4j.env`. Secrets never enter the receipt.

## Notes

- One suite expectation was corrected during the run (not a graph defect):
  `transaction_release` evidence status is `prototype_extraction_only`
  (draft graph-linked supplements exist) rather than `source_coverage_gap`.
  The structural property — zero archived sources, explicit gap — holds and is
  what the suite now asserts.
- Wave-4 observed intact at 824 nodes / 1872 rels; no cross-graph edges.
- Wave-4, S2 replay, Stage 1/2, expanded evaluation, new schemas: PARKED.
