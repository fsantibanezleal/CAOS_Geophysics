# Physical survey objective / Objetivo físico del levantamiento

[Input and geometry](README.md) and [independent acquisition](02_acquisition-controls.md)
precede this chapter. The tiny executable controls in
`tests/numerics/test_magnetic_survey_objective.py` check the actual physical
kernel, likelihood and regularization. They do not fit a survey, certify an
optimizer, select beta or demonstrate a completed L2/IRLS method. Full inverse
definitions and acceptance gates remain in the
[continuation algorithms](../../design/features/m04-survey-inversion/algorithms.md)
and [validation matrix](../../design/features/m04-survey-inversion/validation.md).

## English: physical parameters and measurement order

Physical susceptibility chi is dimensionless SI, constrained by the supplied
production bounds to<=.1. The optimizer coordinate q=chi/.01 is a fixed
dimensionless scaling, not a different susceptibility unit. Actual public
SimPEG0.25.2 `Simulation3DIntegral` uses scalar induced magnetization,
Geoana0.8.1 RAM float64, `IdentityMap`, the supplied active mask and original
receiver-major ENU component order. Gchi has nT/SI columns. Jq=.01Gchi.
Linear TMI projects each receiver's three components on the declared field
direction f=(cos I sin D,cos I cos D,-sin I), with positive-down inclination
and clockwise-from-north declination. It is not secondary amplitude or exact
norm-minus-F. No remanence or field direction is silently estimated.

The independent Choclo0.3.2 mathematical unit-chi=1 column oracle uses
magnetization M=B0(T)/mu0 in A/m. This derivative definition does not submit
chi=1 to production. Component functions are independent of the candidate
Geoana kernel, though Choclo's three callables share its own low-level kernels.
The test-only public `LinearSimulation` composes retained physical Jq; it is
not replacement prism physics or an alternate production optimizer.

Residual r=H(q)-d in nT is the fitting sign. Exported signed residual d-H has
the opposite sign. For declared SD sigma, W=diag(1/sigma). For an explicitly
supplied SPD covariance C in nT^2, obtain the principal covariance for each
selected receiver/component set, factor C=LL.T, and apply W=L^-1 by triangular
solves. Never form the inverse. Subsetting a full-survey whitening matrix is
not refactoring a principal covariance. Off-diagonal correlations remain part
of sensitivity and likelihood; correlated partitions are not independent data.

The unhalved dimensionless data objective, gradient and linear Hessian are
phi_d=r.T C^-1 r=||Wr||^2, g_d=2Jq.T W.T Wr and H_d v=2Jq.T W.T W Jq v.
Whitened RMS uses component count D, not receiver count N. The binding diagonal
uses the full column norms of WJq, not a diagonal covariance approximation.

## Pinned vendor covariance limitation

Actual versioned
[SimPEG0.25.2 data_misfit.py](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/data_misfit.py)
uses W.T W for the `L2DataMisfit` gradient, but W W in `deriv2`. With a
triangular Cholesky whitening operator these differ. Diagonal-SD Hessian
controls agree; correlated controls expose the discrepancy. This does not
justify changing the covariance, tolerance or environment.

The required action is explicitly composed using public Jvec/Jtvec and
W.T(W(Jvec(v))), plus beta times actual regularization.deriv2. No vendor patch
or copied optimizer is used. A SciPy `LinearOperator` applies triangular
solves for forward and transpose actions. A dense NumPy whitening array would
also be inappropriate here because the pinned misfit uses `*`, which would
be elementwise for that array. The discrepancy regression remains separate
from verification of the correct public action.

## Nonuniform active-face physical regularization

Let delta=q-q_ref, v_i active cell volumes and V=sum(v_i) in m^3. Actual
`WeightedLeastSquares` uses nonzero explicit q_ref with
`reference_model_in_smooth=True`, alpha_s=1, alpha_j=ell_j^2, second-order
alphas0 and a constant cell weight1/V. The metre lengths ell_j are not vendor
`length_scale_*` multipliers. The dimensionless regularizer is

phi_m=sum_i(v_i/V delta_i^2)
+sum_j ell_j^2 sum_faces[(v_left+v_right)/(2V) (D_j delta)^2].

Only interior faces with both neighbors active participate. Independent
center distances give D_j delta=(delta_right-delta_left)/((h_left+h_right)/2).
There is no derivative across an inactive hole or exterior boundary. Explicit
row matching compares actual RegularizationMesh gradient/averaging operators
with this independent topology, rather than assuming vendor face ordering.
The complete objective is phi_d+beta phi_m; beta is dimensionless for THIS
whitening/q/volume/length convention, not portable from gravity or unscaled chi.

One worked authored control has12 nonuniform cells,7 active cells,30 exterior
receivers and90 ENU components. Active volumes are
[72000,126000,120000,210000,132000,231000,693000]m^3; the interior face counts
are[3,2,2] for E,N,U. Field F50000nT,I37,D-73 and lengths[400,1200,600]m
are explicitly authored, not field metadata. The test's q and q_ref are fixed
before any response; the observations are separate Choclo responses plus a
declared deterministic .07sin(i)nT perturbation, not an estimated uncertainty.

| Fixed-q evaluation, not a fitted result | Approximate value |
| --- | --- |
| phi_d with SD.5nT | 2.926162606371031 |
| phi_d with declared correlated covariance | 2.044459195546168 |
| phi_m | 91.05322070977151 |
| total with covariance and beta.3 | 29.36042540847762 |

The two likelihoods differ because they declare different noise models; neither
is an inferred error model. Full-covariance sigma_i=.5+.002i nT and correlation
.22^abs(i-j) are a tiny well-conditioned control only. Geometry-fixed principal
subsets exercise independent refactoring, not held-out fit success.

## Sparse weights are not completed IRLS

Actual `Sparse` uses norms[1,2,2,2], `gradient_type="components"`,
`irls_scaled=False`, the same volumes/lengths/reference and all eight frozen
epsilon_q values[.1,.05,.025,.0125,.00625,.003125,.0015625,.001]. Smoothness
threshold epsilon_j=epsilon_q/ell_j has units m^-1; p=2 gives weight1.
At each tested model `update_weights` supplies smallness weights
1/sqrt(delta_i^2+epsilon_q^2). Null delta has finite positive1/epsilon_q.

The true smallness is2 sum_i(v_i/V [sqrt(delta_i^2+epsilon_q^2)-epsilon_q]);
evaluate the bracket as delta_i^2/(sqrt(delta_i^2+epsilon_q^2)+epsilon_q)
to retain tiny positives. Independent stdlib Decimal80, from_float on each
operand, verifies direct square-root subtraction without Windows longdouble.
Refreshed surrogate and true gradients agree. Raw surrogate value and Hessian
are not the true sparse value and Hessian; those distinctions are tested.
These controls perform no reweight-and-solve or epsilon advancement. Actual
fixed-epsilon descent, accepted inner solve, final stationarity, sealed
selection/refit, negative discrimination and local user-data export remain
required. A positive weights/algebra result cannot replace any of those gates.

## Español: unidades, covarianza y regularización

La susceptibilidad física chi está en SI, con límites suministrados<=.1.
q=chi/.01 es una escala fija adimensional; no cambia la unidad física.
Gchi del operador real SimPEG/Geoana está en nT/SI y Jq=.01Gchi, con orden
receptor-componente E,N,U. El oráculo Choclo chi=1 define una columna
matemática con M=B0(T)/mu0; no es entrada de producción. TMI lineal proyecta
sobre f declarado y no equivale a amplitud secundaria ni norma total menos F.
No se estima remanencia, dirección del campo, datum o incertidumbre faltante.

El residuo del ajuste es H-d; el exportado es d-H. Para covarianza SPD declarada
en nT^2, cada selección usa su propia submatriz principal y Cholesky C=LL.T.
W=L^-1 se aplica por resolución triangular, sin invertir C ni L. Recortar
una matriz de blanqueo del levantamiento completo no produce el blanqueo de
la covarianza principal. Se conservan las correlaciones; no se afirma
independencia entre particiones correlacionadas.

phi_d=||Wr||^2 no lleva factor1/2; g=2Jq.T W.T Wr y la acción Hessiana es
2Jq.T W.T W Jq v. El código real SimPEG0.25.2 `L2DataMisfit.deriv2` usa W W:
vale para W diagonal, no para este Cholesky triangular. La composición pública
correcta usa Jvec/Jtvec, W y W.T; no modifica el proveedor ni aproxima C por
su diagonal. Los controles conservan explícitamente esa discrepancia.
`LinearOperator` evita tanto la inversión como el `*` elemento a elemento
que tendría una matriz NumPy densa en este código del proveedor.

La penalización real `WeightedLeastSquares` usa referencia no nula también
en suavidad, volúmenes activos normalizados por V total y longitudes físicas
[400,1200,600]m mediante alpha_j=ell_j^2. Solo usa caras interiores entre
dos celdas activas, diferencias divididas por distancia entre centros y volumen
promedio de los dos vecinos. No conecta huecos inactivos ni fronteras exteriores.
La tabla anterior evalúa un q fijo: no presenta una inversión ni geología.
Las dos covarianzas, alturas y perturbaciones son controles escritos explícitos.

`Sparse` usa p=[1,2,2,2], componentes y pesos sin escalamiento IRLS oculto.
Los ocho epsilon positivos pertenecen a q; los de suavidad son epsilon_q/ell_j.
Se comprueban pesos, gradientes refrescados y distinción entre valor/Hessiana
de sustituto cuadrático y objetivo verdadero. Decimal80 verifica términos
positivos diminutos, sin piso absoluto ni longdouble de Windows. No se ejecutan
iteraciones inversas, certificados de convergencia o selección sellada.
Persisten obligatorios L2/IRLS completos, datos de usuario, negativos físicos,
campo real, resolución, durabilidad, límites de recursos y vistas vinculadas.

## Actual primary definitions / Definiciones primarias

[Magnetic simulation](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/potential_fields/magnetics/simulation.py),
[regularization](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/regularization/base.py),
[active regularization mesh](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/regularization/regularization_mesh.py),
[Sparse](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/regularization/sparse.py)
and [Choclo components](https://raw.githubusercontent.com/fatiando/choclo/v0.3.2/choclo/prism/_magnetic.py)
define the real versioned operators. Source-linked definitions and tiny tests
do not establish a scientific target, field license, native admission or release.
