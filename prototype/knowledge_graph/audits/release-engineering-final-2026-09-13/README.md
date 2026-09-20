# Final individual-axle and release-engineering capture

September 13, 2026. This is a synthetic local engineering capture against the
pinned live Neo4j release. **Production remains blocked.** No language model was
invoked, no browser acceptance passed, and no legal evaluator beyond the existing
synthetic induction check was activated.

| Verification | Result |
| --- | --- |
| Full local suite | 300 tests passed. |
| Prior reported-check regression | 20 live stdio assessments across ten driver/dispatcher pairs. |
| Individual axle behavior | Seven live stdio assessments: matching driver/dispatcher inputs, corrected gross mismatch, disputed gross report, vehicle reassignment, trailer reassignment and legacy group arrays. |
| Inconsistent input rejection | One count/layout contradiction rejected through MCP. |
| Application confirmation | Two HTTP assessments in separate synthetic driver/dispatcher conversations; original statement recorded before explicit confirmation. |
| Response contract | All 29 successful assessments validated against the current output schema. |
| Runtime binding | SHA256 map for 36 runtime/review files collected before the capture and verified unchanged afterward. The verifier script is separately hashed and retained. |
| Existing evidence | All 155 manifest-bound artifacts in preceding captures verified intact. |
| Source release | Source bytes and content-addressed release verified; 144 records, 228 relationships, unchanged revision. |
| Local operation | Application database integrity check passed; current JavaScript served; `node --check`, `git diff --check` and unchanged `kg/` checks passed. |
| Claude activation | Existing connector restarted via CUA; initialization and tool-discovery result receipt observed. No model prompt or configuration edit. |
| Browser | Last visible local page reports Chrome `ERR_BLOCKED_BY_CLIENT`; final tab reselection returned `Debugger unattached`. No rendered acceptance claim. |

The release revision is
`f5dffe0f7a32b5144920efb5a644f8c4dc9f20def76b4217c38b0cdbc454cf5c`.

The synthetic five-axle example reports 80,000 lb total and a 624-inch first-to-last
span. Correcting gross to 79,000 lb produces a 1,000 lb disagreement and suppresses
the gross comparison. Leaving the gross report disputed produces no reconciliation
difference. Changing the assigned truck or trailer invalidates the layout.
Legacy 12,000/34,000/34,000 lb group reports remain structurally unknown as an
individual layout. These arithmetic and intake outcomes establish no bridge-rule,
axle-group, road-classification or permit eligibility conclusion.

`source-inventory.json` identifies all 33 source records and their dependent
requirements/checks. `source-review-packet.json` retains exact stored clauses and
all 13 draft requirements. `transaction_release` still has no retained governing
clause. The proposed scope preserves the complete catalog; no scope was removed
to make a grade pass.

The source comparison is deliberately a same-snapshot control. It demonstrates
no change between the supplied releases, not external currentness monitoring.
Changed-source/context/metadata and missing-clause behavior is covered in the
local tests. The inactive official bridge-equation image and receipt remain
separate from the graph. Definitions, rounding, applicability and exceptions
have not completed review.

Capture layout:

- `summary.json`: current graph revision, runtime hashes, surface and behavior counts.
- `axle-mcp-transcript.json`, `tools.json`, `stdio-stderr.txt`: actual local MCP exchanges.
- `axle-http-transcript.json`: synthetic application capture and confirmation; login keys, session cookies and CSRF values omitted.
- `reported-checks/`: fresh prior-check cases, results, tool exchange and controlled HTML report. Its sub-summary follows that verifier's older runtime-map format; the root summary provides the complete binding for this capture.
- `source-inventory.json`, `source-review-packet.json`, `unchanged-release-comparison.json`, `proposed-scope.json`: read-only operator review artifacts.
- `inactive-source-candidate/`: exact candidate image and receipt; not activated.
- `local-tests.txt`, `verifier.py`, `validation-status.json`: test log, exact verifier and schema/source/history checks.
- `activation-receipt.json`, `browser-status.json`: precise application/connector acceptance limits.
- `artifact-manifest.json`: byte hashes for every artifact except the manifest itself.

The manifest establishes consistency, not reviewer authenticity. A matching
runtime hash does not prove test adequacy or replace a domain/security review.
The [readiness report](../../docs/release-readiness-2026-09-13.json) was generated
only after sealing this capture, so it is external to this manifest. Reproduce it
with `python3 tools/review_release.py readiness --capture audits/release-engineering-final-2026-09-13`.
Exit 2 means the current synthetic implementation remains blocked for production;
a passing artifact/graph binding does not change that result.

The earlier `../release-engineering-2026-09-13/` directory is an immutable
intermediate capture predating the final disputed-report and graph-binding fixes.
Its passing exchanges remain historical evidence and were not relabeled as final.

Reproduce the live capture using a **new output directory**, the existing
synthetic application running current code, the private synthetic access directory,
and the pinned Neo4j credentials file:

```sh
.venv-neo4j/bin/python tools/verify_release_engineering.py \
  --credentials-file /Users/marbin/.config/drayage-mcp/neo4j.env \
  --private-directory .runtime/integrated-app-2026-09-12 \
  --output .runtime/new-release-capture
```

This command creates synthetic conversations and renews expired synthetic access
only when required. It does not modify the public graph or invoke a language
model. It creates raw captures; manifest sealing, full-suite capture, schema
validation and client activation receipts are separate recorded checks.
