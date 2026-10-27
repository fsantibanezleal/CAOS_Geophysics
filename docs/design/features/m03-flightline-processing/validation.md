# M03 mapped flight-line processing validation

Run on the local pinned pipeline environment (NumPy 2.2.6, SciPy 1.15.2):

```powershell
.venv-pipeline\Scripts\python.exe -m pytest tests\numerics\test_magnetic_processing.py -q
.venv-pipeline\Scripts\python.exe -m ruff check data-pipeline\magnetic_processing.py tests\numerics\test_magnetic_processing.py
```

Observed during implementation: the initial random whole-line holdout selected an exterior line, giving zero convex-hull support. The failing control exposed the defect. The split was changed to select a seeded contiguous interior block along the measured flight-line-normal coordinate. The focused line-processing suite passes 14 tests; the new upward-continuation suite passes 11 tests. Line controls construct crossing flight/tie lines on an analytic plane, recover a deliberately injected 7 nT tie offset from independent segment interpolation, reject duplicate per-line sample-order keys and excessive segment-pair work, and exclude parallel/collinear segment pairs. Continuation controls recover the affine plane, match the analytic Fourier attenuation of a single mode, preserve grid coordinates/units and parent-result digest, reject unsupported/nonuniform grids, and refuse output overwrite. These are authored algorithm controls, not field evidence.

The SDD-declared `tests/numerics/test_magnetic_processing.py::test_blocked_line_holdout` symbol is present. The optional `data-pipeline/magnetic_continuation.py` utility now passes analytic affine-plane preservation and single-Fourier-mode attenuation checks, rejects incomplete support and nonuniform axes, binds outputs to the parent M03 artifact digest, and refuses overwrite. Reproduce with `.venv-pipeline\Scripts\python.exe -m pytest tests\numerics\test_magnetic_processing.py tests\numerics\test_magnetic_continuation.py -q` and Ruff on both implementation and test files. These controls verify the spectral operator only; they are not measured survey evidence.

This structural and numerical evidence does not confer M03 scientific acceptance. M03 remains unaccepted because Charleston provider assets and source-specific processing comparison, tie-line/diurnal/IGRF state, measured-data continuation, integrated project/worker/view flows, and live browser/host gates remain incomplete. Continuation additionally assumes a caller-selected complete uniform ROI and a periodic FFT extension; the returned seam diagnostic is review evidence, not an automatic quality pass.

## Authenticated project intake: 2026-10-27

`POST /api/projects/{project_id}/datasets` now admits an owned `magnetic_csv`
only with an explicit seven-column M03 map, source citation, processing state,
measured quantity, sensor-height reference, declared nT units and projected
metric CRS. Admission scans the CSV header and bounded row count without
retaining its observations in the API process, rechecks the raw SHA-256, and
stores a canonical source-bound dataset receipt. `GET .../methods` rechecks the
owned source, rights attestation and physical metadata and reports the M03
method as `pending_host_admission`; it does not claim that numerical processing
has run. Intake and existing dataset API tests pass.

## Authenticated worker, result and export: 2026-10-27

The worker launches `app.magnetic_compute` with the immutable dataset, original
file, job identity and admitted resource limits. The child re-hashes the source,
uses the same `data-pipeline/magnetic_processing.py` implementation as the local
pipeline, writes a canonical result without overwrite, and adds exact job/source
identity. Parent validation checks the result contract and executing engine
SHA-256 before commit. Result export has its own bounded uncompressed ZIP
contract with units, source citation, rights, attribution and hashes; original
bytes are never included.

`test_admitted_local_m03_worker_creates_provenance_bound_result_and_export`
executes the real API worker and child on an authored planar control, reads the
stored result and round-trips the bundle. Held-out interpolation RMSE is below
`1e-8` nT. Focused API and numerical tests pass, alongside Ruff and diff checks.
The online flag remains off in normal settings until actual ML VPS timing,
memory, scratch and cancellation measurements are reviewed. Authored controls
do not establish field validity: Charleston provider files, source-specific
holdout, browser parity and the M03 scientific acceptance gate remain open.
