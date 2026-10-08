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

### Closed installation and retention protocol

The installed root configuration is one bounded canonical JSON file under
`/etc/fasl/geophysics-waveform-runtime.json`. It pins the source namespace and
revision, scientific interpreter/site-packages/native admission, complete import
inventory, application UID/GID, private database root and separate external
custody root. The worker command is fixed sudo with isolated distro Python and
the installed waveform supervisor plus ONE canonical job UUID. No installation
parameter is accepted through HTTP, stdin or request JSON. A checked installation
snapshot is kept through receipt verification, including cancellation, rather
than discarded after constructing argv. Windows remains its separate lane.

The closed installation configuration v2 also pins the isolated distro launch
interpreter separately from the scientific interpreter. The prelaunch operational
binding has exactly five fields: configuration, scientific interpreter,
environment and invocation SHA256 plus the complete source-hash map. The
invocation includes the one job UUID, fixed argv, launch interpreter digest,
working root and fixed environment. Terminal records compare to the independently
retained snapshot before success OR cancellation classification. Historical
read/export validation uses the recorded binding, never today's configuration.

The root helper forks a reader before SQLite/WAL/original opens; that reader
closes inherited root descriptors and irrevocably drops groups/GID/UID. It reads
the current running job, project owner, dataset, both dependency rows and both
asset/source relations in one bounded read transaction. All generated storage
keys, closed request, scientific/implementation identities, versions/rights and
original byte counts/hashes must agree. Only bounded JSON and base64 snapshots
return over anonymous pipes. Root never follows worker-controlled SQLite paths.

An exclusive root-owned plan precedes new custody directories and input copies.
At most four outstanding plans and 80 MiB held-input debt and at most256 bounded
64 KiB receipts are allowed. These are operational retention bounds, not changes
to any scientific input, scratch, CPU, memory or timing envelope. Unknown names,
links, owners, missing/changed plans and exceeded bounds refuse launches without
deletion. Originals, requests and operational files live beneath the configured
external custody root; `/run` is not application working storage. An operational
lock can use manager runtime IPC without becoming a raw-copy destination.

Configuration v3 also fixes a disjoint external scientific-work root. This
root-owned non-writable traverse-only mount anchor contains empty per-run targets,
not originals, plans, root receipts or host scratch copies. The manager mounts the
unchanged private scientific tmpfs at one exact random run target before the
scientific UID enters it. Root custody remains inaccessible to that UID; the
scientific user does not acquire application/root groups merely to traverse
private ancestry. The native observer retains the actual namespace descriptor,
charges every scientific byte under the unchanged scratch envelope, verifies
scope extinction and removes only its known empty target after handle closure.
Unknown targets preserve debt and refuse admission. The mount anchor is configured
from an external device temp/data root, never /run or system temp, and is absent
from HTTP/job argv. Actual POSIX `200/CHDIR` failures cannot be counted as guard
controls or hidden by permissive drvfs modes.

The existing descriptor-bound guardian and fixed scientific supervisor execute
inside internally constructed custody. Caller CANCEL/EOF is checked before ACK
and during scientific wait; only exact owned scopes are stopped. A full bounded
installation receipt binds job/request/dataset/source versions, installation,
import closure, stage identity, original snapshots, native receipt/release and
extinction. Missing readback never becomes cancelled or success. The worker holds
its ordinary stage before launch, verifies exact retained export/native/receipt
bytes and source-bound custody, then uses existing scientific verification and
transactional publication. Successful exact cleanup follows the commit only;
failed/uncertain stages and root debt remain recoverable. No fourth SQL artifact
or numerical-method change is required.

The outer result may include `linux_execution` and `linux_installation` only as
a complete pair. The first is a closed65536-byte native terminal graph, the
second is the exact five-field prelaunch binding already carried by that graph.
The historical `app/waveform_linux_execution.py` validator binds the retained
job/request/dataset/source identities, stage/custody, unchanged native resource
receipt/release, complete guardian removal and final counters. Measured success
also binds the actual calculation/member inventory, scientific status and
projected charge resources. Terminal quiescence cannot precede the native final
seal. Cancel/caller-loss retain exact matching timing and extinction evidence.
Native uint64 monotonic stamps remain separately bounded; scientific metadata
keeps its existing JS-safe integer grammar. Historical reads never inspect or
adopt the current installation. Original Windows results without the pair keep
their existing result grammar and make no installed-Linux claim.

In the installed nonroot caller model, the independent guardian also holds the
inherited read end of the worker's anonymous stdin pipe before native submission.
It polls readable/HUP/error without consuming bytes, so the root observer remains
the single closed-frame parser. Caller loss or pending control drains the exact
scientific units even if the root observer is paused. Partial/invalid control may
fail closed but is never labelled a successful cancellation without the complete
frame, independently matched installation and terminal extinction receipt.
The descriptor must be a read-only anonymous pipe, never a request-selected path,
numeric caller PID, root SQLite/lease or socket. The already reviewed root guardian
operational limits and scientific B60/S57/2s quiescence bounds are unchanged.
Successful science closes that guardian before the separate postcommit COMMIT
frame; COMMIT is not admitted while scientific execution can still be live.

### Complete interpreted runtime closure

The inventory includes exact names and file/directory/link identities, owners,
modes, sizes and hashes across every admitted stdlib, dynamic-module and selected
scientific import root, plus the exact source namespace and pinned mapped ELF
closure. Immutable ancestor ownership and link targets are checked, not only
listed file bytes. Unknown additions, missing names, byte/mode/identity changes,
escaped links and startup hooks refuse execution. Fixed isolated no-site startup
avoids executing `.pth`, sitecustomize or usercustomize before the barrier;
selected scientific modules are added only after native ACK. Absent startup/search
paths remain absent. An independently measured actual import/search/mapped-image
receipt precedes installation; regenerating a digest is not acceptance.

Closure v2 records every startup search path and directory-root identity; a
bounded isolated no-site probe must reproduce the sealed search list. Existing
inactive wheel `.pth`/customization files, if present in an independently reviewed
installation, are inventoried by exact name and hash as inactive hooks. No hook
is executed or newly adopted; an addition or any change refuses the exact census.
Immutable code/native images may retain pinned hardlinks; uploaded originals
must always remain single-link no-follow regular files.

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
