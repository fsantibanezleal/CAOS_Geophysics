# Explicit physical API and worker assembly

The current-stage decision permits private operator assembly without changing
the default registry or authentication policy. `create_app(..., physical=...)`
accepts only an explicit `PhysicalAssembly`. Its existing private file root,
writer leases, original worker exclusion and immutable source/custody registries
are supplied by the operator, not by an HTTP header or environment flag.

The participant middleware is outermost and same-task, before authentication
SQL writes, and remains held through the final streamed response. Startup takes
exclusive writer and worker exclusion, opens a fresh WAL snapshot, validates
the complete registered filesystem/SQL forest and refuses unknown or prepared
state. It never invokes legacy interrupted-row mutation before this observation.
The bound engine uses FULL synchronization and trusted-schema OFF. Session-bound
quota accounting includes original bytes, immutable outputs, reservations,
retained custody and the distinct registered profile archives.

An optional participating `run_forever` holds the writer SH lease and the
existing processing lock from original claim through execution and cleanup.
Idle workers hold neither lock. Repeated cancellation drains execution before
either lifetime guard is released. This transport does not itself qualify the
physical scientific dispatcher or its Linux resource containment.

The shielded cycle task acquires both guards itself. Its parent awaits/drains
outside the guards. An inherited ContextVar is not lease authority:
`require_held` checks the acquiring task identity. Processing has its own
`require_processing_held` predicate under SH; original DELETE/recovery EX checks
remain unchanged. Accounting within the executing cycle uses that same task.

## Private lock initialization

`scripts/ops_physical_bootstrap.py --data-root <absolute-external-private-root>`
creates only the two fixed lock files, exclusively and descriptor-relative, in
an already verified owner-private root. Each file and directory is synchronized.
Existing locks are never rewritten: exact marker, owner, mode, single-link,
same-device and held inode identity are required. Partial or uncertain creation
is retained. This command creates no schema, accounts, runtime authority,
configuration, services or public activation. Normal API/worker startup does
not initialize or repair locks.

Portable assembly and fault tests exercise actual SQL/auth/upload paths but use
explicit test lock transports. Linux lock, child, durability and full merged
runtime evidence remain separate acceptance gates; no portable fixture is an
OS receipt. The default application remains at the waveform predecessor until
the integration owner mounts the reviewed literal successor chain.
