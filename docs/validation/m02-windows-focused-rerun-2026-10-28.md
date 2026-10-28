# M02 locked gravity controls on Windows

The previously reported Windows failures were rechecked on 2026-10-28 using
the repository's reviewed single-thread native environment. Four locked controls
passed: condition/family pairs `(0,0)`, `(0,1)`, `(1,0)`, and `(1,1)`.

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:NUMEXPR_NUM_THREADS='1'
$env:PYTHONDONTWRITEBYTECODE='1'
.venv-pipeline\Scripts\python.exe -m pytest -q `
  tests/numerics/test_gravity_l2_selection.py::test_complete_locked_l2_control_matrix `
  -k '0-0 or 0-1 or 1-0 or 1-1'
```

Result: **4 passed, 0 failed, 0 skipped** on Windows, CPython 3.12.10,
`.venv-pipeline`. The controls exercised the existing frozen beta candidates,
three geometry-only folds, final refit/evaluation where eligible, and the
independent prism oracle in the authored test.

An earlier direct invocation omitted the required one-thread variables. The
optimizer's workspace guard rejected it before optimization; the API recorded
those as `engine_error`, which is not a solver convergence result. This is a
harness invocation error, not evidence for relaxing the solver's stopping
policy. The full 24-control Windows matrix was not rerun. The existing pinned
Linux full-matrix receipt remains separate evidence; overall M02 and M01-M13
product acceptance remain open.
