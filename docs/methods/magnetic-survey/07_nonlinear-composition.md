# Exact total-field composition and retained proof failures

The single-property SI adapter uses the public nonlinear physical optimizer,
not its private classes, a copied CG or a SciPy production replacement. The
reviewed seam is native projected GNCG, epoch
`physical-gncg-nonlinear-candidate-2`, policy
`exact-bound-native-gncg-actual-armijo-1`. Source binding remains explicit; this
is local candidate execution, not an accepted source registry or online admission.

For q=chi/.01, H=norm(B0+A_b q)-F retains the actual rounded B0/F baseline.
The exact derivative uses u=(B0+b)/T, J=u dot A_b. Full principal covariance is
whitened by triangular solves, without a nugget or diagonal substitution. The
refreshed PSD search Hessian is 2 J.T W.T W J plus the fixed vendor regularizer.
The separate exact Hessian adds

\[
2\sum_i (W^TWr)_i A_{b,i}^T(I-u_i u_i^T)A_{b,i}/T_i.
\]

This curvature can be indefinite. It is an independent derivative-audit
operator, never passed as the GN search matrix. The positive initial GN diagonal
is fixed for one native fit, as required by the reviewed public policy; that
does not freeze the GN Jacobian. No floor, jitter or changed preconditioning.
Inactive gravity and coupling operands are exactly zero in the five-term
physical engine decomposition. Susceptibility is explicitly SI, scale(.01,).

The public nonlinear trace's `phi_m` is the already beta-weighted penalty
subtotal; its `beta_engine` is one. M04's lossless history instead stores beta
and the unweighted physical regularizer separately. For every saved native
model, `recorded_objective_terms` evaluates that same fixed vendor regularizer
and requires exact equality with the recorded weighted operand. It retains the
actual engine F and requires `F == phi_d + beta*phi_regularizer`, without
dividing by beta, rounding a repair, or relaxing equality. This applies to both
L2 and fixed IRLS surrogate records. True-p1 records retain their separate
unweighted true objective. A mismatching trace fails rather than exporting a
false converged history.

Native accepted steps satisfy actual projected Armijo, not exact-real interval
acceptance. M04 therefore separately audits every recorded accepted chord with
its original directed34/50/80 native-norm certificate. Any unresolved/rejected
proof makes the magnetic fit fail while preserving the actual native trace and
proof cause. It is not retried through another solver or relabelled quadratic.
The original per-fit120s/200-step and independent1e-7 projected-gradient gates
remain. Native1e-5 success alone cannot waive M04's stricter gate. Sparse still
requires every positive epsilon and true fixed-objective stationarity.

## Espanol

La composicion usa el optimizador no lineal publico y la unidad SI explicita.
No copia CG ni usa helpers privados. La curvatura GN semidefinida positiva se
actualiza con la direccion total, mientras la diagonal positiva inicial queda
fija durante el ajuste segun el contrato revisado. El Hessiano exacto separado
incluye curvatura de norma y puede ser indefinido; no sustituye la matriz GN.

Cada desplazamiento nativo realmente aceptado se audita con el certificado
original de norma34/50/80 digitos. Un resultado ambiguo/rechazado conserva la
traza y produce fallo, no aprobacion. Se mantienen limites120s/200 pasos y KKT
independiente1e-7, todos los epsilons IRLS y ausencia de pisos, nugget o reintento.
Exito nativo no establece geologia, datos de campo ni admision en linea.

La traza publica no lineal ya incluye beta en `phi_m`. El historial M04 guarda
beta y regularizador fisico sin ponderar por separado. En cada modelo nativo
guardado se evalua el mismo regularizador vendor fijo y se exige igualdad
exacta del operando ponderado y de `F == phi_d + beta*phi_regularizer`. No se
divide por beta, no se repara el redondeo y no se debilita ninguna tolerancia.
L2 y sustitutos IRLS usan esta regla; p1 real conserva su objetivo distinto.

Definitions: [native norm proof](04_native-norm-certificate.md),
[full workflow](06_local-calibration.md), and actual
[SimPEG magnetic source](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/potential_fields/magnetics/simulation.py).
