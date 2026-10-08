# Independent gravity L2 metadata and bounded-solution review

Date: 2026-10-03. Reviewed candidate: [PR132](https://github.com/fsantibanezleal/CAOS_Geophysics/pull/132)
at `d7c66704edaeb46bc83dad4917f7cd41d12e09f1`. This document records MAIN's
actual local execution, not acceptance of the complete inverse or a field case.
The candidate is isolated and unmerged; this evidence does not promote its code.

## Source and test identities

MAIN read the complete320-line gravity_l2.py, the entire metadata/test delta
from8acab62, the complete277-line producer receipt and implementation ledger.
The previously reviewed seven-file specification and first planner/objective
evidence remain unchanged. Execution used a detached worktree at the exact
candidate and the existing read-only CPython3.12.10 pipeline interpreter, with
BLAS/OMP threads1, bytecode/cache disabled and a new private Numba cache.
No packages or original environments were changed.

| Candidate file | Measured SHA-256 |
| --- | --- |
| data-pipeline/gravity_l2.py | 8f60909da5abe9cbc1f5fd6159a9a262e402346af4cf57a2bc566e8915684561 |
| data-pipeline/gravity_survey_l2.py | 50934e1f56fcd468787b113598d01966b0a0eb1b124cb95363605fea8278da97 |

MAIN's replay of the four candidate files passed168 tests, zero skips/errors/
failures, in22.43 seconds (JUnit22.431). The JUnit SHA-256 is
`5ff79c2347fa1361268205aa1b0d3941c75a0360ca22382b4abfa391574c7623`.
The files are tests/data/test_gravity_survey_l2.py and tests/numerics/
test_gravity_l2.py, test_gravity_l2_selection.py and test_gravity_forward.py.
Shared conftest was disabled and the pipeline import path was supplied explicitly.
MAIN's first invocation omitted that path and produced three collection errors;
its private XML is retained with SHA-256
`ebd489b30c720606834ccfd26e4ceba89581ed16971a62601f988e28b34f96ad`.
That was a MAIN harness error, not a candidate numerical or dependency failure.

## Independently constructed descriptor-boundary controls

MAIN's separate helper uses original literals and independent compact JSON byte
counts, not the producer fixtures. Its SHA-256 is
`ce600ccab414319aad037c110d942ab84c7960b1350a7ff772752dc754fc8666`.
It passed12 checks: exact descriptor capacity and one byte below for four nested/
escaped-Unicode/primitive/array cases; the original491531-byte shared-container
counterexample rejects against262144; a120009-byte tuple containing40000 empty
containers passes without changing original scalar-count semantics;1536 logical
occurrences of a65536-byte array pass at96MiB, while1537 reject. Only one64KiB
physical array is allocated for the alias control. No whole-job RSS claim follows.

The original counterexample is fixed in this candidate. This narrow metadata
pass is separate from the optimizer failure below and from operational admission.

## New physical bounded-inversion oracle

MAIN authored independent_bounded_solve.py, SHA-256
`dc4a6da238d84d9fe65592cd818961ac57ddad6f78471ecdf1e16080d35de070`.
It constructs its own physical Choclo prism Jacobian, both-active pairwise
regularization and lower-triangular Cholesky whitening. scipy.optimize.lsq_linear
with BVLS solves the augmented mathematical control; production does not use
that oracle or substitute an independently supplied kernel.

Geometry is a nonuniform3x2x2 mesh with origin(-320,-140,-510)m, widths
x=(70,110,90), y=(80,140), z=(120,60)m and active x-fast cells(0,1,4,6,9,11).
Five receivers are(-100,50,140), (500,-450,80), (-450,300,-900),
(20,-200,350), (100,200,220)m. Signed truth is(250,-450,600,-800,300,1000)
kg/m3; independently fixed background is(.002,-.003,.001,.004,-.002)mGal.
Reference is(10,-15,25,-40,5,0)kg/m3, density scale750kg/m3, length scales
(60,110,75)m, reference-in-smooth true, zero initial density, candidate beta.01
and engine beta.05 for five observations. Both SD=.005mGal and covariance
.005^2(.65I+.35ones) are tested with symmetric bounds1500 and75kg/m3.

The comparison gates were frozen before execution: converged status, relative
unhalved objective discrepancy<=1e-6, normalized model discrepancy<=1e-3 and
maximum prediction discrepancy<=1e-6mGal. They were not weakened after failure.

| Noise | Bound kg/m3 | Actual status / reason | Model discrepancy | Objective discrepancy | Max prediction discrepancy mGal | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| Diagonal SD | 1500 | converged / absolute_stationary | 1.2821355927847284e-12 | 6.938893903907228e-18 | 4.1031360877680985e-15 | PASS |
| Diagonal SD | 75 | nonconverged / zero_free_direction | .2598076211353316 | .46671241352722936 | .005208941655261863 | FAIL |
| Full covariance | 1500 | converged / absolute_stationary | 1.372088410424635e-12 | 2.7755575615628914e-17 | 4.076006029669572e-15 | PASS |
| Full covariance | 75 | nonconverged / zero_free_direction | .25980762113533157 | .4669453075688587 | .005208941655261862 | FAIL |

All four stop after one accepted step. The two tight-bound cases retain
normalized KKT violations.47376436515266124 and.45382643801372047. BVLS
reports success in all four, with all six constraints active at each tight-bound
optimum. The aggregate assertion correctly exits1. MAIN retained the actual
private result record with SHA-256
`f118d046a6be3929d9432a921c728cc5a6295bd265cfc444dfecaf8e56f774da`.
The private helpers, XML and failed receipt remain local evidence; they are not
represented as public downloadable artifacts or native scientific job receipts.

## Diagnosed limitation and required next work

MAIN read the installed, source-pinned ProjectedGNCG.findSearchDirection.
When all coordinates are active, the free residual norm and CG step are zero.
The official inward active-gradient contribution is scaled by the maximum CG
step, also zero; merely removing the observer's zero-free stop does not provide
the missing feasible descent. The relative CG diagnostic also divides by the
zero initial free-residual norm. This is not evidence that every all-active
iterate satisfies the bound-constrained KKT conditions.

The candidate truthfully reports nonconvergence; it does not falsely return an
optimum. Nevertheless, this limitation blocks bounded-solver acceptance. A
reviewed explicit algorithm amendment, with independent optimum/KKT/failure
controls, is required before changing the approved official-search-only design.
No vendor monkeypatch, changed runtime/source pins, dense oracle fallback,
tolerance relaxation or removal of the tight-bound cases is authorized by this
review. All historical passes, failures and source identities remain preserved.

Full16-gate L2 acceptance, sealed beta selection, all24 case conditions, resource
measurements, submitted-field eligibility, public API/worker activation, IRLS,
GPU and deployment remain pending. Native accounting, durability, external
deletion authority and final product acceptance are separate requirements.
