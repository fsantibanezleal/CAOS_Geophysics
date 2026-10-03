# Native controller test-first validation and evidence protocol

Date: 2026-10-03. Status: ALL native/ABI/platform/integration gates NOT_RUN.
No files named below exist in this unit. Full MAIN read and explicit assignment,
toolchain/probe and concrete context approval precede even a compile fixture.
Read [requirements](requirements.md), [design](design.md), [contracts](contracts.md).
No CI OS matrix, product test suite, install or native training job is proposed.
MAIN's narrow I01 authoring approval is persisted in [approval](approval.md).
Compile/test-binary/ABI execution still needs [inventory](build-inventory.md)
approval. The explicit drain timestamp/50ms wait amendments below are PENDING
MAIN acceptance before source adoption, not added runtime PASS claims.

## 1. Evidence layers and test-first order

LayerD: actual docs scope, links, receipt hashes, EARS/gate mapping and existing
cheap guards. D cannot pass any NCC runtime gate.
LayerP: unchanged pure419 tests and supplied-record peer checks are historical
consistency evidence, not actual counters. Do not rerun them as a native claim.
LayerU: future deterministic compiled native return/failure/wire tests are
written before implementation and fail until it exists. Test-only static call
substitution in dedicated builds is allowed, no production provider callback.
LayerA: compile/ABI probe checks real selected toolchain/headers/types/offsets.
LayerO: actual OS positive/adversarial controls, real kernel counters and
contained first instructions, not simulated events or only mocked win32 calls.
LayerI: future worker/storage/source/recovery integration after separate scope
approval. An isolated O pass cannot create I or activate the runtime profile.

At each platform record layers separately. Linux NOT_RUN is not a Windows PASS;
Windows NOT_RUN is not a Linux alternative. A skipped/unavailable control leaves
that platform CLOSED. No vendor-source/OS-version/SDK check substitutes for O.
MAIN owns independent review/replay, selected runtime/context, installer and
actual-host execution. This docs author executes NO native controls now.

## 2. Exact prospective gates, positives and adversarials

All sixteen following gates are prospective and currently NOT_RUN:

| Gate and requirements | Required actual positive | Required adversarial / unavailable outcome |
| --- | --- | --- |
| tests/worker_accounting/native/test_lifetime.py::test_exited_descendants_isolated (NCC-001) | Root, sequential sub20ms exited/reaped children, reparented grandchildren, threads and cold import/JIT; lifetime total retains all associated CPU; independent busy API/controller process excluded | Live-PID-only polling misses exited fixture contributors and must NOT pass; shared group/reused object/foreign concurrent CPU closes profile |
| tests/worker_accounting/native/test_windows.py::test_birth_suspended_job (002) | Real native child first science marker occurs only after creation-bound JOB_LIST, membership/readback and resume1 | Inject every sizing/update/create/member/limit/resume error; exact contained cleanup, zero science marker. Unsupported JOB_LIST has no assignment-after-start fallback |
| tests/worker_accounting/native/test_windows.py::test_limits_not_combined_hard_cap (003) | Actual fresh job flags/count/affinity/user-limit readback; user/system-heavy fixture charges both | Job-time limit alone must not pass combined CPU; wrong/end-action/breakaway/ancestor flags, duplicated handle, altered limits or untested nested chain refuse |
| tests/worker_accounting/native/test_linux.py::test_birth_domain_pidfd (004) | First fixed child instruction born inside exact fresh domain, root owned PIDFD, native setup before GO and exec | EPERM/EACCES/ENOSYS/EINVAL/EBUSY/EOPNOTSUPP, bad UAPI, threaded/v1/hybrid group, changed inode or unavailable kill all refuse before science; no fork-migrate |
| tests/worker_accounting/native/test_containment.py::test_denied_escape_and_authority (005) | Actual compute credential cannot modify/query controller authority beyond reviewed data pipes | Attempt each reachable migration/ancestor/sibling path, child job breakaway, nested policy mutation, handle duplication, ptrace/signal/FD acquisition and broker launch. Any successful or untested reachable route CLOSED; no uncontrolled escaped job |
| tests/worker_accounting/native/test_budget.py::test_gap_threshold_final_overbudget (006) | Actual root/thread/rapid-exit CPU reaches S and whole-object stop; final <=B; observed max G/A/K/Q within fixed caps | Equality/above S, native component regression, unit confusion, CPU>B, delayed observer/query/bridge and clock failure stop/fail/profile closed. Never relax threshold or tolerance |
| tests/worker_accounting/native/test_lifecycle.py::test_stop_drain_quiescent_final (007) | Cancel/EOF/heartbeat/resource stop kills root+descendants, native emptiness/reap, three stable final component reads | Root exits0 while grandchild continues, fork during stop, ignored signal, frozen task, dropped notification, delayed/reordered stats and kill timeout cannot claim whole-object finality |
| tests/worker_accounting/native/test_lifecycle.py::test_final_before_release_ack (008) | Exact identity/hash receipt bound, actual durable ack independently checked before release | Wrong/stale/double ack, counter changed after apparent drain, torn receipt, lost ack and last-handle closure before finalization HELD; unavailable never zero |
| tests/worker_accounting/native/test_death.py::test_actual_three_death_orders (009) | Actual separate worker death, controller death, both; independent whole-tree backstop proves no live compute | Hidden inherited/duplicate job handle, PDEATHSIG-only orphan, missing manager and worker-only cleanup cannot pass simultaneous-death control; missing finals unavailable |
| tests/worker_accounting/native/test_contract.py::test_wire_abi_units_errors (010) | Native ABI probe and byte-level golden wire, exact canonical pure conversion, legitimate available0 and unavailable null separated | Every header/payload cap/+1/EOF, unknown kind/reserved/sequence/identity/platform, bad returnedlength, signed/unsigned/bool confusion, overflow/underflow and malformed text rejects without leak |
| tests/worker_accounting/native/test_parent.py::test_final_tail_and_parent_custody (011) | Owned post-exit controller totals and finite-fixture parent totals independently measured, full tail and bounded sum retained; later production lifecycle separately proven | Controller SELF before finalwrite, worker prepublication SELF, lost parent acknowledgment, exited helper omitted or worker unrelated workload invalidates closure; no runtime pass from fixture-only oracle |
| tests/worker_accounting/native/test_bounds.py::test_backpressure_bounded_fail_closed (012) | Bounded output/transport drains under slow reader while native observation remains timely | Fill queue4/+1, stdout/stderr65536/+1, 4096 counter/wire cap/+1, sample32768/+1 or16MiB/+1, receipt/result/scratch/parent cap/+1; stop before allocation/write, no truncate-then-accept |
| tests/worker_accounting/native/test_recovery.py::test_durable_ack_crash_matrix (013) | Future storage-owned fixture persists exact receipt+intent+ack and reconciles deletion/uncertain commits at each crash position | Crash before/after flush/intent/ack/release/final parent/write/SQLite commit keeps liability and no partial visible success; cannot recreate missing final CPU; current source has no such adapter |
| tests/worker_accounting/native/test_recovery.py::test_old_inventory_unknown_closed (014) | Current known0003 gravity/MT fixtures still validate, immutable old snapshots/tombstones retained | New physical receipts/unknown revision/DDL/child variants rejected by unchanged ops; no restore over existing directory, resurrected deletion or backup hot-snapshot acceptance |
| tests/worker_accounting/native/test_admission.py::test_every_parent_gate_closed_until_actual (015) | Full actual-platform evidence set independently reviewed at exact profile/code/context pins | One mock/skip/stale/missing evidence, wrong OS/runtime/ABI/security/domain/topology identity or absent approval keeps CLOSED. Every original15 gate remains separately required |
| tests/worker_accounting/native/test_scope.py::test_no_shared_or_policy_changes (016) | Proposed native isolated scope, old pure/protected source blobs unchanged | Any app/worker/database/migration/import/package/installer/public-admission/source-bundle/runtime-policy change rejects this bounded unit |

## 3. Counter oracle, units and exact arithmetic controls

Native fixture_cpu.c is a fixed original finite executable, not arbitrary user
code or a helper claimed already present. It self-measures Windows owned process
GetProcessTimes or Linux getrusage SELF and returns bounded private values before
exit. Independent outer MAIN harness then reads post-exit GetProcessTimes handles
or reaps with wait4 to observe full native process totals, including report/exit
tail. Neither root CPU nor RUSAGE_CHILDREN becomes production science charge.

For <=32 finite contributors preserve every exact counter pair and setup/exit
boundary; compare lifetime object total against sum complete fixture totals.
Fixed parent oracle lower allowance1ms and upper100ms for measured accounting
boundary/resolution only, after cold/warm root calibration. If those bounds
cannot be substantiated, CLOSED; do not tune tolerance to the measured failure.
An outer oracle using the same kernel is independently constructed call logic,
not a hardware-time proof. Do not claim residual tails from fixture self-reports
are zero. Inherited/cgroup topology is checked before interpreting totals.

Native golden cases, before actual OS controls:

- Windows user1/kernel2 ticks yields300ns; Linux usage1/user2/system3 usec
  yields5000ns. Preserve unequal Linux usage vs components, not false equality.
- Windows max convertible total92233720368547758 ticks ->9223372036854775800ns;
  +1 refuses before multiplication. Linux max9223372036854775usec
  ->9223372036854775000ns; +1 refuses. Native sum itself checked before multiply.
- Negative signed Windows ticks, Linux decimal U64+1, leading sign, duplicate
  field,20digits with out-of-range magnitude, embeddedNUL, native BOOL/non-int
  confusion, malformed SAMPLE empty variants and uint32 process/exit overflow.
- Checked delta current<previous underflows even if aggregate rises; signed
  root exit range differs Windows unsigned32 vs Linux signed32; both preserve
  nonzero exit as failure. Exact available0 differs from unavailable and no
  native record is synthesized for missing length/AccessDenied/ENOENT.
- QPC quotient/remainder golden conversion nearI64, negative/regressed ticks,
  zero frequency, rounding-up elapsed cap; Linux timespec/timeval ns/us
  boundaries and checked seconds. No rounding tolerance for CPU identity.
- Fixed wire endian bytes,unaligned offsets,zero reserved,frame cap before
  copy/int conversion; compare canonical result against unchanged pure decoder.
- Delayed native updates through the admitted50ms visibility window after empty
  state, three identical premature reads and late counter increment: finalization
  waits50ms before first final query and never treats40ms equality as final proof.

Strict B+1ns is a supplied-record negative boundary, not a claimed native
resolution. Actual Windows/Linux overbudget controls use the next representable
100ns/1000ns CPU quantum and must fail; no fictional1ns OS measurement.

ABI probe NOT_RUN: Windows all sizes/offsets/alignments/signatures used in
design and retained error semantics; Linux clone_args88 fields/offsets plus
siginfo_t/timeval/timespec/rusage/PIDFD/wait flags against actual headers/CRT.
No Linux glibc layout guessed from Windows or raw tag. Every binary receipt
binds compiler/linker/headers/sysroot/options/source/binary digests and OS identity.

## 4. Timing repetitions, safety bounds and unavailable cases

After explicit MAIN context approval ONLY, new private fixture root outside
public repository, no production root/data/key/account or shared OS subtree.
No existing directory overwrite. One exact owned attempt, bounded process/task
and outputs. MAIN chooses concrete safe credentials and manager context; the
test cannot invent a temporary manager then call it proof of the deployed one.
No sudo/install/remount/global trust or policy relaxation as a fixture step.

For EACH platform/profile repeat100 times: root-only cold/warm, sequential exited
burst, three-generation/reparent, syscall-heavy, admitted maximum parallelism,
cancel, output backpressure and each abrupt death order. Nominal fixture science
CPU<=2s perattempt, total wall<=30min. Actual S/B threshold controls separately
exercise each real lane once; do not substitute a test-only tiny limit for the
production60/240 gate. Abort on first escape/unknown-live/unauthorized boundary/
counter failure/headroom fail; never run dangerous controls unbounded to finish
a count. An uninterruptible-task control that cannot be safely bounded stays
NOT_RUN/CLOSED instead of deliberately damaging a host.

Record maximum complete gap/query time, independently supported visibility and
rounding limits, stop-to-last-contained-CPU, final settle, root/adopted exits,
native user/system totals and overshoot/undershoot. G20ms/A50ms/K250ms/Q1ms/N8
and drain2s are fixed pass limits; p95/average are descriptive only. Non-real-time
worst-case proof cannot come from100 repeats alone; MAIN must accept residual
monitored risk and source/actual-bound evidence, or leave CLOSED. Memory.max/job
commit counters are not RSS; device/server source ceilings remain provisional.

## 5. Parent15 compatibility and durable crash matrix

Keep original PWA-001..015 tests and gates independently CLOSED/NOT_RUN until
their own complete real evidence exists. Mapping:001->NCC001;002->002/003;
003->004;004/005->005;006->006;007/008->007/008;009->009;010->010;
011->003/006;012->015;013->013;014->011/012;015->014/016.
A new gate map does not replace originals or delete missing conditions.

Crash matrix must distinguish all ten positions from contracts. For each,
record exact source/runtime/attempt/object, native alive/drained evidence,
final known/unavailable, receipt custody/flush/intent/ack/parent release state,
quota/deletion authority and operator-needed outcome. Fixtures write ONLY new
private temp roots and dummy admitted objects, never active app state. Unknown
staging quarantined by exact operator scope/hash proof, not worker auto-cleanup.
Current ops maintenance/deletion/tombstone gates remain untouched. Storage owner
must supply explicit migration/revision/DDL and exact inventory support before
any integrated roundtrip; no claim that future physical children already restore.

## 6. Immutable receipts and independent review

Each actual future receipt records reviewed full commits and hashes of all
controller/bridge/fixture/runtime/library/header/compiler/context inputs, precise
command/OS/identity, configured vs observed limits, raw native bounded samples,
canonical pure transcript hash/count/bytes, original exit/status and failure.
Private original bytes are immutable, including failed/incomplete attempts.
Public guide/report carries only safe reviewed aggregates; no secrets or native
handles/PIDs/privatepaths are pushed. HTTPS source hash is not binary signature.

Record NOT_RUN, unavailable, fail,pass separately. Do not overwrite historical
419pure,43MAIN helper,168L2suite,2bounded numerical failures or host disk failure
with native receipts. MAIN owns independent actual replay and host execution;
this unit has only docs measurements. Approval of this design is neither a
profile activation nor integration/production/deployment authorization.
