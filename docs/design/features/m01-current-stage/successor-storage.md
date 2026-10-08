# Physical persistence successor storage contract

The reviewed current-stage requirements/design govern this implementation. The
original isolated physical revision and its historical source/evidence remain
unchanged. The explicit successor is `0005_physical_forest`, with
`down_revision = 0004_waveform_artifacts`, and null branch/dependency labels.
There is no competing default revision or implicit stamp.

## Source and migration isolation

The waveform predecessor is the exact source from commit
`00f61fa0f851e75c0ac19b0814667288e3f1d901`, blob
`06d28de9c91beab0561737f25829644a7ae621ab`, 1492 bytes, SHA-256
`82c827b94940d803fae42eb7137fda63f2b4d816e11dddd481f79c5b3cb41ac3`.
An unchanged copy in the explicit candidate registry permits migration tests
without changing the default application head. The successor source lives in
`app/migrations/candidates/0005_physical_forest.py`; its SQL definitions extend
the unchanged A/B dictionary through `app/physical_successor.py`. A dedicated
`app/migrations/physical_successor/env.py` accepts only explicit candidate
attributes, version locations and an external database path. It performs no
live discovery, native WAL target opening, service change or automatic upgrade.

The predecessor fingerprint is measured from actual Alembic 0001–0004 DDL using
the original compact UTF-8 sqlite_master projection. Unknown source/DDL/rows,
active jobs, inconsistent ownership or unsupported tuples refuse without
mutation. The new schema registration must bind actual successor source bytes,
Git blob and independently measured DDL; a revision name alone cannot admit it.
Until independently reviewed, the measured registration is not runtime approval.

The isolated SQLite candidate uses delete/memory journal only. Foreign keys are
disabled only before its explicit transaction, restored and checked afterwards.
DDL, backfill, constraints and the Alembic revision update commit in one SQLite
transaction; any injected failure rolls all of them back. This is transaction
rollback evidence, not native power-loss/WAL/directory durability proof.

## Positive roots and immutable forest

The successor preserves every original dataset column value and SQL type,
native JSON/text/timestamp, raw/result/file identity, waveform source dependency
and waveform result-artifact row. It backfills roots only, never scientific
producers, measured CPU, readiness or controls. Root tuples are positively:

| Parser | Modality | Payload schema |
| --- | --- | --- |
| gravity-station-csv/v1 | gravity_station | geophysics.observation-dataset/v1 |
| edi-strict-envelope/v1 | edi_transfer_function | geophysics.observation-dataset/v1 |
| supplied-profile-original/v1 | ert_profile | geophysics.observation-dataset/v1 |
| supplied-profile-original/v1 | traveltime_profile | geophysics.observation-dataset/v1 |
| m08/v1/ plus exactly 64 lowercase hexadecimal digits | waveform_counts_response | geophysics.waveform-dataset/v1 |
| gravity-stations-json/v1 | gravity_physical_station | gravity-stations-1 |

Physical derived tuples remain the exact correction/transform A dictionary.
Neither prefix-only wildcard admission nor deletion of a legacy tuple is allowed.
Family ordinals allocate under BEGIN IMMEDIATE, advance once and never rewind;
failed reservations leave gaps. At most 64 published/reserved members and four
parent edges; ownership/raw/parser/root identity and parent digest must agree.
One parent and one producer per derived child; immutable metadata cannot be
rewritten to repair a contradiction. Publication retains the reviewed intent,
dual-file custody/charge and same-terminal-commit rules. No forest helper may
publish a scientific child without those complete predicates.

## Failure-first validation

Tests exercise real predecessor/successor upgrades with all five existing root
variants, native value/type/byte preservation, waveform foreign-key survival,
unknown DDL/parser/method/state/format refusal, active-job refusal, exact source
binding, transaction cut rollback, composite ownership rejection and refused
downgrade. Separate allocator tests cover concurrent reservation, exhaustion,
gaps, stale/foreign parent and depth/capacity limits. No solver, API activation,
external backup authority, whole-host percentage gate or weakened tolerance is
introduced by this contract. Production API/worker/native/filesystem/browser
qualification remains distinct from these storage tests.
