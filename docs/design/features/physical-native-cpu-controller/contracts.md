# Native controller contracts and closed integration seams

Date: 2026-10-03. Status: proposed, no created source/tests/profile/transport.
Read [design](design.md), [requirements](requirements.md) and [validation](validation-plan.md).
The existing pure [contract](../physical-accounting-protocol/contracts.md) is
not widened or replaced. Its runtime_authorized ALWAYSfalse remains mandatory.

PENDING amendment beyond MAIN-reviewed67c621c: explicit24-byte DRAINED timestamp
and50ms pre-final visibility wait below need exact MAIN acceptance BEFORE source
adoption. Narrow I01 authority does not implicitly approve these changes; see
[approval](approval.md) and [build inventory](build-inventory.md).

## 1. Identity and authority

Private start/trace/receipt/release use unchanged exact pure schemas and keys.
START16384, CONTROL1024, SAMPLE4096, RECEIPT16384 ingress, RELEASE4096 bytes.
Canonical ASCII object only; no arrays/escapes/whitespace-normalization/unknown
keys/duplicate keys/floats/bool-as-int. Depth6, nodes256, members32, keys64bytes,
values128bytes, magnitude20digits and lexical bounds BEFORE int/tree/copy.
The bridge invokes existing RecordKind/Platform/limits_for/decode_record/session
operations, not private imports or overridden constants. All returned types
retain direct-bool rejection; explicit protocol_eligible is only consistency.
Profile/native setup/kernel text are NOT newly accepted pure RecordKinds.

Private launch context must bind exact effective credentials/job chain or
delegation/manager, executable/runtime/code/input hashes, controller SHA,
object directory/handle custody and source commit. A user UUID or digest is
not a kernel capability, signature or approval. Actual authority is evaluated
outside pure protocol and absent now. No public profile record is created.
The future bridge cannot select a service, elevation, executable or path from
an untrusted record. Unknown method/profile/platform/context refuses before OS
birth. Recovery authority and latest deletion authority remain independent.

## 2. Fixed private wire, proposed not a public protocol

The native executable does not parse unbounded JSON or invoke arbitrary Python
callbacks. A dedicated trusted bridge exchanges bounded private binary frames
over fresh owned endpoints. This additional transport needs its own NCC-010/012
review/tests; it confers no runtime authority and is not a new pure variant.
No serialization of raw C structs/pointers or host-endian reinterpret_cast.

Every frame header is EXACTLY64 bytes, little-endian scalar fields at offsets:

| Offset | Size | Field |
| ---: | ---: | --- |
| 0 | 4 | magic ASCII NC01 |
| 4 | 2 | version uint16=1 |
| 6 | 2 | kind uint16, fixed enum below |
| 8 | 4 | payload_bytes uint32, exact kind length |
| 12 | 8 | sequence uint64, starts1 and advances exactly1 per direction |
| 20 | 16 | attempt UUID raw bytes, exact binding |
| 36 | 16 | object UUID raw bytes, exact binding |
| 52 | 12 | reserved, allzero |

At most4096 payload bytes, checked against the kind BEFORE read/allocate/copy.
Use fixed header+one payload buffer, partial bounded I/O state and absolute
deadline. Fixed integers load/store bytewise without unaligned pointer cast.
EOF midframe, unknown kind/version, oversized/short/extra payload, reserved
bits, replay/sequence exhaustion, mismatched identity or frame after terminal
state requires stop/HELD. No kind0/default. No whole stream buffering.

Kinds and complete payload layouts (all offsets relative to payload):

| Kind | Direction / allowed phase | Exact payload |
| --- | --- | --- |
| 1 START | Bridge to native, once PREPARED | 8bytes: platform uint32 at0 (1 Windows/2 Linux), lane uint32 at4 (1 correction/2 transform). Both select compiled exact constants, NOT budget overrides |
| 2 HEARTBEAT | Bridge to native, CONTAINED/RUNNING/STOPPING | 0bytes |
| 3 CANCEL | Bridge to native, CONTAINED/RUNNING, once | 0bytes; native timestamps receipt and stops |
| 4 DURABLE_ACK | Bridge to native, RECEIPT_BOUND only, once | 32bytes exact binary SHA256 of immutable pure receipt; must equal prebound RECEIPT_BIND |
| 5 RECEIPT_BIND | Bridge to native, FINAL_NATIVE only, once | 32bytes exact binary receipt SHA256. It binds identity, NOT durability; native waits for separate ack |
| 6 CONTAINED | Native to bridge, after actual setup checks | 8bytes offset_ns uint64 |
| 7 STARTED | Native to bridge, after resume/GO | 8bytes offset_ns uint64 |
| 8 SAMPLE | Native to bridge, running/stop/drain/final | 96bytes, twelve uint64 slots listed below |
| 9 STOP | Native to bridge, once stop requested | 16bytes: reason uint32 at0, reserved uint32=0 at4, offset_ns uint64 at8 |
| 10 DRAINED | Native to bridge, after actual emptiness/reap | 24bytes: root exit raw32 at0, reserved uint32=0 at4, stop_offset uint64 at8, drained_offset uint64 at16 |
| 11 ERROR | Native to bridge, once failure latched | 16bytes: operation uint32 at0, safe_code uint32 at4, native errno/GetLastError uint32 at8, reserved uint32=0 at12 |
| 12 RELEASED | Native to bridge, after matched ack and actual object release | 8bytes controller preliminary SELF ns. This is explicitly NOT a final lifetime parent RELEASE record |

SAMPLE slots0..11: offset_ns, query_duration_ns, native0,native1,native2,
active0,active1,active2,cpu_ns,phase,final_read_index,reserved0.
phase1running,2stopping,3drained-final. final index0 except final phase1..3.
Windows native0/1 user/kernel int64 nonnegative bit patterns, native2=0;
active0/1/2 DWORD active/total/limit-terminated widened to uint64 after validation.
Linux native0/1/2 usage/user/system uint64; active0 populated0/1,
active1/2 root_reaped/adopted_reaped0/1, converted to strict JSONbool by bridge.
Slots never carry native handle/PID/private path. Offset/query/cpu<=I64;
all slots must satisfy exact platform constraints before canonical conversion.
Wire unavailable has ERROR, not a SAMPLE containing guessed zero.
Unavailable pure receipt is emitted only through its unchanged explicit null
variant; zero available counters are not confused with an absent observation.

STOP reason values1..16 match in order: cpu_limit,wall_limit,memory_limit,
scratch_limit,user_cancelled,output_limit,worker_lost,controller_lost,
unexpected_descendants,identity_changed,counter_invalid,observe_gap,
kill_timeout,startup_failed,receipt_lost,clean_exit. Value16 allowed only for
whole-object natural exit, never a bridge request or repair of earlier failure.
ERROR safe_code1..17 matches pure fixed registry order below; operation1..8 is
prepare,create,contain,resume,query,stop,drain,release. Unknown values reject.
Native errno is private numeric diagnosis, never logged publicly or a safe message.

Bridge event mapping is fixed, not a caller hook: START binds the already decoded
pure START; CONTAINED/STARTED invoke the corresponding scalar session assertions
only after native checks. Binary direction sequence is NOT pure sample/control
sequence: the bridge maintains separate exact1-based counters for each pure
channel, preventing a CONTAINED/event frame from consuming a sample number.
SAMPLE native/active slots produce only the matching canonical pure SAMPLE,
then consume_sample or consume_final_sample by the fixed native phase. Drain
assertion uses the actual DRAINED offset and precedes all final samples; a final
sample must not be accepted first as running evidence or redefine drain time.
Nonclean STOP invokes request_stop with its native timestamp; clean_exit16 is
natural-stop metadata for assert_drained, NEVER request_stop(clean_exit).
ERROR latches held diagnostic and attempts native stop, not a synthesized zero.
RECEIPT_BIND/ACK are never treated as pure RELEASE. RELEASED's preliminary
SELF value cannot populate a final pure parent acknowledgment. Unknown events,
phase mismatch or native-versus-pure identity/counter discrepancy fail held.
Canonical JSON is formed from bounded known primitives after computing exact
encoded length, validated with the unchanged pure decoder; no arbitrary asdict,
caller stringify/coercion or private pure symbols are needed.

## 3. Native setup is owned state, not config strings in START

The launcher/native main entry receives only explicit owned endpoints and a
reviewed immutable local context. MAX argv32 entries, each<=1024 bytes UTF8
equivalent, total<=16384; env<=32 entries/4096 bytes total; Windows bounded
UTF16 command<=16384 code units and env<=4096 code units, checked conversion
before allocation. Context setup limits cannot be chosen from client values.
Every individual path string<=1024 bytes, absolute beneath approved immutable
roots; it is not an allowed file traversal or executable selection protocol.
Unknown context structure/profile or missing trusted closure means no START.

This packet intentionally does not invent an effective token/credential policy,
Linux privileged FD broker or production authority supplier. Concrete context
content and OS ownership MUST be reviewed separately and tied to actual gates
before any native source implementation/launch authorization. CLI of a future
standalone test tool is not an API/worker hook or a deploy command.

Kernel control read cap4096 plus bounded extra-byte/EOF check, max32lines,
key<=64bytes, uint64 decimal max20digits with checked accumulation BEFORE
multiply/add. Required cpu.stat keys appear exactly once; duplicate/unknown/
missing fields reject. Concrete profile lists each additional supported kernel
key (e.g. nr_periods/nr_throttled/throttled_usec/nr_bursts/burst_usec), no prefix
wildcard. cgroup.events likewise uses a reviewed exact registry including
populated and frozen when present. Text format/skew is not JSON canonicality.
Short/error/native length failures cannot become an available zero counter.

## 4. Polling, drain and incremental evidence bounds

Native query start/end offsets bound query duration; complete observation gap
includes scheduling delay and read/query duration. Running CPU>=S or elapsed
wall beyond frozen ceiling sets sticky failure and whole-object stop. An ERROR
must not prevent attempting stop with retained exact authority. Every native
component is nondecreasing; regression fails even if aggregate rises.
Windows checked(user+kernel)*100, Linux checked max(usage,user+system)*1000;
no saturation, truncation, tolerance or wall fallback. All derived ns fitI64.

No more32768 pure samples or16777216 sample bytes, counted as canonical frame
plusLF exactly as unchanged session. Bound before digest/write/queue; retain
only previous sample/final3 in Python, fixed wire buffers in C. Native-to-bridge
pending queue4frames maximum; filling it fails supervision rather than blocking
queries or dropping observations. Separate stdout/stderr caps65536 each, result
67108864, receipt storage65536. All private evidence/cache/log bytes count in
scratch. Log truncation does not undo a limit violation. The supervisor cannot
certify RSS/scratch enforcement solely from these byte caps.

Final phase begins only after native whole-object empty and owned exit proof;
wait at least the admitted50ms visibility bound after drain BEFORE first final
read, with actual empty state still checked. Three equal component totals,
empty active variants, >=20ms spacing, <=2s from
drain. Running20ms gap rule does not impose an upper final-read spacing.
Unavailable final fields remain null with final_reads0 and empty_verifiedfalse.
Clock/stop/drain/exit/receipt loss latches FAILED_HELD, no reset/rebind/replay.

The existing pure contract alone decides supplied sequence/trace/receipt
consistency. A complete science final must still not claim durable/storage
success, final parent closure or actual authority from that pure decision.

## 5. Durable custody and external integration invariants

RECEIPT_BIND names exact receipt bytes; native retains the science job/group.
DURABLE_ACK requires storage-owned independently validated durable attempt,
object, receipt hash and intent identity. A digest over a pipe is not itself
proof of durable storage: the trusted endpoint/context and real write/flush/
transaction/reconciliation controls must justify the ack. No current worker
implements it, so integrated release stays CLOSED. Lost ack times out HELD,
retains empty object/evidence debt for operator. An empty object need not stay
live, but destroying it without acknowledged counter custody loses finality.

After matched ack, release exact empty created object once. RELEASED wire SELF
counter is preliminary: later observer CPU/exit and worker final write are not
included. A pure RELEASE may only be sealed with independently established final
parent totals/actual release, after H04/H05 approval. An isolated helper that
self-reports then exits cannot close this gap. A successful pure ACK_CHECKED
never clears storage debt or declares runtime_authorizedtrue.

Recovery crash positions: before birth, suspended/setup, running, stopping,
drained before seal, after fileflush before intent, after intent before ack,
after ack before release, after release before parent counter/release, after
uncertain SQLite commit. Missing final at any position is unavailable, not last
sample. Recovery must first stop actual objects with exact retained authority,
reconcile deletion/latest tombstones and quota/publication intent, and preserve
history/reservations/stages until independently resolved. No current0003 adapter
understands new receipt/debt records; unknown revision/schema rejects before
backup or NEW-target restore. No restored success recreates OS capability.

## 6. Safe error mapping, exact unchanged registry

Safe output code,message,retryablefalse; ASCII code<=48,message<=96bytes.
No native errno/GetLastError, path, raw bytes, token, source value, command,
stderr, exception context, PID or handle in public output. Errors are fixed
numeric native enums converted to unchanged pure safe_error; unknown maps to
accounting_protocol_invalid. No generic exception repr or logging fallback.

| Number | Existing code | Native behavior |
| ---: | --- | --- |
| 1 | accounting_admission_closed | Refuse before object/science |
| 2 | accounting_launch_failed | Stop exact partly created object; no resume fallback |
| 3 | accounting_counter_invalid | Stop; retain unavailable/invalid evidence |
| 4 | accounting_cpu_limit | Stop complete object; never eligible |
| 5 | accounting_observation_gap | Stop; close profile |
| 6 | accounting_containment_failed | Stop; close profile, operator check |
| 7 | accounting_termination_uncertain | HELD; next admission blocked |
| 8 | accounting_receipt_unavailable | HELD; preserve receipt/stage/debt |
| 9 | accounting_parent_limit | Stop/fail; no preliminary-budget shortcut |
| 10 | accounting_protocol_invalid | Refuse malformed frame; stop if live |
| 11 | accounting_bounds_exceeded | Refuse before allocation/write; stop if live |
| 12 | accounting_integer_invalid | Refuse wrong width/type; no coercion |
| 13 | accounting_counter_overflow | Refuse before sum/product; no saturation |
| 14 | accounting_counter_underflow | Refuse before delta subtraction |
| 15 | accounting_identity_mismatch | Stop mismatched attempt; no rebinding |
| 16 | accounting_transition_invalid | Stop replay/wrong phase; absorbing failure |
| 17 | accounting_release_invalid | Retain held custody; no release |

Cancellation/numerical/nonconverged API mapping is later integration-owned,
not an API modification here. Failure priority follows pure contract; first
latched safe failure survives cleanup diagnostics. Abrupt native death/OOM may
provide no frame at all; EOF/death custody must handle that unavailable case.

## 7. I01 deterministic C test facade, not a native runner

MAIN's reviewer instruction at2dac0ad accepts the24-byte drain timestamp and
50ms wait and /MT I01-only build, under the already human-authorized scope.
See approval.md section5. This facade supplies no measured values or authority.
No JSON/receipt encoder/hash, clock, callbacks, heap, file, native process or
platform API belongs in controller.h/c. Safe arithmetic and private wire/state
consistency only; complete pure receipt/trace validation remains unchanged.

All exports are ncc_ prefixed C17 functions returning0 or fixed safe enum1..17,
except ncc_error_text (fixed immutable ASCII literal). Error outputs never carry
input bytes/native errors. Scalar out parameters remain unchanged on failure.
uint64 scalar arguments are representation-level integers, NOT Python objects;
the test adapter rejects bool/non-int before ctypes narrowing. The core cannot
recover a bool once a foreign caller has coerced it to integer1. Binary flag
slots instead reject every value except0/1; no JSON null is encoded as a SAMPLE.

Exact caller-owned state:1024 zero bytes,8-byte aligned; init once, matching
capacity1024 and two nonnil16-byte UUID bindings. No caller-owned buffer pointer
is retained. State is opaque, not a public C struct serialized on the wire.
Reinitializing an initialized state fails HELD, cannot reset or rebind. Raw
caller memory tampering is outside the trusted in-process facade, not admission.

| Export | Exact purpose |
| --- | --- |
| ncc_windows_cpu(user,kernel,out) | checked signed-range ticks sum then100ns conversion |
| ncc_linux_cpu(usage,user,system,out) | checked U64 sum/max then1000ns conversion |
| ncc_delta(current,previous,out) | I64 ns range, checked nonnegative delta |
| ncc_next_sequence(previous,supplied) | exact+1, rejectU64 exhaustion before addition |
| ncc_qpc_ns(current,previous,frequency,out) | supplied I64 ticks/frequency only; checked quotient/remainder ceil, no clock call/wide-integer assumption |
| ncc_time_ns(seconds,fraction,quantum,out) | supplied timespec/timeval, quantum exactly1/1000, checked ns conversion |
| ncc_parent_cpu(lane,controller,worker,reported) | supplied checked sum==reported, frozen5/10s ceiling; no post-exit measurement claim |
| ncc_limits(lane,out,count) | exact8 integers B,S,M,wall,RSS,scratch,result,parent; lanes1/2 only |
| ncc_frame_preflight(bytes,length,out_kind) | exact64-byte header, known kind/length/reserved; cap BEFORE pointer read/copy |
| ncc_state_init(state,capacity,attempt,object) | once-only zero state/bound nonnil IDs, no OS object |
| ncc_apply(state,capacity,direction,bytes,length) | complete bounded frame only; direction1bridge/2native, separate exact sequences, atomic valid event or absorbing HELD |
| ncc_account_bytes(state,capacity,channel,amount) | pre-add byte caps, channels1stdout/2stderr/3receipt/4result/5scratch/6canonical-sample-bytes |
| ncc_queue(state,capacity,action) | supplied enqueue1/dequeue2 counters, cap4/checked underflow, no real queue or blocked writer |
| ncc_snapshot(state,capacity,out,count) | exact22 uint64 diagnostic scalars, no authority or private input |
| ncc_error_text(code,which) | which0code/1message, unknown selects fixed protocol_invalid, never stringifies input |

Snapshot slots: phase,reason_code,computation_failed,stop_required,
runtime_authorized(always0),sample_count,final_count,last_cpu_ns,last_offset_ns,
bridge_sequence,native_sequence,queue_count,canonical_bytes,stdout_bytes,
stderr_bytes,receipt_bytes,result_bytes,scratch_bytes,required_stop_reason,
stopped_ns,drained_ns,root_exit_raw32. No protocol_eligible/runtime grant export.
Phases0PREPARED/1CONTAINED/2RUNNING/3STOP_REQUIRED/4STOPPING/5DRAINED/
6FINAL_NATIVE/7RECEIPT_BOUND/8ACK_CHECKED/9RELEASE_ASSERTED/10FAILED_HELD.
RELEASE_ASSERTED acknowledges supplied wire consistency ONLY, never actual
release, final parent counters, durable receipt or publication. Runtime stays0.

START binds platform1/2 and lane1/2 once while PREPARED. Native CONTAINED then
STARTED must precede SAMPLE. DRAINED requires started<=stopped<=drained and
last observation<=drained; requested stop timestamp matches exactly and kill
interval<=250ms. Clean STOP16 is natural metadata, never a stop request or a
repair of prior required stop; natural DRAINED may omit clean STOP. First final
offset-drain>=50ms, final spacings>=20ms, <=2s drain deadline; query<=20ms,
empty variants, same counters across final3, no regressions. Invalid native/
phase/identity/length/sequence rejects before observation update. Well-formed
bad timing/budget observations are retained as failed supplied evidence. No
event certifies actual containment/emptiness/visibility/liveness.

Count<=32768 before sample update. The caller separately supplies exact canonical
byte amounts includingLF to channel6 (cap16777216); C does NOT compute/hash or
certify canonical JSON bytes. The unchanged pure decoder/session must still
check real canonical bytes/digest. Resource channels likewise account supplied
amounts only, no filesystem/RSS/scratch measurement or enforcement claim.
Byte/queue helpers reject before additions and hold failure; they cannot block,
drop observations, allocate, emit or free actual resources. Unknown channels/
actions/directions/kinds/platforms/lanes have no fallback. Complete33-bit/unknown
native flags fail before narrowed conversion. ERROR accepts fixed enums only;
errno is never retained in diagnostics, unavailable has no available-zero SAMPLE.

Failed computation is sticky; first HELD error is absorbing. Matched32-byte
bind/ack tokens are consistency, not SHA computation/durability/authentication.
Preliminary SELF in RELEASED cannot pass as final parent closure. State copies
and local buffers are fixed-sized; no stream/trace retention or raw-struct ABI.
Test-only ctypes DLL binding is not a production platform/bridge implementation.

## 8. I01 operator-only build capture contract

`scripts/native_physical_cpu/capture_build.py` imports without execution or writes.
Its only executable recipe consists of core compile/link then probe compile/link,
the exact C17 /MT and five-library /NODEFAULTLIB commands in the build inventory.
No DLL load, ABI execution, test execution, compiler discovery, fallback, install,
environment mutation, native science launch or public API is provided. Executing
the recipe requires an independently reviewed private source/manifest pin.

Private CLI arguments are source/output/scratch/outcome/VC/SDK/SystemRoot, approval manifest and
manifest SHA256; absolute device paths do not belong in the public repository.
The exact `i01-build-approval-2` object has schema, source_commit, source_hashes,
tree_files, execute_i01_build, roots. The execute flag is literaltrue, not a runtime
authority token. roots has EXACT source/output/scratch/outcome/vc/sdk/system strings. Each root
must match the reviewed supplied argument; no relative, parent traversal, symlink
or reparse component. Output, scratch and outcome leaves must all be absent,
pairwise disjoint (neither equal nor nested), and outside source/tools/OS; their
existing ancestors are checked. No hardlinked regular files admitted. The private
manifest itself cannot lie within a writable root. No old-manifest fallback.
Source hashes bind all eight C/header/probe/helper/test files, including the helper
and its separate test_capture_build.py, and the source commit is40 lowercase hex.
Hash pinning binds actual file identities. source_commit is a reviewed receipt
claim, NOT a Git HEAD check performed by this helper. Hashes are64 lowercase hex.

The private manifest is reviewed/hash-pinned operator input, NOT hostile waveform,
physical JSON or browser data. Raw manifest<=2MiB, duplicate decoded keys reject.
tree_files is exactly five maps of relative file name to hash, respectively the
compiler-bin and four include roots. Full member/count/byte totals match the
inventory:90/361/66/303/2214 files and88183442/16162316/1055527/11723353/126821714
bytes. Each file is independently rehashed without relying on a different
culture's reconstructed aggregate hash. Recheck all inputs before each stage;
the two selected tools, five static libraries and read-only Python additionally
match the inventory's fixed hashes. No alternate include/library/root admitted.
Hash pinning does not attest dynamically loaded tool/system dependencies.
After compilation/linking, independently inspect expected PE imports/closure
BEFORE a separate decision authorizes any ABI probe run or DLL load/test.

Each child receives only SystemRoot, pinned PATH, and TEMP/TMP pointing to scratch,
NEVER output or outcome. No inherited
CL/LINK/INCLUDE/LIB/user injection options. One tool stage at a time, stdin closed,
no shell, only reviewed absolute executable. Two reader threads retain at most
2MiB each, check before append, and latch over-limit/unavailable; captured prefixes
on failure are labelled, not presented as full raw stream hashes. Immutable copies
are sealed under a lock after stopping readers. Deadline90s is checked with20ms
polls; root wait after an owned-handle kill<=2s and bounded pipe joins. No broad PID
sweep, tree deletion, retry, extra tool stage or automatic artifact execution.

Output is an exclusive new flat private root, allowlisted core.obj/dll/lib/exp,
abi.obj/exe and eight bounded stage stdout/stderr streams, NOT the outcome receipt.
Scratch is another exclusive new root. The ONLY currently supported scratch entries
are empty directories Microsoft, Microsoft/VSApplicationInsights, and at most one
Microsoft/VSApplicationInsights/vstelf followed by exactly32 lowercase hexadecimal
characters. This is the observed directory shape, NOT an opaque namespace allowlist
or documented vendor guarantee. ANY scratch file or other entry holds the build,
is retained/quarantined and never adopted as an artifact. No telemetry environment
switch or global setting is changed. Future observed files need explicit review.

Observe output+scratch together <=64MiB/32 regular files; diagnostic walk bounds
<=128 entries, <=8 relative components, <=1024 characters per relative name.
Encoded inventory entries total<=64KiB checked before accumulation, including
JSON escaping; partial observations explicitly mark this bound's rejection.
Directory bounds include unexpected directories; they cannot evade entry limits.
The observation retains bounded private relative names/kinds/sizes, observed file
and directory counts, and a completeness flag. Never follow links/reparse points;
hardlinks/special files reject. Partial/unavailable observations are NOT total-byte
proofs.20ms sampling is not a filesystem quota or zero-overshoot bound. Stream writes
use exclusive creation and combined remaining-byte checks; no output/scratch/outcome
is removed or overwritten, even on failure. Guard failure stops later stages; captured
stream prefix bytes/hashes remain in the external receipt even when log writes fail.

Outcome has an independent exclusive build.json reserved/opened BEFORE any tool
launch, outside both tool-writable roots, closed to child inheritance. It is written
ONCE at finalization (<=128KiB, flush/fsync), without revalidating rejected writable
output as a prerequisite. Catch launch/input/guard/write/termination failures as fixed
codes, not raw exception values. Independent outcome I/O failure is still possible:
fixed stderr/exit1, retain partial receipt and all roots, no success or retry.
Observable named-file/handle replacement, nonempty reserved file or links detected
before final write hold custody; no overwrite of an externally modified receipt.
The helper does not promise protection against a malicious tool that discovers an
unadvertised outcome path or races path checks; independent custody is not a sandbox.

Normal four-stage completion requires all six artifacts.
Stage targets must still be absent before each launch; no overwrite of prematurely
created known artifacts, no automatic recovery or adoption of such files.
File hashes are bounded before/after metadata-checked read observations, not future immutability or trusted
executables; snapshot status is OBSERVED_NOT_DRAIN_PROVEN. Any held stage sets artifact
observations null, recipe_completedfalse and artifact_successfalse. Even normal
completion keeps artifact_successfalse pending independent PE/import/closure review.
Cross-API identity compares device/inode/size/mtime_ns/link count/file type, not
permission bits: Windows path stat may encode executable filename permissions
that handle fstat does not. ctime_ns is compared before/after WITHIN the same
path API and WITHIN the same handle API, not across them. The actual CPython3.12.10
path/handle observations differ on ctime for freshly written files: the
[pinned path-stat source](https://github.com/python/cpython/blob/v3.12.10/Modules/posixmodule.c)
copies birthtime to deprecated ctime, while
[pinned handle-stat source](https://github.com/python/cpython/blob/v3.12.10/Python/fileutils.c)
uses available ChangeTime. Authored controls preserve both same-API time checks
without a false cross-API identity rejection. No timestamp-based immutability claim.

Important limitation: this helper kills ONLY the exact owned tool root handle on
failure. It supplies NO compiler-descendant kill/drain or hard filesystem quota
proof. Output monitoring is a sampled rejection policy, not a zero-overshoot
kernel cap; inherited pipes may remain live, leaving custody uncertain. These
outcomes are held and cannot start another stage or claim artifact/native success.
`descendant_drain_proven` remainsfalse even for normal root exit. Separate measured
build containment/context is needed if execution review requires a hard bound on
compiler descendants; this helper cannot self-admit that stronger contract.

The private `i01-build-capture-2` receipt preserves source pin, fixed overall held
code, bounded workspace observations, stage return code, measured tool wall float,
captured stream bytes/hashes and artifact read observations only on normal completion.
Source_commit remains claimed metadata; source hashes bind actual identity.
compiled_tests, abi_execution and loaded_dependency_closure remain NOT_RUN,
runtime_authorizedfalse. Retain output and request review, never report success or
fabricate missing CPU/RSS/ABI values. It is not a science CPU accounting receipt,
durable publication acknowledgment, parent finality or Linux/Windows admission.

### Primary basis and negative controls

Retrieved2026-10-03: [Microsoft GetTempPathW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-gettemppathw)
documents TMP then TEMP selection, no existence/access check, and preserved symlinks.
Explicit scratch selection plus ancestry checks address this contract, NOT all vendor
file writes or telemetry content. [Python3.12 os.stat](https://docs.python.org/3.12/library/os.html#os.stat)
documents link count and file metadata; [exclusive open](https://docs.python.org/3.12/library/functions.html#open)
documents x-mode existing-file rejection. Metadata comparison cannot prove no later
writer. No primary source is claimed to guarantee the observed telemetry names.

Authored controls must cover old/malformed root shape, separate/non-nested/absent
roots, TMP/TEMP placement, exact unchanged argv and pins, observed empty telemetry
shape versus unknown files/directories, combined file/byte and diagnostic limits,
link/reparse/hardlink rejection, mutation detection, no overwrite/cleanup, and safe
external receipt on unexpected output, scratch, launch/stream/log-write failure.
Controls use supplied data/fake child handles only; actual retry and PE/ABI/DLL
execution are separate reviewed operations, NOT promoted by these tests.
