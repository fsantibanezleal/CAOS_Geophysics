# Persistence review gates and tasks

Status: all PA/PB product gates below NOT_RUN. No candidate schema, fixture database, worker, API or recovery runtime is created by this docs-only unit. Document/source/link/content checks are a different evidence class.

## Prospective tests

| Gate | Exact future acceptance evidence |
| --- | --- |
| PA01_legacy_exact | Migrate protected valid0003 candidate covering flag-only/M05/M06/raw-only/source-permission-null/deletion receipts; compare every legacy SQL column value AND typeof, native JSON text/time, FK/index definitions and all original file IDs/keys/bytes/hashes. No fabricated physical controls/producers. Unknown legacy rows refuse unchanged. |
| PA02_reserved_root | Competing root reservations with same raw/parser across connections yield one pending family, then one root; root UUID has no absent-dataset FK; abandon releases slot only after debt transfer. Reserved-root crash and ordinal-exhaustion tests. |
| PA03_forest | Missing edge/producer, duplicate child, wrong owner/project/raw/root/parser, stale parent SHA, self/cycle, parent ordinal>=child, fake v1 child, terminal-transform-as-input and >64 capacity/>four-edge ancestry refuse even after outer JSON rehash. Delete children before parents under RESTRICT. |
| PA04_fingerprint | Same actual submitted NULL/omitted-sensitive parameters/input/modules reuse queued/running/succeeded job; different module or original submission gives distinct identity; failed/cancelled retry new job; concurrent duplicate unique check and deliberate hash-hit input mismatch fail closed. Non_pass success remains reuseable. |
| PA05_stage_first | Inject death before reservation commit, after it and before every file create; no byte may exist without committed batch/slot/full charge. Exact whole-stage cap independent of per-file maxima. |
| PA06_terminal_transfer | Kill/exception before/during/after terminal commit for success/failure/cancel/abandon; visibility, allocator count, permanent conversion, retained custody and intent retirement are one coherent commit. No post-cleanup-failure-only debt creation. |
| PA07_debt_survival | Delete intent/job/project through explicit FK order while stage/pending/deletion debt persists; no cascade/SET NULL loses evidence or charge. Account owner deletion RESTRICT remains explicit. Unknown bytes preserve quarantine even above quota. |
| PA08_removal | Partial unlink/removal/fsync/accounting cuts retain conservative charge; exact durable proof precedes removed ordinal/charge release; aliases/rename/swap races never unlink public targets; original sealed measurements retained. |
| PA09_unknown_closed | Extra cache/subdirectory/link/reparse/unknown role/oversize/unhashable/declaration mismatch or numeric lexeme float/bool/exponent in integer field refuses; no file sweep, guessed role or zero measurement. Dependency-generated caches are NOT presumed admitted. |
| PA10_producer | Full exact30-key saved producer and unchanged13-key receipt/core/config/module bindings; root-null/correction-parent-object, terrain:null versus omitted valid submission hash distinction; wrong/missing/extra/rehashed identity refuses without numeric solver imports. |
| PA11_inventory_bounds | Whole4-MiB/4096-entry/depth/node/token checks, role-specific limits, no partial oversized legacy deletion; roots/corrections/transform16/64-MiB actual complete wrappers,34-MiB request and separate80/128-MiB output reservations; byte-for-byte parsed source through EOF. |
| PA12_quota_equation | Exact committed/raw/derived/result/control/reserved/custody terms across queue, seal, install, terminal, abandon, deletion and partial cleanup; no double charge pending target/custody, no uncharged DB JSON duplicates, no lifetime zeroing of retained files. |
| PB01_wal_cut | Actual all-writers exclusion, fresh WAL with FULL/FK/durability readback, driver versions and every uncertain-cut row; legacy recover_interrupted cannot mutate first; no immutable=1 live proof. |
| PB02_no_lost_writes | Snapshot rollback only under uninterrupted stopped-writer/no-later-write proof; later upload/job/version/source/deletion writes survive reviewed forward repair/reconstruction after reopen. |
| PB03_authority_bridge | Frozen0003 snapshot plus latest registered v2 authority, original receipt digests, post-snapshot child absence not false corruption, overlapping hash/owner mismatch negative, predecessor/sequence/registration/expiry/latest-watermark and missing provider ACK close. |
| PB04_exact_source | Reviewed migration revision/fingerprint and exact physical core/adapter/transform/wrapper/persistence/ops source paths/Git blob pins; missing/extra/future/rehashed module fail; legacy source caps/policy unchanged. |

Tests are not implemented here. Named gates are prospective oracles, not test function names pretending to exist. Full vertical's previous28 gates remain NOT_RUN. CPU lifetime, host/headroom and browser measured-memory tests retain separate holds; no living-psutil/wall fallback or phone512-MiB admission.

## Task sequence and holds

- [x] Create isolated docs task branch; preserve protected PR123/evidence and prior pins.
- [x] Read exact0001/0002/0003, models/database/storage/worker/projects/processing/contracts/config and ops recovery/source-pin policy; fetch actual official references and hash HTTP response bytes.
- [x] Write EARS requirements, complete milestone-A column dictionary, separate inventories/accounting/terminal transfer, cut-matrix boundary and review packet before any code.
- [ ] MAIN full pinned read/approval of milestone A; independently review SQL constraints/custody/capacity amendments.
- [ ] Author and MAIN-review milestone B's complete typed authority/bridge/source-policy/revision/platform-lock protocol BEFORE any schema/worker code.
- [ ] Owner chooses existing-compatible external durable checkpoint path/provider policy; no invented service.
- [ ] Resolve per-job lifetime CPU and measured browser/host gates in separately reviewed units.
- [ ] Only after all pre-code approvals, assign implementation owners and run actual PA/PB and full vertical tests; do not implement from this task list alone.

## Docs-only checks

Stage ONLY new persistence feature/research paths before running `python scripts/check_content_standards.py`, so new tracked docs are scanned. Also run `python scripts/check_template_residue.py`, `python scripts/check_ci_budget.py`, `git diff --cached --check`, strict receipt shape/count/hash-format checks and local-link/EARS-to-gate/scope inspection. These are documentation checks, NOT SQL correctness, migration execution, scientific PASS, filesystem durability or runner capability proof. Final execution results belong in the review packet/PR handoff, with the exact docs commit pin.
