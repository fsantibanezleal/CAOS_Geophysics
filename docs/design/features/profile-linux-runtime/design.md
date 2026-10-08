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

## Review and qualification boundary

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
