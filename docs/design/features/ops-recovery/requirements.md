# Restricted maintenance recovery requirements

Status: implemented with local gates verified; host release gates remain open. Implementation authorized by the approved product SDD and the assigned #80/#37 ops unit on 2026-10-03. Product references: section 8, R-002, R-004, R-017; API deletion receipts and processing storage contracts. No application-owned files change. Exact receipts: [convergence](convergence.md).

R-OPS-01 WHILE all declared writers and activation sources are stopped and masked and ingress is in maintenance, THE tooling SHALL validate fresh path-bound maintenance evidence before and after reading coherent SQLite and immutable bytes. Gate: tests/ops/test_backup.py::test_maintenance_rejection and tests/ops/test_backup.py::test_systemd_proof.

R-OPS-02 WHEN a backup is requested, THE tooling SHALL create only a new restricted directory containing an age-encrypted bounded snapshot, cumulative encrypted recovery authority and private receipt; it SHALL reject unknown schema, foreign-key drift, active jobs, orphaned or changed bytes and interrupted staging. Gate: tests/ops/test_backup.py::test_encrypted_roundtrip and tests/ops/test_backup.py::test_source_rejection.

R-OPS-03 IF any input/output path is relative, linked, overlapping, unsafe or already occupied, THEN THE tooling SHALL reject it without overwriting existing directories, files or keys. Gate: tests/ops/test_backup.py::test_path_rejection.

R-OPS-04 WHEN restoring an older snapshot, THE tooling SHALL require the independently trusted latest encrypted authority hash, reconcile its cumulative tombstones, remove deleted project rows/bytes only inside the newly created target, revoke sessions, recalculate quota and validate surviving immutable files. Gate: tests/ops/test_backup.py::test_deleted_project_cannot_return.

R-OPS-05 IF archive members contain traversal, links, duplicates, unknown names, unsupported schema, excessive bytes/count, missing files or mismatched hashes, THEN THE tooling SHALL fail before accepting a restore target. Gate: tests/ops/test_backup.py::test_archive_rejection.

R-OPS-06 WHEN a snapshot or tombstone checkpoint is produced, THE encrypted authority SHALL retain preceding tombstones and snapshot retention provenance; restore SHALL reject an unregistered, expired or deployment-mismatched snapshot and preserve the encrypted originals. Gate: tests/ops/test_backup.py::test_authority_rejection and tests/ops/test_backup.py::test_retention_and_chain.

R-OPS-07 THE operations guide SHALL state the trust boundary, deletion checkpoint gap, published retention behavior, exact commands and a separate actual-host drill with no claim it ran. Gate: tests/ops/test_backup.py::test_operational_contract.

R-OPS-08 THE tooling SHALL use the maintained age executable without implementing cryptography, store plaintext only under an explicit restricted scratch parent, bound subprocess/decryption/archive work and redact failures from public logs. Gate: tests/ops/test_backup.py::test_age_failure and tests/ops/test_backup.py::test_encrypted_roundtrip.
