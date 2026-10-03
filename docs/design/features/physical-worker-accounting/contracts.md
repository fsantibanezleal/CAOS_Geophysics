# Physical accounting strict proposed contracts

Date: 2026-10-03. Status: planned; no schema, request, API response, migration,
module manifest or source-bundle change is implemented/authorized here.
Read [design](design.md) and [requirements](requirements.md) as prerequisites.
These are native-controller/private evidence contracts for later review, not
permitted additions to current 0003 recovery inventory or public admission.

## 1. Type rules and encoding

All records are UTF-8 canonical JSON for hashing: sorted object keys, compact
separators, no BOM, no NaN/Infinity, duplicate keys rejected before construction.
Digest covers exact canonical bytes excluding no fields unless explicitly stated.
Receipt has no self-digest key: its digest is stored separately in an existing or
future explicitly reviewed identity record. JSON integer means integer, never
bool, float, numeric string or null unless listed nullable. Unit conversion uses
checked native width and a checked int64 ns domain. No ambiguous seconds floats.
Every object has an exact named key set and variant; unknown keys/variants reject.

UUID fields use lowercase canonical UUID strings; SHA-256 values are exactly 64
lowercase hex chars; Git commit pins exactly 40 lowerhex. Native handles, pointers,
PIDs and private cgroup/unit paths are not public identifiers or JSON authority.
An integer handle copied from a client cannot select an OS object. Native launch
calls receive validated owned handles/Fds through an internal interface only.

Controller JSON/frame cap 16384 bytes BEFORE allocating/parsing, max depth 6,
max total nodes 256, no user strings exceeding 128 UTF-8 bytes. Counter control
file read cap 4096 bytes, at most 32 lines, key length <=64, uint64 decimal no
sign/leading plus/space, duplicate keys rejected. Required semantic fields have
explicit allowlists below; extra kernel fields require an exact profile registry,
not a wildcard future-kernel acceptance. Unknown interfaces never select another
accounting method. Native setup/ack frame 4096 bytes; control-message cap 1024.

## 2. Start frame

Exact keys: schema, attempt_id, job_id, method_id, input_sha256,
request_sha256, source_commit, runtime_sha256, module_set_sha256,
profile_sha256, object_token, limits, parent_limits.

- schema: literal physical-accounting-start-1.
- method_id: exactly gravity.station-corrections/v1 or
  gravity.equivalent-source-transform/v1, as proposed in the physical SDD.
  This does not register either method with the current worker/API.
- object_token: internal random canonical UUID, not a path or runtime job handle;
  controller assigns it to a fresh object, never opens an existing named job.
- Other identifiers: the strict UUID/digest types above, bound by worker
  ownership and request identity before launch; a token alone is not authentication.
- limits exact keys: cpu_ceiling_ns, cpu_stop_ns, cpu_margin_ns,
  wall_ns, rss_bytes, scratch_bytes, result_bytes. Exact lane values from design;
  no submitted override, scaling, NaN or fallback lane.
- parent_limits exact keys: cpu_ceiling_ns, control_bytes, receipt_bytes,
  stdout_bytes, stderr_bytes. CPU 5000000000/10000000000 by lane;
  control_bytes=16384, receipt_bytes=65536, stdout_bytes=65536,
  stderr_bytes=65536. Logging counts in scratch; a byte-cap crossing kills,
  never writes an unbounded trace and truncates afterward.

Interpreter, argv, credentials and object location are resolved exclusively from
the reviewed private profile. No client path, command, environment, provider or
alternate executable is included. Worker/guardian heartbeat and cancel frames
have exact keys schema, attempt_id, sequence, action; schema literal
physical-accounting-control-1; sequence strictly increasing uint64;
action exactly heartbeat or cancel. Duplicate/replayed/stale attempt frames
fail. EOF or invalid frame stops without waiting for database progress.

## 3. Platform admission profile

Exact top-level keys: schema, status, platform, os_identity_sha256,
runtime_sha256, controller_sha256, source_commit, module_set_sha256,
context_sha256, timing, evidence, approval_receipt_sha256.

schema: physical-accounting-profile-1. status: CLOSED or REVIEWED_ADMITTED;
platform: windows-job-x64-1 or linux-cgroup2-x64-1 only. CLOSED records may have
null identity/context/timing/evidence/approval fields; they confer no authority.
REVIEWED_ADMITTED requires all complete nonnull strict fields plus actual
test receipt hashes; a docs commit cannot set it. No automatic discovery or
inherited activation from MT, builder, physical source-byte or storage receipts.
Both initial platforms here are CLOSED with no profile file created.

context_sha256 identifies a private, fully reviewed platform context record;
it cannot hide unspecified capability behind a digest. Its underlying content
must be supplied to MAIN and validated by actual OS gates. Windows record binds
OS build/SDK ABI, effective token/session, controller process security/ACLs,
whole job chain and nonmutable breakaway/duplication/broker-denial policy.
Linux record binds kernel build, mount/hierarchy/directory identities, delegation
owner, controller and compute credentials/capabilities/ACLs, syscall/seccomp
policy, control-file registry, manager-death configuration and permission proofs.
Private records are evidence, not public-repo secrets or self-issued authority.
Missing actual launch context keeps Linux closed, not a guessed Delegate unit.

timing exact keys: max_logical_cpus, observe_gap_ns, visibility_lag_ns,
kill_interval_ns, rounding_reserve_ns, margin_ns, heartbeat_interval_ns,
heartbeat_grace_ns, drain_timeout_ns, final_spacing_ns.
Exact maxima/design values: 8,20000000,50000000,250000000,1000000,
3000000000,100000000,500000000,2000000000,20000000 respectively.
Smaller measured bounds do not expand B/S or substitute a different ABI.
evidence exact keys: abi_sha256, launch_sha256, lifetime_sha256,
no_escape_sha256, threshold_sha256, timing_sha256, death_sha256,
finalization_sha256, parent_bounds_sha256. All are actual-platform receipts,
not mock receipts or a status string. No unknown-OS lifetime polling fallback.

Profile identity becomes stale after any relevant OS/kernel/SDK/controller/runtime,
credentials/ACL/delegation/manager, policy or effective CPU topology change.
Every launch rechecks actual identity. MAIN approval authorizes the identified
profile/evidence, not every future machine with the same OS name.

## 4. Counter samples and native conversions

Each private bounded sample exact keys: schema, attempt_id, object_token,
sequence, platform, monotonic_ns, query_duration_ns, native, cpu_ns, active.
schema: physical-accounting-sample-1. sequence/monotonic_ns strictly increasing;
query_duration_ns nonnegative, complete-observation gap <=20 ms; samples preserve
native and computed counters, with nondecreasing cumulative totals. Active is a
variant, not root.is_running. Samples are controller evidence, never client
measurements. Persist streaming records with an exclusive file and running hash;
max 32768 samples and max 16 MiB sample file (both charged in scratch).
Do not buffer all samples in memory; cap before emitting a record.

| Platform | Exact native keys | Exact active keys | Charge |
| --- | --- | --- | --- |
| windows-job-x64-1 | total_user_ticks, total_kernel_ticks | active_processes, total_processes, limit_terminated_processes | (user+kernel)*100 ns |
| linux-cgroup2-x64-1 | usage_usec, user_usec, system_usec | populated, root_reaped, adopted_reaped | max(usage,user+system)*1000 ns |

Windows ticks are int64 >=0. DWORD process counts in [0,2^32-1]; active <=32
under the required job cap. limit_terminated_processes is NOT all exited
processes. Linux counts are uint64, populated exactly 0/1, reaped flags strict
bool. Native sum/conversion and final cpu_ns must fit int64 [0,2^63-1]; overflow
fails, never saturates or wraps. Linux readback can contain documented controller
fields in the exact approved registry, but receipt native keys remain just these
three. Counter-subfield skew is validated independently; do not require false
instantaneous equality of usage to user+system or erase mismatch evidence.

Windows ThisPeriodTotal fields never determine charging. Linux cpu.stat.local,
CPU quota/throttle counters and /proc PID stats never replace these fields.
Zero is legitimate only when returned by a validated fresh/final object, never
the fallback for AccessDenied, ENOENT, invalid returned length or destroyed job.
Missing final counter is represented by null only under the uncertainty receipt
variant, not the complete variant.

## 5. Final private receipt

Exact top-level keys: schema, attempt_id, job_id, object_token, platform,
binding, verdict, stop_reason, limits, final, timing, samples, controller,
cleanup, nonclaims.

- schema: physical-accounting-receipt-1.
- binding exact keys: input_sha256, request_sha256, source_commit,
  runtime_sha256, module_set_sha256, controller_sha256, profile_sha256.
- verdict exactly complete_within_budget, failed_final_overbudget,
  failed_control, or uncertain. Only first may be accounting-publication-eligible.
  Numerical/process success, cancellation and DB-publication status are separate.
  Accounting eligibility also requires stop_reason=clean_exit, no earlier
  failed control, complete final state and subsequent validated release/parent
  acknowledgment. A CPU-limited attempt below B is still a failed computation.
- stop_reason: exactly clean_exit, cpu_limit, wall_limit, memory_limit,
  scratch_limit, user_cancelled, output_limit, worker_lost, controller_lost,
  unexpected_descendants, identity_changed, counter_invalid, observe_gap,
  kill_timeout, startup_failed or receipt_lost. A clean numerical exit does not
  override a prior control failure. User cancellation remains cancellation.
- limits: exact start-frame limits, unmodified.
- final complete variant exact keys: status, native, cpu_ns, empty_verified,
  root_exit_code, final_reads, monotonic_ns. status literal complete;
  native is the platform variant above; empty_verified=true; final_reads=3;
  root_exit_code checked int32 or uint32 by platform. A lost/unknown exit status
  cannot be called complete. Final reads are equal, >=20 ms apart after drain.
- final uncertain variant exact keys: status, native, cpu_ns, empty_verified,
  root_exit_code, final_reads, monotonic_ns. status literal unavailable;
  native/cpu_ns/root_exit_code/monotonic_ns=null, empty_verified=false,
  final_reads=0. Prior observations remain in samples, not relabelled final.
- timing exact keys: started_ns, stopped_ns, drained_ns, finalized_ns,
  max_observe_gap_ns, max_query_duration_ns, kill_interval_ns,
  visibility_evidence_sha256. Monotonic offsets relative to controller launch,
  not UTC or values compared across process clock domains. unavailable entries
  are null only for uncertain; no negative/impossible ordering accepted.
- samples exact keys: sha256, record_count, byte_count; validated caps above.
- controller exact keys: cpu_ns, wall_ns, peak_private_bytes;
  actual controller-plus-worker pre/post overhead counters, not estimated
  subtraction from science CPU. int64/byte ints, with private-memory ceiling
  67108864 bytes and proposed 5/10 s CPU cap. Parent CPU evidence includes exited
  fixed launch/controller processes; current worker has no such proof yet.
- cleanup exact keys: object_drained, object_released, receipt_acknowledged,
  filesystem_debt_resolved. First three bool; filesystem_debt_resolved is false
  here until separately approved storage integration proves it. The receipt is
  sealed before acknowledgment/release and therefore object_released=false and
  receipt_acknowledged=false; exact subsequent release acknowledgment is
  separate, never mutates these sealed bytes.
- nonclaims exact keys: production_approved, physics_certified,
  recovery_adapter_approved, hard_zero_overshoot_guaranteed; all false.

Release acknowledgment exact keys: schema, attempt_id, object_token,
receipt_sha256, object_released, controller_cpu_ns, worker_cpu_ns,
parent_total_cpu_ns, parent_budget_passed. Schema literal
physical-accounting-release-1; strict identifiers; object_released=true;
parent_total_cpu_ns is checked sum of final controller SELF CPU plus worker
per-attempt overhead, within the lane's parent limit. parent_budget_passed=true
is independently checked, not trusted from a boolean. Max 4096 bytes, immutable
private exclusive storage; its digest lives separately. The worker sends its
bounded durable-receipt acknowledgment before object release; controller
reports release and final SELF CPU. Worker adds its final overhead delta and
seals this acknowledgment before separately reviewed publication eligibility.
Lost acknowledgment/final parent counter remains unavailable/held; no success
from the preliminary receipt alone. Storage transaction/ack atomicity is still
the separately approved storage owner's responsibility.

Main's private execution-admission authority is separate from this receipt.
Content digests are identity/integrity, not a signature, OS trust or proof of
latest deletion authority. Receipt loss during abrupt death or uncertain storage
acknowledgment is not recoverable by fabricating a final counter from the last
sample. File receipt storage and recovery acceptance require a separate exact
revision/schema change; this unit has none.

## 6. Safe error contract

Internal native errors retain numeric GetLastError/errno and fixed operation
enum privately, with no format-message trace, path, input value or environment.
Public mapping proposal has exact keys code, message, retryable; message is fixed
ASCII <=96 bytes, code <=48 bytes, retryable=false. It is not implemented in API.

| Code | Fixed message | Action |
| --- | --- | --- |
| accounting_admission_closed | Physical CPU accounting admission is closed | No launch |
| accounting_launch_failed | Contained execution could not start | Never resume/GO; stop exact created object |
| accounting_counter_invalid | CPU accounting could not be verified | Kill; failed/held if drain uncertain |
| accounting_cpu_limit | Aggregate CPU budget was reached | Whole-object stop; no publication |
| accounting_observation_gap | CPU observation timing could not be verified | Stop and close profile |
| accounting_containment_failed | Execution containment could not be verified | Stop and close profile |
| accounting_termination_uncertain | Execution termination could not be verified | Held; block next admission |
| accounting_receipt_unavailable | Final CPU receipt is unavailable | Failed/held; preserve stage/debt |
| accounting_parent_limit | Controller resource budget was reached | Stop and fail |

Cancellation uses the existing user_cancelled outcome through separately reviewed
integration. No error includes private project/source/citation values, PID, unit,
path, native handle, process command line or raw stderr. Unknown codes reject,
not an opportunity to leak a generic exception string.
