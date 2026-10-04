# Pure accounting protocol exact contracts

Date: 2026-10-03. Status: exact pure contract MAIN-approved at2c94da4 and
implemented; [local evidence](implementation-evidence.md). No actual measurement.
Parent contract pin: 3959ffc29eb4f93e0cca04fdc3154eca7ea7ddca.
Read [design](design.md), [requirements](requirements.md) and
[validation](validation-plan.md). These are strict subsets/refinements of that
private protocol, not an extension to runtime recovery, admission or APIs.

## 1. Bounds, types and discriminators

Each supplied frame is exact builtin bytes, canonical ASCII JSON object with
sorted keys, compact separators, no BOM, escapes, arrays or trailing LF. An LF
is added only to the incremental sample digest, not to the supplied frame.
All keys and shapes below are exact; no optional/unknown keys or schemas.

| RecordKind | Exact schema | Ingress byte ceiling |
| --- | --- | ---: |
| START | physical-accounting-start-1 | 16384 |
| CONTROL | physical-accounting-control-1 | 1024 |
| SAMPLE | physical-accounting-sample-1 | 4096 |
| RECEIPT | physical-accounting-receipt-1 | 16384 |
| RELEASE | physical-accounting-release-1 | 4096 |

Ingress receipt bound is intentionally stricter than the parent's 65536-byte
sealed storage ceiling; the start frame still requires receipt_bytes=65536.
This module supplies no transport/storage reader or change to its contract.
Profile, native setup, kernel control-file, public result and future variants
are NOT supported records, even when their contents are otherwise valid JSON.

Before decode/tree/int allocation: object depth<=6 including root at depth1,
nodes<=256 (each object, key and scalar counts once), members/object<=32,
key<=64 ASCII bytes, string value<=128 ASCII bytes, numeric token<=20 magnitude
digits. Fixed-size scanning state only; no token slicing first. Integers must
lexically fit [-2147483648,18446744073709551615] by sign/length/decimal comparison
BEFORE int conversion; field validation then narrows this range. No float,
exponent, nonfinite constant, leading plus/zero, negative zero or whitespace
canonicalization. JSON booleans/null are accepted only at fields listed below.
Duplicate keys reject via the bounded internal JSON hook, never last-key wins.

Every numeric field requires type(value) is int, never bool/int subclass or a
coercible object. Every boolean requires type(value) is bool, never 0/1. Exact
str means builtin str, not an arbitrary object or subclass. Identifier scalar
arguments are length-checked BEFORE format inspection/copying; no str(value).
UUIDs: nonnil, lowercase canonical 36-character 8-4-4-4-12 hex (no inferred UUID
version authority); SHA-256: 64 lowerhex; Git commit: 40 lowerhex. No paths,
native handles, PIDs, source buffers, callers' dicts or callbacks accepted.

I64=9223372036854775807; U64=18446744073709551615; U32=4294967295.
Ns, cumulative derived CPU and byte-count scalars use 0..I64 unless a smaller
bound is listed. Sequence uses 1..U64 and advances by EXACTLY1; reject exhaustion
before addition. Unknown RecordKind/Platform, method, reason or safe-code input
does not select defaults or another format. A malformed/oversized input never
gets attached to errors, logs, result objects or a retained diagnostic buffer.

## 2. Start, limits and control

START exact keys: schema,attempt_id,job_id,method_id,input_sha256,
request_sha256,source_commit,runtime_sha256,module_set_sha256,profile_sha256,
object_token,limits,parent_limits. IDs use the scalar types above. All identity
fields become immutable session bindings; method_id has only these two values:

| Limit | gravity.station-corrections/v1 | gravity.equivalent-source-transform/v1 |
| --- | ---: | ---: |
| cpu_ceiling_ns | 60000000000 | 240000000000 |
| cpu_stop_ns | 57000000000 | 237000000000 |
| cpu_margin_ns | 3000000000 | 3000000000 |
| wall_ns | 120000000000 | 300000000000 |
| rss_bytes | 805306368 | 1610612736 |
| scratch_bytes | 268435456 | 536870912 |
| result_bytes | 67108864 | 67108864 |

limits exact keys are the seven row names, with EXACT values (not lesser
submitted overrides). parent_limits exact keys cpu_ceiling_ns,control_bytes,
receipt_bytes,stdout_bytes,stderr_bytes: CPU respectively 5000000000/10000000000,
then 16384,65536,65536,65536. These constants are declarations, not measurements.
limits_for returns the frozen lane values; no optional config/profile/env input.
LaneLimits exact scalar fields: method_id,cpu_ceiling_ns,cpu_stop_ns,cpu_margin_ns,
wall_ns,rss_bytes,scratch_bytes,result_bytes,parent_cpu_ceiling_ns,control_bytes,
receipt_bytes,stdout_bytes,stderr_bytes. No mutable nested configuration returned.

CONTROL exact keys: schema,attempt_id,sequence,action. action is heartbeat or
cancel. Its sequence channel starts1, independent of sample sequence. Identity,
phase and sequence are checked before updates. Heartbeat carries NO time: the
module cannot validate real heartbeat interval/grace, EOF or controller liveness.
Cancel latches failed computation and STOP_REQUIRED; an explicit request_stop
with user_cancelled and a supplied timestamp is still required. No OS stop occurs.

## 3. Counter samples, active variants and math

SAMPLE exact keys: schema,attempt_id,object_token,sequence,platform,monotonic_ns,
query_duration_ns,native,cpu_ns,active. platform is exactly windows-job-x64-1 or
linux-cgroup2-x64-1, matching the session's explicit Platform. All times are
supplied offsets in one asserted controller-launch domain, not clock readings.
Sample times strictly increase; query_duration_ns in 0..I64, observed violation
of 20000000 ns is retained as a failed timing observation, not rewritten.
cpu_ns must EXACTLY equal checked conversion of native; no tolerance or rounding.

| Platform | Exact native keys / ranges | Exact active keys / ranges |
| --- | --- | --- |
| windows-job-x64-1 | total_user_ticks,total_kernel_ticks: each 0..I64 | active_processes,total_processes,limit_terminated_processes: each 0..U32 |
| linux-cgroup2-x64-1 | usage_usec,user_usec,system_usec: each 0..U64 | populated: exact int 0/1; root_reaped,adopted_reaped: exact bool |

Windows active_processes<=32, active_processes<=total_processes and
limit_terminated_processes<=total_processes. This latter count is NOT all exits.
total_processes and limit_terminated_processes cannot decrease across samples;
active_processes may decrease. Linux populated may change; reaped flags once
true cannot become false. These are supplied consistency checks, not no-escape
proof. Empty variant: Windows active_processes=0; Linux populated=0 and both
reaped flags=true. Whole-object finality also requires the separate drain assertion.

Windows checked sum user+kernel<=I64, checked multiplication by100 into I64.
Linux checked sum user+system<=U64, max(usage,sum), checked multiplication by1000
into I64. All native components independently nondecreasing throughout the
trace. Valid native width can still fail conversion; do not erase skew or wrap.
checked_delta_ns accepts two exact ints0..I64, requires current>=previous before
subtraction. All bounded sums/differences/products are guarded BEFORE arithmetic.
No packed C structure, ABI, binary counter input or source digest conversion.

## 4. Assertions, phase rules and bounded trace

assert_contained/started require exact bound attempt_id/object_token and at_ns
0..I64. Containment at_ns<=start at_ns. No real elapsed launch guarantee follows.
assert_drained requires these identities, stopped_ns/drained_ns0..I64,
empty_verified exact true and root_exit_code: Windows0..U32, Linux signed32
[-2147483648,2147483647]. Natural drain permits a nonzero exit, but never success.
started_ns<=stopped_ns<=drained_ns; drain must not precede the last accepted sample
or stop request. If stop was requested, stopped_ns equals its supplied request
time; otherwise it is the supplied natural-stop time. A timestamp overflow,
regression or impossible ordering fails held, not clamped.

| Current phase | Allowed event | Next phase / effect |
| --- | --- | --- |
| PREPARED | assert_contained | CONTAINMENT_ASSERTED |
| CONTAINMENT_ASSERTED | assert_started | RUNNING_ASSERTED |
| RUNNING_ASSERTED | valid control/sample without threshold violation | same |
| RUNNING_ASSERTED | cancel, CPU>=S, wall elapsed>limit or timing violation | STOP_REQUIRED; sticky failure |
| RUNNING_ASSERTED or STOP_REQUIRED | request_stop(non-clean reason) | STOP_ASSERTED; sticky failure |
| STOP_REQUIRED or STOP_ASSERTED | valid sample; heartbeat (not a second cancel) | same; cannot clear failure |
| RUNNING_ASSERTED | assert_drained without stop request | DRAIN_ASSERTED |
| STOP_ASSERTED | assert_drained with stop request | DRAIN_ASSERTED |
| DRAIN_ASSERTED | matching final sample1/2 | same, retain bounded final count |
| DRAIN_ASSERTED | matching final sample3 | FINAL_CHECKED |
| FINAL_CHECKED | matched complete receipt | RECEIPT_BOUND |
| RECEIPT_BOUND | matched release | ACK_CHECKED |
| Any phase | invalid/uncertain evidence | FAILED_HELD, no success repair |

FAILED_HELD is absorbing for eligibility. Only a correctly shaped unavailable
receipt with matching identity and current accepted trace may be retained there
as a bounded diagnostic; all other mutators reject. It cannot move the phase.
eligibility is read-only in any phase. Record decode/conversion functions are
stateless; a session wraps their fixed ProtocolError and latches held. No reset,
retry-to-success, replay, mutable binding, default platform or override callback.
Repeated stop/drain/receipt/release assertions reject; cancel after a first cancel
rejects. Reasons are exactly the receipt reasons below except clean_exit is not
a request_stop reason. A previously latched cancel requires user_cancelled;
otherwise a required CPU stop requires cpu_limit; a required timing violation
requires observe_gap; then wall violation requires wall_limit. First required
reason is sticky (final overbudget verdict takes precedence independently).

Running observations, including during required/requested stop, have gap<=20ms
from previous accepted sample, first from supplied start. CPU>=S or CPU>B,
gap/query>20ms or controller-launch offset>wall limit retains the well-formed sample and failure;
no malformed-record fallback. During STOP_ASSERTED the decision remains stop.
The unit cannot autonomously notice silence or elapsed time without new inputs.

Final observations are only after asserted drain, timestamp>=drained and later
than previous sample. Three equal native readings and empty active variants are
required, each query<=20ms, at least20ms between final readings, last within2s of
drained. These drained spacings are NOT constrained by the running<=20ms gap.
Final offset from before launch still must be within lane wall ceiling. A valid
final CPU>B is retained as failure, never eligible; final CPU>=S alone does not
invent a prior running stop. Final CPU values/deltas must match all prior math.
After drain, a well-formed sample with query>20ms, final deadline/spacing or wall
violation is committed only as an accepted diagnostic observation, then latches
FAILED_HELD (observation_gap for timing, counter_invalid for wall); it cannot
complete final3 or manufacture a valid final receipt. Empty/matching/monotonic
native validation failures instead reject the event before any trace update.
Thus valid observed bad timing is preserved, but no final success repair exists.

At most32768 accepted samples, at most16777216 digest bytes including one LF per
record. Check count and frame_length+1 remaining budget BEFORE hash/state update.
Incremental SHA256 over accepted canonical sample bytes then LF, including final
three. Retain previous observation, final three, fixed counters/timestamp extrema
and one digest state, not the whole trace or full-frame list. Final/receipt frames
are bounded individually. Rejected events do not partially increment trace.

## 5. Receipt variants and consistency

RECEIPT exact keys: schema,attempt_id,job_id,object_token,platform,binding,verdict,
stop_reason,limits,final,timing,samples,controller,cleanup,nonclaims.
binding exact keys: input_sha256,request_sha256,source_commit,runtime_sha256,
module_set_sha256,controller_sha256,profile_sha256. They match start plus the
explicit controller digest at session construction; a digest is not authenticity.
limits exactly equal start. verdict is complete_within_budget,
failed_final_overbudget,failed_control or uncertain; no new outcome variant.
stop_reason: clean_exit,cpu_limit,wall_limit,memory_limit,scratch_limit,
user_cancelled,output_limit,worker_lost,controller_lost,unexpected_descendants,
identity_changed,counter_invalid,observe_gap,kill_timeout,startup_failed,
receipt_lost. Sealed receipt cannot undo a sticky prior stop/control failure.

final exact keys: status,native,cpu_ns,empty_verified,root_exit_code,final_reads,
monotonic_ns. Complete: status=complete; native/cpu_ns equal final3; empty=true;
root_exit_code equals drain assertion; final_reads exact int3; monotonic_ns equals
sample3 offset. Unavailable: status=unavailable; native,cpu_ns,root_exit_code,
monotonic_ns all null; empty=false; final_reads exact int0. Null is never zero.
Unavailable requires verdict=uncertain and may not assert clean_exit success.
Unavailable stop_reason must not be clean_exit; it matches the accepted stop if
one exists, else receipt_lost for missing final evidence (not a fabricated stop
timestamp). If the session already held a malformed-counter/identity/timing
failure without an accepted stop, require counter_invalid/identity_changed/
observe_gap respectively; other held decode/state failures use receipt_lost.

timing exact keys: started_ns,stopped_ns,drained_ns,finalized_ns,
max_observe_gap_ns,max_query_duration_ns,kill_interval_ns,visibility_evidence_sha256.
Complete times match assertions; finalized_ns equals final sample3 offset (not
receipt-write time). max_observe_gap_ns derives running observations only;
max_query_duration_ns includes final3; missing running observations gives max0,
not a claim that real observations occurred. kill_interval_ns=drained-stopped
for a requested stop, must<=250000000 for consistency; natural drain requires0.
visibility_evidence_sha256 is a strict digest reference only, not inspected/proven
50ms visibility evidence. Timing constants remain provisional OS admission gates.
An unavailable receipt allows null only for unknown timing entries; any supplied
known times/maxima match retained assertions/extrema. Precisely: started_ns is
the asserted start or null if never supplied; stopped_ns is the asserted drain
stop or supplied stop-request time, else null; drained_ns is the asserted drain
or null. finalized_ns is ALWAYS null for unavailable. max_observe_gap_ns and
max_query_duration_ns are always derived exact ints (0 for an empty relevant
trace), not null; kill_interval_ns is derived if drain is known, else null.
visibility digest may be null or a strict digest reference only in unavailable.
All nonnull times0..I64 ordered where both are known; never relabel last sample
as final. accept_receipt may retain unavailable from any post-start session phase
after exact shape/identity/known-trace checks, then latches FAILED_HELD. It does not
manufacture a complete receipt when a preliminary controller counter is absent:
if that required nonnullable counter is unknown, there is no valid receipt; use
accounting_receipt_unavailable and stay held, not zero replacement.

samples exact keys: sha256,record_count,byte_count; EXACT accumulated digest/count/
bytes, including for unavailable. Empty trace uses SHA256(empty), counts0,0.
controller exact keys: cpu_ns,wall_ns,peak_private_bytes. Each exact int0..I64;
peak_private_bytes eligibility ceiling 67108864. cpu_ns is the supplied preliminary combined
controller+worker overhead, not subtraction from scientific CPU. Parent CPU
ceiling, peak memory<=67108864 and wall_ns<=lane wall_ns are eligibility checks,
not OS measurements. Complete controller.wall_ns>=finalized_ns; both are supplied
offset/duration from the same asserted before-launch origin (not just science
start). There is no newly invented 2s parent wall budget: 2s is the drain bound.
Valid above-cap supplied counters may represent failed_control, never success;
they are retained, not coerced below caps. Peak memory above cap likewise records
failure (bounded numeric width, not rejected as an unavailable zero).

cleanup exact keys: object_drained,object_released,receipt_acknowledged,
filesystem_debt_resolved. Complete requires true,false,false,false respectively;
unavailable allfalse. These sealed bytes are never rewritten after release.
nonclaims exact keys: production_approved,physics_certified,
recovery_adapter_approved,hard_zero_overshoot_guaranteed; each literal false.

For complete receipt: final>B requires failed_final_overbudget regardless of
reason; otherwise any sticky failure/nonzero exit/timing or parent limit failure
requires failed_control; otherwise require complete_within_budget and clean_exit.
A natural nonzero exit may retain clean_exit as stop_reason (natural termination
only), with failed_control verdict. Stop reason otherwise matches accepted stop.
Complete trace with no final CPU overbudget cannot claim failed_final_overbudget.
Eligibility denied for any stopped/failed receipt even if final CPU<=B.

## 6. Release acknowledgment and eligibility

RELEASE exact keys: schema,attempt_id,object_token,receipt_sha256,object_released,
controller_cpu_ns,worker_cpu_ns,parent_total_cpu_ns,parent_budget_passed.
Only after bound complete receipt; IDs match; receipt_sha256 is SHA256 of those
exact canonical in-memory receipt bytes, not a file/signature/durability proof.
object_released and parent_budget_passed must be exact true. CPU counters0..I64;
checked sum(controller_cpu_ns,worker_cpu_ns)==parent_total_cpu_ns, at least the
receipt's preliminary combined overhead and <=lane parent ceiling. No trusted
boolean shortcut. Above-budget/overflow/wrong hash/identity/phase/false flags
fails held. A complete failed receipt can validate cleanup consistency, but the
sticky failed-computation verdict remains ineligible. Unavailable cannot release.

ProtocolEligibility exact fields: protocol_eligible bool, runtime_authorized
literal false, reason_code fixed safe code or protocol_consistent. Only ACK_CHECKED
with no failures, complete_within_budget, clean_exit, root exit0, exact complete
final3 and CPU<=B, valid trace/timing/parent totals and exact nonclaims qualifies.
Absent release uses accounting_release_invalid, absent final/receipt uses
accounting_receipt_unavailable; held failures use the latched fixed error. Valid
but failed limits use accounting_cpu_limit/observation_gap/parent_limit as
appropriate; other stopped/nonzero-exit/wall/memory failures use accounting_counter_invalid.
This is NOT permission to execute, publish, free storage debt or restore a future
revision. runtime_authorized remains false even for fabricated perfect records.

## 7. Complete bounded safe-error registry

SafeError exact fields code,message,retryable=false. Fixed ASCII code<=48 bytes,
message<=96 bytes. ProtocolError's application payload/args contain only the
fixed code/message; no custom raw-input/field/doc/exception/digest attribute.
Recognized parser exceptions map to a code without retaining them, then the fixed
error is raised outside that handler (from None alone does not remove context).
Tests require no parser exception in the emitted __cause__/__context__ under
ordinary direct calls. Python/native traceback frames are NOT an additional safe
payload and may retain caller locals; never serialize/log/debug-export them or
keep raised exceptions as session diagnostics. Session retains a fixed SafeError
only. Caller handling its own exception may itself create context; that cannot be
controlled or certified here. No exception-to-dict/vars/error repr public output.
Unknown
safe_error code maps to accounting_protocol_invalid, never echoes the argument.
No global OOM/native/clock exception is turned into a successful zero; this unit
cannot promise availability under process-wide memory exhaustion. No logging.

| Code | Fixed message |
| --- | --- |
| accounting_admission_closed | Physical CPU accounting admission is closed |
| accounting_launch_failed | Contained execution could not start |
| accounting_counter_invalid | CPU accounting could not be verified |
| accounting_cpu_limit | Aggregate CPU budget was reached |
| accounting_observation_gap | CPU observation timing could not be verified |
| accounting_containment_failed | Execution containment could not be verified |
| accounting_termination_uncertain | Execution termination could not be verified |
| accounting_receipt_unavailable | Final CPU receipt is unavailable |
| accounting_parent_limit | Controller resource budget was reached |
| accounting_protocol_invalid | Private accounting protocol is invalid |
| accounting_bounds_exceeded | Private accounting record exceeds its bounds |
| accounting_integer_invalid | Accounting integer type or range is invalid |
| accounting_counter_overflow | Accounting counter conversion would overflow |
| accounting_counter_underflow | Accounting counter difference would underflow |
| accounting_identity_mismatch | Accounting identity does not match the attempt |
| accounting_transition_invalid | Accounting protocol transition is invalid |
| accounting_release_invalid | Accounting release acknowledgment is invalid |

Deterministic error selection: exact argument-type errors -> integer_invalid for
numeric inputs, protocol_invalid otherwise; preflight size/depth/node/member/
token limits -> bounds_exceeded; other lexical/duplicate/schema/key/canonical
errors -> protocol_invalid; field numeric ranges -> integer_invalid; checked
arithmetic -> overflow/underflow; platform/native CPU mismatch or regression ->
counter_invalid; identities -> identity_mismatch; invalid phase/sequence/replay ->
transition_invalid; missing final -> receipt_unavailable; malformed release uses
the earlier decode error if applicable, otherwise release_invalid. First latched
held error wins. Well-formed timing/CPU/parent failures retain their fixed outcome
without exposing any supplied field/value, exception repr, identity or digest.
