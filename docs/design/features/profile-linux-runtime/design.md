# Fixed Linux profile supervisor

## Existing evidence and missing integration

MAIN independently revalidated all eleven actual private VPS source-bound profile
runs from `8b5691904d70f605743088f67373bd9b03861a88`. Both original and repeated
ERT/traveltime calculations, malformed originals/metadata, cancellation and
administratively lowered wall/RSS/memory/scratch controls passed. Audit SHA-256:
`0b041cfd318896b7953677690c4d2601fd0f28b0b23c3e4dafb6f02b1548bd79`.
The existing production worker still directly launches subprocesses and samples
RSS/files; it does not inherit the private qualification's kernel/mount controls.
This integration closes that implementation gap, not all product acceptance.

## Fixed authority, not arbitrary privileged execution

Use an installation-owned, stdlib-only launcher with one UUID argument and one
root-owned bounded configuration. The unprivileged worker cannot choose its
interpreter, code root, data root, UID/GID, source policy, unit properties or
limits. A narrowly installed sudo command invokes only the pinned launcher and
does not authorize generic systemd-run, shells or caller executables. The
configuration/launcher/source/native environment must be read-only to the worker
and independently verified before installation; source hash equality is not
independent authorization. Privileged code never imports uploaded content.

Read the exact running job and owned immutable relation from the configured
database, validate closed request/producer/raw/dataset identities, and hold
fresh bounded original snapshots before launching. Construct the unit and all
paths internally from canonical UUIDs. Refuse links, traversal, foreign owners,
unknown job states/methods/parameters, changed engine/environment and concurrent
launches. No command or path is accepted from request JSON. The ordinary API
still controls authentication, CSRF, ownership and admission.

The database reader first forks and irrevocably drops groups/GID/UID to the
configured application identity. Only that nonroot reader opens SQLite, its WAL
or uploaded input paths; the privileged parent receives bounded plain JSON and
byte snapshots over anonymous pipes. This avoids granting root file access to
worker-controlled SQLite sidecars or path races. Parent file installation and
retention use held directory descriptors with no-follow/exclusive leaf opens.
Held originals and the mount target use installation-owned custody beneath
`/run/fasl-geophysics-profile-jobs/<UUID>`, not worker-renamable stage parents.
The worker's ordinary private stage is only a separately pinned retention target.
The child checks the mounted input file device/inode/size/hash identities before
engine execution. These copies are separately counted from writable tmpfs
scratch. Remove only those declared copies
after exact extinction and verified original identities; otherwise retain debt.
The earlier in-worker-stage proposal is rejected by independent peer review:
root-owned contents do not prevent an owner from replacing their parent path.

## Child and custody

The system manager creates a fresh exact `geophysics-profile-<UUID>.service`
with empty capabilities, NNP, nonroot IDs, private network/devices/temp,
ProtectSystem=strict, read-only held originals/code, one CPU, memory.max=2 GiB,
swap.max=0, tasks32, RuntimeMaxSec600 and a private 64 MiB tmpfs stage.
Acquire the actual mounted cwd descriptor and verify its capacity before
sampling or retaining files; do not inspect the observer's filesystem through
the misleading /proc/PID/root path. Keep the stage descriptor through child exit.
Observe kernel memory.peak/events and exact extinction independently from
sampled RSS and file-byte scratch. Retain only bounded known result/diagnostic
members; no recursive cleanup or directory adoption.

The launcher's caller pipe is a liveness/cancel channel, not scientific input.
EOF or explicit cancellation stops the exact unit. The worker waits for a
terminal receipt and validated retained bytes before its existing publication
transaction. A launcher failure, uncertain termination, unknown stage entry or
receipt mismatch preserves the stage and never produces successful science.
The ordinary worker startup inventory handles retained debt conservatively.

Independent review rejected the same-UID in-unit watcher: its death was not
fail-closed, and later acquisition of a numeric launcher PID permitted reuse.
Use a root-owned guardian forked before manager submission instead. Acquire the
launcher's pidfd before fork, transfer no privileges/handles to science, require
a ready handshake, and hold the guardian's pidfd as an unreaped owned child.
Unexpected guardian exit stops the exact unit; launcher death makes the guardian
stop/drain that exact unit. A bounded completion frame is sent only after fresh
extinction. Record guardian outcome separately; no port, shell or arbitrary
signal target is exposed. Actual crash/death/interrupted-submission controls are
required before enabling the path. No same-UID watcher is retained.

Do not leave the root guardian inside the caller service's control group:
stopping the worker service could otherwise kill launcher and guardian together.
Enroll the already-held unreaped root guardian in its own exact transient scope
through the systemd255 manager's PIDs interface, before scientific submission.
Verify active state and actual group membership. Bind the science service with
`BindsTo` and `After` to this scope, so guardian failure is independently handled
by the manager as well as the launcher. Names and properties are constructor-
owned, never browser input. Give the guardian a separately recorded bounded
operator memory/task/wall allowance; it is not scientific RSS/CPU admission.
Test caller-service stop, guardian kill and launcher loss independently.
Enrollment passes the already-held guardian pidfd through systemd255's
`PIDFDs` property, not a numeric `PIDs` array. An uncertain/late manager request
must retain the kernel process identity after the launcher reaps its child.
`busctl call` cannot marshal UNIX_FD arguments; inheriting a descriptor does not
change that limitation. Use the installed, root-owned, hash-pinned `libsystemd`
sd-bus interface through stdlib ctypes for this one closed method call, with
fixed scope properties and a five-second reply deadline. No generic D-Bus API
is exposed to users. The configuration pins `systemd_library` and its SHA-256.
Read back memory, task and wall properties and actual membership. Qualify
descriptor transfer, failed/late acceptance and caller death on the installed
manager before activation. Primary implementation:
[systemd255 PIDFDs](https://raw.githubusercontent.com/systemd/systemd/v255/src/core/dbus-scope.c)
and [sd-bus basic arguments](https://raw.githubusercontent.com/systemd/systemd/v255/man/sd_bus_message_append_basic.xml).
Primary interfaces: [systemd255 unit dependencies](https://raw.githubusercontent.com/systemd/systemd/v255/man/systemd.unit.xml)
and [scope lifecycle](https://raw.githubusercontent.com/systemd/systemd/v255/man/systemd.scope.xml).

Bound installation-owned retained custody independently of unit scratch: at
most four outstanding job plans and 16 MiB of declared held originals, and at
most 256 bounded 64 KiB operational receipts. Write an immutable exclusive plan
before any UUID directory or held copy is created. Unknown names/links/owners,
missing or altered plan identities and exceeded caps refuse new launches, not
delete anything. Success removes only checked declared copies and empty checked
directories after extinction, then retains a root-owned receipt. Failure/crash
retains the plan and known debt for a separately reviewed exact-UUID recovery;
there is no recursive adoption, sweeping delete, backup or external service.

## Review and qualification boundary

### Owned API/worker adaptation

Keep the Windows path-invoked profile lane and its actual tests unchanged. Add
an optional installation-only `profile_linux_supervisor` setting; POSIX protected
jobs configured with it use the fixed sudo/isolated distro-Python command and
one canonical UUID. The setting must match the root-owned installation config,
source hash and private database root. It cannot be supplied in job parameters.
The worker neither reads native memory counters itself nor signals numerical
root PIDs. Owner cancel and its whole-job wall deadline send the bounded cancel
frame; caller loss closes that liveness stream. Failed/uncertain supervision
retains the stage, rather than cleaning a possibly live or replaced directory.

Pin the ordinary stage directory before launching. Read the root receipt and
producer result through that held descriptor, verify retained-stage device/inode,
request/raw/dataset/source identities, exact retained bytes, extinction and
guardian completion. A path rename/replacement refuses publication. Successful
result publication adds the complete bounded operational receipt as
`linux_execution` to the outer JSON result; the scientific inner result is not
changed. Reconstructing the outer producer JSON without this member must match
the supervisor's retained producer digest. This keeps execution evidence charged,
hash-bound, downloadable and included in the existing exact three-member export,
without a new database migration or silently discarded fourth artifact.
Validate this optional receipt on API read, reconciliation and bundle reopen.
It records sampled RSS and memcg charge separately and does not assert full
native CPU admission. A successful process result can still carry an explicit
scientific `ineligible` verdict, as in the unchanged original profile contract.

Only after existing bundle/science checks and the ordinary owned transaction
commit can checked known stage files be removed. Unknown bytes, cancellation,
failed supervision, changed originals or ambiguous commit preserve known debt.
Operational root receipts remain independently bounded. Exact-UUID recovery,
resource/cancel/crash tests, original preservation and authentic API/browser
roundtrip are required on the separate VPS candidate before live activation.

The configuration also pins a root-owned import-closure inventory by SHA-256.
Before native execution, compare complete runtime and environment name sets,
entry kinds, ownership, modes, device/inode identities and file hashes with that
inventory; verify pinned links and native dependencies. Checking only the
previously listed files is insufficient: an added startup hook or importable
file must refuse execution. The independently qualified source/cache/startup
proof remains necessary when this inventory is installed, and changing the
runtime requires requalification rather than regenerating an accepted digest.
The product source closure includes the engines' imported `sources.py` and
`data/source-ledger.json`, with only the declared files and ancestor directories
allowed in the separate sealed source root. The older qualification's source
inventory is not authority for a different product source installation.
The unactivated configuration advances to `geophysics.profile-linux-config/v2`
with explicit `import_closure` and `import_closure_sha256` fields. The imported
inventory is scientific-runtime authority only; it cannot alter commands, IDs,
paths, properties or privileges. Actual final-source import and queue execution
remain host acceptance gates.

First implement failing closed-packet/constructor/source and relation tests,
then the fixed supervisor and additive worker adaptation. Preserve M08's pending
shared worker changes by integrating its pinned version before the union patch.
No M01 persistence or waveform source is overwritten. Install/execute initially
only in a separate private candidate with no live pointer/account mutation.
Actual full API/worker proof precedes profile flag activation. Native CPU/broker
fixture accounting remains separate and unaccepted; this launcher does not
claim its fifteen-gate admission or nanosecond CPU completeness.

Primary execution references: [systemd's execution settings](https://github.com/systemd/systemd/blob/main/man/systemd.exec.xml),
[transient settings](https://github.com/systemd/systemd/blob/main/docs/TRANSIENT-SETTINGS.md)
and [control-group API](https://systemd.io/CONTROL_GROUP_INTERFACE/).
Verify the installed systemd255 interface; current upstream documentation alone
does not prove the installed host supports every setting.
