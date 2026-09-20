# Evidence delivery fix — September 12, 2026

The MCP now includes the selected requirement evidence directly in trip
assessments and updates. Two missing clause mappings are repaired. The dated
Port Street bulletin is separately identified as an observation, and two PDF
extraction issues have release-scoped review annotations. Drivers and dispatchers
share the same evidence standard, with explicit instructions to start separate
cases for separate conversations and new moves.

This implements the remediation after the [frozen September 10
audit](../evidence-2026-09-10/README.md). That audit and its casebook are unchanged.
It does not add a general eligibility engine or authenticated multi-user service.

## Measured before and after

| Check | September 10 | September 12 |
| --- | --- | --- |
| S3 permit handoff: expected focused passages | 1/3 | 3/3 |
| S4 oversize/Port Street: expected focused passages | 2/3 | 3/3 |
| Assessment includes selected source passages | Separate requirement calls needed | Bundled in assessment/update |
| Expected passages delivered inside all 24 broad assessments | Not bundled | 24/24 complete |
| Port Street bulletin in trip evidence tools | Legacy context only | Separate observation in assessment and focused route endpoint |
| PDF extraction review notes | Audit report only | Delivered with the affected source objects |
| Local tests | 209 passed | 216 passed |
| Live controls | 8 passed | 8 passed |

S1, S2, and S5 focused recall remains 2/2, 6/6, and 4/4 respectively. S6 focused
recall remains 4/5 because the unchanged frozen focus list omits the DTR/RFID
requirement. S6 whole-catalog recall and its actual broad assessment package
are 5/5. The focus-list gap remains visible; the casebook was not revised to
improve the score.

## What changed

- `neo4j_kg/requirements.py` links the retained NJTA roadway clause and PANYNJ
  terminal weight/dimension clause to their catalog requirements. Inclusion
  does not establish that every authority's approval applies to a given trip.
- `neo4j_kg/evidence.py` builds deduplicated passages, requirement links, and
  separate observations from the same Neo4j transaction as the findings.
  True, unknown, or conflicted Port Street membership retains candidate context;
  an unconflicted false report or narrow scope omits it without granting permission.
- `neo4j_kg/assessment.py` returns the package on assessments and updates.
  Retrieval failures return an unavailable package and no partial findings or
  cached evidence while retaining the committed fact-write receipt.
- `neo4j_kg/provenance_notes.py` supplies a reviewed route-clause PDF locator
  (pages 2–3) and identifies the ocean-container table as a transcription.
  Original archive fields, including the previous locator/verbatim declaration,
  remain available unchanged. Notes apply only to the exact reviewed release.
- `neo4j_kg/trip_tools.py` publishes matching schemas and instructions for
  ordinary driver/dispatcher conversations, new-move boundaries, evidence use,
  and source currentness. No role picker is required.
- Retrieval receipts report delivered observation IDs separately from clauses.
  The direct audit harness labels model invocation as not performed in this run.

## Verification

[The live results](direct-results.json) record 24 broad assessments across six
frozen cases and four role/pressure conditions, 49 tool calls, 1,359 query
receipts, zero retained-source-field mismatches, and eight passing controls.
All broad cases remain unresolved. The harness supplied the expected structured
facts; condition invariance measures backend behavior, not a model's response
to wording. No Claude model was invoked.

[Bundle verification](bundle-verification.json) checks the exact captured
responses, not reconstructed examples. All 24 broad assessments contain their
case's expected passages, without duplicate clause IDs. Every bundled source
object matches its focused endpoint; every requirement link matches its finding.
Observation records match the original live legacy context exactly. Delivery
receipts match the delivered clause and observation IDs. All 45 successful calls
with a published output schema validate; text and structured payloads agree.
The remaining successful legacy context calls do not publish output schemas,
and the deliberately invalid requirement call is an expected error.

[The local test log](unit-tests.txt) records 216 passing tests. Seven added tests
cover expected family evidence, equal driver/dispatcher standards and fresh case
facts, complete observation retention, unknown/false/conflicted route selection,
correction and mutation isolation, fail-closed retrieval after a saved write,
and release-scoped provenance notes. No original test was weakened.

All 89 files in the original audit manifest still match their hashes. The frozen
casebook is byte-identical. Historical `kg/` has no Git diff. The runtime files
match the live capture, and `git diff --check` passes.

Pinned graph release:
`f5dffe0f7a32b5144920efb5a644f8c4dc9f20def76b4217c38b0cdbc454cf5c`

Measured runtime implementation:
`e0fc2cb7f6bf4846d4747fc186ff1f77a7c9d4b3924eedb4f059ddbb9af1290f`

Recheck the saved capture without invoking Neo4j or a model:

```sh
python3 audits/evidence-fix-2026-09-12/verify_bundle.py
python3 -m unittest discover -s tests -v
```

The live run used the installed isolated runtime and protected credentials file:

```sh
.venv-neo4j/bin/python tools/audit_evidence_delivery.py \
  --credentials-file /Users/marbin/.config/drayage-mcp/neo4j.env \
  --output audits/evidence-fix-2026-09-12
```

The harness refuses to overwrite a completed run. To collect another run, use
a new output directory containing the unchanged casebook and its hash.

## Remaining boundaries

Only APM induction executes a synthetic requirement check. Other requirements
identify evidence needs and gaps; user reports never become verified permit,
weight, registry, appointment, route, or whole-trip findings. The static catalog
retrieves the pinned source subset, not the entire GitHub repository or every PDF.
The original 96-response study and incomplete consumer matrix are not regraded.

Separate SQLite cases and model instructions are not access control. The MCP
does not authenticate users or enforce conversation ownership. A real shared
deployment needs authenticated case ownership and explicit sharing. These
changes add no real identifiers, credentials, public endpoint, or app configuration.

The fresh Neo4j read retrieves a pinned release, not automatically the latest
law. Reviewed source changes require a new release; dated operating conditions
still require current verification. Source change monitoring is not implemented.

Broad assessment packages contain 26 passages and 50,775 bytes of evidence JSON
in this capture. Complete structured assessments are 72,714–80,961 bytes, and
MCP envelopes are 149,514–166,088 bytes because they include both text and
structured content. Query receipts increased from 451 to 1,359 across the same
49-call audit. Batching and response-size optimization remain work; no passages
were silently truncated. These are byte counts, not measured model token costs
or production latency benchmarks.

No new Claude wording test, Desktop restart, or configuration change was made.
The fresh local MCP process verified the updated code; a Desktop process must
load this runtime before it can use the new package. No claim is made about
Claude's final narration of these new responses.
