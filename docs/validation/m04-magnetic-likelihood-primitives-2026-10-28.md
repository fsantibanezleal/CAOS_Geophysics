# M04 magnetic Gaussian likelihood primitives

This receipt covers the local likelihood algebra added to
`data-pipeline/magnetic_likelihood.py`. It is a component check, not magnetic
inverse, M04, field, upload, or release acceptance.

## Implemented behavior

- Diagonal standard-deviation weighting and full-covariance Cholesky whitening.
- Exact symmetry checks; full-matrix and selected principal-matrix positive
  definiteness and condition-number checks; no covariance repair, nugget, or
  diagonal substitution.
- Increasing, unique original flattened row selections, preserving the
  receiver-major/component-minor mapping.
- Gaussian data misfit `phi_d = ||W(H(q)-d)||^2`, its gradient, complete
  Gauss-Newton Hessian action, and weighted sensitivity column norms.
- Quantity composition from a component Jacobian for secondary ENU, linear TMI,
  and exact total-field anomaly, including the magnitude Jacobian, null-model
  derivative, and ill-conditioned total-field rejection. A cross-check composes
  an independent Choclo prism component kernel and finite-differences the exact
  magnitude lane against new Choclo responses. Decimal80 controls retain signed
  tiny longitudinal anomalies without subtractive cancellation.
- Independent, read-only snapshots for retained observations and computed
  result arrays.

## Local evidence

Command:

```powershell
$env:PYTHONPATH='data-pipeline'
.\.venv-pipeline\Scripts\python.exe -m pytest tests/numerics/test_magnetic_likelihood.py tests/numerics/test_magnetic_quantity.py tests/numerics/test_magnetic_forward.py::test_m04_quantity_composition_against_independent_choclo_kernel_and_derivative -q
.\.venv-pipeline\Scripts\python.exe -m ruff check data-pipeline/magnetic_likelihood.py data-pipeline/magnetic_quantity.py tests/numerics/test_magnetic_likelihood.py tests/numerics/test_magnetic_quantity.py tests/numerics/test_magnetic_forward.py
.\.venv-pipeline\Scripts\python.exe -m py_compile data-pipeline/magnetic_likelihood.py
.\.venv-pipeline\Scripts\python.exe -m py_compile data-pipeline/magnetic_quantity.py
git diff --check
```

Result: **28 passed** across the two component suites and the independent
Choclo-backed integration control. Ruff, byte compilation and whitespace
validation passed.
Controls compare the full-covariance quadratic, gradient and Gauss-Newton
action with direct small-matrix solutions, check directional finite
differences for both the likelihood and exact-magnitude Jacobian, compare the
quantity composition with a Choclo-generated component kernel, test principal
covariance selection and quantity-specific responses, reject asymmetric,
indefinite, ill-conditioned and malformed inputs, verify that covariance
dimension caps run before element scans, and check tiny anomaly values against
Decimal80 square roots.

The optimizer binding remains unaccepted. These modules do not generate or
independently verify the supplied SimPEG kernel, choose or seal survey
partitions, apply regularization, solve an inverse, or enable application/host
execution.
The approved M04 source-binding, native-resource, held-out, field, user-data,
UI/course and VPS gates remain separate and open.
