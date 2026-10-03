# Pure accounting protocol prospective validation

Date: 2026-10-03. Status: ALL PURE GATES NOT_RUN; documents only.
Exact proposed test path: tests/worker_accounting/test_protocol.py.
Read [requirements](requirements.md), [contracts](contracts.md), [design](design.md).
No code/test file, native fixture, compile probe, environment or profile created.

## 1. Test provenance and oracle boundary

After FULL MAIN approval of the exact sub-SDD pin and separate source scope,
the assigned owner may implement just the two proposed paths and run local pure
tests. Fixtures are literal dummy UUID/digest strings and bounded in-memory byte
records; any receipt is SYNTHETIC PROTOCOL EVIDENCE, not actual native CPU/lifetime
or host evidence. No clocks/sleeps/files/processes/network, measurements of source
bytes, platform discovery, native structures or launch calls in tests or unit.
Normal test/module import is allowed, not source inspection/digest measurement.

Golden constants below are hand-computed independently of converters under test.
Use exact expected integers, not converter-under-test to construct every oracle.
Optional internal spies monkeypatch only the bounded JSON decode/int conversion
and digest update sites to establish ordering; no production callback interface.
Boundary generators produce bounded in-memory fixtures, never private directories
or buffers from files. Docs guard evidence is not a prospective test pass.

## 2. Exact requirement-to-gate matrix

All names below belong solely to the exact proposed test path. Parametrized
subcases may be used without inventing additional code/test paths.

| Requirement | Prospective test | Required evidence | Status |
| --- | --- | --- | --- |
| PAP-001 | test_pure_boundary_and_no_authority | Supplied statements only; even perfect trace returns runtime_authorized=false, no native/profile callbacks or implicit platform | NOT_RUN |
| PAP-002 | test_bounds_precede_decode_and_conversion | Exact-byte check, each ingress ceiling +/-1, depth/node/member/string/digit checks before tree/int/copy; rejected input never reaches bounded decoder/hash | NOT_RUN |
| PAP-003 | test_strict_shapes_and_canonical_records | Every key/discriminator/type positive and negative; duplicate/unknown key, noncanonical encoding and unknown variant reject | NOT_RUN |
| PAP-004 | test_golden_units_and_native_maxima | Exact Windows/Linux unit cases, max convertibles, native-width and addition/multiplication guards | NOT_RUN |
| PAP-005 | test_regression_overflow_underflow_and_bool | Independent component regressions, checked deltas, bool/subclass/float rejection, no counter wrapping or zero repair | NOT_RUN |
| PAP-006 | test_exact_lane_limits_and_no_override | Both full fixed limit tables, all modified/missing/unknown bounds and methods reject | NOT_RUN |
| PAP-007 | test_transition_identity_and_replay | Entire phase table, changed bindings, wrong platform, duplicate/skipped/exhausted sequences and held-error absorption | NOT_RUN |
| PAP-008 | test_bounded_trace_and_final_consistency | Independent sample SHA/count/bytes, final3 spacing/equality/empty state, timing consistency and pre-update retention caps | NOT_RUN |
| PAP-009 | test_unavailable_is_not_final_zero | Exact null/false unavailable shape, known timing consistency, no repair from last sample or release | NOT_RUN |
| PAP-010 | test_receipt_release_and_eligibility | Complete/failed/uncertain, B/B+1, receipt binding/digest and checked release totals; stopped below B cannot become success | NOT_RUN |
| PAP-011 | test_safe_errors_and_forged_authority | All17 registry entries and length/type checks; no echoed input/trace; forged flags never confer authority | NOT_RUN |
| PAP-012 | test_public_surface_and_exports | Exact assigned public exports/scalar types, no CLI/package/profile/OS/controller interface; two-path scope independently reviewed | NOT_RUN |

## 3. Golden native units and arithmetic

| Function / supplied counters | Exact expected result |
| --- | --- |
| Windows user0,kernel0 | 0 ns |
| Windows user1,kernel2 | 300 ns |
| Windows user10,kernel0 | 1000 ns |
| Windows sum92233720368547758 ticks | 9223372036854775800 ns |
| Windows sum92233720368547759 ticks | accounting_counter_overflow |
| Windows user=I64,kernel0 (width valid, conversion invalid) | accounting_counter_overflow |
| Windows user=I64,kernel1 | accounting_counter_overflow before addition |
| Linux usage0,user0,system0 | 0 ns |
| Linux usage1,user0,system0 | 1000 ns |
| Linux usage8,user3,system4 | 8000 ns |
| Linux usage2,user3,system4 | 7000 ns; no false equality assumption |
| Linux conservative total9223372036854775 usec | 9223372036854775000 ns |
| Linux conservative total9223372036854776 usec | accounting_counter_overflow |
| Linux user=U64,system1 | accounting_counter_overflow before addition |
| Linux component=U64+1 | accounting_integer_invalid |
| Delta current0,previous0 | 0 ns |
| Delta current=I64,previous0 | I64 ns |
| Delta current0,previous1 | accounting_counter_underflow before subtraction |

Each scalar position also tests negative/maximum/+1, True/False, int subclass,
float, numeric string, null and wrong container. Linux uint64 can be valid at
native width but fail derived ns. A native subcounter decreasing while max/total
increases MUST reject, as do process-count/reaped-flag regressions. Strict bool
fields reject ints0/1 even though numeric fields separately reject bools.

## 4. Parser boundaries before allocation

Test every kind ceiling exactly/-1/+1, including valid-but-padded oversize which
must fail before ASCII decode/tree construction. Legal boundary sizes need not
be reachable under all semantic field caps: structural length approval alone
never implies full record approval. Check bytes subclasses, memoryview/bytearray,
str/readable object and hostile objects with conversion methods (never invoked).
Depth6/7, nodes256/257, members32/33, key64/65, value128/129, numeric20/21 digits
and lexical U64/U64+1; -2147483648/-2147483649; ASCII vs UTF-8/BOM/UTF-16/escapes.
Before conversion use decimal comparisons, not parse-then-range-check on an
unbounded token. Reject malformed punctuation, truncated strings/objects, arrays,
duplicates, trailing whitespace/LF, unsorted keys, nonminimal JSON, float/exponent,
NaN/Infinity, leading plus/zero and negative zero. Reject unknown schema/platform,
profile/future variant and extra keys at EVERY nested object, not only root.

Every failure returns a fixed registry code without copying attacker input into
errors, safe objects or retained state. Test staged validation leaves no partial
digest/count/sequence updates. Public-surface test inspects runtime exports and
signatures/behavior, not source-file bytes or filesystem provenance; repository
scope review remains an external docs/code review obligation, not a pure test.

## 5. Complete state, timing, receipt and release cases

Exercise each allowed transition and each forbidden phase/event pair. Assert
IDs and platform, all start/receipt bindings, sequence1/exact increments/U64
exhaustion, mutable/aliased-input rejection and independent sessions. Failed held
cannot reset, rebind, accept a fake success or authorize the next attempt; creation
of a new session is not evidence old objects/debt were cleaned. Cancel contains
no timestamp and cannot measure real heartbeat/EOF; requires explicit stop.

Boundaries: running gap/query20000000 ns passes vs20000001 latches stop; first
gap measured from supplied start. CPU S-1/S/S+1; stop requested then below B still
failed. Natural drain then final-only S..B may pass pure consistency if no earlier
failure. Both lane final B+1 ALWAYS fail. Native granularity means B+1 ns is not
representable by these conversions: a supplied mismatched cpu_ns=B+1 rejects;
also test valid first-representable B+100 ns (Windows) and B+1000 ns (Linux) as
failed_final_overbudget. Root nonzero natural exit remains failed.
Final samples: exact3 matched native/empty variants, spacing20000000 vs19999999,
drain deadline2000000000 vs2000000001, final query20ms+1, final sample before
drain and running/final sequence regression; no <=20ms upper-gap rule on drained
final reads. Requested stop kill250000000 vs250000001; ordered timestamps and
checked wall offsets from before launch, including nonzero supplied start offsets.
Controller preliminary CPU/peak memory/wall bounds and final release CPU are
separate; above-cap supplied valid counters record failure, never coerced zero.
Visibility
digest syntax alone never proves real lag or containment. Missing samples/max0
cannot acquire runtime authority.

Independently SHA256 known literal canonical sample bytes+LF in memory; verify
count,bytes and empty digest. Record-count32768 cap and byte-count16777216 cap
before digest/sequence mutation; test rejection at both caps with bounded helper
state setup internal to tests, not exported setters. Retained state has only fixed
metadata, previous observation and final3; no unbounded trace/frame cache.

Receipt: complete final zero is distinct from unavailable null; incorrect exit,
final count/times/native conversion, limits/digests/trace summaries, false nonclaims,
sealed cleanup flags and mismatched identity reject. Complete failed receipt can
remain diagnostic/cleanup-consistent but never eligible. Uncertain allows only
null unknown timing and exact known assertions, never relabels last observation
as finalized. It cannot be followed by success/release repair. No file sealing
or persistence simulated as a passed actual gate.

Release: missing/wrong receipt hash, nonfinal receipt, wrong identity/phase,
object_released=false, parent_budget_passed=false/bool-as-int, checked-sum overflow,
sum mismatch, total below preliminary or parent ceiling+1 all fail held. Sealed
receipt bytes remain unchanged; eligibility requires a distinct matching release.
Even asserted true release/durability/containment and dummy valid hashes cannot
set runtime_authorized=true. Unknown/deceptive safe codes return fixed errors,
not payload/exception/stringified-object details. Direct malformed-input errors
have fixed args/payload and no retained parser exception in cause/context; session
diagnostic retains only SafeError. No assertion that Python traceback frames lack
private locals, and no traceback/log serialization is tested as an approved API.

## 6. Explicit excluded execution

No actual native counter oracle, ABI compile/SDK inspection, OS thread/process/job
launch, cgroup/control write, real-time observation, isolation/no-escape proof,
deletion, publication, recovery, source inventory, private disk fixture or host
drill is run here. Parent15 actual-platform gates remain NOT_RUN and profiles
CLOSED. Pure synthetic gates cannot replace them, disk headroom authorization,
Bacon's storage integration or MAIN's later exact implementation approval.
