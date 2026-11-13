# Safeguarded scaled IRLS correction requirements

Status: implementation approved after full mathematical/native pre-code review,
2026-10-08;18 partition controls PASS. The `exact-q-1` matrix exposed one
nonconverged final refit. The current `exact-q-replay-legacy-init-1` source-bound
original24 matrix passed (25 tests, 0 failures/errors/skips; 18 nominal controls
below WRMS1.5; six condition3 nuisance controls remain poor). One selected
nominal baseline's 32 corrected fixed-recipe noise refits converged and passed
source-bound replay. The local fixed-workload 20-repeat resource gate is PASS:
20/20 cap and 20/20 nominal selected trials have complete measurements.
Nominal peak-RSS p95 is308,944,076.8 bytes and p95 wall time892.8912s; cap
peak-RSS p95 is285,847,347.2 bytes and p95 wall time137.1935s. The retained
first cap12 receipt has WinError1455 and is incomplete; its explicitly named
retry is the selected valid sample. A bounded 40-test current-source unit gate
passed. These samples do not prove a resource upper bound or qualify host limits.
Independent review and host/product/release acceptance remain NOT RUN. See
[resource repeat evidence](resource-repeat-2026-11-01.md).
Old cpu1/plain positive remains a genuine failure and is not rewritten.
[Design](design.md),
[tasks](tasks.md), [historical cause](../m02-survey-l2/irls-positive-cause.md).

CIR01 THE corrected policy SHALL preserve the original geometry, physical
objective, scientific weights/norms/beta, epsilon log17/floor17,21stages/20updates,
all21 actual inner convergence and original last-three model/weight1e-6 gates;
the owner-approved additive exact terminal certificate may accept only the
strictly certified CPU2 fixed-point case specified in
[the 2026-10-31 amendment](terminal-certificate-amendment-2026-10-31.md).
Gate: tests/numerics/test_gravity_irls_corrected.py::test_corrected_original_positive

CIR02 WHEN a predictor is enabled, THE unit SHALL apply the derived source-action
SPD M and rank-one J without dense production inverse/Hessian or copied CG.
Gate: tests/numerics/test_gravity_irls_corrected.py::test_matrixfree_independent_jacobian

CIR03 IF the model has any literal bound face, tied max or null x, THEN THE unit
SHALL disable its derivative before proposal construction/CG and record why.
Gate: tests/numerics/test_gravity_irls_corrected.py::test_branch_disable

CIR04 WHEN a pair is solved, THE unit SHALL require actual CG200/rtol1e-6/atol0
true residual, delta>0,delta/(1+||c||inf)>=sqrt(eps64),strict actual merit descent,
and20or fewer actual trials, with no failed-call fallback or retry.
Gate: tests/numerics/test_gravity_irls_corrected.py::test_guard_reject

CIR05 WHILE fitting, THE unit SHALL charge all initialization/auxiliary/native
moves to one200accepted/201states/120sfit/1800scalibration ledger, at most3pairs
perstage/126actualCGcalls/63anchors and retain actual timing/failure evidence.
Gate: tests/numerics/test_gravity_irls_corrected.py::test_caps

CIR06 WHEN replayed, THE result SHALL reconstruct every physical frozen stage,
canonical weight/KKT and auxiliary linear residual/merit/timing/count lineage,
reject rehashed inconsistencies and obey unchanged whole-wrapper limits.
Gate: tests/numerics/test_gravity_irls_corrected.py::test_ledger_replay

CIR07 THE request/result SHALL explicitly bind cpu2/newpolicy/source inventory
and never implicitly upgrade or accept cpu1/plain archives as corrected.
Gate: tests/numerics/test_gravity_irls_corrected.py::test_epoch_separation

CIR08 WHEN full scientific validation runs, THE corrected workflow SHALL retain
all original24 cases/folds/assertions,actual negative/noise/refit/resource outcomes
without changing original physical error/KKT/mapping/positive thresholds.
Gate: tests/numerics/test_gravity_irls_corrected_matrix.py::test_original24_corrected_science

API/UI/course use the separate [inspection SDD](../m02-result-inspection/requirements.md);
no completeness, source/native/Linux/host or field acceptance from this unit.

The certificate changes CPU2 policy identity and runtime epoch. CPU1 remains
unchanged. Its positive/adversarial controls passed, and fresh source-bound
matrices are required for later source identities. Noise/refit/resource gates
and independent review remain mandatory; historical archives are not eligible
under a new source identity.

CIR09 WHEN replaying the corrected CPU2 native initialization, THE unit SHALL
retain and use the exact optimizer q path alongside the physical kg/m3 path;
round-trip division of the physical path SHALL NOT alter the Armijo certificate.
Gate: tests/numerics/test_gravity_l2.py::test_exact_q_trace_is_opt_in_and_physically_bound,
tests/numerics/test_gravity_irls_corrected.py::test_corrected_original_positive,
and the complete source-bound original24 matrix.
