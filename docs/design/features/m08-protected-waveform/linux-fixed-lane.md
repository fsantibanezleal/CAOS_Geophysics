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
reads precede ACK. Numeric observer PID lookup after manager birth is NOT an
identity binding and is not accepted for parent-death containment. The observer
must acquire its own pidfd before any guardian fork or scientific submission.
A root guardian holds that descriptor, signals readiness, and is enrolled by its
held unreaped child pidfd through the installed systemd255 `PIDFDs`/`ah` interface
in an independent exact scope. Science uses `BindsTo` and `After` on that scope.
The guardian cannot remain in the API/worker caller's control group. Guardian
death, caller death before bootstrap/ACK, interrupted or late manager acceptance
and caller-service stop must all fail closed and drain the exact science group
and retained accounting slice. No delayed numeric PID adoption, generic root
signals or new native CPU broker is permitted. No DB or writer-lease descriptors
are inherited. The manager transport library is installation-owned and pinned;
passing an integer FD through busctl is not UNIX_FD transfer.

The single process performs the unchanged genuine counts/complex-response/filter/
Welch/classic calculation, independent sealed reopener, optional post-seal
evaluation and verification of held originals. It does not run a second solver.
TasksMax=2 remains a strict science-task ceiling and is stricter than the original
maximum two-process envelope. It is not a claim that threads equal processes.
The independent root guardian's operational memory/task/wall allowance is
recorded separately, never subtracted from or substituted for scientific CPU.

## Fixed installation authority and API boundary

The actual qualification lane uses a root observer and a nonroot scientific
child. That is Linux mechanics evidence, NOT authority to run the production
API or database worker as root. The protected Linux path must use a fixed
installation-owned launcher, fixed root-owned bounded configuration and one
canonical owned job UUID. The unprivileged API/worker may not choose interpreter,
admission file, UID/GID, code/data/custody root, unit properties or manager commands
from job JSON or arbitrary argv. No generic sudo/systemd authorization is added.

Resolve the exact running immutable job, dataset, raw/source pair and original
snapshots under the configured application identity, not by granting root read
access to worker-controlled SQLite/WAL or uploaded paths. The privileged parent
receives only bounded checked relations and snapshot bytes, installs them under
held installation-owned external custody descriptors and constructs the native
packet internally. Root-owned leaf files inside a worker-renamable parent are
not sufficient custody. Pin the ordinary publication stage before launch;
publication and successful exact post-transaction cleanup must use that identity.
Uncertain termination, renamed parents, unknown entries or mismatched receipts
retain debt. Native scientific result and original resource ceilings are unchanged.
Missing fixed installation authority must make production Linux unavailable,
not select the qualification root command or an uncontained fallback.

## Qualification boundary

Previous successful native/API/browser calculations retain their original
receipts. They do not prove the pre-acquisition parent-death interval, paused or
late manager acceptance, guardian extinction or a nonroot production API boundary.
Actual controls for these intervals precede protected Linux activation. Existing
adversarial, cold, runtime-closure and actual VPS qualification gates remain open;
this correction adds no scientific method, numerical tolerance or CPU broker.

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
