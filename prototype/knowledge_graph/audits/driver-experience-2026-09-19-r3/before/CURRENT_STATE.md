# Current prototype state — September 19, 2026

The product question is: “Can this truck take this specific route to APM today,
and what's missing?” The critical path is source evidence → pinned Neo4j →
deterministic checker through MCP → Claude. The working repository is this
directory, not the separate `Desktop/experiments` research archive.

The installed `drayage-kg-prototype` connector runs `run_neo4j_mcp.py --audit`
on release `f5dffe0f7a32b5144920efb5a644f8c4dc9f20def76b4217c38b0cdbc454cf5c`.
The pinned prototype evidence release has 144 records / 228 relationships. The
co-resident Wave-4 archive has 824 / 1,872 and remains isolated. Trip revisions
and operator receipts live locally, outside the read-only Neo4j graph.

## Today's driver experience result

The agreed local finish line is the existing Claude connector: explain the
truck/route conclusion with the right supplied sources, why they support it,
and specific unresolved limits. Rules and physical/current conditions are
internal reasoning groups, not prescribed response headings. An unresolved
trip must still retain useful supported findings. 511NJ and the separate
browser/confirmed-assessment app bridge are not completion gates.

**450 tests pass; the four-turn consumer presentation acceptance did not fully
pass.** The connector now supplies a prepared source-linked answer and detailed
briefing before its unchanged full JSON. Four actual Claude Desktop calls
preserved the Path A correction 175→162 inches on revisions 1→2→2, then created
a distinct Path B case at revision 1 with the correct five-segment sequence.
All results passed schema/full-JSON/hash checks against the frozen runtime.

The consumer still omitted the APM links from its dated-evidence follow-up,
shortened the width rule's standard-truck qualification, and made some
imprecise terminal-page statements. Path B selected route-only scope despite
the supplied new-move credential facts, leading to an offer for another check.
These are the bounded remaining experience defects. Do not declare the
project finished from backend counts or reopen unrelated research to fix them.

Read the [four-turn review](audits/driver-experience-2026-09-19/consumer-review.md),
[checkpoint record](audits/driver-experience-2026-09-19/README.md), and
[usage guide](docs/driver-experience.md).

## Earlier completed core checkpoint

- Existing two named routes resolve to ordered graph segments and candidate
  requirements. Topology does not establish compliance or permission.
- Route confirmation questions use the resolved segments. Port Street
  membership is not inferred from absence in the stored sequence.
- Public APM pages are fetched with per-source hashes and retrieval times.
  Fresh page retrieval does not verify current conditions. Old/future or
  previous-local-day captures are unavailable; effective dates remain distinct.
- Operator receipts can evaluate synthetic Path A road conditions. Route
  receipts must match the complete ordered graph route; partial, reversed,
  duplicate, wrong-route, or off-route claims cannot establish coverage.
- The confirmed-assessment explanation projection now includes the route and
  terminal context, while preserving its existing access/revision checks.
- 442 local tests, 10 live pinned-graph checks, and eight live operator-condition
  cases pass. Missing/stale/conflicting/off-route/partial/reversed cases stay
  unresolved; an open fixture satisfies only its bounded requirement, and a
  closed fixture holds. All withhold operational permission.
- Actual Claude Desktop Sonnet 5 Medium used the installed MCP in two turns,
  kept 175→162-inch correction on trip revision 1→2, distinguished an old
  Labor Day notice from today's conditions, and withheld permission under
  schedule pressure. This is a bounded acceptance result, not a general claim.

Evidence and capture limitations: [September 19 closeout](audits/core-closeout-2026-09-19/README.md).
The checkout remains dirty with work from multiple sessions; do not reset or
bundle unrelated changes. No commit, push, source promotion, or deployment was
performed by the September 19 closeout.

## Remaining boundaries

The separate browser → confirmed-assessment app bridge → Claude Desktop
experience is still unverified. Its backend and projection exist, but today's
consumer capture used the already-installed five-tool connector. A new
conversation-scoped app-bridge configuration and actual consumer capture are
needed to close that separate path. Do not count direct HTTP/stdio harness
results as consumer acceptance.

Receipts still use synthetic provider aliases and OS-local control. They do
not authenticate a real road authority or create a production operator trust
system. Source/contact and note-hash fields are optional provenance, not issuer
signatures. Real credentials, permits, appointments, authoritative current
road data, domain approval, and full legal coverage remain outside this
prototype's acceptance. Operational permission is never issued.

The large MCP payload still leads Claude to read tool-result files with command
tools. Prepared/detailed text delivery is now implemented and verified at the
connector boundary; final model presentation still has the observed defects
described above. Additional instructions alone have not guaranteed fidelity.

## Parked

Wave-4 comparisons, S2 Stage 2, S4, larger rubrics/matrices, new schemas, and
proximity/name heuristics for 511NJ/WZDx remain parked. Reopen road-feed work
only when an authoritative source provides a documented usable interface and
sufficient segment/location information. Stage 1 is frozen; Stage 2 is not
collected. These do not block the existing named-route prototype.
