# Physical root: original API transaction integration

2026-10-08. This implements the approved current-stage immutable-root lane;
it is not a new approval, CPU controller, backup or host prerequisite.

The existing root verification and publication SQL remain one implementation.
Keep their outside-transaction candidate entry points restricted to delete/memory
journals. Add distinct closed native operations for the original API's existing
WAL transaction: exact literal0005/DDL, foreign_keys1, synchronous2 and
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
mounted endpoint. Parent retains default mounts and combined-schema adaptation.
