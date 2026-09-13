# Offline scientific engine

`geophysicslab` is the single source of computational truth for the release bake. It contains typed input and replay contracts, seeded original cases, potential-field kernels, layered MT recursion, finite-difference acoustics, solver certificates, learned probes, staged evaluation, and manifest export.

Run `python data-pipeline/run.py all` from the repository root, or use `scripts/precompute.ps1`. The command writes compact JSON into `data/derived/` and never requires a server. Heavy native and accelerator dependencies are isolated in `.venv-pipeline`; the root `.venv` remains the slim runtime environment.
