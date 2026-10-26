# Separate objective-preserving direct QR prerequisite

Epoch `m03-augmented-direct-qr/1` does not alter frozen v1/v2/HP evidence or
their receipts. Original S1/opened100/50 predictive failures and HP candidate39
stop7/2000 with gradient1.0764842455268023e-8 remain failures.

Use A=diag(1/sigma)Gdiag(1/S), b=diag(1/sigma)y, Gij=1/distance_m,
S=original unweighted population STD without mean removal;
Pj=1/sqrt(sum_training Aij^2+lambda). Solve B=[A;sqrt(lambda)I]P against
d=[b;0] with SciPy1.15.2 low-level DGELS, then c=Pz, q=c/S. No intercept,
Gram solve, rank truncation, refinement, response/outer tuning or warm start.
Query lwork before dense allocation; owned writable Fortran float64 buffers,
trans=N, nrhs=1, overwrite requested with actual copy/alias accounting.

Require actual DGELS info0, finite c/q, independent direct original objective
and relative gradient<=1e-9 using the original denominator without a floor.
Extract R; DTRTRI on a separate upper-triangular buffer is diagnostic only.
Require actual inverse info0 and finite Frobenius(R)*Frobenius(inverse(R))<1e8.
Label this a conservative cond2(B) upper bound, never an A/recurrence estimate.
Retain actual native status, c/q/P/scales hashes and diagnostics on failure.

Receipt exactly schema, epoch, rows, sources, augmented_rows, damping,
preconditioner_sha256, column_scales_sha256, coefficients_sha256,
scaled_coefficients_sha256, lapack_info, triangular_inverse_info, lwork,
condition_domain, condition_upper_bound, triangular_diagonal_min_abs,
triangular_diagonal_max_abs, original_diagnostics, dense_capacity,
engine_identity, numerical_verdict. Native lifetime is separate, not invented
LSMR iterations. This does not yet amend SurveyResult.

## Prospective proof and fail-first gates

For r=n+m, queried integral positive L, extra peak reserve above existing HP
phase proof is8*(4*r*m+4*m*m+8*r+16*m+L)+33554432. Four augmented and four
triangular buffers conservatively include wrapper copies, plus RHS/vectors/
workspace/native slack. Shape/copy overflow refuses before allocation.
No97 simultaneous dense buffers. One additional97-row receipt table/index
adds2498560B and one logical/two physical members above HP closure.
Kernel work is6*n*m per fit plus existing prediction/verification, not4006
iterative passes. Additional factorization envelope U=8*(n+m)*m^2+8*m^3,
summed over exact96 inner shapes and conservative final (optional comparator
separate), ceiling10^12. Keep logical192/physical1m, chunk/page/root8/4/2MiB,
CPU21600s/wall43200s/RSS+commit4GiB/scratch32GiB/parent300s/one-child caps.
All16 maps and complete97/98 proof precede any values; no coarsening.

Gates: independently constructed weighted/unweighted G/S/A/P/B actions,
adjoint, objective, NumPy-SVD coefficients, original gradient; correlated
columns/zero target and invalid lambda/workspace/rank/copy/condition negatives;
independent R/inverse/cond2 diagnostic. Cold native controls enforce threads1
before imports and byte-pin installed wrappers/DLLs/source/runtime. Only then
one original249/127 candidate39,200m/depth500/lambda.0001/foldC, fresh value-free
seal and selective training-only decoding, sigma unopened. Independently
reconstruct P/S/gradient afterward. First failure stops dependents. Even PASS
does not run full97 or outer values: parent reads prerequisite before a new
full Result/export/replay epoch. Original8201 eligibility remains unverified.

Primary: [DGELS](https://docs.scipy.org/doc/scipy-1.15.2/reference/generated/scipy.linalg.lapack.dgels.html),
[DTRTRI](https://docs.scipy.org/doc/scipy-1.15.2/reference/generated/scipy.linalg.lapack.dtrtri.html),
[LAPACK least squares](https://www.netlib.org/lapack/lug/node27.html).
Full rank is an assumption, not an acceptance proof from the native name.

## Espanol

Se transforma tambien la regularizacion: penalizar z en vez de Pz cambiaria
el objetivo. QR es una epoca distinta, no una repeticion HP ni un nuevo pase
historico. La prueba independiente del gradiente original y del limite
conservador cond2(B) sigue obligatoria. Solo se abren las249 posiciones de
entrenamiento declaradas despues del sello nuevo; no hay validacion externa
ni matriz completa hasta que el prerequisito real pase y sea revisado.
