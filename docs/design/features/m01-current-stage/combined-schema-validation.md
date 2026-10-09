# Literal combined migration validation

The isolated registry binds literal M01 `d222387` revision
`0005_physical_forest`, M11 `b9cd9a1` revision `0006_joint_artifacts` and M03
`6909634` revision `0007_magnetic_line_artifacts`. It copies the actual closed
plural0004 SQLite fixture with SQLite's consistent backup API before migration.
The retained predecessor, native JSON/SQL types and external original bytes
remain unchanged. No migration stamp, placeholder predecessor, competing0005,
numerical replay, deletion implementation or default application mount occurs.

`tests/ops/physical_union_fixture.py` closes all pinned source bytes before any
target opening, emits an exclusive external registry and source manifest, and
requires exactly one head with the literal predecessor chain. Its optional
`--mount-packet` output emits additive unmodified migration/model/helper sources
for the integration owner's private union. It does not modify default versions,
database migration head, server, worker or runtime configuration. The candidate
environment and0005's explicit offline transactional/DDL/source guards remain.
Apply/check this source-hashed patch with `git -c core.autocrlf=false apply`:
Windows global newline conversion would otherwise change literal source hashes.

`tests/api/test_physical_union_schema.py` verifies native retained rows/types
through0004→0005→0006→0007, exact empty0007→0006→0005 DDL restoration,
retained M03 custody refusal before table drops, retained joint dependency and
physical debt preservation, composite M01/M11 owner/project/input identity,
and actual migration/revision-update failure rollback. Literal0005 ALWAYS
refuses0005→0004 downgrade, including empty state. That refusal is not a full
reversible rollback claim and must not be removed to pass an integration test.

An adverse separate gate is retained unchanged:
`test_m03_cross_owner_intake_is_not_granted_by_separate_foreign_keys`.
The pinned0007 DDL has individual owner/project/raw foreign keys, not a composite
owner binding. It accepts an intake whose existing owner and existing project
belong to different accounts. This is not evidence that an authenticated M03
route grants access: the reviewed application joins are independently required.
Neither a green migration roundtrip nor M01/M11's composite constraints proves
M03 application ownership. Preserve this failed source-bound assertion; don't
rerun its unchanged fingerprint, relabel it green, weaken it or silently change
another owner's literal DDL. The integration owner must retain the explicit
application ownership gate before mounting M03 admission/read/export/delete.

This fixture proves bounded SQL/source integration, not scientific acceptance,
production WAL admission, all-writer startup, lifecycle mounting, process drain,
browser acceptance or activation. Original scientific failures remain separate.
