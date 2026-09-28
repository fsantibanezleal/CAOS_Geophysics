# Numerical scripts

Plain path-invoked modules, not an installable package. `rebuild.py` orchestrates `geology.py`, `potential.py`, `electromagnetics.py`, `seismic.py`, `joint.py`, and `learning.py`. `ingest.py` validates and preprocesses external observations or runs user CSV inversion. See the root README for invocation and `docs/problem-types/problem-types.md` for exact algorithms.

`velocity_validation.py` is an independent local M12 experiment for learned first-arrival velocity tomography. It never enters `rebuild.py` or canonical derived artifacts. Run `scripts/run_m12_velocity.ps1` or `scripts/run_m12_velocity.sh` and inspect the [M12 method record](../docs/problem-types/04_learned-velocity-validation.md). Its experimental checkpoint is not a public web or field-inversion result.
