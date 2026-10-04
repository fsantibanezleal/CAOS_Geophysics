# Native worker operations, following measured I01 ABI

This is the executable-controller design supplement to [design](design.md),
[contracts](contracts.md), [requirements](requirements.md) and
[validation](validation-plan.md). It defines real kernel-operation work, not a
second supplied-data facade. The deterministic core remains a separate unit.
No application-facing profile or production admission is supplied by this file.

The independently compiled I01 SDK probe measured all 47 emitted x64 layout
checks successfully: accounting48, basic limits64, extended limits144,
STARTUPINFOW104, STARTUPINFOEXW112 and PROCESS_INFORMATION24 bytes, with the
specified alignments/offsets. The exact three-file compiled arithmetic/state
suite passed179 with zero skips. [Measured evidence](../../../validation/native-i01-abi-pure-20261004.json)
binds the original source/artifact/stream/XML digests and all47 layout rows.
Those facts establish neither actual Job Object
behavior nor Linux ABI/credential/delegation behavior. Historical pre-execution
inventory statements remain historical; they do not override these measurements.

## 1. Implementation unit and exclusions

Keep controller.h/c, abi_probe.c and their I01 artifacts unchanged. Implement the
existing proposed `windows_job.c`, `linux_cgroup.c` and
`physical_native_accounting_bridge.py` paths; add a separate
`scripts/native_physical_cpu/worker_main.c` and `worker_operations.h`. These are
ordinary executable sources, not a package, injectable provider or installation.
The Windows and Linux translation units each implement the same private native
operation interface. Only the selected platform unit is linked. The main loop
owns clocks, observation cadence, nonblocking transport, stop and final custody.
The bridge owns strict bounded canonical evidence and never decides native CPU
by polling the science PID. Missing platform support fails before science birth.

Do not put platform calls into the pure controller.h/c or weaken its checked
arithmetic/state rules. Do not link the ABI probe, fault-injection controls or
authored fixture into the operational executable. No compiler discovery, build
inside a test, shell, plugin/callback registry, installation or fallback process
launcher. Tests receive exact reviewed executable paths and hashes. Existing
application/MT launch, database/API and receipt schemas remain unchanged until
their distinct integration review; none is silently claimed to call this runner.

The concrete application seams are `_execute`, `_command`, `_mt_command` and
`_terminate_tree` in app/worker.py. Today they use Popen and live-process psutil
enumeration, not this controller. Replacing their launch/termination functions
requires a separately reviewed integration diff: project/job/principal identity,
dataset/request/raw-byte pins, result verification, cancellation, reservations,
publication and existing M01 behavior must all remain intact. CPU lane constants
apply only to their exact correction/transform identities, not by relabelling MT.

## 2. Private operation interface and state

The platform unit owns retained object/root identities in caller-owned fixed
storage. No raw object, handle, PID or path goes onto the public result wire.

| Operation | Concrete responsibility | Failure custody |
| --- | --- | --- |
| prepare | Create exclusive native object; set/read back limits; establish clock origin and owned endpoints | No science; preserve created object and partial evidence |
| birth | Create root already assigned to object, still suspended or awaiting GO | Never start outside object; retain partly created root |
| start | Verify object membership/setup and release exactly one start barrier | Failed verification stops whole object; no second launch |
| observe | Native cumulative components, recursive live state, owned root exit state, query start/end | Invalid/unavailable is an error, never a zero sample |
| stop | Request whole-object termination exactly once with retained authority | Preserve first failed verdict and request timestamp |
| drain | Repeated whole-object emptiness and owned exit/reap proof | Timeout remains live/unknown HELD, not a release |
| final | Actual empty state plus three equal component reads after >=50ms settle | Preserve late changes, no tolerance repair |
| release | Destroy exact empty object only after trusted matched durable custody | No implicit ACK, cleanup-on-error or named-object reopening |

Operation errors retain an internal numeric native error immediately, plus the
fixed safe enum. Only fixed safe code/message crosses a public boundary. No
exception/context/path/stderr values become API messages. Outputs are unchanged
on an invalid native observation; there is no saturation or best-effort success.

The native main loop applies every observed event through the existing checked
core, while retaining the actual raw native components. Core acceptance is a
second consistency check, never authority to assert an unmeasured native event.
The bridge independently runs the unchanged pure decoder/session on canonical
records. Binary sequences and pure channel sequences remain distinct.

## 3. Windows kernel operations and build boundary

Use the measured SDK types directly. Fresh unnamed noninheritable Job Object;
explicit reviewed security attributes, no guessed default-DACL protection.
Set JOB_TIME once, ACTIVE_PROCESS32, fixed affinity domain <=8 CPUs and
KILL_ON_JOB_CLOSE, with both breakaway flags absent. Set/read terminate end-action0
and read back exact limits before birth. Committed-memory limits, if selected by
the resource unit, are labelled committed memory, never RSS.

Birth uses two attributes: JOB_LIST containing the retained job and HANDLE_LIST
containing only the three declared child stdio endpoints. Attribute values and
aligned bounded allocation remain live through deletion. CreateProcessW receives
an explicit immutable application, bounded mutable UTF16 argv/environment,
private cwd, STARTUPINFOEXW, CREATE_SUSPENDED and no breakaway. bInheritHandles is
TRUE only for that handle list; no job/control/receipt handle enters it.
Verify IsProcessInJob, readback limits and initial accounting before ResumeThread;
only previous suspend-count1 is acceptable. Any failure terminates the exact
job/root; it never permits a running assignment or alternate launch.
This call order follows Microsoft's [attribute-list contract](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute).

Every query uses class1, exact returned length and checked nonnegative signed64
TotalUserTime/TotalKernelTime; charge checked(user+kernel)*100ns. Keep the job
after root exit, because lifetime descendants include terminated associated
processes. Root completion with ActiveProcesses>0 is unexpected descendants:
stop/fail, not clean completion. TerminateJobObject must return success; finality
requires ActiveProcesses0 plus owned root signalled/exit-code evidence, not job
notification, root wait alone or exit-code259. Final queries keep the same handle.

Build the actual runner as a standalone /MD executable under design section7,
not a DLL loaded into the pipeline interpreter. I01 /MT approval does not extend
to this runner. This avoids assuming which of the three different VC runtime
versions a Python DLL load selects; it does not prove standalone loaded closure.
Exact source/header/include/link/import/runtime inventory and a fresh private
recipe/output are required before compiling/running the new executable. The
I01 artifacts must not be rebuilt or reused as a platform runner. ABI layouts
are reusable facts, but APIs not exercised by the probe remain unmeasured.

Actual effective token, controller/job DACLs, nested ancestor jobs, compute
duplication/signal/broker rights and last-handle death behavior must be recorded.
Same-user immutable scientific code is not proof that hostile inputs cannot
reach an escape through native libraries. No asserted security flag in START
substitutes for those actual controls.

## 4. Linux kernel operations and build boundary

Linux is a separate native build/ABI/context lane, not arithmetic success on
Windows. Use actual reviewed Linux headers and SYS constants; no hardcoded
syscall numbers, guessed libc layouts or toolchain/version fallback.

Anchor the admitted pre-existing delegated parent using no-follow directory FDs,
fstat/fstatfs/mount identity. mkdirat creates exactly one new private attempt
domain; retain its directory FD and opened native endpoints. Require domain
cgroup2, initial populated0 and fresh CPU0. Controller stays outside science.
Set/read back cpu.max100000/100000, cpu.max.burst0 and pids.max256 in that newly
owned domain only. None is a lifetime CPU credit or an RSS guarantee. Memory and
scratch have separate enforcement/evidence. Unknown native keys/files refuse.

Birth calls clone3 with INTO_CGROUP and PIDFD, SIGCHLD and the retained FD;
no fork-then-migrate/Popen/preexec fallback. Child executes only fixed native
setup inside the object before GO: close authority FDs, apply reviewed distinct
UID/GID/capability transition, verify IDs/caps, no_new_privs, nondumpable and
parent-death signal after credential changes. Recheck parent identity. Setup
failure exits without scientific imports; setup-ready/GO precedes execve.
The [clone3 contract](https://man7.org/linux/man-pages/man2/clone.2.html) and
[cgroup2 semantics](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html)
are source requirements, not proof that a host supports/delegates them.

Read cpu.stat <=4096 bytes plus bounded EOF probe, exact keys/numeric grammar;
preserve usage/user/system and charge checked max(usage,user+system)*1000ns.
Read recursive populated state separately. Stop writes exactly1 plus LF to the
retained cgroup.kill endpoint. Drain requires populated0, owned PIDFD exit and
reaping all owned adopted exits. Subreaping and root PDEATHSIG are not a
grandchild/simultaneous-death backstop. Actual existing manager authority and
credential denial are required; no new service/delegation/sudo operation is
hidden in the implementation. Keep same domain for final reads and matched
durable custody; release uses exact empty unlinkat, never recursive deletion.

If actual compiler/UAPI/libc/delegation/credentials/manager proof is unavailable,
record that precise lane NOT_RUN/CLOSED. Do not port Windows receipts to Linux,
install a toolchain, weaken clone3 birth, or use live-PID CPU as its substitute.

## 5. Real controller loop, resources and exit tails

One single-threaded native loop, fixed working buffers and pending queue4. Native
queries precede bounded I/O work on every wake; no blocking Python serialization,
SQLite flush, network or stdout drain can postpone the independent stop timer.
Windows uses overlapped private pipe operations; Linux nonblocking FDs and poll.
Each pass has a monotonic deadline, byte/operation work quota and a counter query
after I/O. Partial frames retain at most64+4096 bytes; oversize is rejected before
allocation/copy. A full output queue is a failed supervision observation, not a
dropped sample. Finish whole-object stop even if the bridge no longer reads.

G is actual complete-observation gap including query/dispatch time, not a20ms
sleep setting. At CPU>=S, bad query/components, elapsed wall ceiling, observation
gap, EOF, cancellation, heartbeat grace loss or resource failure: latch failure,
request native whole-object stop and retain offending evidence. Three equal
final reads begin no earlier than drain+50ms, >=20ms apart, all within2s; verify
emptiness throughout. Final CPU>B always fails at native resolution with no
blanket float/rounding allowance. Keep the frozen margin and process/topology
limits; ordinary scheduling is not a real-time no-overshoot guarantee.

Source/input buffers, stdout/stderr65536 each, sample32768/16MiB, private receipt
65536 and result64MiB are checked before allocation/emission. All evidence/log/
cache bytes count against scratch. RSS is measured separately from commit/
memory.max. Monitoring a directory is not a filesystem quota: actual scratch
allocation/identity/link/error controls must be measured and reviewed. No
whole-buffer input expansion or unbounded filesystem walk enters the observer.

The outer worker measures the exited controller with retained Windows process
handle or Linux wait4. The persistent worker's post-result/hash/DB/flush CPU tail
requires a distinct boundary/observer; a preliminary SELF value cannot include
its own later publication work. The bridge must not synthesize that parent
closure. No production RELEASED/publication until complete parent budget and
durable intent/ack/release integration pass. Backup/SMTP are not substitute gates
for the actual operations in this unit; no arbitrary disk-percentage threshold
is imposed here. Actual write/allocation failures remain failures.

## 6. Required executable tests and review packet

Retain I01179 and ABI47 as exact historical measured evidence. New tests are
test-first and native-platform separately, at the paths already in design:

| Test unit | Required measured behavior |
| --- | --- |
| test_windows.py | Creation-bound job, suspended first marker, exact limits and every failed pre-resume call; no breakaway fallback |
| test_linux.py | Actual domain birth/PIDFD/setup/GO and each denied syscall/native record; no migrate fallback |
| test_lifetime.py | Rapid exited descendants/threads included; concurrent controller/API excluded by independent post-exit oracle |
| test_budget.py | CPU equality/above stop, system-heavy load, actual native-quantum final>B, query delay/regression and measured G/A/K/Q |
| test_lifecycle.py | Cancel/EOF/backpressure/natural root exit with live child, bounded whole-object drain, settle/read/ack custody |
| test_containment.py and test_death.py | Real migration/handle/broker denial plus worker/controller/both-death orders, no root-only certification |
| test_parent.py and test_recovery.py | Full exit/write/publication tails and storage-owned crash matrix; no fake durable acknowledgment |
| test_admission.py | One missing/stale/skipped/unsafe native control keeps that platform CLOSED |

Freeze every actual source, test, context, tool/library/header and resulting
binary hash before native execution. Preserve failure streams and original
typed telemetry, with explicit measured versus configured bounds. Independent
review includes full source/call-order/error cleanup and actual import closure.
No claimed Git SHA replaces file identity; no I01 PASS approves platform gates.
There is no source/OS/worker integration completion or deployment claim here.
