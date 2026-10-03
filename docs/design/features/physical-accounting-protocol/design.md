# Pure accounting protocol design

Date: 2026-10-03. Status: PROPOSED, full MAIN pre-code review required.
All pure tests NOT_RUN; all actual OS/profile/host capability CLOSED/NOT_RUN.
Parent pin: 3959ffc29eb4f93e0cca04fdc3154eca7ea7ddca.
See [contracts](contracts.md), [requirements](requirements.md),
[validation](validation-plan.md) and [research](research.md).

## 1. Scope, assigned paths and non-authority

Future implementation owner: this bounded ops accounting unit. MAIN owns review
and exact next-scope approval. Only these NEW paths are proposed for later code:

```text
scripts/physical_accounting_protocol.py
tests/worker_accounting/test_protocol.py
```

No __init__, package, dependency, CLI, controller executable, native binding,
compiled fixture, app import, clock, environment reader, file/network/process
I/O, source/executable digest measurement, profile discovery or activation.
Normal Python module import/test harness loading is not an OS measurement; the
module has no import-time work except bounded constants/types. Stdlib imports
limited to dataclasses, enum, hashlib and json; tests use pytest and in-memory
fixtures. No arbitrary object hooks/callables are accepted from callers.

Inputs are supplied immutable byte records or exact builtin scalar integers.
The caller already owns their allocations; this unit bounds its own copies,
decoding, tree construction, hashing and retained state. It cannot prevent
unbounded allocation by an upstream receiver, prove actual RSS or supply a
transport reader. Those obligations stay with the unimplemented OS/integration
units. No process or actual counter is observed, no duration measured here.

The unit may return protocol_eligible=true only as a consistency property of
the supplied trace. runtime_authorized is always false and has no setter.
External OS admission, actual lifetime/containment/finality, storage/durability,
source integrity and publication must separately be proven. Synthetic assertions
can satisfy the pure unit and still have zero runtime authority.

## 2. Exact future public interface

- RecordKind: START, CONTROL, SAMPLE, RECEIPT, RELEASE only.
- Platform: WINDOWS_JOB_X64_1, LINUX_CGROUP2_X64_1, mapping to the two parent literals.
- limits_for(method_id: exact str) -> frozen LaneLimits; no configurable ceilings.
- decode_record(kind: RecordKind, frame: exact bytes) -> immutable typed Record.
- windows_cpu_ns(user_ticks: exact int, kernel_ticks: exact int) -> int.
- linux_cpu_ns(usage_usec: exact int, user_usec: exact int, system_usec: exact int) -> int.
- checked_delta_ns(current: exact int, previous: exact int) -> nonnegative int.
- safe_error(code: exact str) -> immutable SafeError(code,message,retryable=False).
- ProtocolSession.from_start(start_frame: exact bytes, platform: Platform,
  controller_sha256: exact str) -> an independent bounded in-memory session.
- Session methods: assert_contained(attempt_id,object_token,at_ns),
  assert_started(attempt_id,object_token,at_ns), consume_control(frame),
  consume_sample(frame), request_stop(reason,at_ns),
  assert_drained(attempt_id,object_token,stopped_ns,drained_ns,empty_verified,
  root_exit_code), consume_final_sample(frame), accept_receipt(frame),
  accept_release(frame), eligibility() -> frozen ProtocolEligibility.
  All successful mutators return frozen ProtocolDecision; invalid events raise
  fixed ProtocolError after latching FAILED_HELD, without partial trace updates.

Exact public exports (via __all__): RecordKind, Platform, LaneLimits, SafeError,
ProtocolError, ProtocolDecision, ProtocolEligibility, ProtocolSession, StartRecord, ControlRecord,
SampleRecord, ReceiptRecord, ReleaseRecord, limits_for, decode_record,
windows_cpu_ns, linux_cpu_ns, checked_delta_ns, safe_error. decode_record returns
the one matching frozen record class, not a caller-editable dict; nested values
use private frozen typed structures. Session phase is a read-only exact string
from the phase table; no exported state setters or general event/callback API.
Public constructors of records do not grant a session mutation path: it accepts
only the specified scalar assertions/bytes and validates again. Eligibility and
SafeError have the exact fields in contracts; additional public exports require
review, not automatic acceptance. No implicit truthy success conversion is defined.
ProtocolDecision exact fields: phase (one table literal), stop_required (strict
bool, true in STOP_REQUIRED/STOP_ASSERTED/FAILED_HELD), computation_failed
(strict bool, sticky failure or held), reason_code (fixed safe code or
protocol_consistent). This is an obligation inferred from supplied evidence,
not an OS action or assertion a process exists. Eligibility is a separate check;
a decision with stop_required=false is NOT success/admission/publication.

All scalar argument types/ranges are exact and bounded per contracts. The
assert_* methods receive caller statements, not native handles or capabilities.
They do not certify those statements. A supplied stop reason is a fixed enum
from contracts, never an exception/path/message. Mutability is confined to one
session's deterministic memory; no shared global activation or cross-job cache.
Return objects contain bounded scalars/enums, not aliased caller dictionaries.
Internal typed Records are not user-provided dict constructors or serialization
of arbitrary objects. No hidden environment/default platform/alternate lane.

## 3. Before-allocation decoding algorithm

1. Require exact bytes (not bytearray, memoryview, str, subclass, iterator or
   read-capable object) and a known RecordKind; len check before slicing/copying.
2. Scan byte positions without decoding/copying string/number tokens. A fixed
   six-level stack tracks JSON objects/members; reject arrays, overdepth,
   >256 nodes, >32 members/object, key>64 bytes, value-string>128 bytes and
   integer token>20 digits before JSON tree or int conversion. Compare bounded
   decimal digits to the contracts' lexical range BEFORE int conversion. Each object,
   member name and scalar value counts as one node; root object is depth one.
3. Accept only printable ASCII string content without escapes, plus JSON
   structural tokens, minus/digits, true/false/null and JSON whitespace outside
   strings. Every current protocol string field is ASCII; escaped/non-ASCII/BOM/
   UTF-16/surrogate strings, control bytes, floats, exponents and NaN/Infinity
   reject. Negative integers are lexically possible only for later signed-exit
   validation; a leading plus/invalid leading zero rejects. Not a generic JSON
   ingestion parser. Whitespace is subsequently rejected by canonical equality.
4. After bounds succeed, decode ASCII then json.loads with internal duplicate-
   rejecting object_pairs_hook, bounded parse_int and rejecting float/constant
   hooks. The lexical pass is a bound/type preflight, not a replacement JSON
   implementation; stdlib JSON decides syntax. No load(file) or default hook.
5. Validate exact schema/discriminator/key sets, builtin types, per-field ranges,
   identity and cross-field arithmetic. Build bounded immutable typed records.
6. Compute canonical encoded length from validated primitive tree BEFORE dumps:
   ASCII strings have no escapes, so lengths plus quotes/key punctuation/object
   punctuation and bounded numeric digit counts are exact. If over kind cap,
   reject before serialization. Then json.dumps with sorted keys, compact
   separators, ensure_ascii=True, allow_nan=False; ASCII encode and require
   equality to original frame. Receipt content SHA-256 is in-memory only.

Default decoder numeric size protection is not the bound. No whole decode then
inspect, object stringify then inspect, recursive unbounded copy, truncation or
native-width wrap. Frame ceilings limit decoding copies, but are not a measured
heap/OS memory guarantee. An external writer must separately bound reads/writes.

## 4. Checked arithmetic

I64=9223372036854775807, U64=18446744073709551615, U32=4294967295.
Use type(x) is int; bool, float, Decimal, numpy scalar, int subclass and numeric
string reject. Check scalar widths before operations. For checked add a+b<=C,
require a<=C-b BEFORE addition; for multiply a*k<=I64 require
a<=I64//k BEFORE multiplication. Python arbitrary precision is not permission
to accept a value incompatible with native/receipt domains.

Windows: each counter 0..I64; checked sum <=I64; ns=sum*100 with above guard.
Linux: each counter 0..U64; checked user+system <=U64; choose max(usage,sum),
then checked *1000. No equality assumption between Linux subcounters and usage;
retain them all. Maximum convertible Windows total ticks 92233720368547758;
Linux conservative total usec 9223372036854775. A valid native-width operand
can still fail ns conversion. checked_delta_ns requires both operands 0..I64
and current>=previous before subtraction. Track each native component separately;
a rising aggregate cannot hide a declining component. No clocks, FILETIME/ABI
binary layout or process getrusage conversion in this unit.

## 5. Deterministic supplied-evidence state machine

```text
PREPARED -> CONTAINMENT_ASSERTED -> RUNNING_ASSERTED
RUNNING_ASSERTED -> DRAIN_ASSERTED (supplied clean whole-object exit)
RUNNING_ASSERTED -> STOP_REQUIRED -> STOP_ASSERTED -> DRAIN_ASSERTED
RUNNING_ASSERTED -> STOP_ASSERTED (supplied cancel/failure)
DRAIN_ASSERTED -> FINAL_CHECKED -> RECEIPT_BOUND -> ACK_CHECKED
invalid/uncertain record -> FAILED_HELD (absorbing for eligibility)
```

Stop-required is a returned pure decision, not kill. Any accepted stop request
sets a sticky failed-computation flag; final counter<=B cannot undo it. Valid
overbudget/timing violations are retained as supplied evidence and require stop,
not discarded as zero. Unavailable, malformed, identity-changing, replayed,
decreasing or arithmetically invalid evidence latches FAILED_HELD and a fixed
safe error; no reset/rebind/resume method. A new session is a new attempt token,
not evidence that the old object/debt was cleaned. Stale old frames remain invalid.

PREPARED binds the entire start identity, lane, platform and controller digest.
assertions check IDs/types/timestamp order; they cannot activate a profile.
Sample sequence and control sequence each start at 1 and increase by exactly 1;
they are independent channels. All sample identities/platforms bind to start.
Running sample gaps from the previous supplied observation (first from supplied
start) must be <=20 ms; query duration <=20 ms and nonnegative. CPU>=S yields
STOP_REQUIRED/sticky failure. CPU>B also latches overbudget. No native call.
Wall offsets include setup from the asserted controller-launch origin, not only
the interval after assert_started. Assertions may have nonzero start offsets;
their ordering is checked, but no launch duration or origin is measured.

Only whole-object drain assertion with empty_verified=true is accepted for
final checking, with stopped<=drained timestamps and checked exit-code range.
This does not establish real no-live descendants. The three final samples must
have matching native counters and empty active variants, be >=20 ms apart,
nondecreasing versus prior components, and arrive by drained+2 s. Running gap
policy does not impose <=20 ms spacing on drained final reads. Sample count,
byte count and running SHA-256 update incrementally with canonical frame bytes
then one LF; retain only previous sample and final three, never whole trace.
Cap before digest/state update; rejected event does not partly increment state.

Receipt consistency binds final samples, identity, exact limits, digest/count/
bytes, supplied timestamp extrema and failure flags. An unavailable receipt
can be decoded/retained as diagnostic in FAILED_HELD but cannot supply final
zero or repair eligibility. Release requires exact immutable receipt hash,
object token and parent math/flags, after receipt binding. It cannot infer an
OS release or durable write. A release without a complete matched receipt,
wrong phase or changed identity fails held.

## 6. Protocol eligibility predicate and excluded facts

protocol_eligible requires ACK_CHECKED, no sticky failure/uncertainty, clean_exit,
root_exit_code=0, complete final with CPU<=B, exact three matched final samples,
valid supplied timing/trace metadata, false nonclaim/debt booleans and valid
release/parent total. A clean final counter between S and B can be consistent
if the object was already drained before final-only counter observation and no
running sample/stop request latched failure; this is not a zero-overshoot claim.
Final B+1 always FAIL, even with valid science, ack or asserted parent flags.

ProtocolEligibility exact fields: protocol_eligible (bool), runtime_authorized
(literal false), reason_code (fixed safe code or protocol_consistent). No actual
host, physics, filesystem-cleanup, backup, source-integrity or publication verdict.
Profile records, REVIEWED_ADMITTED, native launch/control callbacks, heartbeat
measurement, EOF detection, clocks, file receipt durability, runtime source
measurement and OS ABI compilation are excluded. Actual contexts remain absent.
