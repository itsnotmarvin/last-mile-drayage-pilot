# Input consistency and controlled report verification

The final runtime rejects recognized fact/text contradictions before saving
synthetic trip data. It also returns explicit unconfirmed-extraction metadata
and a deterministic decision brief, with an inert report export from a fresh
assessment. This increment does not complete production readiness.

## Results

- All **229 local tests passed**, including 13 new extraction and presentation
  regressions. The existing tests were not modified or narrowed.
- **Nine live stdio MCP calls** used an isolated temporary SQLite database and
  the pinned Neo4j release. Four exact saved Claude assessment calls were
  rejected for text inconsistencies; no cases or request receipts were created.
- The S4 pressure call was rejected for its truncated height, unsupported
  timestamps, and uncertain approvals represented as booleans. The S2 calls
  contained a clock time in the model-supplied summary but lacked a recognized
  explicit timezone, so that guard rejected them. This is not proof that every
  invented time can be detected from a model-supplied summary.
- Corrected driver and dispatcher cases both retained **175 inches** and produced
  equal findings in distinct cases. A rejected update left revision 1 intact;
  a clarified correction stored **176 inches** at revision 2.
- The report exporter independently reassessed that saved case through Neo4j
  and produced [the revision-2 report](controlled-trip-report.html). It states
  that operational permission is not issued. It accepts no assistant answer or
  arbitrary assessment JSON input.
- All four successful MCP responses validate against the published output
  schemas and match their text representations. All advertised input/output
  schemas validate. Five tool errors are expected rejections.
- The original evidence-audit manifests remain intact: 89 baseline files and
  16 evidence-fix files. The graph release and source archive are unchanged.
- Claude Desktop was restarted after verification. Its log confirms initialization
  and tool discovery with runtime files matching this capture. No model prompt
  was sent; the app was left on an empty new chat.

The adversarial checks cover atomic rejection, rejected-key reuse for a clarified
write, old stored inconsistencies, scoped positive controls, driver/dispatcher
parity, evidence outages, ambiguous measurements, source/model HTML injection,
and the distinction between a positive unverified report and unknown status.

## Artifacts and reproduction

- [Results and exact rejected-capture hashes](results.json)
- [Exact stdio exchanges](stdio-transcript.json)
- [Representative corrected assessment](representative-assessment.json)
- [Schema and preservation checks](artifact-checks.json)
- [Unit-test log](unit-tests.txt)
- [Runtime file hashes](runtime-files.json)
- [Desktop startup receipt](desktop-activation.json)

```sh
python3 -m unittest discover -s tests -v
.venv-neo4j/bin/python tools/verify_input_review.py \
  --credentials-file /path/outside/repository/neo4j.env \
  --output audits/NEW_INPUT_REVIEW_RUN
```

The verifier requires a new directory and never overwrites a prior capture.
The earlier `audits/input-review-2026-09-12/` run is retained as a checkpoint
before the positive-unverified-report refinement; this directory records the
final code. No capture was regraded as a model success.

Runtime implementation:
`4fa3a70b7386220dcdbd5c0ba4d5b9c9b78005ca9a293f9fba521ee160e52926`

Pinned evidence release:
`f5dffe0f7a32b5144920efb5a644f8c4dc9f20def76b4217c38b0cdbc454cf5c`

## Remaining limitations

The MCP caller still supplies both facts and source text. Consistent invented
values can pass these bounded checks. Original transcript capture and an
authenticated, application-owned confirmation workflow remain required.

The report controls its own displayed status. It does not force Claude Desktop
to use the tools or prevent contradictory prose elsewhere in the conversation.
The exported HTML is a snapshot and does not enforce current-revision selection
in a future application. Authenticated users, broader reviewed evaluators,
operational verification, production hosting, and deployed-client acceptance
remain open in the [release requirements](../../docs/production-readiness.md).
