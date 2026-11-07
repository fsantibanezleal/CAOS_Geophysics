# Failure-retirement transaction boundary

Reuse the existing checked `_ledger` caller-owned savepoint from physical root
publication. It requires original native SQLite tuples/TEXT, foreign keys, WAL,
FULL synchronization, untrusted schema, active transaction and registered schema.
The internal retirement body is shared, not duplicated or independently relaxed.
The isolated public entry uses its original owned BEGIN/commit/rollback lane.
The new explicit transaction entry never commits, opens or closes the connection.

The SQL transition preserves original running job/control/stage identities,
sealed inventory and exact installed subset. Failed work never obtains a child
or producer. Installed copies remain charged as cleanup debt, and the monotonic
family ordinal is not reused. Errors retain original custody and cannot initiate
cleanup. Native extinction, file measurement and writer ownership are caller
prerequisites, not claims established by this SQL operation.

The dispatcher registers one literal operation name. It retains existing native
thread serialization and cancellation-drain behavior. Tests use real SQLite
connections and independent readers but explicitly authored SQL fixtures; they
are not numerical, filesystem-durability or deployment acceptance.
