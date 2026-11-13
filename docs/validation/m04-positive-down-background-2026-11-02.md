# M04 positive-down inducing-field background correction : 2026-11-02

## Finding and correction

The fit-fold assembler independently reconstructed the inducing-field vector
using a positive Up component for positive-down inclination. The ordinary
SimPEG forward operator validates and returns the background as
`F * (cos(I) sin(D), cos(I) cos(D), -sin(I))` in ENU. The former sign made the
exact-total-field objective use a different background than the physical
forward operator. The fit assembler now uses the engine-validated ENU vector
returned by the same forward call that supplies its component Jacobian.

The regression constructs a nonzero exact-total-anomaly fit objective on the
frozen M04 mesh, independently forms the expected ENU field direction from the
declared positive-down convention, and compares the assembled predictions with
the actual SimPEG forward operator at identical receivers and susceptibility.
The previous sign would fail this comparison.

## Current-source replay

The focused M04 regression selection passed **454 tests**, with zero failures,
errors, or skips. This includes the synthetic matrix and the existing magnetic
survey, forward, likelihood, quantity, regularization, objective, fold assembly,
and fold scoring tests. The JUnit report is stored outside the checkout at
`E:\_Datos\CAOS_Geophysics\validation\m04-current-regression-20261102.xml`;
SHA-256: `1f229288ced15b0a632a86ce3dc27f126edadb7c4a046ec5d4fdc49b7b08c1f0`.
BLAS/OpenMP/MKL/NumExpr pools were capped at one thread.

Ruff and Python compilation passed for the changed assembler and test. This
corrects the field convention in the fit-objective foundation; it does not
implement or accept an optimizer, complete M04 calibration, or authorize
field-data interpretation or deployment.
