# Operator-managed synthetic verification receipts

September 14, 2026. This is a local prototype control for synthetic evidence.
It does not authenticate a real terminal, road authority, registry, scale or
credential provider. A stored receipt can support a bounded synthetic finding;
it cannot issue dispatch, route, gate or legal permission.

## The write boundary

`tools/manage_verifications.py` is the supported operator command for importing
and revoking receipts. The MCP tools and trip application do not accept receipt
objects. A driver, dispatcher or model therefore cannot turn a claim in chat
into verified evidence through either caller-facing surface.

The command relies on local operating-system access. It does not add user
accounts, provider authentication, signatures or role-based authorization. The
`syn-provider-*` values in the receipt contract name fixture adapters. They are
not proof that the named authority supplied or approved anything.

The default ledger is
`.runtime/operator-verifications.sqlite3`. `VerificationStore` creates the file
with mode `0600` and any missing directories with mode `0700`. It rejects an
existing file with group or other permissions, a symbolic-link target, a
non-regular file, or a file owned by another local user. Existing parent
directory permissions are left alone.

## What the store guarantees

An import validates the full batch before creating or changing the database.
Every receipt must pass the live contract in `neo4j_kg/verification_models.py`
and must bind to all four values supplied with the import:

- the server-issued synthetic trip ID;
- the exact positive trip revision;
- the SHA-256 fingerprint of the case facts and conflicts;
- the pinned graph release SHA-256.

Receipt IDs are global and immutable. Re-importing the same canonical receipt
is safe. Reusing its ID for changed content, another revision or another trip is
rejected. SQLite triggers reject updates and deletes to receipt rows. A
revocation is a separate append-only event with a required reason; repeating
the same revocation is safe, while changing its reason is rejected.

Each read checks the SQLite schema and integrity, every canonical receipt and
content hash, the complete receipt-set hash, and the revocation sequence and
hash chain. A malformed database, missing schema object, invalid stored receipt,
permission problem or SQLite read failure raises an error. It never turns into
an empty evidence set.

An absent ledger is different: `snapshot()` returns a deterministic empty
snapshot without creating the file or its parent directory. This represents an
optional synthetic provider with no stored evidence. It does not represent a
successful provider lookup.

Snapshots isolate trips. They include every active receipt for the requested
trip, including receipts tied to an older case fingerprint, trip revision or
graph release. The admission layer needs those stale rows so it can reject them
explicitly. Rows for other trips are excluded. Revoked receipt bodies are also
excluded, but their IDs remain in `revoked_ids` for the requested trip.

The hashes catch partial writes, accidental edits and many forms of corruption.
They are unkeyed and stored beside the data. Someone who controls the operating
system account and deliberately rewrites the database can recompute them, so
the ledger is not a signature system or an independent audit authority.

## Inspect the contract

Run commands from the prototype directory. `schema` prints the accepted JSON
Schema and its contract hash. It does not open or create the ledger.

```sh
python3 tools/manage_verifications.py schema
```

The schema accepts only synthetic identities and one of the configured fixture
kinds: scale, dimensions, route, permit, approval, conditions, DTR, TWIC,
SeaLink, appointment or transaction. Each receipt has a start-inclusive,
end-exclusive validity interval. Kind-specific checks also reject contradictions
such as an available transaction with an active hold or scale axles that do not
reconcile to gross weight.

## Import a receipt batch

Prepare two JSON files. `case.json` must contain the exact synthetic case object
for the assessment revision. `receipts.json` must be a JSON array produced for
that case and graph release. The receipt producer computes `case_sha256` with
`neo4j_kg.verification_models.case_fingerprint`; the import checks it again.

```sh
python3 tools/manage_verifications.py import \
  --case .runtime/case.json \
  --receipts .runtime/receipts.json \
  --graph-release 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
```

Use `--store PATH` to select another owner-only ledger. The command writes the
batch in one transaction, then prints the scoped snapshot metadata. It does not
print receipt payloads. Invalid JSON, one invalid receipt, a binding mismatch or
an existing ID with different content rejects the whole batch.

## List metadata for one trip

Listing also needs the exact case and graph release because the snapshot version
binds its result to that context.

```sh
python3 tools/manage_verifications.py list \
  --case .runtime/case.json \
  --graph-release 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
```

The output includes receipt IDs, kinds, provider aliases, trip/release bindings,
observation and validity times, plus revoked IDs. Payload values stay out of the
listing. An older receipt may appear here by design; appearance in this list is
not admission for the requested assessment.

## Revoke a receipt

Revocation keeps the original receipt row and adds an immutable journal event.
Use a concrete reason that explains why the synthetic observation was withdrawn.

```sh
python3 tools/manage_verifications.py revoke \
  --id syn-verification-example \
  --reason "Synthetic appointment fixture was withdrawn"
```

The next scoped snapshot omits that receipt and reports its ID under
`revoked_ids`. There is no un-revoke operation. If a replacement observation is
needed, import a new receipt with a new ID and the current case and release
bindings.

Do not edit the SQLite file directly. A locked database, failed write or failed
integrity check blocks the operation and preserves the last committed state.
Operational deployment still needs authenticated providers, a reviewed identity
and authorization design, retention and recovery rules, monitoring, and human
approval of the evidence contracts.
