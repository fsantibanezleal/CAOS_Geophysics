# Inverse Earth Studio · 0.04.000

[Open the observatory](https://geophysics.ml.fasl-work.com/) · [GitHub Pages](https://fsantibanezleal.github.io/CAOS_Geophysics/) · [Documentation](docs/README.md) · [0.04 scientific and browser evidence](docs/validation/scientific-ui-0.04.md) · [0.04 public deployment evidence](docs/validation/deployment-0.04.md)

A geophysics investigation workbench with 20 distinct geological cases, six conditions per case, and 348 computed inverse-method results. The release uses original synthetic geology and arrays calculated by SimPEG, SciPy, PyTorch and Deepwave. The catalogue records each method's target, units, final state and recovery verdict.

## Investigate

- Gravity and magnetics: 3D geological volumes, survey fields, spatially regularized, noise-weighted scalar/vector inverses and conditional data-noise ensembles.
- Magnetotellurics: layered complex impedance, matched bounded TRF/Adam/neural inverses, fixed-thickness uncertainty, and original EDI parsing and inversion fixtures.
- Seismics: four geological sections, three shots, computed wavefields and receiver gathers, full-band adjoint FWI and frequency continuation with withheld receivers.
- Joint inversion: matched uncoupled, cross-gradient and independently fitted Gaussian-mixture petrophysical priors, including a mismatched-prior control.
- Learned models: a trained column-density CNN and observation autoencoder with identical noisy classical comparison inputs, held-out geometries, and recorded detection failures.
- Online operations: orbit and angle steps, cuts, physical playback, comparisons, numerical exports, and a live MT calculator with model import/export.

## Reproduce

```powershell
./scripts/setup.ps1 -Gpu
./scripts/precompute.ps1
./.venv-pipeline/Scripts/python.exe data-pipeline/ingest.py --external
./.venv-pipeline/Scripts/python.exe tests/run_validation.py
./.venv-pipeline/Scripts/python.exe scripts/check_artifacts.py
./.venv-pipeline/Scripts/python.exe scripts/validate_recovery.py
cd frontend
npm ci
npm test
npm run build
npm run dev
```

Python 3.12. Both `.venv` and `.venv-pipeline` are local and ignored. Scripts are invoked by file path; there is no internal Python package. Bash equivalents are in `scripts/`. Filtered bakes require a separate `--output` directory to protect the canonical catalogue.

## What the results mean

The release uses original synthetic geology with known truth, not a field interpretation. A low data residual is not proof of recovered geology. The basin gravity target remains unresolved, the salt FWI case remains a cycle-skipping control, and the autoencoder missed all 80 withheld-family examples in its separate test. The conditional observation-noise intervals omit geological and forward-model uncertainty and are not calibrated posterior intervals. Neural column density does not resolve 3D depth; MT thicknesses are known; seismic propagation is constant-density 2D acoustics. No new inverse algorithm or field-validation claim is made.

GPU computations were executed locally on an NVIDIA RTX 4070 Laptop GPU. Public hosts serve computed artifacts; there is no public GPU execution endpoint. The live MT calculation is independent browser computation, checked against the offline recursion.

## Repository

`data-pipeline/`: plain numerical and ingestion scripts. `data/derived/v2/`: catalogue, experiments and checkpoints. `frontend/`: shared-shell bilingual React instrument. `tests/`: numerical tests including CUDA adjoint verification. `docs/validation/`: release evidence. `docs/research/`: primary-source review. `manuscripts/`: software technical report, not a novelty claim.

The [reference course](https://github.com/Anagabrielamantilla/inversion-geofisica-python) informed the topic sequence. Its unlicensed notebooks and data are not redistributed. Two external SimPEG tutorial archives are downloaded, hashed, validated and preprocessed locally; values stay ignored pending redistribution review. Original code: Apache-2.0. Original content and generated data: CC-BY-4.0.
