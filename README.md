# Inverse Earth Studio · 0.03.000

[Open the observatory](https://geophysics.ml.fasl-work.com/) · [GitHub Pages](https://fsantibanezleal.github.io/CAOS_Geophysics/) · [Documentation](docs/README.md)

A geophysics investigation workbench: 20 distinct geological cases, six controlled conditions per case, and 324 computed inverse-method results. The v2 rebuild replaces the rejected repeated-Gaussian analytic renderer. It uses the actual arrays produced by SimPEG, SciPy, PyTorch and Deepwave.

## Investigate

- Gravity and magnetics: 3D geological volumes, survey fields, sections, scalar/vector inversion, L2 and sparse IRLS.
- Magnetotellurics: layered-earth impedance, bounded least squares, differentiable inversion and a physics-guided neural parameterization.
- Seismics: four geological sections, three shots, finite-difference pressure animation, receiver gathers, adjoint FWI and continuation.
- Joint inversion: shared and conflicting property structures with a cross-gradient objective.
- Learned models: a trained column-density CNN and observation autoencoder with held-out geometries, serialized weights and test errors.
- Online operations: orbit and angle steps, cuts, physical playback, comparisons, numerical exports, and a live MT calculator with model import/export.

## Reproduce

```powershell
./scripts/setup.ps1 -Gpu
./scripts/precompute.ps1
./.venv-pipeline/Scripts/python.exe data-pipeline/ingest.py --external
./.venv-pipeline/Scripts/python.exe tests/run_validation.py
./.venv-pipeline/Scripts/python.exe scripts/check_artifacts.py
cd frontend
npm ci
npm test
npm run build
npm run dev
```

Python 3.12. Both `.venv` and `.venv-pipeline` are local and ignored. Scripts are invoked by file path; there is no internal Python package. Bash equivalents are in `scripts/`. Filtered bakes require a separate `--output` directory to protect the canonical catalogue.

## What the results mean

The release uses original synthetic geology with known truth, not a real field interpretation. A low data residual is not proof of the recovered geology. Neural column density does not resolve 3D depth. MT thicknesses are known. Seismics is constant-density 2D acoustics, not field-scale elastic FWI. The limited FWI optimization budget and training distribution are declared. No posterior uncertainty or algorithmic novelty is claimed.

GPU computations were executed locally on an NVIDIA RTX 4070 Laptop GPU. Public hosts serve computed artifacts; there is no public GPU execution endpoint. The live MT calculation is independent browser computation, checked against the offline recursion.

## Repository

`data-pipeline/`: plain numerical and ingestion scripts. `data/derived/v2/`: catalogue, experiments and checkpoints. `frontend/`: shared-shell bilingual React instrument. `tests/`: numerical tests including CUDA adjoint verification. `docs/validation/`: release evidence. `docs/research/`: primary-source review. `manuscripts/`: software technical report, not a novelty claim.

The [reference course](https://github.com/Anagabrielamantilla/inversion-geofisica-python) informed the topic sequence. Its unlicensed notebooks and data are not redistributed. Two external SimPEG tutorial archives are downloaded, hashed, validated and preprocessed locally; values stay ignored pending redistribution review. Original code: Apache-2.0. Original content and generated data: CC-BY-4.0.
