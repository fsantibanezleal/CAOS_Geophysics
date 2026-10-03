# Native physical CPU controller design

Date: 2026-10-03. Status: proposed, FULL MAIN pre-code review required.
Base ba54d32f0932a09502f463f3aff9c8f21270dca1. All native gates NOT_RUN.
Read [research](research.md), [requirements](requirements.md),
[contracts](contracts.md), [validation](validation-plan.md) and [tasks](tasks.md).
Parent [design](../physical-worker-accounting/design.md) and approved pure
[contracts](../physical-accounting-protocol/contracts.md) remain unchanged.

## 1. Scope and precise implementation candidate

This sub-SDD specifies the concrete native isolated controller, not a new
production worker, privileged service, package or universal sandbox. A fixed
single-threaded C17 executable owns science birth, authoritative polling, stop,
drain and retained OS-object custody. A bounded Python bridge uses the existing
pure module unchanged to validate supplied records, serialize/hash evidence and
report consistency. The C observer never delegates its stop timer to Python,
SQLite, a log drain or a network request. No generic callback/native provider.

Exactly proposed NEW implementation paths, requiring later explicit assignment:

```text
scripts/native_physical_cpu/controller.c
scripts/native_physical_cpu/controller.h
scripts/native_physical_cpu/windows_job.c
scripts/native_physical_cpu/linux_cgroup.c
scripts/native_physical_cpu/abi_probe.c
scripts/physical_native_accounting_bridge.py
tests/worker_accounting/native/fixture_cpu.c
tests/worker_accounting/native/test_lifetime.py
tests/worker_accounting/native/test_windows.py
tests/worker_accounting/native/test_linux.py
tests/worker_accounting/native/test_containment.py
tests/worker_accounting/native/test_budget.py
tests/worker_accounting/native/test_lifecycle.py
tests/worker_accounting/native/test_death.py
tests/worker_accounting/native/test_contract.py
tests/worker_accounting/native/test_parent.py
tests/worker_accounting/native/test_bounds.py
tests/worker_accounting/native/test_recovery.py
tests/worker_accounting/native/test_admission.py
tests/worker_accounting/native/test_scope.py
```

These paths are NOT created here. No __init__, build package, dependency,
installed binary or hook. Platform compile selects exactly its native translation
unit; unsupported platform refuses before launch, not a portable polling stub.
No source is approved until MAIN reviews ALL seven docs and separately releases
the actual-context, toolchain/probe and path-assignment holds.

Current app/worker has no bridge call, OS profile or durable acknowledgment.
Standalone fixture controls can validate science-object mechanisms without
claiming integrated admission. Parent CPU/final receipt/recovery closure remain
explicit prerequisites for production, not capabilities supplied by this bridge.

## 2. Fixed bounds, policy and clock

Lane constants MUST come from unchanged pure limits_for, rechecked against
native compiled constants. No submitted smaller/greater override or defaults.

| Bound | Correction | Transform |
| --- | ---: | ---: |
| B aggregate CPU ns | 60000000000 | 240000000000 |
| S stop ns | 57000000000 | 237000000000 |
| Margin ns | 3000000000 | 3000000000 |
| Wall ns including setup/drain | 120000000000 | 300000000000 |
| Science RSS bytes, independent gate | 805306368 | 1610612736 |
| Scratch bytes including all evidence | 268435456 | 536870912 |
| Result bytes | 67108864 | 67108864 |
| Parent CPU ns | 5000000000 | 10000000000 |

One attempt. N<=8 logical CPUs in a fixed domain, process cap32, task/thread
admission cap256. Windows process cap is not an invented hard thread cap.
Observer/controller private-memory cap67108864 bytes, not a measured result here.
G<=20000000 ns complete-observation gap, A<=50000000 ns visibility lag,
K<=250000000 ns request-to-last-contained-CPU, Q<=1000000 ns rounding reserve.
N*(G+A+K)+Q<=M is the candidate margin check (2561000000<=3000000000),
NOT a real-time guarantee. The fixed margin does not enlarge B. Violating
G/A/K/Q/N closes profile and fails; final>B alwaysfails regardless of exit0.

Windows QueryPerformanceFrequency returns positive signed64; QPC ticks must
not regress. For elapsed ns compute quotient/remainder to avoid intermediate
overflow: delta/f*1e9 + ceil((delta%f)*1e9/f), with checked multiplication or
reviewed widened arithmetic. Do not assume MSVC C17 provides __int128. Linux
clock_gettime(CLOCK_MONOTONIC) returns0; tv_sec nonnegative, tv_nsec0..999999999,
check seconds before multiplying1e9. Clock offsets share one controller origin.
Monotonic time measures supervision, not science CPU. Timer jitter is measured
and checked after every wake/query; setting a20 ms timer is not evidence of G.

## 3. Native lifecycle and trusted endpoints

```text
CLOSED -> PREPARED -> CONTAINED_NO_SCIENCE -> RUNNING
RUNNING -> STOP_REQUESTED -> DRAINED
RUNNING -> DRAINED (whole-object natural exit)
DRAINED -> FINAL_NATIVE -> RECEIPT_BOUND -> DURABLE_ACK -> RELEASED
any uncertainty -> FAILED_HELD (absorbing admission, preserve custody/debt)
```

Bridge PREPARED is not native containment. Native custody assertions are
converted to pure assert_contained/started only AFTER real gates pass. Linux
fixed native child setup may execute inside the object before GO; science
interpreter/imports cannot. Windows first thread stays suspended until checks.
The observer remains independent during a slow bridge or durable flush.

Native launch input is a private fixed wire record and owned OS endpoints, not
untrusted paths/PIDs/handles from API callers. Reviewed context determines an
explicit immutable interpreter, code/input/runtime closure, argv, minimal env,
credential rights and exclusive stage. Source paths are not a client-selectable
launch facility. ACL/credential immutability and fixed-open identities must cover
the interval from hashing to execution; rehash alone cannot close a mutation race.
No PATH, shell, fetch, installation, user executable or .git global trust.

Control heartbeat<=100 ms, grace500 ms; EOF immediate stop. Every sequence/ID
binds one attempt. Bounded native reads/writes run in the same observation loop.
Windows uses private overlapped named pipes and an explicitly limited HANDLE_LIST;
Linux nonblocking pipes plus poll with deadline. A bounded pending frame is not
an unbounded queue. Output/read readiness never substitutes for the timer.
Backpressure, queue overflow or invalid frames stop the object. A dropped sample
means no complete receipt, not silently repaired counters.

## 4. Windows concrete call order, types and errors

Research N06-N11/N16/N20/N21/N24 is the official API basis. Required x64 native
Windows10+/Server2016+ API floor is not context admission. Unknown build,
architecture, ancestry, token/DACL or broker permissions closes the route.

1. CreateJobObjectW(noninheritable explicit SECURITY_ATTRIBUTES,NULL) returns
   new unnamed HANDLE, NULL means failure. Job rights and controller process
   DACL must prevent compute acquisition/duplication/mutation; no default proof.
2. SetInformationJobObject(class9, exact SDK extended limits) sets JOB_TIME0x4,
   ACTIVE_PROCESS0x8, AFFINITY0x10, KILL_ON_JOB_CLOSE0x2000. Process count32,
   PerJobUserTimeLimit=S/100 (570000000/2370000000 ticks), fixed <=8 CPU mask
   in one processor group. BREAKAWAY0x800/SILENT_BREAKAWAY0x1000 forbidden.
   Set JOB_TIME ONCE on the empty job; no update adds existing elapsed credit.
   Set/read back JobObjectEndOfJobTimeInformation class6 with EndOfJobTimeAction
   JOB_OBJECT_TERMINATE_AT_END_OF_JOB=0; notification-only behavior rejects.
   Read back class9 exactly. Reject an incompatible/unknown inherited job chain.
   User-time termination remains a secondary guard, NOT aggregate enforcement.
3. InitializeProcThreadAttributeList(NULL,2,0,&SIZE_T) must fail with
   ERROR_INSUFFICIENT_BUFFER and bounded size1..65536. Initialize aligned
   allocated buffer; UpdateProcThreadAttribute JOB_LIST with HANDLE[1], and
   HANDLE_LIST only fixed child stdin/stdout/stderr handles. Values live until
   DeleteProcThreadAttributeList; job handle absent from child inheritance list.
4. CreateProcessW uses explicit pinned absolute application, bounded mutable
   UTF16 fixed command/environment and private cwd, STARTUPINFOEXW, explicit
   process/thread security, STARTF_USESTDHANDLES. Flags CREATE_SUSPENDED,
   EXTENDED_STARTUPINFO_PRESENT, CREATE_UNICODE_ENVIRONMENT, CREATE_NO_WINDOW.
   bInheritHandles=TRUE only with declared list. No BREAKAWAY/alternate parent.
   BOOL0 failure captures GetLastError immediately, no resume or alternate launch.
5. IsProcessInJob(owned process,exact job,&BOOL) must return success/TRUE.
   Verify class9 policies, empty-before-birth evidence and initial class1 query.
   ResumeThread must return previous count1; DWORD -1 or any other value fails
   and terminates exact job/root without permitting science as a test.
6. QueryInformationJobObject(class1) requires exact returned DWORD byte length,
   nonnegative signed64 user/kernel totals and sane DWORD process counts.
   Charge checked(user+kernel)*100 into int64 ns. Keep cumulative totals;
   ThisPeriod and TotalTerminatedProcesses cannot stand for all lifetime exits.
7. On stop, TerminateJobObject with fixed private status; require BOOL success,
   query ActiveProcesses until0 and bounded WaitForSingleObject slices on owned
   root; GetExitCodeProcess after signaled termination, unsigned32 exit value.
   Exit code259 alone is ambiguous, not proof of liveness. Notification/job wait
   cannot replace whole-object emptiness. Close ended process handles as needed
   for process-limit accounting while retaining the job. Repeat final queries.
8. Keep final job through matched durable ack. Close owned handles once;
   never reopen by public name. On observer death sole last-handle close must
   actually kill all compute, proven by independent real controls.

Native ABI uses SDK, no #pragma pack: HANDLE/SIZE_T/ULONG_PTR8, DWORD/BOOL4,
LARGE_INTEGER8. Proposed sizeof: basic accounting48, basic limits64,
extended limits144, STARTUPINFOW104, STARTUPINFOEXW112, PROCESS_INFORMATION24.
Probe every used offsetof (including totals0/8, process counts36/40/44), alignment,
calling convention and GetLastError lifetime against SDK10.0.22621.0. These
numbers are expected targets, not actual compilation evidence.

Child process creation normally inherits the non-breakaway job, but WMI/COM/
service/task brokers can create work elsewhere. Same-user PROCESS_DUP_HANDLE,
writeable parent policies or external broker access is an admission failure.
No restricted token/AppContainer policy is invented here. A future security
unit must supply the actual effective context if existing rights do not suffice.
Non-breakaway nested jobs require actual aggregation/ancestry proof, not a label.

## 5. Linux concrete call order, types and errors

No VPS inspection. Linux x86_64 native unified domain cgroup2, clone3,
INTO_CGROUP/PIDFD/cgroup.kill and concrete retained delegation identity required.
No v1/hybrid/threaded/container guess. Linux headers/compiler/libc remain unpinned
until MAIN supplies read-only inventory; v6.12 sched.h is research only.

1. Existing authorized context must separate controller/compute UID/GID,
   capabilities and all migration/control/broker access. It must already permit
   credential transition and exact manager-death kill. Missing context refuses;
   no sudo, new service, delegation edit, remount or setuid install is selected.
2. openat anchored O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC, fstat/fstatfs and ancestry
   validate admitted parent device/inode/mount and cgroup2 magic0x63677270.
   mkdirat0700 creates exclusive internally named attempt domain, retain its FD;
   confirm cgroup.type=domain, populated0, fresh CPU0. Controller stays outside.
   Never use shared service counter or reused group. Host parent controls are
   preexisting; only exact newly owned object limits may be set after authority.
3. Fixed SCHED_OTHER, affinity<=8, read-back cpu.max100000/100000 usec,
   approved exact cpu.max.burst0 registry, pids.max256; memory/scratch policies
   remain independent. cpu.max, pids.max and memory.max do not certify RSS/CPU
   lifetime. Unknown/denied files keep CLOSED, no best-effort substitutions.
4. Before launch prctl(PR_SET_CHILD_SUBREAPER,1L). Zero-init struct clone_args
   eleven aligned u64 fields,88 bytes at the proposed ABI. syscall(SYS_clone3)
   flags CLONE_INTO_CGROUP|CLONE_PIDFD, exit_signalSIGCHLD, cgroup=owned fd,
   pidfd points to int output; other fields0, no CLONE_VM/THREAD/FILES/PARENT.
   Return>0 parent,0 child,-1 captured errno. ENOSYS/EPERM/EINVAL/EACCES/EBUSY/
   EOPNOTSUPP refuse, no fork+move/Popen/preexec fallback. No hardcoded syscall
   number from another architecture; compile against reviewed UAPI headers.
5. Child born accounted runs fixed native setup only. Close all cgroup/control
   authority FDs; retain exact data/stdio/GO/setup endpoints. Under authorized
   context setgroups0, setresgid/resuid allIDs, verify IDs/fsIDs and zero
   effective/permitted/inheritable/ambient caps (capget/capset version3).
   PR_SET_NO_NEW_PRIVS1, PR_SET_DUMPABLE0; set PDEATHSIG SIGKILL AFTER credential
   changes, recheck expected parent to close race. Failure _exit, bounded errno.
   Setup-ready/GO handshake precedes execve pinned interpreter/argv/env.
   No hidden helper child/thread or science import before GO. Child execution
   from birth to exit, including setup/JIT, enters science charge.
6. Bounded openat/read cpu.stat <=4096 bytes+EOF probe, known exact profile
   keys only. Preserve required usage/user/system once each as uint64 decimal,
   check user+system before summing, then max and *1000 into int64 ns.
   cgroup.events populated is recursive live-state evidence; zombies absent
   from process listings still require reaping. Poll events only wake the loop.
7. Stop writes exactly1 plus LF to retained cgroup.kill, require full write.
   Read populated0, waitid(P_PIDFD,owned fd,WEXITED|WNOHANG) root identity,
   waitpid(-1,WNOHANG) solely owned adopted children; explicitly process EINTR,
   ECHILD and actual statuses. Reap and account exits. No PID-number kill sweep.
8. Final stats from retained same object three times, then durable ack before
   unlinkat exact empty created directory AT_REMOVEDIR. No recursive deletion.
   Worker-held exact kill custody and existing manager cover controller/both
   death; PDEATHSIG/subreaping alone cannot kill all grandchildren. Unknown
   survival/inode/ack means retain HELD for operator, never automatic adoption.

## 6. Final counters, parent tails, durability and recovery

After whole-object emptiness/root+owned exit proof, three identical component
counter samples at least20 ms apart within2 s. Require no native regressions,
no missed active period, valid previous trace, strict units and known exit code.
Natural root exit with a surviving child is unexpected_descendants, stop/fail.
Drained final CPU betweenS andB may be consistent only absent earlier failed
running observation; final>B is alwaysfailed. Finite settling is evidence for
that profile, not a vendor guarantee. Timed-out drain remains live/unknown HELD.

Science object total excludes API/controller/bridge/publication. Windows owned
GetProcessTimes post-exit preserves controller lifetime; Linux wait4 on an
owned exited controller provides rusage, independently compared to SELF samples.
Persistent worker baseline delta measures attempt overhead only if unrelated
work cannot enter it. Final SELF report, last CPU poll or shutdown estimate
cannot include the reporter's later flush/exit/publication CPU. The unchanged
pure RELEASE checks a supplied sum, not authenticity or that missing tail.

H04 is deliberately unresolved for production: MAIN must approve exact worker
attempt boundary, exit-tail observer and durable release custody in a separate
integration unit. An independent finite-fixture harness can measure after both
fixture processes exit, but is NOT an existing runtime provider/supervisor.
Native unit must not emit a production complete-release claim while H04/H05
are closed, even if its science counter and pure transcript are consistent.

If matched durable ack does not arrive within2 s of receipt bind or the earlier
wall/parent limit, latch HELD and block subsequent admission. Do not busy-wait,
reset final counters or deliberately emit successful RELEASED. Actual failed
shutdown/death may destroy a Windows job handle despite lost receipt custody;
record that loss as unavailable/held, not a violation repaired by fabrication.
Linux retained empty groups are operator-owned liabilities, never automatically
removed on timeout. Stop/live uncertainty invokes exact backstop/operator custody.

Private receipt bytes canonical under unchanged pure contract (<=16384 ingress;
65536 storage ceiling). Exclusive no-follow/reparse-denied new file, bounded
write then FlushFileBuffers or fsync; POSIX parent directory fsync required.
Windows directory/rename/reparse durability must have exact filesystem evidence;
file flush alone cannot assert it. The storage owner specifies durable attempt,
receipt SHA and ack identity BEFORE object destruction, with uncertain commit
reconciliation rather than retry-as-success. No file+SQLite transaction invented.

Current0003 and gravity/MT inventory accepts only known exact runtime schemas.
New receipts/stages/DDL revisions must FAIL current ops gates. Separate storage
and explicit modality/revision adapter design precede integration; no wildcard,
source-manifest extension or unknown child restore. Backup requires all writers
stopped and no unresolved stage/control debt. Latest durable deletion authority
still wins over any old snapshot; restore only to NEW target. Operator review/
exact quarantine remains required for preserved crash stages, not unattended
worker reconciliation. This unit cannot clear any quota/deletion/cleanup debt.

## 7. Later build/ABI recipe, not authorized to execute

Windows proposed native build uses the inspected MSVC/SDK only after explicit
compile/probe approval, with fully resolved compiler/linker/include/lib paths
and a NEW private output root. Flags: /nologo /std:c17 /W4 /WX /sdl /guard:cf
/DUNICODE /D_UNICODE /D_WIN32_WINNT=0x0A00 /MD; linker /Brepro /DYNAMICBASE
/NXCOMPAT /HIGHENTROPYVA /guard:cf /INCREMENTAL:NO /OPT:REF /OPT:ICF.
The CRT DLL closure, import libraries and SDK headers need exact SHA inventory;
cl.exe file hash alone does not prove a runnable or reproducible native build.
ABI probe and fixture are separate binaries, never linked into production.

Linux proposed C17 flags -std=c17 -Wall -Wextra -Werror -Wconversion
-Wshadow -fstack-protector-strong -D_FORTIFY_SOURCE=2 -O2 with PIE/RELRO/NOW
and no dependency downloads. Compiler/linker/sysroot/libc/kernel header version
and exact bytes are UNSET until MAIN supplies read-only inventory. GCC/Clang
version cannot be guessed; unsupported options/toolchain remain CLOSED.
Record every input/command and resulting binary hash before any actual launch.
Debug/fault-injection build never admits a profile; release hashes separate.
No commands in this section were executed, no output root created or files built.

## 8. Risks and kill criteria

No platform becomes admitted by OS version, SDK presence, ABI pass, mocked unit
return, 419 pure tests, local scientific gates or docs merge. No host/production
action; MAIN's reported headroom failure and30% gate are unchanged, not remeasured.
No arbitrary code sandbox, physics certification, source-byte ceiling admission,
RSS proof, zero overshoot or final-counter availability after abrupt death claim.

Stop promotion on pre-containment science marker, exited CPU omission, escape,
mutable identity, wrong units, unknown native record, observation/backpressure
stall, root-only completion, early release, unavailable=0, CPU>B accepted,
parent tail omitted, stale/double ack or unknown recovery variant. If a dangerous
actual control cannot be bounded safely, record NOT_RUN/CLOSED, not PASS.
