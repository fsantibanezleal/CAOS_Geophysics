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
The ordinary waveform source fingerprint is the complete installation source
map. Linux availability checks the fixed snapshot as the nonroot application
identity; the waveform dispatcher delegates to the installed client before any
legacy context file, generic CLI argv or observer PID signal is used. Windows
continues to use its selected Windows context and existing copy publication.
Historical root qualification commands remain scientific mechanics tools, not
an alternative production queue path.

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
The unprivileged fixed launcher starts at `/`, not inside inaccessible root-only
custody. After privilege transition and checked bootstrap, only the root helper
enters the fixed custody directory. Both working directories are installation
behavior, never a caller-selected path or permission workaround.

The ordinary installation snapshot must not attempt directory entries inside
root-only custody. It checks the fixed custody leaf with no-follow lstat as a
root-owned directory with exact0700 mode and checks every readable ancestor for
repository markers. Root bootstrap separately checks the interior repository
marker and complete closure before any owned reader or native launch. All other
working roots retain their interior and ancestor repository checks. A missing,
linked, nonroot-owned or differently permissioned custody leaf refuses the
ordinary snapshot. No PermissionError fallback, readable custody, chmod repair
or successful native claim is introduced. Pure role controls and actual nonroot
installed snapshot precede the whole native queue qualification.

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

The scientific UID has search, not directory-read authority on these fixed
traverse-only ancestors. On Linux, held ancestor leases therefore use
`O_PATH|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC`; the final directory still uses
`O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC` for actual inventory/file operations.
Ancestor handles remain descriptor-relative, type/identity-checked and retained
for the entire lease. They cannot enumerate an inaccessible custody/anchor or
replace a readable final export handle. Windows handles and non-Linux POSIX
behavior remain unchanged. Do not chmod an existing parent to make traversal
work. Gate: `tests/data/test_waveform_search_handles.py` on ordinary nonroot
Linux storage (search-only ancestor, final readable handle, link refusal and
replacement identity), followed by actual changed-source installed native queue.

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
Postcommit root cleanup compares every relative directory/member name, byte
count and digest against the internally constructed input/admission/native and
sealed export inventories before the first unlink. Unknown nested entries are
not retrospectively adopted as cleanup authority. Startup debt traversal is
finite, closed by generated run names and existing export-member grammar, and
rejects unsafe links, owners, modes or unresolved scientific mount contents.

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

### Held-stage publication without a third copy

For the installed lane, root custody and the verified ordinary export are the
two retained copies. Publication adopts the ordinary export with Linux
`renameat2(RENAME_NOREPLACE)`, never another member copy or overwrite. The worker
retains stage and export descriptors; the transaction checks source/cancel/quota
and all exact destination paths before the rename. Source entry, held export and
generated target-parent descriptors must agree on identity and filesystem.
Reopen the same held export before and after installation using the existing
bounded scientific reopener. Rebind the generated destination through no-follow
ancestor descriptors and compare it to the held export immediately before
metadata installation and again before SQL success; independently reopen the
installed metadata against its exact digest. A changed source/destination, unsupported atomic
operation, existing target or uncertain commit retains every remaining byte and
cannot publish success. There is no cross-device copy fallback.

The root receives COMMIT only after the ordinary transaction has committed.
After its exact CLEAN acknowledgement, validate persisted result/member rows
again. Then remove only the verified receipt-only stage; adopted published
members are not stage cleanup targets. Failed/unknown stage names, replaced
identities or acknowledgement failure retain debt for exact recovery. These
storage operations add no numerical solver, scientific resource allowance,
SQL artifact, public installation parameter or privileged API access.

The genuine-science held-publication component gate uses actual calculation,
SQLite, member downloads, ZIP reopening, reconciliation and deletion but authored
root/resource records. Its inode-preservation checks prove no third member copy,
not installed authority or native resource containment. Actual nonroot filesystem
controls cover existing targets, replacement identities, unavailable atomic
operations, uncertain acknowledgement and receipt-only stage cleanup. An
unsupported filesystem is retained as failure, never replaced by copy fallback.

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

### Ordinary client lifetime under the existing writer lease

Both waveform producers create a new shared `.job-staging` parent with mode
`0700`, matching the restrictive new-root profile/generic producer correction.
Existing parents are not chmodded or repaired. Recovery's owner/mode checks
remain unchanged; an old unsafe parent requires exact recovery, not relaxed
admission. Mixed-method qualification must check the actual producer/recovery
sequence on ordinary POSIX storage with the same restrictive creation mode.

The caller's existing singleton and any enclosing common all-writer lease must
cover process creation/adoption, helper reap and stdout/stderr EOF, not only the
scientific terminal. Shield the single creation task against caller cancellation;
adopt that exact returned process even if cancellation arrives during creation.
Close its anonymous stdin on failure/cancellation and keep bounded readers
draining refused/oversized output until EOF. Refusal is signalled immediately,
but does not strand the privileged writer on a full pipe. Repeated cancellation
cannot cancel this mandatory cleanup or release held stage descriptors early.

The normal five-second postterminal wait may report uncertainty, never authorize
lease release with a live helper or retained stream writer. Mandatory cleanup
keeps the original caller alive until the exact helper is reaped and both streams
reach EOF; an uncertain reap retains authority instead of a second timeout escape.
This is ownership containment, not an increased scientific time allowance or a
successful extinction receipt. No root PID signal, new lock, privileged database
write, common-lease implementation or profile recovery change is introduced.
Actual ordinary child/lock controls verify creation cancellation, repeated cancel,
oversized streams and retained descendant writers. Full root/native queue remains
a separate qualification gate.

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

An inactive distro hook may be a link to a file outside one directory inventory.
It remains outside admission unless its exact resolved target is separately
declared in the closed immutable closure graph. The optional
`inactive_link_targets` member records only root-owned no-follow regular targets
of existing inactive sitecustomize/usercustomize/PTH names, with full file identity,
mode, link count, byte count, modification/change timestamps and SHA256. No target
is discovered and adopted during checking. Existing inward links use their exact
inventoried resolved regular member rather than adding an external target.
Every declared target must be used by an exact inventoried inactive link; unknown,
unused, changed or unbound links/targets refuse. Isolated no-site startup remains
mandatory and no hook is executed. Old closures without this member continue to
reject every outward link. This completes the existing interpreted-closure
requirement; it does not widen search paths, request authority or scientific caps.

The same existing complete-closure obligation covers a distro development
libpython link whose resolved ELF image is outside its stdlib directory. Optional
`native_link_targets` binds only libpython versioned shared-image names, using the
same exact file-identity/byte/hash record. The target must also be present with
the identical digest in the existing native-image map; no new native executable
or import path is admitted by following a link. Check the ELF signature without
loading the image. Every target must be used by its inventoried library link;
unknown, unused, hook-as-native and unbound ordinary outward links still refuse.
Absent optional graphs preserve the strict historical outward-link refusal.

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
The installed kernel may also emit the exact cpu.stat field
`core_sched.force_idle_usec`. Accept that bounded numeric kernel field without
using or subtracting it from usage/user/system lifetime counters. Other dotted
field names remain invalid; required names, duplicate/name/value checks,
counter monotonicity and CPU ceilings remain unchanged. Capture actual kernel
bytes and test this ABI case before repeating changed-source native queue.
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

Seal the scientific sampler only after successful child exit and the existing
stable zero-task final barrier. Stop/join its thread, check every retained failure
and final-ready invariant, then retain that exact final row before observer-side
scientific export reopening/hashing/copying. Those post-exit observer operations
are not scientific tasks or a reason to relax the100ms scientific sampling cap.
Immediately before native release, reread the held accounting scope's CPU/task/
peak/event values and require exact equality to the sealed empty row. A late
failure, changed counter or task refuses, never produces measured success.
The actual nominal3 q06 post-exit551294670ns sampler gap remains a failed
receipt. API resource-validation errors must also classify as unproved terminal
failure and retain stage/debt, not escape leaving a running SQL job. Gates:
closed final-seal and invalid-terminal classification regressions, followed by
changed-source installed nominal/upper qualification with original limits.

An exact Linux final receipt and digest-bound release acknowledge measured scope
extinction and owned handle closure. Portable resources discriminate positively
between linux_cgroup_charge and windows_job_committed; neither is RSS. All
method/runtime/host acceptance flags remain false. Old admitted jobs reject
changed implementation hashes; merged source/runtime contexts need qualification.

Ordinary packet/counter tests are not OS proof. Actual original, nominal/upper,
cancel/observer-loss, exited-CPU, memory/scratch/gap/process controls and API/
restart/delete/export/browser qualification are separate gates. WSL mechanics
cannot establish the single ML VPS gate. No public activation follows here.

### Pending caller frame and exact failed-service retirement

An independent guardian may drain a live scientific child while the observer
is still checking launch/namespace membership. On a refused native operation,
the observer checks its original held caller pipe before classifying the
terminal. Only the complete unchanged CANCEL frame or actual pipe EOF sets
the caller reason and timestamp; malformed/partial frames do not invent cancel.
Cleanup still requires retained zero-task counters and original quiescence.
A killed constructor-owned service can remain failed after successful stop.
Reset only that exact generated service after the held accounting descriptor
reports zero tasks and manager readback proves MainPID0, ControlPID0 and an
empty ControlGroup. Then require the original strict inactive/not-found
readback. Failed state, good RSS or missing readback is never extinction proof;
no unknown unit, numeric root signal or counter reset is authorized. Gate:
closed frame/failed-service controls, then fresh installed original CANCEL/EOF
under unchanged limits. The first failed installed cancellation remains retained.
