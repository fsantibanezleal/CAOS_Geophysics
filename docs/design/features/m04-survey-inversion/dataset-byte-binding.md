# Exact dataset-byte transfer and readable publication envelope

## Requirements

R-477 AFTER bounded download but BEFORE UTF8/JSON decoding, THE magnetic client
SHALL hash the complete received dataset body and compare it with the selected
authenticated dataset receipt.sha256. A matching request_utf8 hash, IDs or
geometry claims does not substitute for that complete byte binding. Gate:
retained Python-produced dataset bytes pass without JS reserialization;
same-ID/request-hash changed metadata/geometry fails before parsing.

R-478 THE backend SHALL publish/read M04 datasets only inside the existing
consumer8MiB full-body limit. The physical request8MiB limit is distinct because
JSON escaping and geometry metadata increase the serialized dataset size. A
capacity refusal SHALL occur before creating/reserving derived bytes. Gate:
actual parsed supplied request whose serialized dataset exceeds8MiB is refused
before publication, while originals/existing datasets/debts stay unchanged.

R-479 THE client SHALL retain pre-accumulation transport bounds and cancellation
checks around asynchronous hashing. No response is accepted after cancellation
and no malformed hash becomes an unauthenticated parse. Gate: exact-byte hash,
malformed JSON before-parse hash ordering, mid-stream and post-hash cancellation
controls, bad declared lengths and stream overflows.

## Design

Reuse requestBoundedBytes and crypto.subtle.digest over the exact Uint8Array,
not canonical JSON, a projected request or parsed/reencoded float values. Retain
the raw server file in external QA storage; the browser fixture points to those
bytes. Receipt/source mapping remain independently authenticated route inputs.
This proves transfer custody, not physics or provider authenticity.

Use one backend MAX_DATASET=8388608 in owned read, serialized publication and
charged write. Historical charged-attempt grammar retains its existing16MiB
debt ceiling, so prior known debt is not silently rewritten/unaccounted. No new
dataset above8MiB is published/read. Such existing bytes are preserved/refused,
not deleted, adopted or automatically upgraded. Request/original/ZIP caps,
reservation amounts and scientific budgets stay unchanged.

## Tasks

1. Add complete-byte hash before decoding, with cancellation recheck.
2. Bind raw Python dataset-body fixture to client controls.
3. Align owned backend publication/read/write limit without expanding caps.
4. Run actual producer capacity refusal and focused transfer regressions.
