# Physical worker accounting requirements

Status: planned
Date: 2026-10-03. Documentation proposal only; every runtime gate is NOT_RUN.
Full MAIN read and explicit approval of this entire folder precedes any source,
test implementation, Job Object, cgroup, service or environment action.

Read [research](../../../research/physical-worker-accounting-2026-10-03.md),
[design](design.md), [typed contracts](contracts.md),
[validation](validation-plan.md), [tasks](tasks.md) and
[review packet](review-packet.md) together. These named test paths are prospective,
not created files or current capabilities. No feature flag is enabled by this SDD.

PWA-001 THE accounting unit SHALL bind one fresh, exclusive OS accounting object
to one immutable job attempt, with controller CPU excluded and complete lifetime
user plus system CPU including exited descendants retained.
Gate: tests/worker_accounting/test_lifetime.py::test_exited_descendants_and_isolation.

PWA-002 WHEN a Windows child is launched, THE unit SHALL assign its exact Job
Object through PROC_THREAD_ATTRIBUTE_JOB_LIST during CreateProcessW, verify
membership and limits while suspended, and resume only after admission succeeds.
Gate: tests/worker_accounting/test_windows.py::test_creation_bound_job_before_marker.

PWA-003 WHEN a Linux child is launched, THE unit SHALL use clone3 with
CLONE_INTO_CGROUP into its fresh domain cgroup before child execution, preserve
object/credential identity and reject create-then-migrate fallback.
Gate: tests/worker_accounting/test_linux.py::test_clone3_birth_in_owned_group.

PWA-004 IF breakaway, brokered execution, cgroup migration, controller-handle
inheritance or privileged descendant escape is possible in the admitted trust
domain, THEN THE unit SHALL refuse launch and close platform admission.
Gate: tests/worker_accounting/test_containment.py::test_no_escape_and_no_control_authority.

PWA-005 WHERE Linux accounting is included, THE unit SHALL require MAIN-approved
existing delegation and launch credentials, deny compute writes to every
migration destination/control ancestor, and refuse absent or unknown authority.
Gate: tests/worker_accounting/test_linux.py::test_missing_or_shared_authority_closed.

PWA-006 WHILE a contained attempt is active, THE controller SHALL compare
authoritative aggregate counters against the fixed early-stop threshold, enforce
monotonic observation timing and stop on counter, identity or timing uncertainty.
Gate: tests/worker_accounting/test_budget.py::test_threshold_gap_and_counter_fail_closed.

PWA-007 IF a budget, cancellation, heartbeat, output, integrity or runtime
failure occurs, THEN THE controller SHALL terminate the complete accounting
object, retain it until counters and absence of live descendants are validated,
and prevent partial results from becoming publication-eligible.
Gate: tests/worker_accounting/test_lifecycle.py::test_kill_drain_final_counter_before_release.

PWA-008 WHEN the root process exits, THE controller SHALL continue lifetime
accounting until the whole object is empty, reap owned descendants and reject
unexpected surviving children rather than treating root exit as completion.
Gate: tests/worker_accounting/test_lifecycle.py::test_root_exit_with_live_grandchild.

PWA-009 IF the worker or controller is killed, THEN THE platform SHALL prove its
independently admitted whole-tree death backstop or remain CLOSED; missing final
counters SHALL remain unavailable and prevent success.
Gate: tests/worker_accounting/test_death.py::test_worker_guardian_and_simultaneous_death.

PWA-010 THE unit SHALL retain integer native counters, checked conversions,
exact receipt/profile variants and safe bounded errors; malformed, decreasing,
overflowing or missing counters SHALL NOT be replaced with zero or wall time.
Gate: tests/worker_accounting/test_contract.py::test_exact_units_shapes_and_safe_errors.

PWA-011 THE unit SHALL preserve proposed correction/transform 60/240-second
aggregate ceilings without treating bandwidth, user-only limits, wall time or
live psutil polling as an equivalent combined CPU hard cap.
Gate: tests/worker_accounting/test_budget.py::test_no_false_hard_cap_and_final_overbudget.

PWA-012 WHEN a platform profile is evaluated, THE admission gate SHALL require
exact OS/build/runtime pins and independently measured worst-case timing,
retention, containment and death controls, with separate Windows/Linux verdicts;
skipped, mocked, stale or absent evidence SHALL remain NOT_RUN/CLOSED.
Gate: tests/worker_accounting/test_admission.py::test_all_platform_evidence_required.

PWA-013 WHILE accounting or termination is uncertain, THE integration SHALL
preserve staging, cleanup liabilities and reservations and refuse the next
attempt, backup or adoption until separately reviewed recovery resolves them.
Gate: tests/worker_accounting/test_integration.py::test_uncertainty_preserves_debt_and_blocks.

PWA-014 THE unit SHALL bound control input, counter reads, sample records,
stdout/stderr, private receipts and controller overhead without weakening
physical RSS, scratch, memory, wall or result limits.
Gate: tests/worker_accounting/test_bounds.py::test_stream_caps_and_parent_budget.

PWA-015 THE accounting integration SHALL require explicit later approval of
worker/API/storage schema and source/admission pins, leaving current 0003 ops
and all unknown future variants fail-closed rather than accepting a wildcard.
Gate: tests/worker_accounting/test_integration.py::test_unknown_revision_and_pin_rejected.
