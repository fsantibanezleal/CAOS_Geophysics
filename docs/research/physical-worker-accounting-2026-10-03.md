# Physical worker lifetime CPU accounting research

Date: 2026-10-03. Scope: documentation only, review gap 8.
Status: research persisted before feature design; actual Windows/Linux capability NOT_RUN.
Base: `7e26d253ac7d3a3688cb6263f669a747681aa077`, freshly fetched develop.
Preserved builder: `41f705245116e1f9d0a2ec4555bbeb050e4dea62`.

## Question and baseline

Can a physical job retain real aggregate user plus system CPU for its complete
process lifetime, including descendants that exit between observations, and stop
the whole contained job without a launch, migration or reparenting escape?

The approved [product SDD](../design/SDD.md) requires distinct unprivileged
numerics, resource limits and actual-platform admission. Bacon's review input is
the immutable [physical design at e422d94](https://github.com/fsantibanezleal/CAOS_Geophysics/blob/e422d94c2c89247c79939cc3de6ae10d16784023/docs/design/features/m01-physical-vertical/design.md#L54).
Its proposed correction/transform CPU ceilings are 60/240 seconds, wall 120/300
seconds. These are proposals, not measured admission. Seven storage findings
remain Bacon-owned; this feature does not resolve them by changing accounting.

At the base, app/worker.py Git blob
`17f784f9166d477c0429b9717d5040dfda6c2ce3` uses subprocess creation and
live psutil tree inspection. That does not establish exited-descendant CPU.
Neither the earlier MT host controls nor the ops suites prove this capability.
Host facts previously supplied in coordination came from MAIN, not the user.
No host contact, OS containment object, environment modification or test
execution was used for this research.

## Primary findings, not machine-capability claims

### Linux lifetime group counters and atomic placement

The [kernel cgroup2 specification](https://docs.kernel.org/admin-guide/cgroup-v2.html)
defines cpu.stat usage_usec, user_usec and system_usec in microseconds with
hierarchical coverage. cgroup.kill addresses the group and descendants while
handling concurrent forks/migration. cpu.max limits bandwidth, not lifetime
CPU. A shared service cgroup cannot separate observer, API or other-job CPU.

The [Linux man-pages clone3 interface](https://man7.org/linux/man-pages/man2/clone.2.html)
provides CLONE_INTO_CGROUP and a cgroup directory FD at process creation, avoiding
create-then-migrate jitter. CLONE_PIDFD gives a root identity handle. glibc has no
clone3 wrapper; a future single-threaded native launcher must use the declared
syscall/ABI, not a Python callback after uncontrolled Popen. Kernel version
alone does not prove seccomp, permissions, cgroup mode or interface availability.

A fresh retained domain cgroup is the chosen accounting object. The design
requires exited-child retention controls on the exact kernel. It does not
substitute root getrusage, wait totals plus sampled descendants, PID membership
lists or wall time for authoritative group counters.

### Delegation is authority, not a discovered path

[systemd's delegation contract](https://systemd.io/CGROUP_DELEGATION/) separates
service-manager ownership from delegated subtrees. A writable directory or
CPUAccounting setting is not authority to create arbitrary host groups. No
delegation, service UID, privilege-bearing launch context or configured manager
cleanup has been measured here. All start unset and close Linux admission.

Distinct controller and compute credentials are required by the proposed Linux
profile. [setresuid/setresgid](https://man7.org/linux/man-pages/man2/setresuid.2.html)
and [setgroups](https://man7.org/linux/man-pages/man2/setgroups.2.html) have
checked failure returns and privilege requirements.
[Capabilities](https://man7.org/linux/man-pages/man7/capabilities.7.html) cannot
be inferred from UID labels. MAIN must identify and authorize an actual launch
context before implementation targets it; no new daemon/provider is assumed.

### Parent loss and reap are separate obligations

[PR_SET_PDEATHSIG](https://man7.org/linux/man-pages/man2/PR_SET_PDEATHSIG.2const.html)
is cleared across fork and credential changes; it is not a whole-tree kill.
[Subreaper behavior](https://man7.org/linux/man-pages/man2/PR_SET_CHILD_SUBREAPER.2const.html)
and [waitid/waitpid](https://man7.org/linux/man-pages/man2/wait.2.html) support
exit observation/reaping, not replacement group accounting.
[no_new_privs](https://man7.org/linux/man-pages/man2/PR_SET_NO_NEW_PRIVS.2const.html)
survives fork/exec but does not revoke existing authority.

The version-pinned official [systemd kill manual source](https://raw.githubusercontent.com/systemd/systemd/v257/man/systemd.kill.xml)
documents control-group stop cleanup. The [resource-control source](https://raw.githubusercontent.com/systemd/systemd/v257/man/systemd.resource-control.xml)
distinguishes CPU accounting, quota and delegation. This is documentation
provenance, not a claim that v257 is installed or that guardian death actually
stops an existing unit. Simultaneous observer/controller death requires a
separate measured manager backstop; absent proof, the lane remains CLOSED.

### Windows cumulative job accounting

Microsoft's [basic accounting structure](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_accounting_information)
defines TotalUserTime and TotalKernelTime as LARGE_INTEGER cumulative counters
including terminated associated processes, in 100-nanosecond ticks. ThisPeriod
counters are resettable and are not the chosen receipt source.

[Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)
covers child inheritance, breakaway exceptions, nested aggregation and last-
handle kill. It explicitly notes brokered WMI creation does not inherit the
job. Thus a job is not a universal sandbox or proof that external brokers cannot
create work. The accepted trust domain is pinned scientific code, never arbitrary
user executables. A reachable broker or mutable ancestor policy closes admission.

### Windows launch before execution and final queries

[UpdateProcThreadAttribute](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute)
selects PROC_THREAD_ATTRIBUTE_JOB_LIST, a job-handle array at creation.
[Attribute-list initialization](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-initializeprocthreadattributelist)
has an expected sizing failure, distinct from a failed initialized call.
[CreateProcessW](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw)
and [creation flags](https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags)
permit extended startup plus suspended initial execution.
[IsProcessInJob](https://learn.microsoft.com/en-us/windows/win32/api/jobapi/nf-jobapi-isprocessinjob)
must confirm the exact job before
[ResumeThread](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-resumethread).
The weaker post-creation [AssignProcessToJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-assignprocesstojobobject)
route is not an automatic fallback.

[CreateJobObjectW](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-createjobobjectw),
[SetInformationJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-setinformationjobobject),
[QueryInformationJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-queryinformationjobobject)
and [TerminateJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-terminatejobobject)
are the selected create/control/counter/kill operations.
[Nested-job restrictions](https://learn.microsoft.com/en-us/windows/win32/procthread/nested-jobs)
need a real parent-context gate, not global breakaway.

### Enforcement limitation and review decision

[Basic job limits](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information)
give PerJobUserTimeLimit in 100-ns ticks, checked periodically and user-only.
[Extended limits](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information)
contain aggregate committed-memory limits, not an aggregate RSS measurement.
Neither is an exact instantaneous user-plus-kernel hard stop.

Design conclusion (our inference): select lifetime kernel accounting, an early
aggregate threshold, whole-object termination, separately measured observation
and kill bounds, and strict final-counter publication eligibility. Ordinary
non-real-time OS scheduling does not imply a mathematical zero-overshoot
guarantee. If the physical vertical requires that stronger guarantee, these
stock interfaces do not establish it; MAIN must keep the lane closed or approve
a different, researched enforcement contract. A final counter above 60/240 s is
failure, never a revised budget or accepted output.

## Evidence receipt method and limits

The table records actual read-only HTTPS requests made on 2026-10-03.
PowerShell Invoke-WebRequest -UseBasicParsing supplied RawContentStream body
bytes; SHA256 was computed in memory, with status, byte count and UTC completion.
These are response-body hashes after HTTP content decoding, not TLS wire hashes,
signed attestations, installed library hashes, kernel capability evidence or
production trust. No full copyrighted page, credentials, hostname inventory or
private data was saved. Mutable documentation can change; the hash identifies
the observed body, not future URL bytes. Linux man-pages is the kernel/C-library
interface documentation project linked by kernel.org.

The freedesktop rendered manual URLs failed in browsing; the official v257
source XML above is the successful, byte-recorded primary fallback. We do not
call the rendered failures successful receipts. Runtime and enforcement
experiments are all NOT_RUN.

| ID | Official primary URL | UTC completion | HTTP | Body bytes | SHA-256 |
| --- | --- | --- | ---: | ---: | --- |
| P01 | [primary source](https://docs.kernel.org/admin-guide/cgroup-v2.html) | 2026-10-03T10:33:14.9831648Z | 200 | 172971 | `6efabe7ed748f1d863859a0e5c50e770e47255c9a071bf878f6460e7e01c0563` |
| P02 | [primary source](https://man7.org/linux/man-pages/man2/clone.2.html) | 2026-10-03T10:33:16.2616912Z | 200 | 75546 | `2ca4447e1dd2bcd221478f495a745cb34cfaeff0cd379e30451be817db16f13a` |
| P03 | [primary source](https://systemd.io/CGROUP_DELEGATION/) | 2026-10-03T10:33:17.2413118Z | 200 | 31109 | `7d60dadf36c1772a8f5d596294ed2524b4e69e474412ef3a7c6d3ea58b8bd14a` |
| P04 | [primary source](https://man7.org/linux/man-pages/man2/wait.2.html) | 2026-10-03T10:33:17.7078460Z | 200 | 31979 | `fe247c4fc91a2dafd978157a46fa2a91fa48b902e643d852e8352d78c4b32fd3` |
| P05 | [primary source](https://man7.org/linux/man-pages/man2/setresuid.2.html) | 2026-10-03T10:33:17.9470579Z | 200 | 13134 | `a005dc6c1f4019174ca469290b01422e9a756086421fd5fa70107609deb81474` |
| P06 | [primary source](https://man7.org/linux/man-pages/man2/setgroups.2.html) | 2026-10-03T10:33:18.1898770Z | 200 | 16234 | `618b2a92c91b3d183974617947e5e690f545ff18000f88dec2bfd28f30a753c9` |
| P07 | [primary source](https://man7.org/linux/man-pages/man7/capabilities.7.html) | 2026-10-03T10:33:18.6705340Z | 200 | 83601 | `79ca88f6d8984ca2858860e7267d7c4660f6555151cc1f570305a9c6dfccf714` |
| P08 | [primary source](https://man7.org/linux/man-pages/man2/PR_SET_PDEATHSIG.2const.html) | 2026-10-03T10:33:18.9093001Z | 200 | 10684 | `5e72367effe41fab8ca6a0969ed39c201c98a7495c9cbc94b574b4949144fc82` |
| P09 | [primary source](https://man7.org/linux/man-pages/man2/PR_SET_CHILD_SUBREAPER.2const.html) | 2026-10-03T10:33:19.1476851Z | 200 | 9879 | `b805fe23c7251ad6c3d08a829ed755b80a8fa106929c67325c7122f3b126ef2c` |
| P10 | [primary source](https://man7.org/linux/man-pages/man2/PR_SET_NO_NEW_PRIVS.2const.html) | 2026-10-03T10:33:19.4040419Z | 200 | 9759 | `ede9b1e67e51420ca0c3c41f45189e3df4c9ceb6158f49ff50ffc8d0c96deaaa` |
| P11 | [primary source](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_accounting_information) | 2026-10-03T10:33:19.6500909Z | 200 | 52723 | `b33eb0ae491fe2c23c8faa7624ae69db4051955af85079f9bdd9ee6eee1d0b10` |
| P12 | [primary source](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects) | 2026-10-03T10:33:19.8361912Z | 200 | 61660 | `dd302113e93f866f7c445c87e255199f7d698cd5174d6492d0ba4505d04bcff1` |
| P13 | [primary source](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute) | 2026-10-03T10:33:20.0310465Z | 200 | 85377 | `ad6eac4717f3f3d503675fc64f8371fa09b88d96abae41f7af9596269a09ceb0` |
| P14 | [primary source](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-createjobobjectw) | 2026-10-03T10:33:20.7547188Z | 200 | 55451 | `0833177ad0a7b03312a76305c646832e9e1f8106624d008460fb321d0dd46a52` |
| P15 | [primary source](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-queryinformationjobobject) | 2026-10-03T10:33:21.1746942Z | 200 | 66433 | `158f19d0ed23018afa3654696340bb9d9df9f5ff68ddb423462dbc7e409b9964` |
| P16 | [primary source](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-setinformationjobobject) | 2026-10-03T10:33:21.7955706Z | 200 | 64822 | `4a65ca285a0903201f631b19c703aae22794ffe0c4df6e656049e38b9b48f2fe` |
| P17 | [primary source](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-terminatejobobject) | 2026-10-03T10:33:22.0528753Z | 200 | 53241 | `535d014bcbb8aae72c60a6b86f5fe4ab5723115ee39b98f5e53642c035091600` |
| P18 | [primary source](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information) | 2026-10-03T10:33:22.4425828Z | 200 | 67906 | `696212d147c68762a4c532a213d5c7d0c03840702ed8414b3e4063c7336bbc77` |
| P19 | [primary source](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information) | 2026-10-03T10:33:22.8757730Z | 200 | 53188 | `aab91fe80b6b323d856622950e9704b8e1184f0b097c564bd0b38a9a3957bf9b` |
| P20 | [primary source](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw) | 2026-10-03T10:33:23.0709817Z | 200 | 76621 | `aad7c4a7eb7ce82e105b5af68095cc24b6d1d221696d0440792afd391edf4738` |
| P21 | [primary source](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-assignprocesstojobobject) | 2026-10-03T10:33:23.2708264Z | 200 | 58029 | `bd269cd8046f05958e5470ecf2ec309933a0b030bbac34c3502c4e9d851c2d06` |
| P22 | [primary source](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-resumethread) | 2026-10-03T10:33:23.7599317Z | 200 | 54295 | `3db835e19ee69c690645182a2a021970bf6ff95e46f99c32ea8a37dd65576c55` |
| P23 | [primary source](https://learn.microsoft.com/en-us/windows/win32/procthread/nested-jobs) | 2026-10-03T10:33:23.9511411Z | 200 | 54981 | `fcfb24ac092c6cbd48608a65efcf2c7f6dd53f51c48814e86c9b64c7d969794d` |
| P24 | [primary source](https://raw.githubusercontent.com/systemd/systemd/v257/man/systemd.kill.xml) | 2026-10-03T10:35:25.1166956Z | 200 | 11224 | `448322830dbbd02c64cca99941ba92705afe9648241fc917db7a8d6ae7910e72` |
| P25 | [primary source](https://raw.githubusercontent.com/systemd/systemd/v257/man/systemd.resource-control.xml) | 2026-10-03T10:35:25.4720350Z | 200 | 100514 | `f9e9ceaa2aba6c7f8b0e625c71abdb5ea0c0354bf3fd90577bfbf42c4487a21f` |
| P26 | [primary source](https://learn.microsoft.com/en-us/windows/win32/api/jobapi/nf-jobapi-isprocessinjob) | 2026-10-03T10:35:25.6997807Z | 200 | 52588 | `e1b9aad227854a38a8a4f8cef60d540c145273c2a35ffb323729038210f69a21` |
| P27 | [primary source](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-initializeprocthreadattributelist) | 2026-10-03T10:35:26.1244257Z | 200 | 54705 | `8bc08827a2798a268452824682209b1cd7f92572273cd5bb033712b2336382a1` |
| P28 | [primary source](https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags) | 2026-10-03T10:35:26.3315970Z | 200 | 61344 | `3c9ae2d2c5d5e9dabbf7aca936a26f86df7b197780329094b09aa207f1dc4b8c` |
| P29 | [primary source](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes) | 2026-10-03T10:50:11.1981903Z | 200 | 55762 | `bfda2b717edf1113ef30e5d64b5faa22cfc5feecd6edea25ab48afd8d3333b9c` |
| P30 | [primary source](https://man7.org/linux/man-pages/man2/getrusage.2.html) | 2026-10-03T10:50:12.1697443Z | 200 | 16691 | `ade816073a4c25f6d272fbf628d7bdf6d9a5b4ae76b29f1889cc01420220d523` |
| P31 | [primary source](https://man7.org/linux/man-pages/man2/clock_gettime.2.html) | 2026-10-03T10:50:12.6421051Z | 200 | 30379 | `7d7948bcf8400a786c2795b24e8da979d6e01610f7b8ea6bf1ab97f06205fb69` |
| P32 | [primary source](https://learn.microsoft.com/en-us/windows/win32/api/profileapi/nf-profileapi-queryperformancecounter) | 2026-10-03T10:50:12.9723297Z | 200 | 52841 | `946834d33befbf62d92e1364e3f81f62d3ae7b9369eccedbad983edffeb3e357` |
| P33 | [primary source](https://learn.microsoft.com/en-us/windows/win32/api/profileapi/nf-profileapi-queryperformancefrequency) | 2026-10-03T10:50:13.1965771Z | 200 | 52607 | `448bc05f6b25a8ae61b0df193c93b9941f220e11dd68c3ee48d64f87d2eaa35b` |
| P34 | [primary source](https://man7.org/linux/man-pages/man2/capget.2.html) | 2026-10-03T10:58:27.6418252Z | 200 | 15993 | `b730056850d91156201de4a6e52742a80d519689e9ab312485673151b9c5feb2` |

## Oracle and observer clocks

Microsoft [GetProcessTimes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes)
gives process-only summed thread user/kernel durations as FILETIME (100 ns).
Linux [getrusage(RUSAGE_SELF)](https://man7.org/linux/man-pages/man2/getrusage.2.html)
gives process thread totals in seconds plus microseconds. These are chosen
validation-fixture and separate parent-overhead counters, not substitutes for
group lifetime charging. RUSAGE_CHILDREN can depend on intervening wait behavior
and would double-count science if blindly added to controller overhead.

Linux [clock_gettime(CLOCK_MONOTONIC)](https://man7.org/linux/man-pages/man2/clock_gettime.2.html)
and Windows [QueryPerformanceCounter](https://learn.microsoft.com/en-us/windows/win32/api/profileapi/nf-profileapi-queryperformancecounter)
with [QueryPerformanceFrequency](https://learn.microsoft.com/en-us/windows/win32/api/profileapi/nf-profileapi-queryperformancefrequency)
provide the selected observation clock interfaces. Clock ticks require explicit
checked conversion; neither clock is a CPU-duration oracle. Runtime precision,
latency and scheduling bounds remain NOT_RUN.

The [raw capability ABI](https://man7.org/linux/man-pages/man2/capget.2.html)
defines version-3 two-entry uint32 mask structures and checked syscall capget/
capset returns. glibc provides no wrappers. A proposed native launch path must
pin that ABI explicitly or reject it; reading the API is not evidence that a
worker may acquire or discard arbitrary host authority.

## Research to design

Read the proposed [feature review packet](../design/features/physical-worker-accounting/review-packet.md) only after this research. It pins OS ABI, lifecycle, safe errors, provisional caps and prospective gates. Persisted research is not MAIN approval; neither a docs merge nor previous builder/MT evidence authorizes code or OS execution.
