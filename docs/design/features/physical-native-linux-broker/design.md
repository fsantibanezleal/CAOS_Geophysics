# Exact app-only Linux broker design

Status: proposed executable seam, FULL REVIEW REQUIRED before new broker code.
The already authored qualification controller continues independently. No app,
service-builder, deployed units or production environments are edited here.

## 1. Primary source and preserved sandbox

The broker listens on a root-owned **filesystem** Unix socket. systemd255
PrivateNetwork separates abstract sockets, not filesystem Unix sockets; readonly
mounts do not prohibit such communication. Therefore no network/capability
exception is needed for the worker. Endpoint reachability must be tested in its
actual mount sandbox, rather than inferred from this documentation.
[systemd255 execution contract](https://raw.githubusercontent.com/systemd/systemd/v255/man/systemd.exec.xml)

SO_PEERCRED binds connector credentials at connect time. Linux6.8 SO_PEERPIDFD
returns a kernel FD derived from the socket's retained peer process identity.
Late pidfd_open(numeric_pid) is not an equivalent anti-reuse assertion. Compile
against actual headers; unsupported option/ABI is CLOSED, not a fallback.
[Linux6.8 socket implementation](https://raw.githubusercontent.com/torvalds/linux/v6.8/net/core/sock.c),
[Unix socket contract](https://man7.org/linux/man-pages/man7/unix.7.html)

If API and worker share UID, broker permission requires the exact worker MainPID
and nondumpability. MAIN owns the worker's PR_SET_DUMPABLE=0 startup seam or
separate-account alternative. Actual ptrace/proc-FD tests are required; signals
may still terminate a same-UID worker, so manager lifecycle owns extinction.
No global Yama modification, generic process-name trust or ProtectProc claim.
[PR_SET_DUMPABLE](https://man7.org/linux/man-pages/man2/PR_SET_DUMPABLE.2const.html),
[kernel Yama](https://docs.kernel.org/admin-guide/LSM/Yama.html)

## 2. Exact topology and capacity

```text
unprivileged worker MainPID -- filesystem socket --> native root broker
                                                   fixed manager launch only
PID1: fresh geophysics-cpu-job-<attempt>.service
      observer/ native controller with independent fixed timer
      science/ clone3-born zero-cap distinct-UID scientific family
```

Broker is a separate Type=exec persistent service, Restart=no,
KillMode=control-group, TimeoutStopSec=1s, MemoryMax=64MiB, TasksMax=8,
NoNewPrivileges=yes, PrivateNetwork=yes, PrivateDevices=yes, ProtectSystem=strict,
UMask=0077, no credentials/DB environment and empty capability bounding/ambient
sets. Root UID may call PID1 as root and access only its root-owned endpoint/state;
it does not itself drop science credentials. Observer receives only reviewed
CAP_SETUID/SETGID/SETPCAP from its separate manager-created service. No science
library is linked/imported in the broker. Exact root read/write path exceptions
are supplied by deployment owner; not client fields.

Use a non-socket-activated native listener (no Accept=yes per-connection process
creation). SOCK_SEQPACKET/nonblocking/CLOEXEC, backlog2, at most two unaccepted
handshakes each500ms, one active attempt, no in-broker job queue. One accepted
worker connection owns an attempt. A second SUBMIT returns busy before input
hashing/native launch. Poll loop fixed5ms, bounded eight FDs/connection, fixed
buffers; no unbounded accept, ancillary FD leak or slowloris allocation. Ingress
at most one352-byte packet per handshake; thereafter one64-byte control frame
per10ms, burst4. Excess is sticky failure/whole-group stop, not dropped commands.

The manager launch is native fork/execve of the selected hashed systemd-run with
fixed argv, no shell/PATH search/client-supplied option. That relay is not science
birth or CPU accounting. Manager owns the observer service; native clone3 owns
science birth. The relay's stdio are broker-created control/output pipes with
explicit CLOEXEC closure. The broker cannot use a general launch request.

Attempt unit is Type=exec, ExitType=main, Delegate=cpu memory pids,
DelegateSubgroup=observer, KillMode=control-group, SendSIGKILL=yes, Restart=no,
TimeoutStopSec=1s, Accounting=yes for CPU/memory/tasks, and exact registry wall
bound. BindsTo and After reference **both** configured worker and broker service.
No --scope/--collect/restart/reset, user.slice grant or root science. Check actual
parent/observer/science membership before GO. Worker, broker, controller and
simultaneous deaths must independently empty the whole science family.
[systemd255 service lifecycle](https://raw.githubusercontent.com/systemd/systemd/v255/man/systemd.service.xml),
[kill contract](https://raw.githubusercontent.com/systemd/systemd/v255/man/systemd.kill.xml)

Manager StopUnit and RuntimeMaxSec are crash backstops. They do not prove the
native250ms kill/20ms observation bounds. Native controller timing, retained
cpu.stat/cgroup.kill/event FDs and final drain are unchanged; broker hashing and
DB publication never run in that timer loop.

## 3. Peer authentication without PID reuse or caller assertions

For each accepted socket, immediately retain SO_PEERPIDFD and SO_PEERCRED.
Require exact native sizes and a live PIDFD (no POLLIN exit). Authenticate before
reading client payload/FDs. Selected root-owned registry fixes UID/GID, worker
unit and release identities. Query actual PID1 unit MainPID/ControlGroup by a
fixed bounded systemctl show argv (specific unit/properties only, no shell);
output4KiB, timeout250ms, native full relay reap. Retained PIDFD must stay live
before/after this query and before/after proc inspection.

Peer PID must equal the worker unit's MainPID, not an authorized process's child.
Open proc PID directories with anchored no-follow FDs, read cgroup/executable
identity and executable mapping/venv launch identity under fixed bounds. Compare
exact cgroup path and boot/unit invocation identity. Resolve proc executable
magic link through the separately specified proc identity operation, not a
general symlink-follow input path. Hold immutable release/runtime FDs and actual
device/inode/hash identity; sys.executable string alone is not executable proof.
Parent worker startup must independently report and test nondumpability; broker
does not invent a readable /proc/status Dumpable field. Absence of demonstrated
same-UID FD-theft denial keeps the shared-UID profile CLOSED.

Set SO_PASSCRED before accepting input and require actual SCM_CREDENTIALS on
every packet, with PID/UID/GID equal to the retained authenticated worker. This
additionally rejects an inherited/passed connection used by a different sender;
SO_PEERCRED alone still describes the original connector. Recheck retained
PIDFD liveness at each command. A compromised authorized worker deliberately
proxying another sender is outside peer authentication; the fixed allowlist and
normal app ownership/source gates still apply.

Reject UID-only, forged PID strings, same-UID API, child/sibling units, stale
invocation, different sender on a passed socket, dead PIDFD and unsupported SO_PEERPIDFD.
Do not implement pidfd_open fallback, numeric PID signal/cancel or process-name
authentication. Science cannot connect successfully even if filesystem socket
is visible. Close every rejected ancillary FD and socket exactly once.

## 4. Literal input protocol and byte custody

LBR1 is private broker version1, not an existing API/bundle wire amendment.
First packet exactly352 bytes little endian, all reserved fields zero:

| Offset | Field |
| --- | --- |
| 0 | magic4 LBR1, versionu16=1, opu16=SUBMIT1 |
| 8 | bytesu32=352, reservedu32=0, sequenceu64=1 |
| 24 | attempt16, job16, project16, owner16, registry method-slot16 |
| 104 | releaseSHA25632, profileSHA25632, sourceSHA25632 |
| 200 | source_bytesu64, parameterSHA25632, parameter_bytesu64 |
| 248 | lineageSHA25632, lineage_bytesu64, native object16 |
| 304 | nonnil worker nonce16, boot-ID16, reserved16=0 |

All IDs are nonnil raw16-byte identities, no string/float coercion. Exactly one
SCM_RIGHTS record with three memfds in source/parameter/lineage order plus exactly
one kernel SCM_CREDENTIALS record; no other ancillary record. recvmsg uses
MSG_CMSG_CLOEXEC and fixed CMSG_SPACE(3*sizeof(int))+CMSG_SPACE(sizeof(struct ucred));
MSG_TRUNC/MSG_CTRUNC/extra FD reject before allocation. No caller paths, argv,
UID, environment, unit name, network address, time budget or policy override.

Each FD must be a regular memfd, opened read-only by the sender, and contain
F_SEAL_WRITE|F_SEAL_GROW|F_SEAL_SHRINK|F_SEAL_SEAL. Require nonnegative exact size
within immutable profile cap before reading. Reject F_SEAL_FUTURE_WRITE alone,
ordinary mutable regular file, proc/device/directory/symlink and +1/short input.
Stream pread over exactly declared bytes in64KiB fixed buffers with bounded
hashing time2s for the current5MiB lane; record actual wall/CPU and fail rather
than silently extend. No native root EDI/JSON/XML parser. FDs retained across
hash/launch; no reopening by caller path. Kernel seals provide immutability,
not a client assertion or before/after size observation.

Parameters cap64KiB and lineage16KiB are transport ceilings, not relaxed method
schemas. They preserve exact worker serialization bytes, including native JSON
int/float dialect; broker hashes them without reserializing. The unprivileged
entrypoint still validates actual method schemas, raw scientific bytes, source
hash, owner/project/job and lineage/version using unchanged contracts. A
structurally bounded input is not scientifically eligible.

Every later packet carries exactly SCM_CREDENTIALS and no input FDs.
After ACCEPT reply the private control transport uses existing64-byte framing
shape with new magic LBC1/version1, exact attempt/object/sequence/monotonic clock;
HB, CANCEL, BIND and ACK only, exact lengths and states from controller contract.
Samples/final/digest are relayed unchanged with a broker identity envelope,
never regenerated from JSON. Client has no ability to send START twice, choose
native handles, replace input or call release for a different object. Decoder
and corruption gates are required before claiming wire compatibility.

## 5. Immutable registry and production context (distinct from LCX1)

Root-owned registry pins exact release tree, entrypoint/base interpreter/venv,
native observer, method ID, schema versions and environment plus all resource
ceilings. Its exact bytes/profile SHA are in SUBMIT and outcome; no dynamic
method import, runtime flag, mutable latest path or qualification fixture.
Registry source cap64KiB, at most16 exact entries, unknown keys/duplicate decoded
keys/nonfinite/coerced numeric fields reject. Registry is configuration, not
user-uploaded content. Only measured/reviewed entries may be enabled.

Current seam candidates from existing app contracts are
gravity.station-outlier-flags/v1 (flag QC only), mt.edi-full-tensor-qc/v1 and
mt.edi-fixed-thickness-trf/v1. This names allowed future scopes, NOT admission.
Existing MT raw cap5MiB, M05 memory768MiB/scratch8MiB/wall90s, M06 memory1GiB/
scratch32MiB/wall300s must remain exact or tighter. Current qualification wall120s
cannot replace M05 wall90s. The approved CPU budget/stop margin must be bound
explicitly per method; absent resource proof remains disabled. No16/64MiB input
or512MiB phone/server profile is inferred. Gravity flag profile is independently
defined from its existing contract, not invented as a physical inversion lane.

New production LCX2 context is required: bounded explicit profile fields,
retained sealed input FDs and read-only runtime FDs; actual definition/test-first
change is separately reviewed. Existing LCX1 is frozen for qualification and
cannot be silently relaxed. Production child descriptor allowlist adds source,
parameter and lineage read-only FDs7/8/9; those are data, not broker/cgroup/control
authority. All other FDs close before READY; control GO closes before exec.
Science gets no API/DB secrets, broker socket, manager/cgroup FD or receipt FD.
Base-Python fexecve with selected venv argv0 must pass actual isolated smoke;
Python recognizing the intended venv/native engines is not assumed from a string.
Exact HOME/TMP/MPL/locale/thread/PYTHONPATH values are derived only from immutable
profile/cwd and reviewed entrypoint; no inherited worker environment.

MAIN owns the future app native entrypoint and job/result bridge. This task owns
native broker/context/client protocol. No app file is authored in this SDD.
Science can write only its exclusive bounded job workspace; separate storage
quota/write/custody proof remains required. memcg memory is not RSS and filesystem
polling is not a hard scratch quota.

## 6. State, failure, result and recovery

States: AUTH -> INPUT_BOUND -> RESERVED -> STARTING -> RUNNING -> DRAINING ->
FINAL_HELD -> SEALED -> RELEASED. First error is sticky; every failure after
reservation attempts whole-group stop, bounded drain and records availability
truthfully. No final observation, broken relay, PIDFD exit, unknown unit status,
disk/full write, interrupted ACK or uncertain commit can publish science.

Exclusive root-owned attempt state derives names only from validated raw IDs;
mkdirat O_EXCL/no-follow anchored parent, no caller path. Store immutable identities,
raw transcript hash and failure/outcome in fsynced exclusive files. Existing
attempt/job reservation, stale unit, partial state or invocation mismatch is
HELD/replay rejection; never adopt/delete/reset/retry automatically. Production
one-active-attempt lock belongs to broker and persistent manager-visible state;
broker restart discovers uncertainty and stays closed pending exact recovery,
not a memory-only replay cache.

Broker relay pipe cap4 frames, native trace65536 samples/16MiB, science stdout/
stderr65536 each and exact method result/scratch ceilings remain independent.
Caller disappearance cancels. Final CPU uses retained cgroup components and
strict checked charge, not manager aggregate. Broker/observer/worker post-exit
CPU tails are measured separately through complete durable publication; missing
tail proof keeps H04 closed. ACK binds exact native transcript/result identity
and the worker's durable receipt claim; it does NOT prove database commit from
a hash. Storage owner supplies actual intent/receipt/commit/recovery/release
adapter; H05 stays closed until independently tested.

Safe errors: peer_denied, unsupported_kernel, protocol_invalid, input_unsealed,
input_bounds, source_mismatch, profile_disabled, busy, replay_held,
launch_failed, control_lost, native_failed, custody_held, resource_failed.
Public exposure maps fixed codes only, no errno/private path/source or traceback.
Detailed private diagnostics are bounded and labelled; unavailable is not zero.
No public source publication or method-success claim from broker acceptance.

## 7. Source and execution review packet

Proposed NEW owned paths, after complete design review:
scripts/native_physical_cpu/linux_broker.h, linux_broker.c,
linux_broker_main.c, linux_broker_probe.c;
scripts/native_broker_client.py;
tests/worker_accounting/native/test_linux_broker.py.
Production LCX2 changes stay in owned native/context tests only after its literal
layout/source review. MAIN app/unit/storage files remain separate-owner seams.

Build uses existing selected C17 compiler/headers/libc, pinned sources and fresh
exclusive source/output/scratch/outcome. Recipe/static imports must be reviewed
before compile; actual ELF/header closure before probe/load, then isolated OS
controls before production admission. No dependency install/global toolchain,
unbounded provider, Python accounting or facade substituted for actual operations.
All named adversarials, raw resources and failures are retained at their executed
source pin. This SDD and controller's local tests are not Linux broker evidence.

## 8. Independently reviewed literal client-input unit

The request codec and sealed input preparation can be tested independently of
the unresolved production topology. This unit implements section4 exactly and
does not open a socket, authenticate a peer, start a unit, parse scientific
content, decide CPU accounting or release an attempt. Full production review
and the B01..B14 gates remain required; no pure transport result accepts B04 or
B05 end to end. LCX1 and existing controller/native operation sources remain
unchanged. Only the named new client/test paths are used.

The codec accepts only exact raw16-byte nonnil identities, raw32-byte hashes,
and exact non-boolean integer lengths within the original5MiB/64KiB/16KiB
ceilings. It constructs352 bytes only after validating all fields. Its decoder
requires exact bytes, header, sequence, reserved zeros, fields and ceilings.
Unknown fields and mutable byte buffers are rejected. Input hashes bind literal
bytes, not JSON normalization. These transport ceilings do not admit the larger
physical correction/transform request or imply a new method profile.

On supported Linux, each input is written to one fresh CLOEXEC memfd in bounded
64KiB writes, then sealed WRITE/GROW/SHRINK/SEAL. A read-only descriptor is opened
through the fixed self-proc FD namespace while the original descriptor remains
held. Device/inode/size/seals/read-only/CLOEXEC identity is checked before
publication; the writable descriptor is closed. Partial preparation and context
exit close only this operation's owned descriptors. There is no pathname-input,
ordinary-file fallback, mutable shared-memory fallback or debug-name identity
claim. Unsupported platforms fail before any descriptor allocation. Original
input bodies are neither transformed nor written to persistent storage.

Named pure controls in tests/worker_accounting/native/test_linux_broker.py are
test_exact_submit_offsets_and_roundtrip, test_ids_are_exact_non_nil_bytes,
test_hashes_are_literal_32_bytes, test_size_admission_before_encoding,
test_header_reserved_and_sequence_corruption, test_only_exact_bounded_packet_is_decoded,
test_input_hashes_preserve_original_json_dialect_and_empty_is_rejected and
test_exact_caps_roundtrip. Actual Linux sealing, mutation refusal, descriptor
closure and partial-failure controls are measured by broker_memfd_drill.py;
Windows pure tests do not assert those kernel operations.
