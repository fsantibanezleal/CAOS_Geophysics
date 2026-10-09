# Physical accounting prospective validation

Date: 2026-10-03. Status: planned, ALL runtime tests NOT_RUN.
No tests/source/helper files or actual OS objects are created by this document.
Full MAIN read/approval precedes even native probes or isolated OS fixture setup.
These exact prospective filenames are gate identifiers, not commands to run now.
No added CI jobs or OS matrix; actual controls run locally under later authority.

## 1. Evidence tiers and prospective recipe

1. Documentation checks validate scope, links, requirement gate mapping and
   receipt provenance. They cannot pass a runtime requirement.
2. Future deterministic parser/state-machine unit tests exercise fake call returns
   and bounded fixture files. They prove only contract logic, never OS capability.
3. Future native ABI/layout probe on each approved platform checks exact symbols,
   structure sizes/offsets, syscall arguments, units and return/error handling.
4. Future isolated actual OS controls measure birth containment, lifetime CPU,
   denied escape, threshold overshoot, full death/termination and counter drain.
5. Future exact physical-worker integration remains storage-owner/MAIN gated,
   including science, quota, deletion, cancellation, uncertain commit and recovery.

For later authorized actual controls: MAIN provides a new private external temp
fixture root, pinned code/runtime/controller/executable hashes and a concrete
approved OS context; never use production state, public raw fixtures, shared
existing cgroup roots, an active project or owner keys. Before any OS creation,
resolve exact fixture/context boundaries, inspect existing policies read-only and
refuse wrong/unknown identity. Instantiate only fresh private job objects under
the admitted context, run only fixed fixture executables with process/task/output
ceilings, save private receipts and retain unknown state for operator review.
No sudo/install, global trust, new delegation, remount or service change is an
implicit test prerequisite. MAIN owns installer/context and actual host execution.

Each receipt binds full reviewed Git commits and all actual input/executable/
runtime/controller/profile hashes, OS/kernel/build/ABI, exact argv, context,
configured versus observed limits, native samples, final CPU and drain/death
evidence. Never infer a fresh pass from an old runtime, changed library, mutable
source checkout, average or p95. Private paths/credentials stay outside public
repo/logs. Publish only redacted aggregate facts approved by MAIN. A skipped
platform control stays NOT_RUN, not PASS/ineligible proof for the other platform.

## 2. Counter oracle and named controls

Independent positive oracle: fixed native fixture executables self-measure their
user/system CPU with Windows GetProcessTimes(own process HANDLE, FILETIME outputs)
or Linux getrusage(RUSAGE_SELF,&rusage) and report it
through bounded private pipes before exit. Parent then reaps them. Kernel group
totals must retain the sum of every completed fixture plus current root CPU,
within separately calibrated resolution and group-creation accounting boundary.
Fixture-reported counters are validation-only, never authoritative job charging.
FILETIME high/low DWORDs reconstruct uint64 user/kernel 100-ns ticks;
Linux ru_utime/ru_stime timeval sec/usec convert with checked arithmetic. For
finite fixtures of <=32 processes, the proposed fixed comparison is group CPU
>= sum(self reports)-1000000 ns and <=sum(self reports)+100000000 ns, including
the root report and a separately observed fixed setup/exit-tail allowance. The
lower bound permits at most 1 ms undercount; the upper allowance is at most
100 ms for whole-fixture unreported setup/exit tails, not missing descendants.
Before the positive gate, cold/warm root-only calibration must show those tails
and native clock/accounting resolution within these bounds; otherwise CLOSED,
not fitted tolerance. This oracle is structurally independent of group queries
but shares kernel accounting; it does not prove an external hardware-time oracle
or zero-overshoot guarantee. The exact SDK/UAPI layouts are native compile/probe
review gates; until measured lifetime remains NOT_RUN. Negative fixture
deliberately creates and reaps children faster than
the 20 ms observation window: live-only psutil should miss them while the chosen
group accounting retains them. Test labels must report that distinction.

| Prospective exact gate | Required control and failing oracle | Current |
| --- | --- | --- |
| tests/worker_accounting/test_lifetime.py::test_exited_descendants_and_isolation | Root + sequential short-lived children + grandchildren; reaped and unreaped exits, concurrent threads, cold imports/JIT/replay; group total retains every exited contributor. Concurrent busy API/controller/external process does not enter science counter | NOT_RUN |
| tests/worker_accounting/test_windows.py::test_creation_bound_job_before_marker | Fixed child writes a bounded first-user-code marker; JOB_LIST containment exists before marker. Inject sizing/update/create/membership/limit/resume errors; no marker on any failed gate. Unsupported job list has no assignment fallback | NOT_RUN |
| tests/worker_accounting/test_linux.py::test_clone3_birth_in_owned_group | Native first-child instruction observes exact fresh domain; clone3 errors do not fork/Popen. Account setup/exec/import and exited descendants; reject existing/foreign/changed inode, hybrid/threaded group or controller inside measured subtree | NOT_RUN |
| tests/worker_accounting/test_containment.py::test_no_escape_and_no_control_authority | Actual credential attempts breakaway, nested jobs, brokered WMI/service launch, job-handle duplication/policy changes or Linux migration to every reachable ancestor/sibling, ptrace/controller-FD acquisition, capability escalation; success or untested reachable broker closes profile. No fixture escape is silently swept | NOT_RUN |
| tests/worker_accounting/test_linux.py::test_missing_or_shared_authority_closed | No delegation/context, same compute/controller control rights, permission denial, unavailable kill/syscall, missing manager backstop, mutable ancestors and absent credential transition; all refuse before numerics, never repair host | NOT_RUN |
| tests/worker_accounting/test_budget.py::test_threshold_gap_and_counter_fail_closed | Below/equal/above S; decreasing counters, overflow, duplicate/missing keys, short read, query failure, wrong return length and delayed observation; kill entire object and close profile | NOT_RUN |
| tests/worker_accounting/test_lifecycle.py::test_kill_drain_final_counter_before_release | Root/child/grandchild ignore graceful signals, fork around stop, stale/missing notification, delayed counter updates and ack loss; prove no live descendants, reap and three stable reads before sealing/release. Kill timeout retains unknown state | NOT_RUN |
| tests/worker_accounting/test_lifecycle.py::test_root_exit_with_live_grandchild | Root exits success while grandchild continues CPU; no result eligibility, whole-object stop and retained final CPU | NOT_RUN |
| tests/worker_accounting/test_death.py::test_worker_guardian_and_simultaneous_death | Real separate worker SIGKILL/TerminateProcess, real controller death, both, root death and inherited-control-handle negative; prove independent whole-tree backstop and bounded latency. Missing final counters remain unavailable | NOT_RUN |
| tests/worker_accounting/test_contract.py::test_exact_units_shapes_and_safe_errors | Windows 100 ns versus Linux 1000 ns; signed/unsigned boundaries, bool/float/string confusion, counter skew, nullable unavailable variant, unknown fields/platforms and fixed safe message mapping; no sensitive output | NOT_RUN |
| tests/worker_accounting/test_budget.py::test_no_false_hard_cap_and_final_overbudget | User-heavy and syscall/kernel-heavy CPU, rapidly exiting contributors, threads on all admitted CPUs and controller starvation; user-only/quota/wall/live polling cannot pass combined budget. Final B+1 ns fails; old claimed hard-kernel guarantee rejects | NOT_RUN |
| tests/worker_accounting/test_admission.py::test_all_platform_evidence_required | Exact OS/runtime/context/profile digest change, one missing/mock/skip/stale evidence or timing/escape failure keeps CLOSED. Parent context with Windows jobs or Linux namespace/seccomp restrictions tested separately | NOT_RUN |
| tests/worker_accounting/test_integration.py::test_uncertainty_preserves_debt_and_blocks | Counter/kill/receipt loss, cancel-before-publication, deletion, worker crash and uncertain commit leave no visible partial success, preserve reservations/intents/stages and block next admission/backup. No new storage behavior is implemented here | NOT_RUN |
| tests/worker_accounting/test_bounds.py::test_stream_caps_and_parent_budget | 16KiB start, 1KiB control frames, 4KiB setup/release ack, 64KiB stdout/stderr/receipt, 32768 records/16MiB samples, parent memory/CPU ceiling and result/scratch envelopes at cap/+1; enforce before allocation/write, no whole buffering | NOT_RUN |
| tests/worker_accounting/test_integration.py::test_unknown_revision_and_pin_rejected | Existing 0003 roots/gravity/MT unchanged; unknown receipt/revision/DDL/source pin rejected. Future exact approved adapter only; no wildcard or public admission mutation | NOT_RUN |

## 3. Timing and containment admission, exact pass criteria

For EACH actual supported platform/profile, positive and negative native controls
must be repeated 100 times for root-only, sequential exited-child burst,
three-generation fork/reparent tree, syscall-heavy fixture, max admitted parallel
threads/tasks, cancellation near threshold, output-cap failure and abrupt deaths.
Use bounded fixture CPU (nominal <=2 s per attempt; explicit threshold controls
exercise the actual S/B once per lane separately). At most one contained attempt;
total isolated run wall budget 30 minutes, abort on any escape/unknown live state,
unbounded allocation, unauthorized path/context or headroom failure. Do not
continue 100 repetitions after a failed containment control. Real physical
upper-bound jobs are a different admission unit, not fabricated by CPU fixtures.

Report max successful-counter observation gap, max query duration, independently
substantiated counter visibility/rounding bound, max stop-to-last-CPU interval,
final-counter settle time, root/grandchild exits and final over/undershoot. Every
control must meet G<=20 ms, A<=50 ms, K<=250 ms, Q<=1 ms aggregate, drain<=2 s,
N<=8 and final CPU<=B with the 3 s margin. The formula alone does not prove A/K
or OS scheduling determinism; explain independent source/measurement evidence
and residual monitored-enforcement risk to MAIN. Percentiles are descriptive,
never the pass oracle for a maximum bound. If proof fails, preserve CLOSED,
do not increase B, silence failures or call bandwidth an equivalent budget.

Windows actual ABI oracle must check every declared structure size/offset and
API error path against selected SDK; Linux native probe fixes syscall/UAPI and
waitid flags/PIDFD support. Completion notifications are deliberately dropped
in controls to prove absence is not used as no-live/final-counter evidence.
Controller-death Windows test must prove last-handle behavior without another
hidden job handle. Linux simultaneous-death test must demonstrate the actual
existing manager policy, not a dummy manager that only exists inside the test.

## 4. Additional fail-closed and regression controls

Long suspension/starvation of observer, frozen group, uninterruptible task
simulation, delayed termination, counter lag >50 ms, failed readback and OS
topology/credential changes all close profile and retain failed/held state.
If a dangerous control cannot be safely bounded on that platform, record NOT_RUN
and CLOSED instead of performing an uncontrolled host experiment.

Future integration gates need the separately approved physical publication and
new revision/DDL adapters. Run real immutable API states through correction,
transform, cancel/deletion/backup/restore only after their owners authorize the
exact integrated tree. Current ops known-schema gates remain negative controls;
do not modify them to accept unknown future children. Counter fixtures cannot
prove numerical physics or legal field-source rights. MAIN's existing 30% disk
gate remains unchanged; no owner answer or actual host execution is implied.
