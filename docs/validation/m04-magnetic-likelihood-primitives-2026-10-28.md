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
- Independent, read-only snapshots for retained observations and computed
  result arrays.

## Local evidence

Command:

```powershell
$env:PYTHONPATH='data-pipeline'
.\.venv-pipeline\Scripts\python.exe -m pytest tests/numerics/test_magnetic_likelihood.py -q
.\.venv-pipeline\Scripts\python.exe -m ruff check data-pipeline/magnetic_likelihood.py tests/numerics/test_magnetic_likelihood.py
.\.venv-pipeline\Scripts\python.exe -m py_compile data-pipeline/magnetic_likelihood.py
git diff --check
```

Result: **12 passed**. Ruff, byte compilation and whitespace validation passed.
Controls compare the full-covariance quadratic, gradient and Gauss-Newton
action with direct small-matrix solutions, check a directional finite
difference, test principal covariance selection, and reject asymmetric,
indefinite, ill-conditioned and malformed inputs.

The optimizer binding remains unaccepted. This module does not call SimPEG,
choose or seal survey partitions, construct magnetic quantities/Jacobians,
apply regularization, solve an inverse, or enable application/host execution.
The approved M04 source-binding, native-resource, held-out, field, user-data,
UI/course and VPS gates remain separate and open.
