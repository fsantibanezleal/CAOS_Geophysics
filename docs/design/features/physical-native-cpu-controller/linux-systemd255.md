# Linux systemd255 per-job native controller source contract

This is the precise Linux implementation packet following the accepted
[worker operation definition](worker-operations.md). Windows I01 remains separate.
Necessary application-specific accounts, units and delegation are normal scoped
deployment work, not prerequisites that must already exist. Actual setup is
reviewed and measured before native qualification; missing setup does not stop
source implementation. No global toolchain installation, user.slice delegation,
mail, off-host backup or arbitrary disk-percentage requirement is introduced.

## 1. Concrete topology and retained accounting object

One fresh system-manager transient service per attempt, in system.slice:

```text
geophysics-cpu-job-<32 lower hex attempt>.service  (PID1 owns lifecycle)
  observer/   native single-thread controller, separate CPU/memory charge
  science/    clone3-born root and all descendants, retained cpu.stat
```

Qualification uses the disjoint geophysics-cpu-qual- prefix and dedicated fixture
units/state, never a production worker/service/account/database. The parent unit
has Type=exec, ExitType=main, Delegate=cpu memory pids,
DelegateSubgroup=observer, KillMode=control-group, SendSIGKILL=yes,
TimeoutStopSec=1s, Restart=no, CPUAccounting=yes, MemoryAccounting=yes and
TasksAccounting=yes. RuntimeMaxSec is the reviewed wall bound. No --scope,
--collect, automatic unit reset or service retry. The complete manager stop
bound1s is a crash backstop, NOT evidence of the native250ms kill gate.

The delegatee is the native controller only. Compute uses a distinct unprivileged
application science UID/GID, supplementary groups empty and all capabilities
zero. The existing API/worker UID is not reused for compute. Exact account
creation and controller launch permission belong to the scoped host setup, not
a blanket PolicyKit grant or arbitrary systemd-run permission to the API.
The controller initially has only the reviewed permissions needed for owned
cgroup files and credential drop; no compute privilege crosses GO.

DelegateSubgroup keeps observer tasks out of the delegated domain parent, so the
no-internal-process rule permits cpu/memory/pids controllers below it. Verify
actual /proc/self/cgroup is exactly this unit's observer subgroup, not user.slice,
the worker cgroup or a shared scope. Open the unit directory anchored beneath
the actual cgroup2 mount with no-follow directory FDs; record device/inode.
Require parent cgroup.procs empty and required controllers enabled; do not write
an ancestor or change a shared slice. Exclusive mkdirat creates science only.
The controller never moves itself or a running science PID between groups.
See the [v255 delegation/subgroup contract](https://raw.githubusercontent.com/systemd/systemd/v255/man/systemd.resource-control.xml)
and [v255 execution implementation](https://raw.githubusercontent.com/systemd/systemd/v255/src/core/exec-invoke.c).

Keep science group/FD/counter files until final counter custody is sealed and
acknowledged. No systemd CPUUsageNSec over the whole unit is substituted: it
includes observer work, and is only an independent diagnostic. PID1 teardown
after abrupt controller death can lose the science counters; that case is
explicit unavailable/failed, never repaired by the last running observation.

## 2. Exact new source/test scope

```text
scripts/native_physical_cpu/linux_controller.h
scripts/native_physical_cpu/linux_controller.c
scripts/native_physical_cpu/linux_main.c
scripts/native_physical_cpu/linux_probe.c
scripts/native_physical_cpu/linux_fixture.c
scripts/prepare_linux_cpu_context.py
scripts/run_linux_cpu_controls.py
tests/worker_accounting/native/test_linux_context.py
tests/worker_accounting/native/test_linux_source.py
tests/worker_accounting/native/test_linux_controller.py
```

The first three files implement real OS operations and the independent native
event loop. No supplied-counter provider or Python observer is the implementation.
Probe and finite authored fixture are separate binaries. Context preparation and
host harness are ordinary stdlib scripts, not a package, deployment installer,
new app route or patched runtime. Keep existing controller.h/c, ABI probe,
capture helper, pure protocol and I01 tests/artifacts byte-identical. No app/,
database, migration, service-builder or service-unit edit in this source unit.

## 3. Root-owned launch context and private worker seam

An operator/owned-launcher prepares one exclusive root-owned0600 context, bounded
32768 bytes, with exact bytes hashed in the private launch receipt. It is not an
API upload and never accepts executable selection from a public request.
Header64 little-endian bytes: magicLCX1 at0, versionu16=1 at4, budget_classu16 at6,
compute_uidu32 at8, compute_gidu32 at12, argc u32 at16, envc u32 at20,
payload_bytesu32 at24, reserved0 at28, attempt16bytes at32, object16bytes at48.
Both IDs are nonnil and must match the selected unit/control identities.
Payload is length-prefixed UTF8 strings: resolved immutable executable, explicit
argv0/venv identity, private working directory, then argc arguments and envc
literal environment entries. Each length is checked before copy, no NUL,
surrogates/invalid UTF8, traversal or relative executable/cwd. Path cap1024,
argc1..32/each1024/total16384, envc0..32/total4096, no duplicate environment keys.
No JSON, shell, PATH lookup, response file or callback in the C launcher.

Budget class1 is the frozen60s CPU/57s stop/120s wall qualification class;
class2 is240s/237s/300s. They name resource classes, NOT scientific methods.
No M05/M06 is silently relabelled as a gravity lane. The future app seam must
explicitly bind a method-specific immutable policy including its existing tighter
wall/memory/scratch/result limits; source, parameters, job/project/principal
identity and raw EDI byte/eligibility guards remain untouched. Qualification
classes cannot activate an app method. Classes outside1/2 reject.

Candidate private worker seam after separate review: launch one controller;
send START/heartbeat/cancel on its owned control pipe; receive bounded native
samples, status and retained-counter outcome; continue existing result identity
validation/publication only after the resource verdict. No API token, password,
SMTP or database path enters compute. Root-owned launcher authorization checks
the worker credential and exact allowed operation, not a caller runtime flag.
Current app.worker has no such call and is not edited here. Its Popen/live-PID
polling cannot be represented as this controller. The secure system-manager
launch endpoint is an explicit MAIN-owned seam review, not a fictitious provider.

## 4. Native birth, credential barrier and authoritative samples

On empty science: set/read back cpu.max100000/100000, cpu.max.burst0,
pids.max256 and reviewed memory.max/memory.swap.max0. Domain type required.
CPU bandwidth is not lifetime credit; memory.max/current/peak are not RSS.
Host online/available CPU domain must have1..8 logical CPUs, recorded for the
fixed margin; no Windows affinity assumption is imported. Set subreaper once.

Zero-init actual struct clone_args; call SYS_clone3 with INTO_CGROUP|PIDFD,
SIGCHLD and the retained science FD. Capture errno immediately. ENOSYS/EPERM/
EACCES/EINVAL/EBUSY/EOPNOTSUPP all fail, no fork/Popen/migrate fallback.
The child begins accounted and executes fixed native setup only: controlled
stdio, close all cgroup/observer/receipt authority FDs, setgroups0,
setresgid/resuid all IDs and verify them, clear effective/permitted/inheritable/
ambient capabilities and verify, no_new_privs1/dumpable0, PDEATHSIG SIGKILL after
credential changes and expected-parent recheck. Setup-ready then GO precedes
exec of the immutable open executable. No science import before GO. Missing
barrier/setup/parent identity fails and stops the entire group.

Controller monotonic clock is actual clock_gettime(CLOCK_MONOTONIC), checked
signed seconds/nsec conversion. Native cpu.stat read cap4096 plus EOF probe,
<=32 lines/key64/decimal20 digits; exact required usage/user/system once each,
known optional kernel keys only. Preserve all three raw components and charge
checked max(usage,user+system)*1000ns including exited descendants. Read
cgroup.events populated separately. Unknown/unavailable/regressed/overflowed
records never become available0. No live-PID CPU aggregation.

Whole-group stop writes exactly1 plusLF to retained cgroup.kill. Drain requires
recursive populated0, owned root PIDFD exit and owned adopted-child reaping.
Natural root exit with live descendants is failed/unexpected_descendants, not
successful output. Wait >=50ms after actual drain, then three equal component
reads >=20ms apart within2s while emptiness remains verified. Final CPU>B fails
at1000ns native resolution; no tolerance relaxation or invented1ns OS sample.
See [clone3](https://man7.org/linux/man-pages/man2/clone.2.html) and the
[kernel cgroup2 contract](https://docs.kernel.org/admin-guide/cgroup-v2.html).

## 5. Independent loop, cancellation and crash custody

Control uses the existing bounded64-byte framing shape with a distinct Linux
qualification magic/version, fixed IDs/sequences and known START/heartbeat/
cancel/bind/ack variants. Native sample records preserve query start/end, raw
components, populated/root-reaped/adopted-reaped and CPU ns. No native handle,
PID/path/stderr goes into safe public errors. Transcript/schema is an isolated
qualification artifact, not an accepted existing0003 bundle/receipt revision.

Set owned control/output pipes nonblocking; keep fixed input buffer64+4096 and
pending output queue4. Poll at most5ms to the next deadline; check complete
successful observation gap/query duration<=20ms after every wake and I/O batch.
Heartbeat interval<=100ms, grace500ms; EOF/cancel/output-backpressure stops the
whole science group. Bounded ready/GO and stdout/stderr drains cannot defer native
queries. A full queue or unavailable output is a failure, not dropped evidence.
Always attempt whole-group stop even when the first safe failure is already
latched. Store only previous/final3 counters; incremental bounded trace<=32768
samples/16MiB. No unbounded allocation, filesystem traversal or JSON serializer
inside this timer loop. Science stdout/stderr each65536; exceeding is failure,
never truncate then accept.

PID1 owns the outer service death backstop. For production BindsTo/After bind
each attempt to its exact worker service; qualification binds a fresh owned
fixture-parent service instead. Worker death stops the attempt; controller death
causes unit main-process termination and complete group kill; simultaneous death
still has PID1/RuntimeMaxSec. Independently test all three orders. PDEATHSIG and
subreaping alone are not credited as the grandchild kill mechanism. Failed/lost
finals, interrupted output or unacknowledged custody stay failed/unavailable;
never auto-adopt a stale unit, retry, publish or fabricate a counter receipt.
Source basis: [v255 kill contract](https://raw.githubusercontent.com/systemd/systemd/v255/man/systemd.kill.xml)
and [v255 service lifecycle](https://raw.githubusercontent.com/systemd/systemd/v255/man/systemd.service.xml).

Bounded native object release only follows exact trusted receipt-hash custody;
lost/mismatched ACK retains HELD evidence. This does not prove file+DB durability,
full worker/controller publication tails or quota/deletion acceptance. Outer
qualification harness obtains exited controller rusage via wait4/manager record
and separately accounts fixture parent overhead. No preliminary SELF is labelled
final production parent CPU. Real scratch/RSS enforcement remains separately
measured with unchanged ceilings; directory polling is not a hard filesystem
quota and memcg memory is not relabelled RSS. None is an excuse to defer CPU
implementation or to accept incomplete resource evidence.

## 6. Exact build/probe and isolated host gate packet

Existing system compiler only, no install. First freeze/hash C/header/scripts/
tests and actual selected cc/gcc, assembler/linker, libc/loader and emitted header
dependencies, resolving ordinary tool/runtime links explicitly. Reuse actual
host sched.h/syscall.h identities in the private inventory, not Windows closures.
Record compiler --version and Linux/systemd version, uname, cgroup mount/type/
controllers and selected account/unit identities. The probe prints actual
clone_args size/alignment/offsets, syscall constants, pid/uid/gid/time_t widths,
timespec/timeval/rusage layout, wait/PIDFD flags and cgroup2 magic. It invokes no
clone/cgroup creation/credential change. Compare with actual selected headers;
no hardcoded syscall numbers. Unexpected ABI remains a retained failure.

Proposed arrays: selected cc with -std=c17 -Wall -Wextra -Werror -Wconversion
-Wshadow -fstack-protector-strong -D_FORTIFY_SOURCE=2 -O2 -fPIE;
link -pie -Wl,-z,relro,-z,now. Compile controller/main and unchanged arithmetic
core; separately compile probe and finite fixture. Emit dependency lists for
each translation unit and hash actual included files, no whole-toolchain tree
ritual. Fresh exclusive private output and receipt roots, bounded logs/time,
no auto retry/overwrite/cleanup. Read ELF interpreter/NEEDED/library closure and
probe receipt at the source pin BEFORE controller/fixture native OS execution.
Actual isolated host controls follow full source/recipe/context review.

| Named gate | Positive and required negative |
| --- | --- |
| test_linux_context.py::test_caps_before_copy | Exact root-owned byte context, UTF8/native ints/IDs; +1/duplicates/traversal/bool/coercion refuse before launch |
| test_linux_controller.py::test_birth_and_credential_barrier | First science marker inside fresh science group after zero-cap distinct credential GO; denied clone/setup and invalid parent have no science marker |
| test_linux_controller.py::test_exited_descendants_accounted | Root/threads/rapid exited descendants and reparented grandchild charged; concurrent busy observer/other job excluded; independent complete wait4 oracle |
| test_linux_controller.py::test_cancel_and_root_exit_descendants | Cancel/EOF and natural root exit with live grandchild stop whole group; no root-only success |
| test_linux_controller.py::test_actual_budget_and_gap | User/system load, equality/above stop, actual next CPU quantum>B, regressing/malformed counter and delayed observer/backpressure fail; preserve max G/A/K |
| test_linux_controller.py::test_manager_three_death_orders | Actual parent/controller/both SIGKILL; PID1 whole-unit extinction, missing final remains unavailable |
| test_linux_controller.py::test_escape_and_cross_attempt | Compute cannot migrate/modify limits/ptrace observer/open control/launch broker; sibling/old unit/ID and wrong credential refuse |
| test_linux_controller.py::test_final_custody_and_resource_failures | Late updates/early/mismatched/lost ACK remain HELD; OOM/output/scratch/write failure preserves original evidence and no publication |
| test_linux_source.py::test_no_fallback_or_activation | Real native call paths, immutable I01 and no app/service/canonical/env edit; no substituted provider, runtime grant or fixture PASS as method acceptance |

Host harness selects only NEW geophysics qualification units/private state and
exact separately reviewed accounts/delegation. Retain original raw observations,
typed times/bytes/hashes, exit/termination failures and source/runtime versions.
Record nominal/upper/malformed/cancel/crash/resource status separately. Missing,
skipped/stale/failed OS gates never admit a platform or scientific method. Full
M01-M13 eligibility, source guards, numerical thresholds and original evidence
are unchanged. No automatic promotion, activation or production edit is performed
by the compile/probe/qualification harness.
