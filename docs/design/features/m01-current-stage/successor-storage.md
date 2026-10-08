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
The exact measured record is [successor-schema-registration.json](successor-schema-registration.json).
Its positive revision pair extends the current-stage chain only; historical
isolated 0004/v1 restore validators still refuse it. No runtime source-policy or
native patch admission follows from this registration's mere presence.

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

## Literal charges, root publication and terminal debt

`physical_wire` structurally reads the complete original gravity JSON before
exposing a root. UTF-8, EOF, duplicate keys, finite literal numbers, station
identities and explicit height/geoid/instrument metadata are checked. It does
not wrap longitude, convert height or units, replay history, or run a solver.
The canonical v2 envelope retains the scientific payload and supplied source;
root producer and parent bindings are null, not fabricated scientific proof.

`physical_roots` binds raw/source ownership, permission, discriminator, original
hash/length and complete sealed stage inventory before reserving the family.
The root intent and single exact target commit together. Only an independently
installed, fully re-read target permits the final root/family publication,
intent retirement and stage-cleanup debt transition in the same transaction.
An uncertain SQL commit retains the installed copy and preparation; it never
adopts a pathname as a root merely because that pathname exists.

`physical_abandon` implements the opposite verified precommit root disposition:
the original rows/stage/raw remain; an installed exact target becomes separate
charged abandonment custody; stage-cleanup debt, intent/target retirement and
deletion of the empty pending family co-commit. It never creates a root, adopts
an installed file, unlinks data or releases charge on pathname absence. Unknown
stage/target/family/source state refuses, and injected debt/retirement cuts roll
back the entire transaction. The caller must first obtain independent exclusive
exclusion and a complete fresh classification; this helper is not that audit.

`physical_debt` transfers failed/cancelled running jobs, their complete sealed
stage, exact installed target subset, permanent reservation retirement and
family reservation decrement in one terminal transaction. Installed targets
become independently charged abandonment custody. Gaps are retained, and no
child or result is published. Unknown files, mismatched controls or incomplete
target declarations refuse without reducing liabilities.

Account charge sums each literal retained copy: original raw, datasets, main
results, waveform extra artifacts, saved control BLOBs and native UTF-8 JSON
text, permanent reservations, custody and admitted legacy active scratch caps.
`AccountUsage.raw_bytes` remains raw-only and must equal the actual raw sum.
Identical hashes do not deduplicate copies. Positive legacy caps preserve flag
QC, EDI QC/inversion, protected ERT/TT and M08's exact 52690944-byte contract;
an unknown method does not inherit the flag-QC fallback.

## Native filesystem and cleanup boundary

Saved correction producer verification uses the exact 30-key parent snapshot,
all four original input/child/request/result byte bodies, and the independently
registered producing module manifest. It binds the complete 6-key scientific
request, 4-key adapter output and unchanged 13-key adapter receipt, SQL job and
production receipts, false acceptance declarations, immutable family/source,
submitted versus normalized config and both digest dialects. Numerical replay,
uncertainty reconstruction and source file access are forbidden in this parent.
Each earlier edge requires its own complete audit; a nested snapshot alone is
not a verified ancestry or a new runtime/host approval.

`physical_publication.audit_correction_ancestry` reads the exact owned original
root and every earlier correction's child, input, saved request/result and SQL
receipts. It binds the full earlier snapshot rather than trusting nested hashes,
retains native SQL request values, and rejects transform parents. Registration
is supplied independently. It performs no numerical replay or normalization.

Correction publication re-reads the complete sealed stage, fixed completion,
original scientific bytes and both independently installed target copies. The
trusted supervisor's aggregate metrics must equal the saved resource receipt,
whose environment and output byte length must match the registered runtime and
actual scientific serialization. Cancellation before the write-locked terminal
decision prevents publication. Child, edge, producer, succeeded job, retained
stage cleanup debt, zero permanent reservation, intent retirement and allocator
counts co-commit. All four precommit cuts roll back every public row while
retaining both installed files and reservations. This is an explicit ordinary
publication, never automatic adoption of an uncertain prepared outcome.

The complete global fresh classifier, transform terminal publication, logical
deletion and integrated queue/API/export/client remain separate mechanisms;
this correction transaction does not manufacture their approval or native WAL
admission. Default startup and migration registries remain unchanged.

`physical_posix` retains no-follow directory descriptors and ancestry identity,
rejects links/device changes/root replacement, reads exact ordinary-file
identities and hashes, and installs independent exclusive copies. Installation
orders file fsync before containing-directory fsync. Uncertain installed copies
are never unlinked in a finally clause. Cleanup verifies the exact saved slot,
unlinks one ordinary file and syncs its containing directory before committing
the SQL removed ordinal, updated inventory and reduced charge. A failed SQL
acknowledgement keeps charge; later pathname absence alone cannot release it.

Its complete census consumes only trusted declared slots, exact caps and optional
presealed partial slots. It recursively streams the closed namespace through
retained descriptors, refuses unknown names and links before body reads, and
bounds entries, elapsed time and aggregate bytes. Each ordinary file is hashed
in bounded chunks with unchanged inode/size/time/link checks. Declared optional
absence is not adoption or charge relief. Actual Linux controls cover complete
and partial inventories, unknown bodies/directories, links/FIFO, wrong sizes and
hashes, missing required slots and a real mutation during the read. This primitive
still requires independent writer exclusion and the complete SQL/forest classifier.

`physical_leases` provides task-scoped Linux shared/exclusive flock acquisition
on an already initialized immutable lock inode. Acquisition does not create or
replace that lock, upgrade shared to exclusive, expire a live lease, or inherit
its descriptor through exec. All participating writers must hold the shared
lease until their children quiesce. Recovery/cleanup uses an independently
obtained exclusive lease and full fresh audit. The primitive does not exclude
nonparticipants or privileged operators by itself.

The isolated native drills execute these actual file/SQL mechanisms under a
source-bound patched SQLite build, including fresh WAL visibility and stale
main-file rejection. They do not establish power-loss survival, all-production
writer participation, full forest/scientific classification, queue/API wiring
or activation. Default startup and migration registries remain unchanged.
