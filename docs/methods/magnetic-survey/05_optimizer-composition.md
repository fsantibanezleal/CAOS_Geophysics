# Magnetic L2 and frozen sparse objective composition

The local magnetic objective uses actual SimPEG 0.25.2 regularizers and the
physical component matrix from Geoana. It is composed with a separately reviewed
bounded optimizer. This chapter describes that executable composition, not
acceptance of a whole field survey, hosted execution or geology.

## Coordinates, units and factors

Susceptibility is dimensionless SI. The numerical variable is
\(q=\chi/0.01\). The retained binary64 component matrix is
\(A_b=0.01G_\chi\), in nT per q. For a declared observation vector \(d\),
the unhalved objective is

\[
\Phi(q)=\|W(H(q)-d)\|^2+\beta\phi_m(q).
\]

Here \(H\) is secondary ENU, projected linear TMI, or the separately defined
total norm minus the retained inducing amplitude. The beta is dimensionless;
no station-count normalization or gravity-unit conversion enters this equation.
Bounds and the start/reference originate in supplied SI metadata.

For a full principal covariance \(C=LL^T\), whitening uses triangular solves
\(W=L^{-1}\). The action \(2J^TW^TWJv\) uses both transposes. It does not
use the pinned vendor misfit's \(W W\) Hessian shortcut. The gradient and GN
action are

\[
g=2J^TW^TW(H-d)+\beta\nabla\phi_m,\qquad
Kv=2J^TW^TWJv+\beta\nabla^2\phi_mv.
\]

The regularizer is actual `WeightedLeastSquares` with an identity map,
reference in all smooth terms, \(\alpha_s=1\),
\(\alpha_j=\ell_j^2\), and constant cell weight \(1/V\), where
\(V\) is total active volume. Active interior-face geometry, distances and
averaged volumes are vendor quantities checked against independent physical
stencils. No derivative bridges an inactive hole.

## Frozen surrogate and true sparse objective

Actual `Sparse` uses norms [1,2,2,2], components, and `irls_scaled=False`.
At an explicit weight model it computes
\(r_i=(\delta_i^2+\epsilon^2)^{-1/2}\), with
\(\delta=q-q_{ref}\). Positive epsilon follows the eight frozen thresholds
from 0.1 to 0.001. Smoothness thresholds are epsilon divided by each declared
physical length; p2 weights are exactly one. No automatic vendor beta schedule
or percentile initialization changes these policies.

The surrogate smallness is \(\sum_i(v_i/V)r_i\delta_i^2\).
The true smoothed p1 smallness is

\[
2\sum_i\frac{v_i}{V}
\frac{\delta_i^2}{\sqrt{\delta_i^2+\epsilon^2}+\epsilon}.
\]

Their gradients agree at the weight refresh point, but their values and
Hessians differ. `true_value_gradient` evaluates the true expression separately;
it never exports the surrogate as p1. The rationalized smallness retains tiny
positive terms and is checked against an independent Decimal80 direct root.
At delta zero the smallness is exactly zero and the weight is finite 1/epsilon.

## The public optimizer boundary

`MagneticObjective` supplies the seven-method trusted interface: identity,
value/gradient/Hessian, terms, full diagonal, free metric, directed certificate,
and cache release. The free metric stores native 1/diagonal and multiplies
on the explicit free face, matching the public core's literal arithmetic.
Direct division can differ by an ulp and is not interchangeable at that ABI.
The registered action is zero outside that face and has no diagonal floor.

The adapter verifies the current optimizer and magnetic certificate source
hashes. A hash records identity; it does not independently accept a source
inventory, native allocation profile or scientific method. The optimizer module
must be supplied by its reviewed dependency. No production BVLS, copied CG,
private gravity constructor, fallback solve or relaxed stop is used.

Linear secondary/vector and TMI objectives use the quadratic certificate domain.
Exact magnitude requires the separate native magnetic norm domain and a reviewed
nonlinear GN core. `solve_linear` explicitly rejects that unregistered lane.
The norm certificate alone cannot establish optimizer acceptance.

## Independent checks and limits

The adapter test uses a seven-active-cell nonuniform mesh with holes and thirty
exterior receivers. Choclo independently provides unit-SI magnetic columns,
pairwise geometry provides regularization stencils, and SciPy BVLS is TEST ONLY.
It checks both quantities, diagonal errors and full correlated covariance.
Model infinity discrepancy must be at most 1e-6 q, relative objective discrepancy
1e-8, prediction RMS discrepancy 1e-6 nT and independently projected gradient
1e-7 times the declared initial scale. All eight sparse thresholds are checked.
Those controls do not replace nested fitting, source rights, acquisition,
remanence/wrong-field discrimination, full profiles, export or hosted admission.

## Explicacion en espanol

La variable numerica es q=chi/0.01; chi se muestra en SI. El objetivo usa el
residuo fisico sin dividir por el numero de estaciones. Para covarianza completa,
se factoriza cada submatriz principal y se blanquea con soluciones triangulares.
El Hessiano usa W transpuesta por W, sin sustituir la covarianza por su diagonal.
La regularizacion real de SimPEG conserva los volumenes y las distancias fisicas,
la referencia en los terminos suaves y las longitudes declaradas.

Las ponderaciones dispersas se congelan en un modelo explicito, con ocho
umbrales positivos y beta fija. El valor del sustituto cuadratico no es el valor
del objetivo p1 suavizado. Ambos se calculan y se distinguen; un gradiente igual
en el refresco no establece igualdad de Hessianos ni convergencia de IRLS.
El solver publico conserva sus criterios originales. Las pruebas BVLS son
independientes y se usan solo en validacion. La magnitud total necesita un
certificador de norma y un motor GN no lineal revisado. Una prueba sintetica no
demuestra geologia de campo, ausencia de remanencia ni admision del servicio.

## Primary references

- [SimPEG 0.25.2 WeightedLeastSquares](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/regularization/base.py)
- [SimPEG 0.25.2 Sparse](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/regularization/sparse.py)
- [SimPEG 0.25.2 L2DataMisfit](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/data_misfit.py)
- [SciPy 1.15.2 bounded least squares](https://docs.scipy.org/doc/scipy-1.15.2/reference/generated/scipy.optimize.lsq_linear.html)
- [SimPEG framework paper](https://doi.org/10.1016/j.cageo.2015.09.015)
