# Physical persistence B: complete proposed control design

Status: DOCS_ONLY, MAIN_REVIEW_REQUIRED. This is a concrete proposed protocol/registry, not another generic boundary and not production approval. Read [lease/classifier](leases-wal.md), [authority/bridge](authority-bridge.md), [migration/source policy](migration-source-policy.md), [validation](validation-plan.md), [review packet](review-packet.md) and [research](../../../research/m01-physical-persistence-b-2026-10-03.md).

## Accepted input and separation

MAIN reports FULL read of all nine A docs at `e67f7ffebaa1aab3b00f4981ca629803c394ad81` and accepts the exact proposed SQL/custody dictionary and capacities. Record8856f5d adds only that attributed acceptance; no dictionary/receipt changed. This does not approve schema/worker/migration implementation, runtime capabilities, phone budgets or host operation. PR123 scientific87eb9 and one-line attribution9d19209 remain protected. This branch contains NEW B docs only.

B freezes proposed migration identity `0004_physical_persistence`, its two additional control tables, exact source path ownership and positive v1/v2 registries. Actual DDL fingerprint and future integrated source hashes cannot exist before reviewed implementation; the registry remains UNREGISTERED/CLOSED until measured on the candidate and independently approved. Their wire types and registration procedure are fully defined, not silently chosen by an implementer. No fake digest or all-zero approved pin is permitted.

## Native versus pure-data units

| Unit | Complete design contract | Later authorization boundary |
| --- | --- | --- |
| B-DATA | Strict bounded parsers, digest descriptors, receipt wrapping, authority merge/bridge, deterministic classification predicates on an explicit immutable input snapshot | Could be approved EXPLICITLY after FULL B read for temporary pure-data fixtures only; no implicit approval now |
| B-SCHEMA | Reviewed0003->0004 candidate migration, exact A+B tables/constraints, row/file equality and source registration tests | Could be approved EXPLICITLY after B for NEW disposable local candidates only; no live/in-place migration, service or API wiring |
| B-NATIVE | Actual Linux/Windows lease lifetime, same-inode/handle checks, child containment, no-follow exclusive copies/removal, file/directory durability and fresh WAL driver behavior | CLOSED until separately executed platform proofs; no wall/psutil/TTL substitute |
| B-AUTHORITY | External independently durable latest-authority checkpoint and trusted freshness ACK | Provider NOT_SET; production publication/recovery/physical deletion remains CLOSED, no invented channel or ACK |
| B-RUNTIME | API/worker startup ordering, all legacy writer participation, cancellation, child budget and host admission | CLOSED; separate explicit implementation approval and real local/native/host evidence needed |

The data classifier receives a bounded immutable inventory; it does not create locks, enumerate arbitrary host trees, run physics or certify a live source. A fixture-only latest-watermark value is test input, never a production ACK. All fixture outputs are explicitly fixture_only=true,production_activated=false; runtime verdicts remain NOT_RUN.

## Proposed B-only SQL additions

Use exact A domains/naming/nullability/FK RESTRICT rules. No old column/value or A field is removed. Add `uq_deletion_receipt_identity(id,owner_id,project_id)` to the existing table as a suitable unique parent.

`physical_deletion_extensions` complete columns: `receipt_id U` PK NOT NULL; `owner_id O`; `project_id U`; `schema_tag E(geophysics.physical-deletion/v2)`; `tombstone_bytes B(16*M)`; `tombstone_sha256 H`. Composite FK `fk_deletion_extension_receipt(receipt_id,owner_id,project_id)` -> uq_deletion_receipt_identity, ON UPDATE/DELETE RESTRICT NOT DEFERRABLE. UNIQUE `uq_deletion_extension_project(project_id)`. No live-project/root/intent FK. Immutable bytes are generated from actual receipts/rows/inventory IN the final deletion transaction, after native legacy JSON serialization is observed; old receipt plus extension plus custody plus logical deletion co-commit. Existing old receipts get NO fabricated extension during migration.

`physical_runtime_control` complete columns: `singleton I(1,1)` PK NOT NULL; `deployment_id U`; `storage_generation U`; `lease_generation I(1,J)`; `inventory_state E(closed,clean,quarantined)`; `source_policy_sha256 H?`; `last_clean_inventory_sha256 H?`; `audited_us I(0,J)?`. No FK to scientific objects. CHECK `ck_runtime_inventory`: clean requires all three nullable fields non-null; closed permits all NULL or all non-null; quarantined preserves either complete last-clean triplet or all NULL, never a partial triplet. No default and no auto-assigned deployment identity. Candidate migration creates NO row until an explicit fixture/operator input supplies canonical IDs; absent row means runtime CLOSED. "clean" means storage was audited, NOT host/method/CPU/provider admission. Runtime mutations require matching independently approved source policy and leases. Restore starts closed, assigns NEW storage/lease generation only via separate authorized candidate initialization, and revokes sessions; it never inherits source production readiness.

Runtime-control/scalar/extension bytes are private control evidence, included in candidate DB/global resource bounds. Extension byte charge belongs to retained deletion evidence/global DB capacity, not a pretend committed scientific file; exact finite limits and database1-GiB snapshot ceiling remain enforced. It is not media-erasure proof. Account raw-only usage and all A retained-file charges remain unchanged.

## Operation ordering

Shared global lease -> authentication/admission/claim -> bounded A reservation/stage -> one child -> complete structural/hash validation -> prepared intent -> exclusive copies -> final same-commit publication/debt -> verified cleanup. Uncertain commit interrupts this flow: dispose/reap, close ingress, independently obtain exclusive lease, fresh-WAL classify, then authorized abandon/cleanup or preserve inconsistency. Legacy recover_interrupted is NEVER first. Project deletion selects exclusive global lease BEFORE authentication/DB lookup and rejects active/unresolved stages; before moving files persist exact declaration; final receipt/extension/custody/accounting/deletion are one DB commit. No shared-to-exclusive upgrade.

Capture/restore is a separate stopped-writer operation. Positive revision/source dispatch precedes every parser. Captures require no active job/intent, no retained custody charge/files and complete exact inventory; liabilities are not swept to make capture pass. Old snapshots remain immutable. Latest authority removes deleted projects only in a NEW candidate; it cannot reconstruct later writes for rollback. After any writer reopen, only forward repair or separately reviewed reconstruction preserving all subsequent writes is admissible.

Nothing here selects a provider, changes a service/cgroup/key/auth/mail facility, computes a scientific result or permits a512-MiB phone allocation. Production flags stay closed. MAIN's previous read-only disk/memory readings are not remeasured, a40-job rerun or authority acceptance.
