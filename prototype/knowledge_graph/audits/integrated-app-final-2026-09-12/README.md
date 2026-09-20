# Integrated application verification

Local synthetic application capture, September 12, 2026 (timestamps in the JSON
are UTC). This is HTTP, live Neo4j, and local stdio verification. No language
model was invoked and no Claude Desktop consumer exchange is claimed.

- **257 local tests passed**, including 28 new application/HTTP/recovery tests.
- **15 recorded application HTTP requests**, including expected access denials.
- **Four fresh Neo4j assessments** with supporting source passages and requirement
  links. Driver and dispatcher findings match for the same reported facts.
- Mixed feet and inches remain **175 inches**; a user-confirmed correction saves
  **176 inches**. The original statements remain intact.
- Explicit sharing, dispatcher confirmation, removal of sharing and revocation
  of the conversation's proposal keys succeed.
- The restricted stdio bridge discovers exactly `get_statement` and
  `propose_facts`. Its attempted `confirm` tool call is rejected. It never receives
  an application session cookie, private DB credentials, or confirmation rights.
- Consistent backup and verified restoration preserve cases and statements.
  Restore clears access keys, sessions, proposal capabilities and sharing grants.
- JavaScript syntax and Python syntax checks pass. The runtime environment has
  no NetworkX installation/import, and the historical `kg/` diff is empty.
- An adversarial review added explicit concurrent-confirmation and model-injected
  permission/source-field rejection tests. It also addressed response races in
  the UI and authorization restoration. This is developer QA, not independent
  production security or domain review.

## Files

`summary.json` binds the capture to runtime file hashes and summarizes checks.
`http-transcript.json` contains the exact synthetic requests/responses, excluding
login and capability-issuance secrets. `restricted-mcp-transcript.json` records
the real stdio exchange through the running HTTP application.
`operations-verification.json` records the recovery check without private DB
contents. `local-test-results.txt` contains the full suite output.
`verification-status.json` separates successful checks from incomplete ones.
`artifact-manifest.json` hashes all these files and the accompanying README.

The earlier `audits/integrated-app-2026-09-12/` capture is a preserved checkpoint.
Prior evidence and input-review captures have not been rewritten to match this
runtime. Production requirements are recorded in `docs/production-readiness.md`;
implementation details and commands are in `docs/integrated-trip-workspace.md`.

## Unfinished acceptance

Chrome's automation returned `ERR_BLOCKED_BY_CLIENT` for the local application
URL and displayed “127.0.0.1 is blocked.” Therefore this capture does **not**
verify rendered browser interactions, responsive behavior, accessibility, or a
Claude-connected driver experience. Those checks remain required. JavaScript
syntax or successful HTTP calls cannot substitute for them.

The interface uses the bounded local extractor by default. The optional proposal
bridge has not been attached to Claude Desktop. The existing five-tool Neo4j
connector remains separate development access. Only induction has an executable
synthetic evaluator; broader trip clearance is not established. No production
readiness grade or stakeholder-ready claim is assigned.
