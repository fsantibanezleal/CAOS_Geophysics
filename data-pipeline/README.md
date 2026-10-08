# Numerical scripts

Plain path-invoked modules, not an installable package. `rebuild.py` orchestrates `geology.py`, `potential.py`, `electromagnetics.py`, `seismic.py`, `joint.py`, and `learning.py`. `ingest.py` validates and preprocesses external observations or runs user CSV inversion. See the root README for invocation and `docs/problem-types/problem-types.md` for exact algorithms.

`run_magnetic_survey.py` supplies actual local M04 linear L2/IRLS calibration,
sealed evaluation and bounded fitted-generation import/export. Read the
[deep EN/ES method and tools](../docs/methods/magnetic-survey/06_local-calibration.md)
before execution. Explicit external data/scratch roots and a reviewed
local-candidate source receipt are mandatory; no repository raw/model/temp defaults,
accepted nonlinear core, field acceptance, API activation or deployment is implied.

`velocity_validation.py` is an independent local M12 experiment for learned first-arrival velocity tomography. It never enters `rebuild.py` or canonical derived artifacts. Run `scripts/run_m12_velocity.ps1` or `scripts/run_m12_velocity.sh` and inspect the [M12 method record](../docs/problem-types/04_learned-velocity-validation.md). Its experimental checkpoint is not a public web or field-inversion result.
