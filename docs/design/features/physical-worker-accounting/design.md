# Physical worker accounting design

Date: 2026-10-03. Status: PROPOSED, awaiting FULL MAIN approval.
Implementation, actual OS controls and platform admission: NOT_RUN/CLOSED.
Base `7e26d253ac7d3a3688cb6263f669a747681aa077`; research precedes this design.
See [requirements](requirements.md), [contracts](contracts.md),
[validation](validation-plan.md), [tasks](tasks.md) and
[research with primary receipts](../../../research/physical-worker-accounting-2026-10-03.md).

## 1. Problem, trust boundary and precise decision

Resolve physical-vertical review gap 8: select an authoritative per-attempt
lifetime CPU source and a launch/containment/termination protocol. Do not infer
an actual enforcement capability from library documentation or live-PID polling.
The selected sources are Windows Job Object cumulative TotalUserTime plus
TotalKernelTime and Linux retained fresh cgroup2 cpu.stat. Scientific imports,
JIT, replay, threads and associated exited descendants are charged. Controller,
API, hashing and publication CPU are outside this science object and separately
bounded, not subtracted from a shared service measurement.

The future component is a fixed native, single-threaded launch/controller
executable invoked by the worker, not an installed package, plugin, shell, new
daemon or an imaginary external provider. It does not exist in this docs unit.
It needs native lifecycle calls before interpreter execution; a Python preexec
callback in a multithreaded worker is not selected. MAIN must assign its future
implementation/review owner and approve its launch privilege/context first.
No privilege is granted to the API, worker or scientific interpreter here.

Threat domain: immutable reviewed scientific code and runtime, strict data-only
inputs, hostile/malformed input bytes, accidental forks/threads and child crashes.
Not arbitrary executable uploads, malicious replacement native libraries,
host administrator/kernel compromise or a universal security sandbox. Even in
this domain, reachable process-creation brokers, mutable cgroup permissions or
job policies are a failed containment gate. A broker performing work elsewhere
cannot be made accounted merely by calling it a descendant. No broad no-escape
claim is permitted outside the explicitly tested domain.

Selected policy is monitored aggregate enforcement with an early threshold and
strict final admission. It is NOT a mathematically instantaneous kernel hard cap
on user+system CPU. Neither cpu.max nor Windows PerJobUserTimeLimit proves that
stronger property. If MAIN requires zero overshoot for all failures, do not
activate this proposal: research a different mechanism under a new approval.
The physical wording "hard ceiling" needs this explicit qualification before
integration, not an undocumented polling fallback. Final CPU exceeding the
ceiling is always a failed attempt and a closed profile, never accepted output.

## 2. Provisional budgets and enforcement margin

All values below are proposals to review, not measured runtime admission. Existing
global 2 GiB worker memory, 1 GiB scratch and 600 s wall caps remain upper bounds.

| Quantity | Correction | Transform |
| --- | ---: | ---: |
| Combined science CPU ceiling B (ns) | 60000000000 | 240000000000 |
| Stop threshold S (ns) | 57000000000 | 237000000000 |
| Reserved enforcement margin M (ns) | 3000000000 | 3000000000 |
| Wall from before launch, including setup/drain | 120 s | 300 s |
| Aggregate RSS ceiling (separate gate) | 805306368 bytes | 1610612736 bytes |
| Private scratch including output/log/cache | 268435456 bytes | 536870912 bytes |
| Complete result envelope | 67108864 bytes | 67108864 bytes |
| Controller plus worker publication CPU | 5 s | 10 s |

One job attempt at a time. At most eight available logical CPUs in one Windows
processor group or one fixed Linux affinity domain; changing hotplug/affinity
invalidates profile identity. This is a conservative profile admission bound,
not an observation about the actual host. Scientific thread environment remains
one, but is not proof of an OS parallelism bound. Finite normal fixtures allow
up to 32 contained processes and 256 threads/tasks under separately validated
platform controls; a process cap is not a thread or RSS proof. Windows has no
thread-count hard cap selected by these Job Object flags; the proposed 256-thread
bound is an independent admission/monitoring gate, not an invented job limit.

Prospective monitoring caps: complete successful-counter observation gap G at
most 20 ms (including scheduling delay and query duration); bounded accounting
visibility lag A at most 50 ms; request-to-last-contained-CPU kill interval K at
most 250 ms; rounding reserve Q at most 1 ms aggregate. The candidate inequality
is N*(G+A+K)+Q <= M: for N=8 it is 2561 ms <= 3000 ms. These are REQUIRED admission
facts, not vendor guarantees or values measured here. The reserved margin lowers
usable science CPU; it does not increase B. Source/OS counter behavior and an
independent oracle must substantiate A and Q, not infer them from sample p95.

Ordinary non-real-time scheduling can violate a finite observation/kill bound;
stress measurements alone do not prove an absolute bound. MAIN must review the
monitored contract and residual risk separately from a hard-kernel contract.
Actual profile remains unset/CLOSED until every bound is supported and measured.
If a run violates G/A/K, cannot establish N, or finishes above B, terminate,
fail, close admission and preserve evidence even if numerical output is valid.
If stop cannot be completed, retain unknown/live state and request operator
recovery; never pretend a timeout made processes disappear. Linux uninterruptible
tasks and Windows delayed termination are explicit kill-latency failure controls.

Wall, RSS, scratch and byte bounds remain independent. Windows job-wide committed
memory and Linux memory.max are not interchangeable measurements of RSS. This
CPU unit does not certify existing memory/scratch enforcement. The proposed
physical 512 MiB server source ceiling is provisional and device profiles remain
unset/CLOSED; whole-buffer or unzip-then-check processing is not admitted here.

## 3. Lifecycle and proposed worker interface

```text
UNADMITTED -> PREPARED -> CONTAINED_NOT_EXECUTING -> RUNNING
                                      RUNNING -> STOPPING -> DRAINED
                                      RUNNING -> DRAINED (clean whole-object exit)
DRAINED -> COUNTERS_FINAL -> PRIVATE_RECEIPT_DURABLE -> RELEASED
any uncertainty -> FAILED_HELD (no publication, no next attempt)
```

One immutable attempt UUID binds fixed job/input/request/module/runtime/profile
digests and the exclusive stage identity. Existing job schemas/API are unchanged.
The future worker supplies one bounded start frame, then cancellation or heartbeat
frames over a private pipe. Heartbeat interval at most 100 ms; loss grace 500 ms,
with immediate stop on EOF. Controller owns OS object, output pipe drains and
nonblocking counter schedule; it does not wait for API/SQLite to poll CPU.
The worker owns stage reservations and separately reviewed durable publication.

Launch preparation verifies all digests, limits, environment, controlled fixed
argv, explicit interpreter/runtime files and profile. No PATH lookup, command
shell, user-selected modules, inherited control handles, network fetch, install
or secret-bearing environment. Runtime and input reads are bounded; source files
are immutable against the admitted compute credential. Native child setup is
charged from accounting-object birth; launcher work before birth is controller
overhead. OS creation work outside the accounting domain is not attributed as
science CPU by invention; the actual-platform oracle establishes the boundary.

Science only begins after containment and setup admission. After launch, compare
integer authoritative counters to S every bounded observation. Stop on equality
or greater, or any closed gate. A root exit with surviving descendants is not
success: kill, drain and record unexpected descendants. Keep the OS object
alive through final-counter validation and durable private receipt acknowledgment.
Release of a counter object is NOT release of file/DB quota or publication intent.

Observer clock calls are exact: Linux clock_gettime(CLOCK_MONOTONIC,&timespec),
return 0, checked tv_sec*1000000000+tv_nsec with tv_nsec in [0,999999999];
Windows QueryPerformanceFrequency(&LARGE_INTEGER) once with positive frequency,
then QueryPerformanceCounter(&LARGE_INTEGER), checked delta_ticks*1000000000 /
frequency. Use widened intermediate arithmetic, retain native clock ticks and
round conservatively when testing elapsed-time caps. No UTC wall clock or
process-CPU clock is substituted. The clock measures observer delays, not science
CPU. Clock regression, invalid frequency or conversion overflow closes admission.

Parent overhead oracle: GetProcessTimes on owned Windows worker/controller
process handles, reconstruct each FILETIME (DWORD high/low) as uint64 100-ns
user+kernel ticks; Linux getrusage(RUSAGE_SELF,&rusage) in worker and controller,
checked ru_utime/ru_stime timeval seconds/usec to ns. Compute worker per-attempt
delta plus controller lifetime SELF CPU, without RUSAGE_CHILDREN (which would
include and double-count science). Single controller has no other helper child.
Worker measures all pre/post hashing/serialization/receipt/release overhead; a
lost controller report is unavailable, not zero. Preliminary sealed-receipt
overhead is followed by a bounded release acknowledgment; no publication
eligibility until final parent budget and exact release acknowledgment pass.

## 4. Windows exact OS route

Primary references P11-P23 and P26-P28 in the [research receipts](../../../research/physical-worker-accounting-2026-10-03.md).
Proposed support: 64-bit Windows 10 or later / Server 2016 or later, native x64
process ABI. Those documented JOB_LIST minima are necessary, not sufficient.
Any unknown architecture/build, compatibility layer, job chain or API failure
closes Windows admission. No WSL route presented as Windows equivalence.

### Calls, layouts and control rights

1. CreateJobObjectW(checked noninheritable SECURITY_ATTRIBUTES, NULL name) ->
   HANDLE. Require new unnamed exclusive object; no OpenJobObject/reused object.
   Explicit security policy must deny compute mutation/duplication of controller
   handles; default ACL alone is not a no-escape proof. Controller needs QUERY,
   SET_ATTRIBUTES, TERMINATE and ASSIGN_PROCESS; never pass its handle to child.
2. SetInformationJobObject(handle, JobObjectExtendedLimitInformation=9,
   JOBOBJECT_EXTENDED_LIMIT_INFORMATION, sizeof) -> BOOL. Required flags include
   KILL_ON_JOB_CLOSE=0x2000 and ACTIVE_PROCESS=0x8, count=32; neither
   BREAKAWAY_OK=0x800 nor SILENT_BREAKAWAY_OK=0x1000 may be set. An optional
   JOB_TIME=0x4 user-only backstop is set once on an empty job to S/100 ticks,
   read back and explicitly labelled user-only. It never replaces total CPU.
3. QueryInformationJobObject(handle, class=9) verifies exact limits and ancestor
   compatibility before creation and before resume. Unknown ancestor jobs or
   mutable outer policies are closed, not bypassed with breakaway.
4. InitializeProcThreadAttributeList(NULL, count=2, flags=0, &SIZE_T) performs
   expected sizing failure; require bounded positive size <=65536 bytes and the
   documented sizing result. Allocate aligned buffer; second initialized call
   must succeed. UpdateProcThreadAttribute(flags=0, JOB_LIST, HANDLE[1],
   sizeof(HANDLE), NULL, NULL) selects the exclusive job. A second HANDLE_LIST
   contains only fixed stdin/stdout/stderr private-pipe handles. Keep attribute
   values/buffers alive until process creation and DeleteProcThreadAttributeList.
5. CreateProcessW(explicit absolute application, mutable fixed command buffer,
   checked process/thread security, bInheritHandles=TRUE only for HANDLE_LIST,
   EXTENDED_STARTUPINFO_PRESENT | CREATE_SUSPENDED | CREATE_UNICODE_ENVIRONMENT
   | CREATE_NO_WINDOW, bounded explicit UTF-16 environment, private cwd,
   STARTUPINFOEXW, &PROCESS_INFORMATION) -> BOOL. No alternate parent attribute,
   CREATE_BREAKAWAY_FROM_JOB, shell or search-path resolution. Set STARTF_USESTDHANDLES
   with only the declared pipe handles. Avoid shared handle-inheritance races by
   using the dedicated single-threaded controller; job/observer handles remain
   noninheritable and absent from HANDLE_LIST.
6. IsProcessInJob(process_handle, exact_job_handle, &BOOL) must succeed and be
   TRUE; query limits and basic counters before ResumeThread(thread_handle).
   ResumeThread returns the previous suspend count; require exactly 1. DWORD
   -1 or any unexpected count stops and fails. Science imports cannot run before
   this point. Failure after creation terminates the contained job (and exact
   process handle if membership failed), waits/reaps and never resumes to test it.
7. QueryInformationJobObject(handle, JobObjectBasicAccountingInformation=1,
   buffer, DWORD sizeof(buffer), &DWORD returned) -> BOOL. Use non-NULL exact
   job handle, require correct returned byte count and nonnegative counters.
   Never query NULL (observer's own job), resettable ThisPeriod counters or PID
   CPU samples. TotalUserTime/TotalKernelTime are signed 64-bit LARGE_INTEGER;
   preserve both in 100-ns ticks, convert by checked multiplication by 100 to ns.
8. TerminateJobObject(handle, fixed private stop status) -> BOOL, then observe
   empty whole job, wait root process handle with WaitForSingleObject (bounded
   slices), GetExitCodeProcess and final queries. A job wait signal or completion
   port event is not sufficient evidence of general clean completion.
   ActiveProcesses=0 is necessary; counters must then match for three reads
   at least 20 ms apart, within a 2 s drain ceiling. Handle releases may affect
   ActiveProcesses after failed assignment; close ended process/thread handles
   as required while retaining the job. Counter stabilization is a measured
   gate, not a vendor promise of fixed latency.
9. Durably acknowledge receipt, DeleteProcThreadAttributeList and CloseHandle
   owned pipes/process/thread/job handles exactly once. Keep job handle until
   final queries; closing last handle early kills safely but destroys the exact
   receipt opportunity. Missing counters on controller death stay unavailable.

ABI review pins Windows.h/jobapi2.h/processthreadsapi.h symbolic declarations;
do not guess pointer widths. For proposed x64 ABI: HANDLE, SIZE_T and DWORD_PTR
8 bytes; DWORD/BOOL 4 bytes; LARGE_INTEGER 8 bytes. Basic accounting structure
48 bytes, basic limits 64, extended limits 144, STARTUPINFOW 104,
STARTUPINFOEXW 112, PROCESS_INFORMATION 24. SDK sizeof/offsetof probe is a future
gate, not executed here. Reject layout differences; no packed ctypes guess.

### Descendants and controller death

Normal CreateProcess descendants inherit the non-breakaway job; nested jobs may
remain aggregated but are not accepted until exact ancestor/child policy is
measured. WMI/COM/service/scheduled-task brokers can create work outside the job.
Pinned runtime must not call them; actual admission must demonstrate the compute
credential cannot successfully use reachable out-of-job creation paths or mutate
controller state. If denial requires a new restricted token/AppContainer/service
policy, that is a separate approved security design, NOT an assumed provider here.
Same-user access to PROCESS_DUP_HANDLE on controller is likewise a closed gate
until exact ACL/token policy prevents it. Job limits alone do not establish this.

Controller alone owns the kill-on-close job handle. Worker death yields private
pipe EOF and controller whole-job termination. Controller death closes its last
job handle and kills associated descendants; a surviving inherited/duplicated
handle fails the death-control gate. Simultaneous worker/controller death must
leave no live compute. Lost final counters mean failed/unavailable, no fabricated
zero and no success recovery. Verify this with real OS handles after approval.

## 5. Linux exact OS route

Primary references P01-P10, P24-P25 in research. Proposed platform: native
Linux x86_64, unified cgroup2 domain hierarchy, actual clone3 INTO_CGROUP,
PIDFD and cgroup.kill interfaces, readable lifetime counters and approved
controller/compute credentials. Linux 5.7 documents INTO_CGROUP availability;
version alone cannot admit cgroup.kill or seccomp/permission availability.
Hybrid/v1/threaded/domain-invalid groups, unsupported syscalls or controllers,
container migration authority ambiguity and missing manager cleanup all reject.

### Authority prerequisite, presently absent

MAIN must identify an existing owner-authorized delegated parent and launch
context with exact mount ID/device/inode, hierarchy, controller UID/GID,
compute UID/GID, permissions, credential-transition authority and manager-death
policy. Profiles start null; no service/provider/delegation is created by this
proposal. A preopened FD without that proof is insufficient. API and numerics
stay unprivileged; do not grant worker CAP_SYS_ADMIN, run arbitrary root commands,
change global cgroup settings or install a setuid launcher as a default.

Required separation: compute UID differs from controller UID, has no controller
group/ACL grants, has no writable cgroup migration/control destination and cannot
ptrace/signal the controller or obtain its FDs. Existing approved launch context
must already permit checked transitions to compute credentials. If no such
context exists, Linux is CLOSED; a separately reviewed provisioning/security
unit is needed before this unit can be implemented for that platform. This is
an explicit prerequisite, not a claim that DynamicUser/Delegate alone solves it.

### Calls and lifetime ownership

1. Open approved parent using open/openat with O_DIRECTORY | O_NOFOLLOW |
   O_CLOEXEC and verified component ancestry; fstat/fstatfs verify fixed inode
   and CGROUP2_SUPER_MAGIC=0x63677270. Never resolve supplied arbitrary cgroup
   paths, follow symlinks or select /sys/fs/cgroup root. Read bounded control
   files by anchored openat and reject missing/malformed/changed identity.
2. mkdirat(parent_fd, fresh internally derived attempt basename, 0700) must be
   exclusive. Open this retained job directory FD, confirm domain type, empty
   cgroup.events/populated and zero initial CPU stats. Parent controllers must
   already be enabled/usable under authorized delegation; this code does not
   enable them above its exact object. Controller is outside this job subtree.
3. Read-back required per-job fair-class cpu.max bandwidth guard proposed
   100000/100000 usec and cpu.max.burst=0 if supported/required by exact profile;
   bandwidth is a secondary guard, not the total threshold. Require SCHED_OTHER
   scientific execution with no scheduler/capability escape. Require separately
   reviewed memory.max, pids.max=256 (tasks, not Windows processes), affinity and
   scratch policies. Do not set undeclared global controls or call pids.max an
   aggregate CPU limit. Unknown existing state rejects rather than repairing it.
4. In the future single-threaded native controller, use
   syscall(SYS_clone3, &clone_args, sizeof(clone_args)). Proposed struct is
   eleven aligned u64 fields, 88 bytes, from linux/sched.h: flags,
   pidfd, child_tid, parent_tid, exit_signal, stack, stack_size, tls,
   set_tid, set_tid_size, cgroup. Zero-init; flags=CLONE_INTO_CGROUP |
   CLONE_PIDFD, exit_signal=SIGCHLD, cgroup=(u64)job_fd,
   pidfd=(u64)(uintptr_t)&int_pidfd; all other fields zero. No CLONE_VM,
   CLONE_FILES, CLONE_THREAD, CLONE_PARENT or namespace flag. syscall result
   >0 is child pid, 0 is child branch, -1 is errno failure. Unsupported/denied
   EACCES/EPERM/ENOSYS/EINVAL/EBUSY/EOPNOTSUPP closes admission, no fork fallback.
5. Child begins already accounted. It runs only fixed native setup: close every
   controller/cgroup/manager FD, retain fixed pipe/read-input/stage descriptors;
   checked setgroups(0,NULL), setresgid(g,g,g), setresuid(u,u,u) under the
   previously authorized context; clear permitted/effective/inheritable/ambient
   capability sets and verify zero. Check real/effective/saved/fs IDs, no control
   write access and no capability retention. Set PR_SET_NO_NEW_PRIVS(1L),
   PR_SET_DUMPABLE(0L). After credential changes, set PR_SET_PDEATHSIG(SIGKILL)
   and recheck expected parent identity to close the parent-already-dead race.
   None of these operations is inferred to succeed for unprivileged worker.
   Capability ABI is linux/capability.h version 3 (0x20080522): syscall(SYS_capset) with
   __user_cap_header_struct(version,pid=0) and two zeroed
   __user_cap_data_struct entries (effective/permitted/inheritable uint32 masks),
   then syscall(SYS_capget) readback, both require return 0 and save errno on -1;
   glibc supplies no wrappers. prctl(PR_CAP_AMBIENT,PR_CAP_AMBIENT_CLEAR_ALL,0L,0L,0L)
   must succeed. Saved privilege or an unreviewed capability-transition failure
   cannot be ignored. Bounding-set policy belongs to the exact admitted context;
   no_new_privs/zero effective capabilities do not prove every escape denied.
6. Child sends fixed setup-ready acknowledgment <=4096 bytes and waits for one
   private GO frame; controller validates pidfd/root membership and counters,
   then sends GO. Only then execve(explicit pinned interpreter, fixed argv,
   minimal environment). exec error returns bounded errno through CLOEXEC setup
   pipe and _exit; no Python/import/JIT before GO. CLOEXEC closure of the setup
   channel is not itself a scientific success marker.
7. Read cpu.stat by bounded openat/read (<=4096 bytes per read, exact profile
   field registry). Require usage_usec,user_usec,system_usec each once as strict
   unsigned decimal uint64. Preserve all three; aggregate charging uses the
   conservative max(usage_usec, user_usec+system_usec), with checked sum and
   conversion by 1000 to ns. Separate-file/subcounter observations need not be
   atomic or exactly equal; their bounded skew must pass profile tests. Never
   switch to cpu.stat.local, group process lists or v1 units silently.
8. To stop, write exactly "1\n" to the retained cgroup.kill FD, verify full write,
   retain job directory, wait for recursive cgroup.events populated=0 and reap
   root plus adopted descendants. Native controller sets
   prctl(PR_SET_CHILD_SUBREAPER,1L) before launch and uses waitid(P_PIDFD,...)
   with idtype=P_PIDFD, id=owned_pidfd, siginfo_t and WEXITED | WNOHANG
   for root identity plus waitpid(-1,...,WNOHANG) for exclusively owned descendants,
   checking EINTR/ECHILD/state explicitly. No numeric-PID kill sweep.
9. Read three equal final counter records >=20 ms apart after populated=0 and
   all owned exits reaped, within 2 s drain ceiling. Persist private receipt
   before close/unlinkat(AT_REMOVEDIR) of this exact empty created directory.
   Failure, missing manager acknowledgment or changed inode retains held state;
   never recursive-delete a delegation subtree or silently reset counters.

The observed counter is group lifetime cumulative accounting. Normal fork,
setsid and double-fork do not change cgroup placement; migration does. Deny
migration by actual kernel credential/permission policy, close control FDs and
prove denied writes to every reachable ancestor/sibling migration destination.
A read-only-looking local cgroup path, cgroup namespace, no_new_privs or no
numerical forks is insufficient alone. External brokers are not descendants;
an accessible broker closes this profile as on Windows.

### Linux death protocol and honest absence of current backstop

Worker EOF makes the surviving controller call cgroup.kill and drain. A controller
death must be detected by the surviving worker, which must retain an independently
authorized exact-object kill capability (not passed to numerics). It blocks the
next attempt and records counter uncertainty. Simultaneous deaths require the
already configured manager to kill all surviving compute in the admitted subtree.
Record actual unit/manager context privately and verify stop/death ordering and
timeout with MAIN-owned isolated controls, not a global service change here.

PDEATHSIG kills only the affected root and is cleared on descendant fork; it
cannot prove orphan-grandchild termination. Subreaping is not a kill backstop.
If no existing manager context can be proven to empty the delegated subtree,
Linux stays CLOSED. After abrupt controller loss counters may be retained in
the group, but adoption requires exact durable attempt/object association and
separately approved recovery. Do not claim unattended crash recovery; existing
worker stages still require fail-closed operator review/quarantine.

## 6. Counters, publication and recovery boundaries

Native counters, membership/no-live proof, query timing and receipt are private
strict contracts in [contracts](contracts.md). A publication-eligible accounting
receipt requires valid pinned profile, whole-object drain, complete final CPU
<=B, no failed control and bounded parent CPU. Numerical success alone cannot
publish; accounting success alone cannot certify physics, quota, cancellation,
intent durability or a successful SQLite commit.

Guardian/controller holds the OS object through worker receipt acknowledgment.
Worker owns eventual durable receipt/intents/cleanup-debt integration under
Bacon's separately reviewed storage design. A receipt acknowledgment loss never
retries publication or releases debt as if committed. Exact receipts are
immutable and identity-bound, not client-submittable host admission authority.
After counter object destruction, a lost final receipt remains unavailable.
A retry creates a new attempt, object and counters, never zeros prior liability.

No DDL migration, API field, module manifest, online admission record, OS profile
file, ops adapter or selected source-bundle policy changes in this unit. Current
0003 recovery rejects unknown/new revisions and DDL; a future explicit adapter
must independently cover new state/receipts/control debt and tombstone authority.
Even a new accounting receipt cannot widen inventory acceptance. Backup still
requires stopped/masked all-writer maintenance, no live/held attempts or unknown
stages; no SQL read-backup pretends to freeze files/deletion. Restore remains a
NEW-target-only validated operation under latest trusted deletion authority.

## 7. Nonclaims and kill criteria

The proposed interfaces do not certify actual installed OS support, delegation,
security context, final-counter latency, child containment, memory/scratch,
headroom, integrated publication or scientific result correctness. Public receipt
provenance never includes private paths, tokens, raw science or key material.

Kill review/implementation promotion on any executable-before-assignment marker,
unaccounted short-lived child, writable migration/control authority, broker escape,
counter reset/decrease/unit confusion, early object deletion, notification-only
completion, final CPU>B, unknown death outcome, released debt, production contact
or capability claim inferred from a mocked/skipped test. An inconclusive control
is CLOSED, not "best effort". Full MAIN approval authorizes only the separately
assigned next scope; no docs merge is code/OS/deployment authorization.
