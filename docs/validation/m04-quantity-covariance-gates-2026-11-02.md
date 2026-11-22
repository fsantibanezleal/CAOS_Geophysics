# M04 quantity Jacobian and full-covariance gates : 2026-11-02

## R-405: quantity-specific physical composition

`tests/numerics/test_magnetic_inverse.py::test_quantity_specific_physics_and_jacobian`
uses the actual SimPEG/Geoana component kernel on a one-cell mesh. An independent
direct Choclo prism calculation supplies the physical secondary ENU vectors.
The test separately checks secondary ENU, linear TMI, and exact total-field
anomaly predictions, then compares each q-space Jacobian with centered
finite differences of independently recomputed Choclo observations. Exact
anomaly truth is calculated from the total-field norm, not the linear TMI
projection. The assembler's positive-down background convention is also
covered by the regression documented in the
[field-sign validation](m04-positive-down-background-2026-11-02.md).

## R-406: full covariance whitening

`tests/numerics/test_magnetic_inverse.py::test_full_covariance_whitening`
uses a non-diagonal positive-definite 6×6 covariance and a non-contiguous
principal subset. It compares the production whitener's residual, precision
application, and weighted sensitivity norms with explicit Cholesky and linear
solves on the selected principal covariance. A diagonal-only substitute gives
a different residual result and fails the control. Existing assembly tests
also verify selection by the original scalar observation indices.

## Current regression evidence

The current focused M04 source selection passed **456 tests**, with zero
failures, errors, or skips. The external JUnit report is
`E:\_Datos\CAOS_Geophysics\validation\m04-current-regression-20261102.xml`,
SHA-256 `bd60efec5d55d647fabaca4d332bfb64448a32129de0b7c287eddbf30d64b8d2`.
Ruff, Python compilation, and `git diff --check` passed for the changed source
and tests.

The relevant current-source hashes are:

| File | SHA-256 |
|---|---|
| `data-pipeline/magnetic_fit_assembly.py` | `878053cc7f0e45f7d662a758481975dd548f5df57944062814b374e59c407866` |
| `data-pipeline/magnetic_quantity.py` | `3e5fefd8cf64e96b7904d659e113686a209fa7fbdd53c637dfc2e7c95957cf90` |
| `data-pipeline/magnetic_likelihood.py` | `579f95f491a9c93820cdb5c51604e5b443c18b99d5846b5bfc0e776840432119` |
| `data-pipeline/magnetic_forward.py` | `d42dac128182e2f5014800309cdfb39ce1eb9add4d498736bba306170e7a3c5e` |
| `tests/numerics/test_magnetic_inverse.py` | `73ba8e14493e2e8ee7393ba7cc66118ccb14dab7525482f42dc8ba5b8d1cb1d0` |

These controls validate physical objective foundations. The actual full inverse
module, accepted optimizer binding, nested fit, sealed evaluation, field
acceptance, and release gates remain open; passing R-405/R-406 composition
tests does not close R-407 or authorize calibration.
