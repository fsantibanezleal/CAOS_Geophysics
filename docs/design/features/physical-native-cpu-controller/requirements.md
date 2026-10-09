# Native CPU controller requirements

Status: planned
Date: 2026-10-03. Issue [140](https://github.com/fsantibanezleal/CAOS_Geophysics/issues/140).
All named source/test paths are PROPOSED, absent, NOT_RUN. Full MAIN read and
explicit exact-pin approval precedes source, tests, compilation or OS actions.
The [design](design.md), [contracts](contracts.md), [validation](validation-plan.md)
and [research](research.md) are normative together. No runtime profile is admitted.

NCC-001 THE native controller SHALL use one fresh identity-bound science object,
charge aggregate lifetime user+system CPU including exited descendants, preserve
all native components and leave the unchanged pure protocol non-authorizing.
Gate: tests/worker_accounting/native/test_lifetime.py::test_exited_descendants_isolated.

NCC-002 WHEN creating a Windows root, THE controller SHALL use creation-time
JOB_LIST plus CREATE_SUSPENDED, read back job limits/membership before exactly
one resume, and refuse unsupported or failed routes before science executes.
Gate: tests/worker_accounting/native/test_windows.py::test_birth_suspended_job.

NCC-003 WHERE Windows is admitted, THE controller SHALL set and verify fresh
job user-time, process-count, affinity and kill-on-close policies while using
combined total accounting as the authoritative budget, without breakaway.
Gate: tests/worker_accounting/native/test_windows.py::test_limits_not_combined_hard_cap.

NCC-004 WHEN creating a Linux root, THE controller SHALL call clone3 INTO_CGROUP
with PIDFD into a fresh retained domain before child setup/exec, reject every
unsupported/denied context and never create then migrate or use Python preexec.
Gate: tests/worker_accounting/native/test_linux.py::test_birth_domain_pidfd.

NCC-005 IF compute can migrate, duplicate controller authority, mutate limits,
signal/ptrace the observer or invoke an out-of-object broker, THEN THE controller
SHALL reject admission; missing credential/security/manager context SHALL stay CLOSED.
Gate: tests/worker_accounting/native/test_containment.py::test_denied_escape_and_authority.

NCC-006 WHILE running, THE controller SHALL observe native counters independently
of Python/file/database stalls, stop at CPU>=S or observation gap/query failure,
retain offending evidence and refuse final CPU>B without tolerance relaxation.
Gate: tests/worker_accounting/native/test_budget.py::test_gap_threshold_final_overbudget.

NCC-007 IF cancellation, EOF, heartbeat/output/timing failure or root exit with
live descendants occurs, THEN THE controller SHALL stop the whole object,
bound drain and never equate a process/notification exit with whole-job finality.
Gate: tests/worker_accounting/native/test_lifecycle.py::test_stop_drain_quiescent_final.

NCC-008 WHEN finalizing, THE controller SHALL retain the exact object through
three equal empty final reads and durable receipt acknowledgment, preserve unknown
states and never infer a final zero from unavailable counters or destroyed objects.
Gate: tests/worker_accounting/native/test_lifecycle.py::test_final_before_release_ack.

NCC-009 IF worker/controller/both die, THEN THE admitted platform SHALL prove
its independently owned complete-tree backstop or stay CLOSED, with no fabricated
receipt, unattended recovery claim or subsequent attempt over unresolved liability.
Gate: tests/worker_accounting/native/test_death.py::test_actual_three_death_orders.

NCC-010 THE controller SHALL use pinned SDK/UAPI types and checked integer units,
bounded native I/O and exact fixed transport variants; short/malformed/unknown,
overflow/underflow/regression and unavailable observations SHALL fail safely.
Gate: tests/worker_accounting/native/test_contract.py::test_wire_abi_units_errors.

NCC-011 THE integration SHALL measure all controller lifetime and worker attempt
pre/post/publication CPU including exited contributors and final-write tails,
and SHALL NOT claim release eligibility from a preliminary SELF snapshot.
Gate: tests/worker_accounting/native/test_parent.py::test_final_tail_and_parent_custody.

NCC-012 THE controller SHALL cap transport/output/sample/receipt memory and writes
before allocation/emission, retain incremental evidence and avoid a blocked drain
or serializer disabling CPU supervision or weakening other resource ceilings.
Gate: tests/worker_accounting/native/test_bounds.py::test_backpressure_bounded_fail_closed.

NCC-013 WHILE receipt/ack/commit/termination is uncertain, THE integration SHALL
retain immutable stages/reservations/intents/debt, block publication and backup,
and require separately reviewed exact recovery authority rather than replayed success.
Gate: tests/worker_accounting/native/test_recovery.py::test_durable_ack_crash_matrix.

NCC-014 THE recovery boundary SHALL reject unknown physical state/receipt/DDL
variants and leave current0003 ops, source bundles and public admission unchanged
until a distinct exact adapter/migration unit has full approval and actual gates.
Gate: tests/worker_accounting/native/test_recovery.py::test_old_inventory_unknown_closed.

NCC-015 WHEN evaluating a profile, THE reviewer SHALL require independently pinned
actual positive/adversarial controls and maximum timing/lag/kill evidence for
that platform/context; synthetic, skipped, stale or unavailable gates SHALL NOT admit it.
Gate: tests/worker_accounting/native/test_admission.py::test_every_parent_gate_closed_until_actual.

NCC-016 THE implementation scope SHALL leave pure source/tests and existing app,
worker, database, migrations, runtime/security provisioning and all policies
unchanged, with no package/install/host operation implied by documentation approval.
Gate: tests/worker_accounting/native/test_scope.py::test_no_shared_or_policy_changes.
