# Missing-receipt custody design

Status: implemented candidate; portable controls validated, native/integration gates open

## Authority and boundaries

The reviewed failure is root observer death before finish_custody. Neither the
root execution receipt nor stage/linux-execution.json exists. Existing recovery
requires both. Add a separate literal --recover-incomplete UUID; do not weaken
either reader. Privileged SQLite/input reads remain in the irrevocably dropped
reader. The closed eleven-file root import closure is unchanged; constructors
live in its already pinned profile_linux_exec module, native operations in the
supervisor. All new roots remain installation-configured external device roots.

The old custody-plan/v1 remains byte/schema compatible. New immutable 0440 root
records UUID.custody-intent.json and UUID.custody.json record complete installation,
owned relation hashes, held stage device/inode, then UUID/inputs/scratch identities
and exact original/dataset/wrapper device/inode/size/hash. They are fsynced before
mkdir and before guardian/manager respectively. A crash before the second record
is deliberately refused. No surviving identity is reconstructed from a current
path or a terminal successful receipt. Retain these records as bounded evidence;
count them in the existing 256-record/64-KiB census, reserving new records before
admission. Four jobs/16-MiB snapshot limits are not raised.

## Root recovery

Hold the root singleton. Independently bind the terminal failed/cancelled job and
all owned relations to the historical installation and launch. Require absence
of execution receipt and presence of both immutable new records. Validate known
root copies against the manifest; absent declared copies are permissible only
because their exact prelaunch authority already survived (normal input cleanup
can precede observer death). Unknown or structurally incomplete directories,
changed identities and nonempty scratch refuse. Never traverse/remove unknown
scratch. No recursive delete is used.

Fresh manager and kernel evidence covers the science service AND independent
guardian scope before inspection, again before deletion, and on every return.
Persist UUID.incomplete-recovery-intent.json before mutation; preserve it and
the prelaunch records. Resume only the declared subset after fresh verification.
The closed incomplete-recovery/v1 records installation, held stage identity,
authority digests and fresh terminal evidence. It explicitly states the execution
receipt is absent; it contains no peak resources, result acceptance, DONE,
originals_reverified or invented successful execution.

## Ordinary archive / M01 boundary

Separate recover_incomplete_profile_job entry holds the existing worker singleton.
It binds the complete eleven-field ownership using the existing v2 helper, then
holds the stage and archive parents. Only failed/cancelled jobs with no published
or uncommitted derived result are eligible. Root-returned stage identity must
equal the held directory, and linux-execution.json must remain absent. Declared
partial result.json, linux-stderr.txt and stderr.txt are bounded stable single-link
ordinary-owned files; their contents are unadmitted evidence, not parsed science.

Use .profile-incomplete and profile-incomplete-stage/v1 with exact ownership,
installation, stage identity, member inventory and incomplete recovery. Write an
exclusive fsynced UUID.intent.json, no-replace same-filesystem rename, verify
contents, write manifest.json, verify again. Resumption must compare the stored
intent before further mutation. Preserve state/derived/originals. Count old v2
archives plus this namespace within the existing 128-stage/256-MiB ordinary caps.

M01 must admit a DISTINCT incomplete custody descriptor: embed exact manifest,
its literal bytes/hash, canonical installation hash, the original eleven-field
ownership and charged_bytes = two manifest copies + actual member bytes. Do not
encode it as gravity job_stage or successful execution-v2. Parent owns descriptor
admission, shared all-writer lease and original deletion transaction. This leaf
does not edit those files or claim restart/deletion integration before that gate.

The public incomplete_descriptor constructor exposes precisely that separate
geophysics.profile-incomplete-custody/v1 boundary. Incomplete member records bind
native unsigned-64 device/inode plus bytes/hash; this does not change scientific
quantity precision or the existing ownership-v2 member grammar. Census requires
every archived directory's matching exclusive intent and exact literal manifest.
An interrupted manifest still in stage is charged in full before archive rename.

## Recovery helper lifetime correction (pre-code refinement)

Independent review of the initial candidate identified that a second timed wait
in finally could return with the privileged recovery helper still alive, or be
interrupted by cancellation. Replace it with a separately held, shielded reap
and EOF-drain task. Catch repeated caller cancellation only while that barrier
is incomplete, then propagate cancellation after cleanup. Do not release held
descriptors or return through the caller's lease context while the created helper
can still mutate custody. No signal or forced original cleanup is introduced.
The wait is fail-closed, not a new successful recovery or scientific receipt.
Use bounded retaining readers that continue discarding overflow until EOF;
stream collection timeout must not cancel them and deadlock a writer. Actual
ordinary Python subprocess controls test this async lifecycle and the original
singleton, separately from still-pending privileged Linux guardian/queue proof.

## References and claim limits

[Kernel cgroup v2](https://docs.kernel.org/admin-guide/cgroup-v2.html) defines
recursive populated evidence; cgroup.procs alone is insufficient.
[open](https://man7.org/linux/man-pages/man2/open.2.html) and
[rename](https://man7.org/linux/man-pages/man2/rename.2.html) ground held descriptor,
no-follow/exclusive creation and atomic namespace transitions. Portable authored
controls do not demonstrate actual Linux kernel, manager or privileged custody.
