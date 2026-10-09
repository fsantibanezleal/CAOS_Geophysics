# Protected profile dataset, compute and presentation

The existing internal-account API, SQLite projects, immutable raw store and
single unprivileged bounded worker remain the architecture. Profile integration
adds method-specific contracts and dispatch rather than a second service or
request-process numerical execution. Opening local files remains public and
does not upload them. Persisting and computing on the VPS are explicit,
authenticated actions.

## Dataset admission

Supported new original formats are `ert_ohm` and `traveltime_sgt`, with explicit
extensions/MIME and the same strict grammars as the supplied local pipeline.
The common physical declaration retains local reference, elevation-up metre
coordinates, ABMN or source-receiver geometry and ohm/second observations.
The supplied-profile metadata is an explicit addition to dataset creation,
not guessed from a file suffix. Its source ID must equal the persisted source
record, and its hash/count must equal the persisted raw original. Local frame,
datum and quantity must agree with the raw asset declaration. Unknown keys,
invalid rights or booleans, unsupported covariance and mismatched fields reject.

API admission parses only the bounded original, never loads pyGIMLi native
modules or runs an inverse. The recorded envelope contains owner/project/asset
IDs, raw hash/count, parser version, method, exact supplied metadata and original
geometry/count/QC. It is an immutable dataset version and can be independently
revalidated. No inferred field truth is created.

Local acquisition and numerical receipts use an explicit external data root,
selected by `--data-root` or `GEOPHYSICS_LOCAL_DATA_ROOT`. The product's reviewed
ledger remains in the repository. The configured root preserves ledger-relative
storage keys, immutable raw hashes and receipt bytes; it is not a new acquisition
or a reason to rewrite historical provenance. A missing root is a configuration
error, not permission to write raw working data into a checkout. Sandboxed tests
use explicitly configured external temporary roots.

## Compute and state

New `app/profile_contract.py` and `app/profile_compute.py` implement the
method-specific envelope and child command. A path-invoked
`scripts/process_profile_job.py` child needs only the pinned profile environment,
not API/account libraries. That environment remains separate because its
NumPy/SciPy requirements differ from the MT/API runtime. This is a dependency
boundary within the same worker and origin, not another service. Children receive the verified
original path and strict dataset/request bytes from the worker, not an
arbitrary URL, executable, import name or user Python expression. Native
diagnostics stay in private stderr. The scientific core remains
`supplied_profiles.process_profile` with its unchanged primary settings,
physical oracles and independent prediction gates. Geometry-only supplied
whole-shot folds are retained for M09. User numerical parameterization beyond
the frozen validated settings requires its own explicit numerical tests; a
display knob must never be described as a solver parameter.

The result binds job/request/dataset/raw IDs and digests around the complete
portable profile result. Ineligible or failed scientific status is durable and
inspectable; no missing model is synthesized. Runtime failure and user
cancellation remain distinct from completed computation with a failed
scientific verdict. Source input, checksummed arrays, numerical settings,
coverage semantics and residual convention are unchanged by presentation.

The host admission ceiling derives from existing worker limits and measured
nominal/upper runs. An explicit feature flag stays closed until actual-host
receipts exist. Full local supported input remains available when an original
exceeds the admitted online size; the interface returns a reproducible offline
recipe and import path, not a lower-resolution replacement. This flag is a
scientific/resource gate, not another user permission or infrastructure choice.

## Views and exports

The protected project panel lists compatible methods, submits and polls actual
jobs, permits cancellation and opens the owned result. It reuses the native
profile instrument rather than duplicating numerical rendering. Producer byte
bindings and original array orientation are preserved. An export carries the
profile result/manifest and parent/request identities; original bytes are
included only within the declared export rights. Existing account ownership,
CSRF, deletion and plural-user/project behaviour remain binding.

## Independent acceptance

Tests first cover original/metadata/hash/unit/owner drift and no native load on
rejection; actual child computation; preserved failed numerical verdict; result
identity and export tampering; job limits and cancellation; pointer/keyboard
inspection in both languages/themes and phone/desktop; actual ML VPS compute
RSS/wall/scratch and simultaneous public-read responsiveness. Green contract
tests alone do not activate a method or accept the product.
