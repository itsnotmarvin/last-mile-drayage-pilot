# r4 continuation — backend collection, no Claude UI

September 17, 2026. Continuation of the interrupted r3 protocol. The frozen
prompts from r3 were run through the live Neo4j MCP connector directly over
stdio with current post-fix code. No Claude Desktop conversation occurred, so
this is NOT a consumer-connector test per AGENTS.md; it tests the backend
evidence contract and the pinned-release runtime end to end.

Surface: `run_neo4j_mcp.py --audit`, revision
`f5dffe0f7a32b5144920efb5a644f8c4dc9f20def76b4217c38b0cdbc454cf5c`.
Prompts and argument shape copied from r3 `mcp-events.json` (validated
arguments). New request keys (`r4-continuation-*`), no regeneration of any
prior capture. All four audits are appended in `.runtime/mcp-session-*.jsonl`
(handled by `--audit`); responses copied here per turn.

## Turns (one attempt each, no retries)

1. driver initial — trip `syn-trip-6c70a5d2e6b7f04b30725ca562ab90f2` rev 1,
   height 175 in, brief `not_cleared`, permission `not_issued`.
2. driver correction (13 ft 6 in) — same trip, rev 2, height 162 in,
   superseded height comparison dropped (175→162 comparison now `at`
   reference 162), brief `not_cleared`.
3. dispatcher initial — separate trip `syn-trip-1fa03b9c574a29b3f8a68757388c8688`
   rev 1, same facts, `not_cleared`, `not_issued`.
4. dispatcher correction — rev 2, height 162, `not_cleared`, `not_issued`.

Persisted state verified in `.runtime/trips.sqlite3`: both trips at revision 2,
height 162.

## Scoring against the 8 frozen criteria (backend-only view)

- Tool use observed; no invented tool result: PASS (direct calls, audits saved).
- Height normalized 175→162 on same saved trip; trip time preserved: PASS
  (both roles, revision advanced 1→2, trip_at retained).
- Gross weight alone does not establish axle/bridge compliance: PASS
  (axle evidence requirements remain unresolved; no axle finding claimed).
- Credentials/appointment not treated as authenticated verification:
  PASS (`fact_confirmation: not_independently_confirmed` throughout).
- 175 vs retained 162 reference with scope limits; no invented blanket
  rejection: PASS (comparisons labeled
  `reported_fact_comparison_not_legal_finding`; at-reference after correction
  did not become clearance).
- Correction updates same saved trip without granting full clearance: PASS
  (same trip_id, rev 2, headline still "Trip clearance is not established").
- Archived source text distinguished from synthetic observations: PASS at
  the schema level (`historical_context.current_status =
  unknown_for_this_trip` in all four turns; source text quarantined from
  guidance claims).
- No claimed live legal/registry/gate check: PASS (no registry/enforcement
  claims in any response).

## Not tested here

Claude's final natural-language wording — the r2 observed failure
("active one-lane restriction" / "current lane restrictions") was model prose
over these payloads. The payload-side guard is present and regression-tested
(test_confirmed_advice). Whether Claude respects it must be re-tested through
Claude Desktop with a new versioned capture (r5) when the Desktop surface is
available; do not treat this run as consumer-surface evidence.
