# Fixed Linux waveform execution

Status: current authorized implementation, actual Linux qualification in progress.
This design is the current Linux scope amendment, not a passed runtime receipt.
Historical local-only/A5 exclusions do not apply to this approved protected lane.

This lane implements the protected waveform boundary, not a new CPU broker,
provider, deployment service or scientific method. The existing per-run system
manager starts a fixed reviewed argv. API requests cannot choose an executable,
UID, unit, path, environment, context or resource override. All working input,
control, cache, output and temporary paths are explicitly external to checkouts.

One exclusive persistent accounting slice is created empty before launch and
retained through final samples. A manager-born, nonroot, capability-empty science
bootstrap connects to an exact abstract Unix socket in its private network
namespace. Only an isolated observer thread enters that verified manager-born
namespace to bind the listener; the observer main and sampling threads stay in
their original namespace. This runtime handle creates no filesystem temporary
socket and supports external working roots without AF_UNIX inode support.
Peer UID/PID, manager MainPID, membership, security properties,
scope limits, namespace mount and tmpfs capacity are read back before ACK and
readonly original descriptors are transferred. No engine imports or original
reads precede ACK. A pidfd watcher exits on observer death; the manager kills the
service control group. No DB or writer-lease descriptors are inherited.

The single process performs the unchanged genuine counts/complex-response/filter/
Welch/classic calculation, independent sealed reopener, optional post-seal
evaluation and verification of held originals. It does not run a second solver.
TasksMax=2 admits that process and its watcher and is stricter than the original
maximum two-process envelope. It is not a claim that threads equal processes.

The observer samples retained cpu.stat usage/user/system microseconds converted
by checked multiplication to nanoseconds; counters include exited descendants.
No baseline subtraction, smoothing, live-PID sum or CPUQuota substitution.
B=60000000000 and S=57000000000ns, memory charge1073741824, tmpfs52690944,
child60s/transaction120s, poll50ms/maximum observed gap100ms, drain5s and
cancel-to-quiescence2s remain unchanged. Missing/regressing/unreadable counters,
third task, excess bytes, unknown mapped image, incorrect membership or readback
fail closed. CPU bandwidth throttling is supplementary, never lifetime proof.

DRAINED follows the complete final seal and held-original verification. The
observer retains the actual child tmpfs directory descriptor before ACK. Only
after exact successful exit and stable empty-scope final samples may it reopen
and stream verified artifacts into a NEW external publication stage. That API
publication copy is outside scientific CPU, explicitly distinct from in-scope
computation, and both retained copies remain charged to the scratch envelope.
No proc path becomes an unverified output authority. A readonly held-directory
type permits only bounded openat/no-follow regular members of this verified
namespace; no duck-typed directory/path substitution is accepted.

An exact Linux final receipt and digest-bound release acknowledge measured scope
extinction and owned handle closure. Portable resources discriminate positively
between linux_cgroup_charge and windows_job_committed; neither is RSS. All
method/runtime/host acceptance flags remain false. Old admitted jobs reject
changed implementation hashes; merged source/runtime contexts need qualification.

Ordinary packet/counter tests are not OS proof. Actual original, nominal/upper,
cancel/observer-loss, exited-CPU, memory/scratch/gap/process controls and API/
restart/delete/export/browser qualification are separate gates. WSL mechanics
cannot establish the single ML VPS gate. No public activation follows here.
