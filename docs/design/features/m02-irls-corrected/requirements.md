# Safeguarded scaled IRLS correction requirements

Status: prospective implementation approved after full mathematical/native
pre-code review,2026-10-08;18 partition controls PASS, full workflow/matrix gates
below remain NOT RUN. Old cpu1/plain
positive remains a genuine failure and is not rewritten. [Design](design.md),
[tasks](tasks.md), [historical cause](../m02-survey-l2/irls-positive-cause.md).

CIR01 THE corrected policy SHALL preserve the original geometry, physical
objective, scientific weights/norms/beta, epsilon log17/floor17,21stages/20updates,
all21 actual inner convergence and original last-three model/weight1e-6 gates.
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
