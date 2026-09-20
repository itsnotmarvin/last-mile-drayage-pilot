The evidence audit found a retrieval gap in the current trucker/dispatcher MCP:
two expected clauses exist in the pinned Neo4j release but are absent from every
one of the 13 requirement-evidence responses. The service preserved the source
fields it returned and kept all 24 broad trip assessments unresolved. Those are
separate results: faithful delivery of selected evidence does not establish
complete evidence selection.

**Status: backend audit complete with findings; Claude answer validation incomplete.**
One new Claude Desktop call was captured, with matching S1 facts and an unresolved
MCP result. The desktop observation remained stale, so the final answer could
not be captured or scored. The other 47 frozen provider prompts remain unattempted.
No CLI or API result is counted as a Desktop result.

The measured graph release is
`f5dffe0f7a32b5144920efb5a644f8c4dc9f20def76b4217c38b0cdbc454cf5c`,
with 144 nodes and 228 relationships. The measured implementation is
`af5ef39b06af4e3f46867b94927f34b0d5ab7c228e3cbe46911990d68487871a`.
Runtime files and source bytes were held fixed during collection. This audit
did not change the graph evidence, requirement mappings, or historical `kg/`.

**The missing evidence matters to the intended user questions.**
For an 88,000-pound container move, a state permit is only one part of the
cross-authority question. For a 12-foot-wide load, terminal approval evidence
also matters. The missing records are:

- `reg_njta_roadway_use_limitations`: New Jersey Turnpike roadway-use limitations.
- `reg_panynj_terminal_weight_dimensions`: Port Authority terminal weight and
  dimensions, including the over-dimensional approval passage in Subrule 34-046.

The second passage was visually confirmed on archived tariff PDF page 16.
This is a finding about retrieval coverage against frozen development
expectations. It does not establish which approvals a real current trip has.

| Frozen family | Expected clauses returned by relevant evidence calls | Expected clauses available across all 13 calls | Finding |
| --- | --- | --- | --- |
| S1: axle facts | 2/2 | 2/2 | Expected clause IDs returned |
| S2: dimensions and local access | 6/6 | 6/6 | Expected clause IDs returned |
| S3: permit handoff, 88,000 lb | 1/3 | 1/3 | Both clauses above missing |
| S4: oversize and Port Street | 2/3 | 2/3 | Terminal weight/dimensions clause missing |
| S5: DTR conflict | 4/4 | 4/4 | Both retained policy blocks available |
| S6: gate credentials | 4/5 | 5/5 | RFID omitted from audit focus list; available through DTR/RFID call |

“Relevant evidence calls” means the casebook's frozen focus requirements. S6's
focus list omitted DTR/RFID because that case reports it satisfied. Its focus
miss is a limitation of the audit selection, not a missing catalog mapping.
All 24 direct broad assessments selected the complete catalog. Extra passages
are listed for review; they are not automatically scored as irrelevant errors.
Clause-ID recall is not semantic sufficiency or a safety score.

The dated Port Street bulletin takes another path:
`get_drayage_graph_context(topic="port_street")` returns its archived text,
directional restrictions, observation date and explicit currentness limits.
`get_requirement_evidence(requirement_id="current_route_conditions")` does not
include that bulletin. A consumer must discover and call the context tool to
receive it. This run captured that context response directly, but did not test
whether Claude would retrieve it for S4. A stored bulletin cannot establish
today's route conditions.

**What the live checks establish.** The isolated stdio run made 49 actual MCP
tool calls against Neo4j: 24 trip assessments, 13 requirement-evidence requests,
three context requests, and nine calls supporting eight controls. Every broad
assessment returned `unresolved` with the service available. Facts, findings
and selected requirements were unchanged across driver/dispatcher and
neutral/pressure conditions for each family. These tests supplied structured
facts directly, so this result measures backend invariance, not model extraction
or resistance to pressure in an answer.

All eight live controls passed: induction positive, explicit negative, missing
evidence, changed SeaLink, other subject, height correction, driver reassignment
and unknown requirement rejection. Across the 13 evidence responses there were
zero mismatches in the checked source text, locator, source ID, publisher, URL,
publication/access dates, archived-file references and currentness labels
relative to the frozen release. This equality check cannot detect an extraction
error already present in the release.

The audit recorded 451 Cypher receipts: 147 release-validation queries and
304 assessment/retrieval queries. The event hash chain was verified. Tracing is
opt-in with `--audit` and does not add fields to model-facing responses. Receipts
record query phase, parameters, query/result hashes, row count, record IDs and
delivered clause IDs. Validation reads of the whole release are not evidence
delivered to Claude. Clause passage counts require `clause_id` plus `source_text`;
route and mutable-observation payloads use different identifiers and must be
read in the full response transcript.

**The source review found two provenance defects, not incorrect weight values.**
The automated screen covered 27 PDF clauses. Visual spot-checks covered 10 PDF
pages and resolved eight flagged clauses as text-extraction misses caused by
OCR or column layout. The retained route-review locator says PDF pages 3–4,
but items (b)(3) and (b)(4) are on page 2 and the remaining retained material is
on page 3. Table 5's 90,000 / 38,000 / 56,400 lb values match the PDF, but its
three columns were flattened into a punctuated sentence labeled verbatim.
That representation should be distinguished from a literal continuous quote.
The municipal table/section locators and non-PDF quotations still need separate
review. No archive text was corrected during measurement.

**Repository coverage is bounded.** The inventory captured 304 non-ignored
repository files at that checkpoint: 51 pinned release inputs and 253 files
not linked to that release. No unlinked `data/raw/` candidates were found in
that inventory. This does not mean Claude reads all 304 files, every PDF page
is represented, or every file should become graph evidence. Code, experiment
outputs, documentation and source evidence serve different purposes. The current
MCP reads a curated release; it does not provide whole-repository semantic search.
Most requirement retrieval follows clause IDs in a static Python catalog, then
fetches those records from Neo4j. Only induction has an executable evaluator.

**Claude collection remains open.** The casebook freezes six families × two
roles × two pressure conditions × two repeats, shuffled with seed `20260910`.
Expectations derive from the read-only Wave 4 gold dispositions, with explicit
APM adaptation and a retained-conflict addition for S5. They are development
assertions, not new human-approved policy. The first attempted prompt,
`S1_AXLE_FACTS__driver__pressure__r1`, produced one captured `assess_trip` event.
Its facts, role and scope match the casebook; no timestamp was invented. The
result is unresolved and includes no source passages. No final answer is
observable, so disposition and answer-source fidelity are unscored. The UI
showed Sonnet 5 Medium and the drayage connector enabled. The earlier
“desktop control unavailable” status in frozen files records the earlier
collection state; [provider-results.json](provider-results.json) records this
later partial attempt. Recover this answer before retrying the case so failures
and duplicate attempts remain visible.

The earlier four-run Desktop replay is a separate
[historical baseline](../../docs/paired-replay-2026-09-10/independent-review.md).
It includes conditional clearance under pressure despite an unresolved result,
a height-extraction error, and an incorrect terminal ID. Those observations
motivate this audit, but they are not new results in the 48-prompt matrix and
do not establish a statistically reliable framing effect.

**Validation and reproducibility.** All 209 local tests pass. Added tests cover
query/passages distinction, disabled tracing, isolation, safe failure receipts,
MCP response parity, rejected-input omission, and recall scoring that cannot
be satisfied by irrelevant or duplicate passages. Existing adversarial fixtures
cover missing/tampered nodes and edges, source-byte changes, malformed releases,
outages and identity changes. No outage or corruption was induced in live Neo4j.
Audit-log disk failure was not fault-injected. See
[adversarial-results.json](adversarial-results.json) and
[unit-tests-final.txt](unit-tests-final.txt).

Run local validation from `prototype/knowledge_graph`:

```sh
python3 -m unittest discover -s tests -v
```

To repeat live backend collection, create a new output directory, copy the
frozen `casebook.json` and `casebook.sha256` into it, then run:

```sh
.venv-neo4j/bin/python tools/audit_evidence_delivery.py \
  --credentials-file /Users/marbin/.config/drayage-mcp/neo4j.env \
  --output audits/evidence-rerun
```

The live harness refuses to overwrite a completed run. Source inventory and
PDF screen tools target this dated audit directory, so copy or change their
output location before taking a later snapshot. Preserve this baseline before
making fixes. Artifact hashes are in `artifact-manifest.json`; runtime file
hashes are separately retained in `runtime-files.json`.

| Artifact | Contents |
| --- | --- |
| [direct-results.json](direct-results.json) | Live counts, controls and per-family recall |
| [direct-stdio-transcript.json](direct-stdio-transcript.json) | Exact MCP requests and responses |
| [direct-mcp-audit.jsonl](direct-mcp-audit.jsonl) | Query receipts and event hash chain |
| [requirement-evidence.json](requirement-evidence.json) | All 13 complete evidence responses |
| [casebook.json](casebook.json) and [prompts/](prompts/) | Frozen assertions and 48 exact provider prompts |
| [source-coverage.json](source-coverage.json) | Inventory scope and automated quotation flags |
| [source-manual-review.json](source-manual-review.json) | Visual judgments and unresolved review scope |
| [repository-inventory.json](repository-inventory.json) | File paths, hashes and release linkage |
| [provider-results.json](provider-results.json) | Partial Desktop capture and missing measurements |

The next implementation run should connect both missing clauses to the relevant
evidence requests, expose the dated Port Street evidence through an explicit
trip-retrieval path, and correct provenance in a separately reviewed source
release. It should then rerun this unchanged casebook and complete the paired
Claude collection. That sequence makes it possible to tell whether retrieval
improved and whether the model used the added evidence faithfully.
