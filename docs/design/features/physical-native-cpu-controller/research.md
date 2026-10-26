# Native physical CPU controller research

Date: 2026-10-03. Status: research for a NEW native implementation sub-SDD,
not approval to implement, compile, probe or create OS objects.
Issue: [140](https://github.com/fsantibanezleal/CAOS_Geophysics/issues/140).

Read [requirements](requirements.md), [design](design.md), [contracts](contracts.md),
[validation](validation-plan.md), [tasks](tasks.md) and [review packet](review-packet.md).
The [parent research](../../../research/physical-worker-accounting-2026-10-03.md)
and its 34 historical receipts remain unchanged. No claim below turns those
receipts or the approved pure protocol into an actual-platform pass.

## 1. Decision context and evidence classes

Isolated base: ba54d32f0932a09502f463f3aff9c8f21270dca1.
Parent direction accepted at3959ffc29eb4f93e0cca04fdc3154eca7ea7ddca.
Pure candidate:3bedfe0bad821b3638cd9e7de718f7232a0198e7.
MAIN has accepted monitored combined lifetime accounting, NOT instantaneous
zero overshoot. B=60/240 s and S=57/237 s remain frozen. Final CPU>B alwaysFAIL.

Documentation defines interfaces. Installed source inventory establishes bytes
available to review. Native compilation would establish an ABI for one toolchain.
Actual positive/adversarial controls would establish bounded observations for
one context. None substitutes for the next class. Compilation and actual native
controls have NOT_RUN. Security credentials/delegation/manager context is absent.
Both platform profiles are unset/CLOSED. No host connection was made.

## 2. Maintained native mechanisms and rejected substitutes

N06/N09: Windows job totals use signed64 TotalUserTime and TotalKernelTime,
100 ns units, retaining associated terminated processes. ThisPeriod totals are
resettable and not the selected source. The combined checked lifetime total is
the charge, not the root process, elapsed time or live-PID polling.

N07/N20: select the job user-time limit as a SECONDARY mandatory backstop on a
fresh empty object; set PerJobUserTimeLimit once to S/100 ticks. It is user-only
and periodically checked, not an instantaneous combined CPU ceiling.
KILL_ON_JOB_CLOSE requires sole ownership of the final handle for death safety.
Mutable limit policies or leaked handles defeat the intended guarantee.

N08/N10/N21: JOB_LIST associates during process creation. A creation-time job
plus suspended verification is selected over launching then assigning a running
process. A failed sizing/update/create/membership/readback/resume call cannot
permit the first science instruction. SDK declarations are used directly.

N01/N02/N04: select fresh domain cgroup2 accounting and clone3 INTO_CGROUP at
birth. Read cumulative cpu.stat, preserve usage/user/system and charge
max(usage,user+system)*1000 ns. cpu.max is a bandwidth guard, never lifetime
credit. Hierarchical accounting cannot provide per-job isolation when a shared
service group or writable migration authority is used.

N22/N23/N19: parent-death signal covers a root, not all forked descendants.
Subreaping establishes exit ownership, not termination. A concrete existing
manager-death policy must stop the exact subtree even when both parent and
controller die. systemd delegation documentation is not evidence that such
authority or a safe unit exists on the target.

N11/N12/N13: parent/controller accounting must include exited contributions and
setup, hashing, final serialization, release and publication work. A controller
SELF report taken before its last instructions misses its exit tail. A persistent
worker's SELF delta taken before its final write likewise misses that write.
No clock, sampling trick or perfect pure RELEASE record resolves this circular
final-counter/durable-ack problem. The isolated controller can be measured after
exit by MAIN's independent harness, but production needs separate reviewed
worker/storage lifecycle authority. This packet keeps that gate CLOSED.

N14/N15/N17/N18: successful write is not durable receipt acceptance.
File flush/fsync and exclusive identity-bound publication are necessary design
operations, not a portable proof of atomic file+SQLite commit. Windows directory
durability and filesystem semantics require actual context evidence; POSIX fsync
of the file alone omits directory-entry durability. Uncertain ack means HELD.

## 3. Binding selection and real runtime inventory

Select direct SDK/UAPI C17 translation units, not a new Python package,
ctypes-packed structures, pywin32 installation, shell, Python preexec_fn,
vendor modification or claimed external provider. C runtime/platform calls need
an exact later native source/ABI review. Python's unchanged pure module remains
the authoritative supplied-record validator; its runtime_authorized staysfalse.

N05 source review, CPython v3.12.10 _winapi.c lines1026-1127, finds an
attribute-list implementation for HANDLE_LIST, not JOB_LIST. Adding an arbitrary
job_list Python dictionary key would not create the chosen native association.
N25 documents the preexec threading risk. Neither is a reason to patch Python.

Actual read-only local inventory on2026-10-03:

| Item | Observed identity | SHA-256 |
| --- | --- | --- |
| SDK jobapi2.h | Windows SDK10.0.22621.0 | 398ef4f8277a1edb58e41c5e8233e8dce7744522ba8e989d904e93991a254c71 |
| SDK processthreadsapi.h | SDK10.0.22621.0 | a692be0b6e83ad600dccf2ca09131f1c1b599ad1c8073afdc1620d1c23703a1a |
| SDK winnt.h | SDK10.0.22621.0 | 2c8a4932205b4d41a03a8112e6f95d5a337044a393511e17a3324ea96e801cce |
| SDK profileapi.h | SDK10.0.22621.0 | cfa8e3626dba11689997d8fcd65b5dbf4bcef8de09dd7e4e881769d48d165a2 |
| SDK WinBase.h | SDK10.0.22621.0 | adf591f6ce176a190c2d1ac90739399993d7fe3da016389fc1daa5b1eeefa3d5 |
| cl.exe | MSVC14.43.34808, file version19.43.34810.0;867912 bytes | 9beec04038c74406e4c055593edc07ddda7b166272d77cbf85507d5a6be29ff0 |
| Read-only interpreter | CPython3.12.10, pointer width8 bytes | 0b471133e110cfb53a061cad528ce8e517d7b9ac41a0a396c39ad795a487fc14 |
| python312.dll | Built-in _winapi is part of runtime, not a separately hashed module | 9a0e3435aaa680d868150f87ab3e388ad2eebc22f87e036155c7b4eda8cd2120 |
| _ctypes.pyd | Installed binary, NOT selected binding | 0e56107a891100535f2da79d85a5ae65ff1227b4765bd108f8593ac1a1110d81 |
| ctypes/__init__.py | Installed source, NOT a native capability probe | 8fc533f8ae18a7ca06dce88fc8dca5eae61f2a4198ceb9d4b4b5a69862aa42ee |
| subprocess.py | Installed source | e9886605ccac88bcfe2330a1b4cd8f132cbaf97ebb6834b1dcb5a69b127b8d5b |

pywin32 win32job spec is absent. No dependency installation or environment edit.
Compiler bytes/version metadata were read; cl.exe was NOT executed. No link
test, SDK layout probe or Job Object call occurred. Linux compiler/kernel/libc
and launch context were not inspected remotely. v6.12 UAPI is a research pin,
NOT the asserted kernel ABI of a host. Linux remains wholly NOT_RUN.

SDK winnt.h lines12845-12880 declares accounting/limit structures;
lines13210/13226 define JOB_TIME/KILL_ON_JOB_CLOSE; enum class1 at13307.
WinBase.h line3919 declares JOB_LIST, not processthreadsapi.h.
Proposed x64 structure sizes in design are targets for an actual compile probe,
not sizes certified by reading typedefs or Python pointer width.

## 4. Fresh official HTTPS retrieval receipts

These are actual bounded urllib HTTPS reads via the existing read-only Python,
-B, four concurrent readers,15 s per request, max1 MiB/body before acceptance.
Bodies were held in memory for SHA-256 only and not mirrored into the repository.
All statuses are200, requested URL equals final URL; bytes are response-body
bytes, not executable provenance. UTC, size and hash identify exactly what was
read. HTTPS digests are NOT signature/Sigsum proofs or evidence of installation.
Live HTML can change, as the N16 body hash illustrates relative to earlier reads.

| ID | Official requested/final URL | UTC completion | Bytes | SHA-256 |
| --- | --- | --- | ---: | --- |
| N01 | [source](https://docs.kernel.org/admin-guide/cgroup-v2.html) | 2026-10-03T15:11:50.895233+00:00 | 172971 | 6efabe7ed748f1d863859a0e5c50e770e47255c9a071bf878f6460e7e01c0563 |
| N02 | [source](https://man7.org/linux/man-pages/man2/clone.2.html) | 2026-10-03T15:11:52.198848+00:00 | 75546 | 2ca4447e1dd2bcd221478f495a745cb34cfaeff0cd379e30451be817db16f13a |
| N03 | [source](https://systemd.io/CGROUP_DELEGATION/) | 2026-10-03T15:11:51.555303+00:00 | 31109 | 7d60dadf36c1772a8f5d596294ed2524b4e69e474412ef3a7c6d3ea58b8bd14a |
| N04 | [source](https://raw.githubusercontent.com/torvalds/linux/v6.12/include/uapi/linux/sched.h) | 2026-10-03T15:11:51.068143+00:00 | 6302 | 2081b07cee6adab443e4ba320d0ccb13db4c97bed64f3eefafbfde2f25c833a4 |
| N05 | [source](https://raw.githubusercontent.com/python/cpython/v3.12.10/Modules/_winapi.c) | 2026-10-03T15:11:51.174186+00:00 | 78816 | 9f231ff4d286683f3df9ec925cdfc375ae951609d9ea39ddb6529f4649ebfd78 |
| N06 | [source](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_accounting_information) | 2026-10-03T15:11:51.298681+00:00 | 52723 | b33eb0ae491fe2c23c8faa7624ae69db4051955af85079f9bdd9ee6eee1d0b10 |
| N07 | [source](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information) | 2026-10-03T15:11:51.402457+00:00 | 67906 | 696212d147c68762a4c532a213d5c7d0c03840702ed8414b3e4063c7336bbc77 |
| N08 | [source](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute) | 2026-10-03T15:11:51.518787+00:00 | 85377 | ad6eac4717f3f3d503675fc64f8371fa09b88d96abae41f7af9596269a09ceb0 |
| N09 | [source](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-queryinformationjobobject) | 2026-10-03T15:11:51.638376+00:00 | 66433 | 158f19d0ed23018afa3654696340bb9d9df9f5ff68ddb423462dbc7e409b9964 |
| N10 | [source](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw) | 2026-10-03T15:11:51.737205+00:00 | 76621 | aad7c4a7eb7ce82e105b5af68095cc24b6d1d221696d0440792afd391edf4738 |
| N11 | [source](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes) | 2026-10-03T15:11:51.823338+00:00 | 55762 | bfda2b717edf1113ef30e5d64b5faa22cfc5feecd6edea25ab48afd8d3333b9c |
| N12 | [source](https://man7.org/linux/man-pages/man2/getrusage.2.html) | 2026-10-03T15:11:52.560414+00:00 | 16691 | ade816073a4c25f6d272fbf628d7bdf6d9a5b4ae76b29f1889cc01420220d523 |
| N13 | [source](https://man7.org/linux/man-pages/man2/wait.2.html) | 2026-10-03T15:11:52.655495+00:00 | 31979 | fe247c4fc91a2dafd978157a46fa2a91fa48b902e643d852e8352d78c4b32fd3 |
| N14 | [source](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-flushfilebuffers) | 2026-10-03T15:11:52.054655+00:00 | 54775 | bccd0596e69b8f53b43f6b0cb71a2006bcc5d870e3da8818673c4f19ea91b682 |
| N15 | [source](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew) | 2026-10-03T15:11:52.283025+00:00 | 115286 | f3836391ad5c15b6d8376cc4f5950c6a53e768150ab46e1384405becd5ddf1f8 |
| N16 | [source](https://learn.microsoft.com/en-us/windows/win32/procthread/job-object-security-and-access-rights) | 2026-10-03T15:11:52.444839+00:00 | 54159 | 09fe2886164eee8c539813490effdffde0b5967cd54d841732bda90b674cd90b |
| N17 | [source](https://man7.org/linux/man-pages/man2/fsync.2.html) | 2026-10-03T15:11:53.201457+00:00 | 15152 | f0a986d21500222ecb69580fc7a910f346c6b1ff1005ca515501fb05bb5d91f5 |
| N18 | [source](https://man7.org/linux/man-pages/man2/renameat2.2.html) | 2026-10-03T15:11:53.377569+00:00 | 23571 | 8772946a809a0db54f4854f200908f10bee758ea452e8df5efd955bc3b8e6e57 |
| N19 | [source](https://raw.githubusercontent.com/systemd/systemd/v257/man/systemd.kill.xml) | 2026-10-03T15:11:52.798497+00:00 | 11224 | 448322830dbbd02c64cca99941ba92705afe9648241fc917db7a8d6ae7910e72 |
| N20 | [source](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-terminatejobobject) | 2026-10-03T15:11:52.881270+00:00 | 53241 | 535d014bcbb8aae72c60a6b86f5fe4ab5723115ee39b98f5e53642c035091600 |
| N21 | [source](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-resumethread) | 2026-10-03T15:11:53.015859+00:00 | 54295 | 3db835e19ee69c690645182a2a021970bf6ff95e46f99c32ea8a37dd65576c55 |
| N22 | [source](https://man7.org/linux/man-pages/man2/PR_SET_PDEATHSIG.2const.html) | 2026-10-03T15:11:53.575074+00:00 | 10684 | 5e72367effe41fab8ca6a0969ed39c201c98a7495c9cbc94b574b4949144fc82 |
| N23 | [source](https://man7.org/linux/man-pages/man2/PR_SET_CHILD_SUBREAPER.2const.html) | 2026-10-03T15:11:53.708973+00:00 | 9879 | b805fe23c7251ad6c3d08a829ed755b80a8fa106929c67325c7122f3b126ef2c |
| N24 | [source](https://learn.microsoft.com/en-us/windows/win32/api/namedpipeapi/nf-namedpipeapi-createnamedpipew) | 2026-10-03T15:11:53.595595+00:00 | 71499 | 1a9266ab28aae2014f9c8894a3418e725efa17c1ff6f66ee92400eea43ec0886 |
| N25 | [source](https://docs.python.org/3.12/library/subprocess.html) | 2026-10-03T15:11:53.972088+00:00 | 216417 | 48f3c7606979fcfc0b88c7efbe0540dec7744d02a109f455452a7a79b5ebde5b |
| N26 | [source](https://learn.microsoft.com/en-us/windows/win32/api/profileapi/nf-profileapi-queryperformancecounter) | 2026-10-03T15:31:12.957329+00:00 | 52841 | 946834d33befbf62d92e1364e3f81f62d3ae7b9369eccedbad983edffeb3e357 |
| N27 | [source](https://learn.microsoft.com/en-us/windows/win32/api/profileapi/nf-profileapi-queryperformancefrequency) | 2026-10-03T15:31:12.600975+00:00 | 52607 | 448bc05f6b25a8ae61b0df193c93b9941f220e11dd68c3ee48d64f87d2eaa35b |
| N28 | [source](https://man7.org/linux/man-pages/man2/clock_gettime.2.html) | 2026-10-03T15:31:13.301012+00:00 | 30379 | 7d7948bcf8400a786c2795b24e8da979d6e01610f7b8ea6bf1ab97f06205fb69 |
| N29 | [source](https://man7.org/linux/man-pages/man2/wait4.2.html) | 2026-10-03T15:31:13.066869+00:00 | 11408 | 3227e5a279c2c00b682498bdc276f8dc04918d70968bd615c36f8780a9855450 |
| N30 | [source](https://man7.org/linux/man-pages/man2/prctl.2.html) | 2026-10-03T15:31:13.527703+00:00 | 26266 | ef698f6c5aab0224e9bf238ea1820160797c15d0adcee8b37fcaac7297866810 |
| N31 | [source](https://man7.org/linux/man-pages/man2/capget.2.html) | 2026-10-03T15:31:13.889676+00:00 | 15993 | b730056850d91156201de4a6e52742a80d519689e9ab312485673151b9c5feb2 |
| N32 | [source](https://man7.org/linux/man-pages/man2/sched_setaffinity.2.html) | 2026-10-03T15:31:14.001060+00:00 | 23566 | a55f0f1590ae5fb208ac66794b901995b767d9f9ea6e82b11383af85b3cc87d6 |
| N33 | [source](https://man7.org/linux/man-pages/man2/poll.2.html) | 2026-10-03T15:31:14.232114+00:00 | 29911 | 411bb440dcaf29549937e84bbeb4de2ab19ba07becaf21071fc8146c02898c38 |
| N34 | [source](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_end_of_job_time_information) | 2026-10-03T15:31:13.769102+00:00 | 52812 | 436ee937de15de1f1e7d3fa12a2baa227b68ae64b8e4af102e7d1345c5cb403f |

N26-N28 pin observer clock units and checked conversion requirements; clocks
do not measure science CPU. N29 provides an owned exited-process rusage route
for the independent Linux parent oracle, not a replacement cgroup charge.
N30-N33 define concrete credential/death/affinity/event interfaces; availability
does not establish effective permission, no escape or timing bounds. N34 pins
the user-time end action; verify terminate0 rather than relying on an unreviewed
default or notification-only policy.

## 5. Unresolved mechanisms and honest research outcome

H01 actual Windows credential/DACL/ancestor-job/broker/handle denial.
H02 actual Linux credential transition/delegation/manager simultaneous-death
context. No imaginary provider, root grant, setuid daemon or service is assumed.
H03 aggregate visibility/rounding and worst observed scheduling/kill bounds,
with non-real-time residual risk acknowledged by MAIN.
H04 exact post-exit controller CPU and complete per-attempt worker tail/final
release custody in production. An internal self-report is insufficient.
H05 durable receipt/ack/release transaction, uncertain commit, quota/deletion
and exact new revision/DDL plus recovery adapter. Existing0003 must reject it.
H06 native SDK/UAPI/CRT ABI and executable provenance on each approved platform.
All remain CLOSED/NOT_RUN. The SDD selects concrete calls and failing gates;
it does not approve an unknown OS fallback or claim these mechanisms exist.
