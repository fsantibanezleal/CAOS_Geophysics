# M03 mapped flight-line processing validation

Run on the local pinned pipeline environment (NumPy 2.2.6, SciPy 1.15.2):

```powershell
.venv-pipeline\Scripts\python.exe -m pytest tests\numerics\test_magnetic_processing.py -q
.venv-pipeline\Scripts\python.exe -m ruff check data-pipeline\magnetic_processing.py tests\numerics\test_magnetic_processing.py
```

Observed during implementation: the initial random whole-line holdout selected an exterior line, giving zero convex-hull support. The failing control exposed the defect. The split was changed to select a seeded contiguous interior block along the measured flight-line-normal coordinate. The focused line-processing suite passes 14 tests; the new upward-continuation suite passes 11 tests. Line controls construct crossing flight/tie lines on an analytic plane, recover a deliberately injected 7 nT tie offset from independent segment interpolation, reject duplicate per-line sample-order keys and excessive segment-pair work, and exclude parallel/collinear segment pairs. Continuation controls recover the affine plane, match the analytic Fourier attenuation of a single mode, preserve grid coordinates/units and parent-result digest, reject unsupported/nonuniform grids, and refuse output overwrite. These are authored algorithm controls, not field evidence.

The SDD-declared `tests/numerics/test_magnetic_processing.py::test_blocked_line_holdout` symbol is present. The optional `data-pipeline/magnetic_continuation.py` utility now passes analytic affine-plane preservation and single-Fourier-mode attenuation checks, rejects incomplete support and nonuniform axes, binds outputs to the parent M03 artifact digest, and refuses overwrite. Reproduce with `.venv-pipeline\Scripts\python.exe -m pytest tests\numerics\test_magnetic_processing.py tests\numerics\test_magnetic_continuation.py -q` and Ruff on both implementation and test files. These controls verify the spectral operator only; they are not measured survey evidence.

This structural and numerical evidence does not confer M03 scientific acceptance. M03 remains unaccepted because Charleston provider assets and source-specific processing comparison, tie-line/diurnal/IGRF state, measured-data continuation, integrated project/worker/view flows, and live browser/host gates remain incomplete. Continuation additionally assumes a caller-selected complete uniform ROI and a periodic FFT extension; the returned seam diagnostic is review evidence, not an automatic quality pass.
