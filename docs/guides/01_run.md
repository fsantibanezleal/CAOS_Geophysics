# Local reproduction

Run `scripts/setup.ps1 -Gpu` (Windows) or `scripts/setup.sh --gpu` (Linux). Python 3.12 and NVIDIA-compatible CUDA wheels are required for the GPU validation. `.venv` and `.venv-pipeline` are ignored. No editable package installation is used.

Run `scripts/precompute.ps1` or `scripts/precompute.sh` to bake all 120 experiments and train both learned models. For an isolated experiment use `python data-pipeline/rebuild.py --cases FWI_FAULT --variants reference --output data/raw/fault-study`. A filtered bake cannot overwrite the canonical catalogue.

Run `python tests/run_validation.py`, `python scripts/check_artifacts.py`, then in `frontend`, `npm ci`, `npm test`, `npm run build`, and `npm run dev`. Computation is local; the build only copies committed results. The test runner saves JUnit and GPU environment evidence.
