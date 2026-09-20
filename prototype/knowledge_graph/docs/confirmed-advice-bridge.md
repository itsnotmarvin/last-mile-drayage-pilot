# Confirmed assessment explanations

September 16, 2026 evening engineering increment. Synthetic development only.
The triggering experiment is preserved in
`../provider_runs/claude-desktop-exploratory-20260916-r2/README.md`.

## Evidence presentation

Assessments now include `answer_guidance`, built from service results. Each
reported numeric comparison carries its qualification, source IDs and next
action. Unresolved requirements retain their limits. Historical operating
observations have an explicit `unknown_for_this_trip` status, archive timestamp
and recheck action. An effective date or “until further notice” does not supply
currentness. The full assessment still retains the exact archived records.

The explanation boundary distinguishes unresolved from both permission and a
finding of illegality. It does not rank risk probabilities, infer a permit type
from a dimension alone, or claim a rough route resolves verified-route checks.
These are model-facing constraints, not a guarantee that a model follows them.
Actual consumer captures must determine behavior.

## New optional bridge read

`trip_app.mcp_server` now offers `get_statement`, `propose_facts`, and
`get_confirmed_assessment`. The last tool accepts only `message_id` and
`version` from a fresh `get_statement` call after application confirmation.
It cannot select another conversation or trip, confirm facts, edit statements,
share access, or issue permission.

Existing proposal keys remain proposal-only. The separate application control
**Create proposal and confirmed-assessment key** explicitly creates a one-hour
key with the additional read scope. It shares that conversation's original
statements, confirmed reports and fresh assessment projection. Scope is stored
in an additive table keyed to the existing capability; deleting/revoking the
capability cascades to the scope. Existing databases acquire the table on open
without broadening old keys. Restore revokes keys and their scopes.

The application verifies the capability, user, organization/access, conversation
version, latest confirmed message, statement hashes, receipt and trip revision
inside a SQLite transaction. It queries Neo4j outside the lock, then repeats the
checks before returning. Revocation, expiry, sharing downgrade, deletion, a new
statement or confirmation, and a changed trip suppress the result. Evidence
outages return unavailable with empty comparison/source/findings collections;
no earlier assessment is reused.

The returned projection includes exact original statements, confirmation receipt,
reported facts, binding IDs, assessment time and versions, the decision brief,
qualified guidance, scoped findings and relevant numeric source passages.
Historical detour commands remain in the full application evidence view; the
model projection exposes their existence and unverified status rather than
repeating them as instructions. This projection does not include every source.
The bridge rejects oversized responses instead of truncating evidence silently.

Results are snapshots, not continuously valid capabilities to act. A client must
fetch again before a new answer; the model is instructed to do so. The server
cannot retract text already delivered into a chat. The browser continues to show
service-produced findings rather than accepting arbitrary model prose as a
clearance. Local process access under the same OS user is not a production
sandbox or identity boundary.

## Connection and capture

A new app bridge has not been attached to Claude Desktop by this increment.
The existing five-tool connector uses a separate trip store and was only
restarted for the post-change consumer experiment. Do not confuse its results
with the app review/confirmation flow.

After explicit connection authorization, use a newly issued scoped key stored
in an owner-readable file. The separate connector command is:

```sh
.venv-neo4j/bin/python -m trip_app.mcp_server \
  --origin http://127.0.0.1:8765 \
  --capability-file PRIVATE_SCOPED_KEY_FILE
```

For one bounded capture, add `--audit-file NEW_PRIVATE_JSONL_PATH`. This refuses
to overwrite an existing file and records hash-linked tool arguments/results
without the capability. Do not configure a fixed audit filename for automatic
restarts: each process capture needs a new path. Original surface labels are
unattributed until matched to provider UI observations.

`tools/verify_confirmed_advice.py` captures live Neo4j, HTTP confirmation and
stdio bridge reads for separate synthetic driver/dispatcher conversations. It
invokes no model or browser. The capture records scripted confirmations, not
human approval. The audit is at `../audits/advice-bridge-2026-09-16/live/`.

## Validation and remaining work

407 local tests pass, including twelve new tests with parameterized adversarial
cases. They cover unchanged proposal-key authority, same-trip corrections,
original statements, pending/stale reads, expiry/revocation/deletion and sharing
races, external revision changes, evidence outages, schema validation, and an
actual stdio/HTTP round trip with private capture logs.

The live integration yielded four available confirmed reads, preserved both
original and correction messages verbatim, and rejected pending reads. It used
`.venv-neo4j` without NetworkX. Older sealed captures remain historical; a
runtime-binding claim from before this change must not be carried forward.

Full browser → Claude proposal → user confirmation → Claude final explanation
acceptance remains open until the new connector is explicitly attached and
that actual experience is captured. Independent domain review, real authority
verification, complete legal scope and production acceptance remain separate
release gates.
