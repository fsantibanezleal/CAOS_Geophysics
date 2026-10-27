# Numerical scripts

Plain path-invoked modules, not an installable package. `rebuild.py` orchestrates `geology.py`, `potential.py`, `electromagnetics.py`, `seismic.py`, `joint.py`, and `learning.py`. `ingest.py` validates and preprocesses external observations or runs user CSV inversion. See the root README for invocation and `docs/problem-types/problem-types.md` for exact algorithms.

`velocity_validation.py` is an independent local M12 experiment for learned first-arrival velocity tomography. It never enters `rebuild.py` or canonical derived artifacts. Run `scripts/run_m12_velocity.ps1` or `scripts/run_m12_velocity.sh` and inspect the [M12 method record](../docs/problem-types/04_learned-velocity-validation.md). Its experimental checkpoint is not a public web or field-inversion result.

`magnetic_processing.py` performs explicit-map M03 airborne line geometry, height QC, crossover diagnostics, blocked-line interpolation scoring and supported gridding without applying unverified corrections. `magnetic_continuation.py` optionally upward-continues a fully supported regular-grid ROI with the Fourier harmonic transfer function; it rejects missing support and records the parent-result digest and FFT seam diagnostics. The transform has analytic synthetic controls, not provider-data acceptance. See the [M03 method record](../docs/wiki/methods/m01-m06.md#m03-airborne-magnetic-line-qc-and-supported-gridding) and [requirements/validation](../docs/design/features/m03-flightline-processing/requirements.md).

```powershell
.venv-pipeline\Scripts\python.exe data-pipeline\magnetic_processing.py --input request.json --output m03-lines.json
.venv-pipeline\Scripts\python.exe data-pipeline\magnetic_continuation.py --input m03-lines.json --output m03-upward-500m.json --height-m 500 --roi 20 180 30 210
.venv-pipeline\Scripts\python.exe -m pytest tests\numerics\test_magnetic_processing.py tests\numerics\test_magnetic_continuation.py -q
```
