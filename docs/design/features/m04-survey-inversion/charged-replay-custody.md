# Charged local replay custody

## Requirements

R-459 BEFORE creating any replay ZIP, extracted member or publication target,
THE service SHALL commit an existing magnetic preparation-attempt row with
owned source/dataset receipts, a closed operation discriminator, exact stage
identity and conservative scratch plus target reservation. Missing owner,
lease, accounting or attempt-schema binding SHALL refuse before any write.
Gate: actual SQLite independent-reader observation before the first writer,
quota-deficit and unbound-assembly negatives.

R-460 WHILE full generation decode/export/readback is running, THE caller SHALL
retain its same-task all-writer SH lease and worker exclusion. Bounded async
waiting SHALL not cancel a native future or release those guards while work
can still write. Repeated request cancellation SHALL drain the owned work
before failure recording and guard release. A timeout is non-success, never
scientific success or inferred native group extinction.
Gate: held-worker timeout/repeated-cancellation controls and event-loop progress.

R-461 WHEN publication starts, THE service SHALL commit publication uncertainty
BEFORE installing a fresh permanent target, then co-commit the exact successful
job and terminal attempt. A commit exception, partial namespace or changed
copy SHALL retain charged debt and refuse subsequent adoption/startup/deletion.
Gate: before-write/import/after-target/commit failures and unknown-file negatives.

R-462 WHEN accounting or reconciling M04 custody, THE owner SHALL dispatch the
closed `magnetic-owned-custody-attempt-1` operation in the already allocated
`magnetic_survey_dataset_attempts` table, separately from M03 preparation.
Unreleased attempts charge max(reservation,retained); fully drained published
attempts release scratch only after the literal drain, and the permanent ZIP is charged by the
existing result ledger once. Exact ZIP inventory remains `magnetic_result` at
`results/<job UUID>.zip`; no JSON fallback or unknown-sibling exemption.
Gate: exact attempt charge/inventory and incomplete/stale/foreign/unknown refusal.

R-463 BEFORE installing a new immutable magnetic dataset, THE same existing
preparation-attempt lifecycle SHALL reserve32MiB (bounded16MiB structural body
and independent target) with a planned dataset UUID and null unpublished FK.
Actual source/physical-metadata receipts SHALL be rechecked before publication;
the published FK and dataset co-commit. Fresh worker sessions SHALL not commit
or roll back the authenticating caller's unrelated read/write transaction.
Gate: dataset birth/duplicate/uncertain-target and caller-transaction controls.

## Design

Use the existing magnetic preparation-attempt SQL model and literal migration
unchanged, not a new table or general reservation framework. A local replay
import/read/export is custody preparation, NOT M03 native scientific execution.
Its lifetime has a separate closed custody-drain schema: do not synthesize M03
CPU/RSS/kernel counters or an accepted installation. Bind the fixed owner
assembly's task-checked leases, worker exclusion and complete base/device
accounting; callbacks supplied by HTTP are not authority. Parent supplies the
registered reader to the full union; the current unknown-extension refusal
stays effective until that integration is present.

Reserve three bounded numeric copies plus the permanent128MiB target for an
import, and two numeric copies for a read/export. All copies use one predeclared
attempt directory within external owner storage. Source/request/projection
verification remains the existing exact M04 implementation, outside the SQLite
writer transaction. SQLite transactions only reserve, fence source identities
and publish records. A timed-out operation waits confirmed completion of its
bounded work before releasing owner guards; absence of a result is not drain.
No retry, fit, cap increase, provider truth or public activation is introduced.
Dataset creation has its own closed `dataset` operation, not a fabricated
processing job or M03 preparation receipt. Its publication intent is retained
before exclusive target writing just like a replay ZIP. The structural body's
existing16MiB storage bound is unchanged; the browser's8MiB wire bound is a
separate refusal boundary. No temporary dataset copy is written off-ledger.

## Tasks

1. Bind the existing attempt model, owner guards and exact accounting reader.
2. Split reservation, full synchronous I/O work and fenced publication phases.
3. Route every extraction through its predeclared charged directory.
4. Preserve failed and uncertain records and exact finite namespace inventories.
5. Run real SQLite and actual held-work timeout/cancellation/failure cuts before
   handing the immutable source packet to parent for mounted/native gates.
