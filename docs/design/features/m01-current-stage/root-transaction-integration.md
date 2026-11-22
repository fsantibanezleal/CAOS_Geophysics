# Physical root: original API transaction integration

2026-10-08. This implements the approved current-stage immutable-root lane;
it is not a new approval, CPU controller, backup or host prerequisite.

The existing root verification and publication SQL remain one implementation.
Keep their outside-transaction candidate entry points restricted to delete/memory
journals. Add distinct closed native operations for the original API's existing
WAL transaction: exact registered literal0005/0006/changed0007 DDL, foreign_keys1, synchronous2 and
trusted_schema0 are observed, never changed by the operation. No connection is
opened, committed or closed by those operations. A savepoint rolls back an
operation's partial SQL on failure without retiring the caller's unrelated
uncommitted changes. The API retains its original writer/worker lifetime guards
and decides the outer commit or rollback, including uncertain outcomes.

Preparing still verifies the complete original/stage/source and quota, then
reserves the pending family, root intent and exact dataset target. Publishing
still independently verifies those bytes plus the installed immutable target,
then atomically inserts the structural-only dataset, retires the intent and
transfers retained stage copies to cleanup_pending. No solver, filesystem
installation, cleanup, root adoption, active job or scientific verdict is added.

Test actual SQLite WAL and the aiosqlite native thread: independent-reader
invisibility until the caller commits, outer rollback, savepoint failure cuts,
rehashed/foreign/unknown custody refusal, exact original byte retention,
unadmitted PRAGMA/schema/transaction refusal and the unchanged candidate API.
This is ordinary SQL/transport evidence, not native filesystem durability or a
mounted endpoint. Parent retains default mounts. The allocated 0006 and amended
0007 identities are measured from unmodified copied migration sources, not
revision aliases. Nonempty additional-method custody still needs its own exact
registered reader; a recognized DDL cannot grant scientific admission or omit
that method's stored copies.

## Original root dataset route

Before allocating a stage, the original dataset route commits a declared 32-MiB
root-stage reservation and two exact reserved slots. It admits another 16-MiB
independent target, rechecked during preparation. Serialization rejects a second
pending root for the same raw/parser before allocating another directory. Exact
original and structural envelope copies are exclusively written, synchronized
and sealed against the current retained original and complete stage namespace.
The same caller-WAL preparation and publication operations then reserve the
target, independently install it and co-commit root/family/cleanup debt. No stage
is removed on failure or cancellation; committed reservations and partial copies
remain charged for a fresh excluded audit. A GET establishes an actual SQLite
read snapshot, validates the unchanged full bounded producer ancestry and never
executes scientific corrections or transforms. Structural roots remain plainly
unadmitted for scientific execution until the actual fixed child is integrated.

Frozen portable root/assembly gate: 77 PASS, zero failure/error/skip, 239.855s;
`E:/_Temp/m01-root-assembly-r7-20261008.xml`, SHA256
`0ff29f8a7023d7963b264bc11be71bbd2b0d1f3753f533923ff87176b244e4a0`.
Original r6 62 PASS / 7 FAIL (182.249s) remains at its original path and SHA256
`9c0d3b346d4bd5a71b5d10bc6a1734762a432c3a5b5b27b0eecd8d883cf523ee`:
six new fixtures wrongly used Pydantic methods on frozen dataclass settings;
the schema refusal exposed the inner classifier error instead of the original
root transaction error. Fixed fixtures and boundary error, not the rejection.
No native POSIX positive, scientific worker or populated union custody acceptance
is inferred. The original project DELETE still has 0005-only seams to extend;
the full union needs actual M11/M03 accounting and closed namespace readers.

The original DELETE transaction seams now recognize the same exact allocated
schema identities. Historical v2 deletion records retain their original 0005
origin; new records save the actual observed 0005/0006/0007 origin. The unknown
historical 0004-physical alias remains refused. No default head, route, original
byte projection, staged-copy charge, exclusive lifetime or cleanup acknowledgement
is changed. A recognized head does not grant missing method custody.
The changed portable root/deletion/registry gate passed 57 cases, zero errors,
failures or skips, 193.330s, JUnit SHA256
`171f6ed9cf0baa6b9e50a1f6c848d9f32bf7514b6a07f6451f9b17d73cb17fd5`.
The existing atomic receipt/debt assertion now runs on all three exact heads,
both caller commit and rollback: 6 PASS, zero errors/failures/skips, 23.759s;
`E:/_Temp/m01-union-delete-threeheads-r9-20261008.xml`, SHA256
`bd7555c27741f46837de37230a7e2697a010b266c83e8acd96486f69671f1213`.
These tests retain unknown/foreign/debt negatives. Nonempty joint/magnetic
custody and actual Linux scientific dispatch remain unqualified implementation
work; native POSIX root birth is separately measured by a fresh fixed drill.
