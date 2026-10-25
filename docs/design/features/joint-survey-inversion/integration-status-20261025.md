# M11 supplied-survey integration status — 2026-10-25

## Implemented and validated locally

The current product branch contains the closed native input contract, geometry
and mask planner, public gravity and magnetic forward operators, weighted
joint objective, exact cross-gradient and Hessian paths, separately optimized
uncoupled references, conditioned public baselines, sealed selection and
evaluation, private serialization/replay, bounded CLI workflows, and the
frozen 24-case control matrix. Reproduction entry points are
`scripts/run_joint_survey.py`, `scripts/validate_joint_matrix.py`,
`scripts/validate_joint_precision.py`, and
`scripts/validate_joint_resources.py`.

The executable receipt is
[`m11-final-precision-20261025.json`](evidence/m11-final-precision-20261025.json).
Its numerical artifacts were generated outside the repository at
`E:\_worktrees\_runs\CAOS_Geophysics-M11-integrated-20261025`.

| Gate | Observed result |
| --- | --- |
| Focused numerical regression | 451 tests; 446 passed, 5 skipped, 0 failed, 0 errors |
| Actual workflow matrix | 24 of 24 complete; all 24 sealed replays validated |
| Candidate status | 524 converged, 100 nonconverged, 0 engine failures; nonconvergence retained |
| Independent exact-face comparison | 343 converged candidates passed all four predicates; 41 nonconverged retained; 0 reference-stationarity failures |
| Maximum-count resource gate | 4,096 full cells, 1,932 active, 2,048 receivers per modality and full covariance; active-count plus one rejected |
| Maximum-count replay | Validated; peak sampled RSS 464,322,560 bytes during replay; no scratch growth observed |
| Linux CPU regression | 488 passed, 3 skipped across the M11 numerical suite and M04 magnetic forward controls on CPython 3.12.10 x86_64; platform-specific SimPEG, discretize and SciPy source pins recorded in [`runtime-linux-cp312.json`](runtime-linux-cp312.json) |

The matrix tests co-structural, disjoint, flat/null and wrong-field regimes at
dense, sparse-blocked and shifted geometries, including diagonal and full
covariance. A positive coupling was selected in each case, but this is not a
claim that joint inversion improves every regime: the held-out selection,
nonconverged candidates and truth diagnostics remain separately available.
All outputs remain synthetic controls. `field_eligible`,
`scientific_precision_accepted` for the overall matrix, and `public_activation`
remain false by design.

The Linux run verifies the named regression suite against the Linux CPU source
epoch. It does not yet rerun the full 24-case sealed workflow matrix, the
maximum-count resource workflow, or the independent precision receipt on Linux.
The RTX 4070 exists on the Windows development host; M11 remains a measured CPU
lane and makes no GPU performance or VPS-capability claim.

The browser importer is now pinned to the exact current
`physical_nonlinear_optimizer.py` source bytes. `frontend/scripts/verify-joint-pins.mjs`
checks the browser pin against both the optimizer source and the M11 adapter
before every production build. The real-artifact browser import, input, and
result views pass 46 focused tests; eight are conditional on optional component
fixtures. Two additional hash-admission tests still require the retained
maximum-size external output fixture.

## Product integration still open

The local solver and CLI do not yet complete the online workflow. The current
FastAPI assembly does not register the M11 joint-member, dataset, job,
cancellation, custody-history, or result-export routes expected by the
frontend's `JointProjectWorkbench` and `JointCustodyApi`. The frontend's
actual-Python custody tests therefore correctly fail closed when no real API
receipt is supplied. Do not call uploaded-survey M11 available online until
those routes are integrated with the current account/project ownership,
bounded worker, migration, storage and result-custody paths and pass the real
Python API/browser contract tests.

This work does not change the whole-product SDD convergence ledger. It does not
close field-data rights/validity, broader M01–M13 submitted-data coverage,
complete browser visual acceptance, current VPS resource admission, or the
single-origin replacement cutover. No deployment was performed.
