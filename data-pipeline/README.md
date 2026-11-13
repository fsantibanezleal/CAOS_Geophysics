# Numerical scripts

Plain path-invoked modules, not an installable package. `rebuild.py` orchestrates `geology.py`, `potential.py`, `electromagnetics.py`, `seismic.py`, `joint.py`, and `learning.py`. `ingest.py` validates and preprocesses external observations or runs user CSV inversion. See the root README for invocation and `docs/problem-types/problem-types.md` for exact algorithms.

`velocity_validation.py` is an independent local M12 experiment for learned first-arrival velocity tomography. It never enters `rebuild.py` or canonical derived artifacts. Run `scripts/run_m12_velocity.ps1` or `scripts/run_m12_velocity.sh` and inspect the [M12 method record](../docs/problem-types/04_learned-velocity-validation.md). Its experimental checkpoint is not a public web or field-inversion result.

`magnetic_processing.py` performs explicit-map M03 airborne line geometry, height QC, crossover diagnostics, blocked-line interpolation scoring and supported gridding without applying unverified corrections. `magnetic_continuation.py` optionally upward-continues a fully supported regular-grid ROI with the Fourier harmonic transfer function; it rejects missing support and records the parent-result digest and FFT seam diagnostics. The transform has analytic synthetic controls, not provider-data acceptance. See the [M03 method record](../docs/wiki/methods/m01-m06.md#m03-airborne-magnetic-line-qc-and-supported-gridding) and [requirements/validation](../docs/design/features/m03-flightline-processing/requirements.md).

`magnetic_final_refit.py` consumes a completed, hash-bound M04 candidate matrix,
verifies every beta/fold receipt and recomputes the pooled validation selection,
then refits only the frozen final-development rows. It writes a write-once model
freeze outside Git before any sealed outer evaluation. A failed fit is retained
as a failed receipt; the command does not relax numerical/resource limits or
claim field validation, method acceptance, or online admission.

```powershell
.venv-pipeline\Scripts\python.exe data-pipeline\magnetic_processing.py --input request.json --output m03-lines.json
.venv-pipeline\Scripts\python.exe data-pipeline\magnetic_continuation.py --input m03-lines.json --output m03-upward-500m.json --height-m 500 --roi 20 180 30 210
.venv-pipeline\Scripts\python.exe -m pytest tests\numerics\test_magnetic_processing.py tests\numerics\test_magnetic_continuation.py -q
```

M04 final-refit reproduction (the selected candidate id is encoded in the
write-once output filename):

```powershell
$request = (Resolve-Path 'tests\fixtures\magnetic_survey\generated\requests\S2-A-linear_tmi_nT.json').Path
$matrix = "$env:GEOPHYSICS_LOCAL_DATA_ROOT\research-runs\<run-id>\m04-candidate-matrix"
.venv-pipeline\Scripts\python.exe scripts\run_m04_final_refit.py `
  --request $request `
  --matrix-dir $matrix `
  --output "$matrix\final-refit-<selected-id>.json"
.venv-pipeline\Scripts\python.exe scripts\verify_m04_final_refit.py `
  --request $request --matrix-dir $matrix `
  --receipt "$matrix\final-refit-<selected-id>.json"
```

Only after that verifier passes, the sealed evaluator consumes exactly one
outer evaluation token for the matrix file hash. It replays the frozen model on
the original usable rows, scores the development and outer partitions with
their declared Gaussian likelihoods, and writes immutable intent/result
receipts outside Git. A failed or interrupted attempt is not retried under the
same matrix hash. The verifier checks source, freeze, partition, row-order and
receipt identities without recomputing predictions or scores.

```powershell
$freeze = "$matrix\final-refit-<selected-id>.json"
$matrixHash = (Get-FileHash "$matrix\matrix.json" -Algorithm SHA256).Hash.ToLowerInvariant()
$result = "$env:GEOPHYSICS_LOCAL_DATA_ROOT\research-runs\m04-outer-evaluations\$matrixHash.json"
.venv-pipeline\Scripts\python.exe scripts\run_m04_outer_evaluation.py `
  --request $request --matrix-dir $matrix --freeze $freeze
.venv-pipeline\Scripts\python.exe scripts\verify_m04_outer_evaluation.py `
  --request $request --matrix-dir $matrix --freeze $freeze --result $result
```

This S2-A synthetic outer score does not establish field-source provenance,
known geology, method acceptance, or online admission.
