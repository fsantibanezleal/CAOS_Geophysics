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

## Optional fresh-state operator binding

The initial-only `scripts/bootstrap_service_state.py` accepts an optional
root-owned mode-0600 registry and an explicit SHA-256. Before creating state,
it validates the exact versioned registry schema and requires its
`release_manifest_sha256` to match the candidate bundle's literal
`release.json`. It copies the same bytes into the fresh service-owned
`/var/lib/geophysics/physical-operator-bindings/<release-id>.json`, then invokes
the existing lock initializer as the service UID against that fresh private root.
The registry supplies identity references only; it does not create source
policy, approve scientific methods, or admit a release.

Each release receives immutable root-owned mode-0600 API and worker env files
under `/etc/geophysics/releases/<release-id>/`. A bound release points to its
own service-owned registry under
`/var/lib/geophysics/physical-operator-bindings/<release-id>.json`; both envs
carry the same registry path and byte digest. Bootstrap also seeds the global
systemd env pair from that first release. Qualification checks the candidate
release env hashes, exact registry-to-manifest binding, registry ownership,
and lock markers/owners. Activation requires the host-admission receipt to bind
both candidate env hashes, snapshots the currently selected global env files,
then installs the release-scoped pair before switching `current`. On any
failed cutover it restores the exact previous env bytes before restarting the
prior services. A binding for a different `release.json`, partial env
configuration, changed registry/lock, or missing env-hash admission refuses
qualification/activation. A release without a registry retains the legacy
service path, while still using its release-scoped environment files.

The current deployment scripts do not generate the host-admission receipt.
The operator/evidence producer must add the exact `service_environment_hashes`
object (`api.env` and `worker.env`, SHA-256 of the release-scoped bytes) before
activation can pass. Until that producer is updated and independently
qualified, activation intentionally refuses to cut over; no compatibility with
the older admission-receipt shape is claimed.
