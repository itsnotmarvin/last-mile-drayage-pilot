# Final reported-fact check verification

September 13, 2026. Synthetic local backend verification and existing Claude
connector startup. No language model was invoked and no production permission
was issued. The graph remains the pinned 144-record / 228-relationship release
`f5dffe0f7a32b5144920efb5a644f8c4dc9f20def76b4217c38b0cdbc454cf5c`.

The implemented catalog contains **23 draft reported-fact checks referencing
19 retained clauses**: 11 numerical comparisons, seven reported prerequisites,
and five explicit unexecuted gaps. These are separate from legal requirement
findings. Synthetic induction remains the only executable requirement evaluator.

## Verified behavior

| Surface | Evidence and result |
| --- | --- |
| Local Python suite | 273 tests passed; exact final output in `local-tests.txt`. Boundary and negative cases include every numerical reference, each prerequisite, missing/invalid/conflicting input, source mismatch, changed release, scope and evidence outage. |
| Separate-process stdio MCP → live Neo4j | 20 assessments across ten driver/dispatcher pairs. Exact reported-check packages matched across roles. Every expected status and source-text digest matched. All broad assessments remained unresolved and operational permission remained not issued. |
| Existing local HTTP application → live Neo4j | Two new confirmed assessments in separate synthetic driver/dispatcher conversations; six recorded HTTP requests excluding login. Both exposed the 175-inch comparison and prioritized the height action. Served JavaScript matched the captured runtime. |
| Offline capture validation | All 20 stdio and two HTTP assessment payloads validate against the captured MCP output schemas. Structured and text stdio payloads match. |
| Claude Desktop | Quit/reopened through CUA. Fresh UI state showed an empty new-chat composer. Logs record successful connection, initialize/result, initialized notification and tools/list/result. This establishes startup/discovery only. |
| Preservation | Runtime hashes match the final capture. Existing audit manifests verify, `kg/` has no Git diff, and the Neo4j environment has no NetworkX installed. |

The height example preserves the distinct authorities: **175 inches is 13 above
the retained 162-inch NJ reference and 20 below the separate 195-inch terminal
reference**. The terminal comparison never removes the road issue. At/below
results are comparisons, not findings that a move is legal. Reported credentials
and appointments remain unverified.

## Capture contents

- `summary.json`: capture time, counts and runtime SHA256 values recorded before
  execution and checked again after all stdio assessments.
- `cases.json`, `comparison-results.json`: ten frozen synthetic scenarios and
  expected/actual results for each role.
- `mcp-transcript.json`, `tools.json`, `stderr.txt`: exact stdio requests,
  responses, tool schemas and server stderr.
- `reported-check-catalog.json`: the exact draft source-bound catalog.
- [Mixed-height report](mixed-height-report.html): controlled HTML rendering of
  the live driver's 175-inch assessment, including the retained source passages.
- `http-summary.json`, `http-transcript.json`, `http-verifier.py`: sanitized
  application result, requests/responses and exact capture procedure. Login
  secrets and cookies are excluded. The archived verifier targets this frozen
  output directory; do not rerun it in place.
- `activation-receipt.json`: sanitized existing-connector activation events and
  the limits of what Desktop's log exposes.
- `local-tests.txt`, `validation-status.json`: final suite output, schema checks,
  preservation results, documentation hashes and adversarial review findings.
- `artifact-manifest.json`: SHA256 and byte lengths for every file in this
  directory except the manifest itself.

The earlier `../reported-checks-2026-09-13/` directory is an intermediate
checkpoint. Manual-gap summary wording changed during that run, and its verifier
originally recorded runtime hashes only at the end. Its captured records remain
untouched. Use this final directory for verification tied to unchanged source
files throughout execution.

## Reproduce without changing this capture

From the prototype directory, choose a new, unused audit output path:

```sh
python3 -m unittest discover -s tests -v

.venv-neo4j/bin/python tools/verify_reported_checks.py \
  --credentials-file /Users/marbin/.config/drayage-mcp/neo4j.env \
  --output audits/NEW_REPORTED_CHECK_CAPTURE
```

The verifier uses the existing pinned Neo4j release and a temporary synthetic
trip database. It never invokes a model. It refuses an existing output directory
and fails if captured source files change during the run. Dependency installation,
source promotion, account changes and public hosting are not part of this check.

## Remaining limits

No new Claude model prompt, consumer assessment or final answer was captured.
The existing five-tool connector remains a separate development workflow; the
restricted application proposal bridge was not attached or silently substituted.
The Desktop log records discovery result receipt without showing the schema body;
`tools.json` is the separate local-stdio schema capture.

Browser interaction, accessibility and responsive layout remain unverified after
the earlier Chrome `ERR_BLOCKED_BY_CLIENT` result. HTTP verification and HTML
generation do not close that acceptance gap.

Complete axle/bridge rules and input semantics, roadway classification and
cross-authority applicability, DTR interpretation, authoritative credentials and
permits, current conditions and transaction-release evidence remain incomplete.
The catalog is not human-approved policy and does not guarantee current law.
No general advantage over an unmodified Claude model was measured by these
backend tests. See the [implementation guide](../../docs/reported-fact-checks.md),
[review matrix](../../docs/reported-check-review-matrix.md) and
[production requirements](../../docs/production-readiness.md). Production remains
blocked; no letter grade, certification or stakeholder-ready claim is assigned.
