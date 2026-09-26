# Inverse Earth Studio · 0.04.001

[Open the observatory](https://geophysics.ml.fasl-work.com/) · [GitHub Pages](https://fsantibanezleal.github.io/CAOS_Geophysics/) · [Documentation](docs/README.md) · [0.04.001 local scientific and browser evidence](docs/validation/scientific-ui-0.04.001.md) · [0.04.000 public deployment evidence](docs/validation/deployment-0.04.md)

A geophysics investigation workbench with 20 distinct geological cases, six conditions per case, and 348 computed inverse-method results. The release uses original synthetic geology and arrays calculated by SimPEG, SciPy, PyTorch and Deepwave. The catalogue records each method's target, units, final state and recovery verdict.

## Investigate

- Gravity and magnetics: 3D geological volumes, survey fields, spatially regularized, noise-weighted scalar/vector inverses and conditional data-noise ensembles.
- Magnetotellurics: layered complex impedance, matched bounded TRF/Adam/neural inverses, fixed-thickness uncertainty, original synthetic EDI inversion fixtures, and a separately cited measured Clear Lake tensor screen with no field inversion.
- Seismics: four geological sections, three shots, computed wavefields and receiver gathers, full-band adjoint FWI and frequency continuation with withheld receivers.
- Joint inversion: matched uncoupled, cross-gradient and independently fitted Gaussian-mixture petrophysical priors, including a mismatched-prior control.
- Learned models: a trained column-density CNN and observation autoencoder with identical noisy classical comparison inputs, held-out geometries, and recorded detection failures.
- Online operations: orbit and angle steps, cuts, physical playback, comparisons, numerical exports, and a live MT calculator with model import/export.

## Reproduce

```powershell
./scripts/setup.ps1 -Gpu
./scripts/rebuild-release.ps1
$env:INVERSE_EARTH_DATA = 'data/experiments/release-0.04.001'
$env:FWI_RECOVERY_ARTIFACTS = $env:INVERSE_EARTH_DATA
./.venv-pipeline/Scripts/python.exe tests/run_validation.py
./.venv-pipeline/Scripts/python.exe data-pipeline/ingest.py --external
cd frontend
npm ci
npm test
node copy-data.mjs --source ../data/experiments/release-0.04.001
npx vite --host 127.0.0.1 --port 5179
```

Python 3.12. Both `.venv` and `.venv-pipeline` are local and ignored. The full candidate rebuild runs artifact, recovery and 48-model CUDA replay gates; it requires the hash-pinned Clear Lake station EDI at the ignored path in `data/source-ledger.json` and fails before GPU computation if the file is missing. It never overwrites the canonical release. The default numerical precompute path is also ignored. The Vite command above previews candidate arrays; `npm run build` copies the committed canonical release only. CI performs CPU-safe artifact and frontend gates. Scripts are invoked by file path; there is no internal Python package.

## What the results mean

The inverse benchmarks use original synthetic geology with known truth, not field interpretation. The measured Clear Lake EDI supplies observed transfer functions and a failed necessary isotropic-1D compatibility screen; no field inverse model or known geology is presented. A low data residual is not proof of recovered geology. The basin gravity target remains unresolved, the salt FWI case remains a cycle-skipping control, and the autoencoder missed all 80 withheld-family examples in its separate test. A single displayed autoencoder score is not a calibrated geological detector. Conditional observation-noise intervals omit geological and forward-model uncertainty and are not calibrated posterior intervals. Neural column density does not resolve 3D depth; MT thicknesses are known; seismic propagation is constant-density 2D acoustics. No new inverse algorithm or field-validation claim is made.

GPU computations were executed locally on an NVIDIA RTX 4070 Laptop GPU. Public hosts serve computed artifacts; there is no public GPU execution endpoint. The live MT calculation is independent browser computation, checked against the offline recursion.

## Repository

`data-pipeline/`: plain numerical and ingestion scripts. `data/derived/v2/`: catalogue, experiments and checkpoints. `frontend/`: shared-shell bilingual React instrument. `tests/`: numerical tests including CUDA adjoint verification. `docs/validation/`: release evidence. `docs/research/`: primary-source review. `manuscripts/`: software technical report, not a novelty claim.

The [reference course](https://github.com/Anagabrielamantilla/inversion-geofisica-python) informed the topic sequence. Its unlicensed notebooks and data are not redistributed. Two external SimPEG tutorial archives are downloaded, hashed, validated and preprocessed locally; values stay ignored pending redistribution review. The measured EDI derivative cites the [USGS Clear Lake release](https://doi.org/10.5066/P14KAQ3M) and [EarthScope transfer-function collection](https://doi.org/10.17611/DP/EMTF/GMEG/Clearlake). Original code: Apache-2.0. Original content and generated synthetic data: CC-BY-4.0.
