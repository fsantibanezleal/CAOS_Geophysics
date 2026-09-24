# Rebuild validation

The v1 interface and repeated analytic results were rejected. Validation here refers only to v2. Numerical, artifact, browser, CI and deployment gates are separate; one does not substitute for another.

## Numerical evidence

`tests/run_validation.py` persists JUnit in `numerical.xml` and actual CUDA/device data in `environment.json`. The release suite checks homogeneous MT, layer-splitting invariance, NumPy/Torch parity, directional MT derivatives, independent Choclo/SimPEG prism values and gravity sign, L2/IRLS data reduction, cross-gradient parallel/orthogonal behavior, every family/variant's finite model and residual closure, learned split uniqueness, checkpoint reloaded predictions, and a double-precision Deepwave CUDA directional derivative.

SimPEG's small prism matrix is float32, so its linearity tolerance reflects float32 precision. JSON uses seven significant digits; residual tests include an absolute scale-aware cancellation floor. These are representation tolerances, not data-noise acceptance thresholds.

`scripts/check_artifacts.py` checks 20 distinct reference truth hashes, 120 experiments, 324 method results, all schemas/identities/metrics, SHA-256, sizes and both checkpoint hashes. The browser unit suite tests array orientation, plot bounds, input rejection and live-MT parity over all 24 truth soundings.

Detailed results are in [results.md](results.md); source hashes and machine-readable metrics are in [metrics.json](metrics.json). External source preprocessing records both 289-station observation tables and their transformation hashes in `data/external-preprocessing.json`.

## Interpretation checks

- A good data fit is never called proof of resolved geology.
- MT layer thickness is disclosed as known. There are no posterior error bands.
- Neural MT is per-sounding optimization, not a pretrained universal inverse.
- FWI is constant-density 2D acoustics with a finite 28-update budget and known source.
- Cross-gradient uses normalized cell-index derivatives, not physical gradient units.
- The CNN predicts column density, not 3D depth.
- The autoencoder misses the two withheld reference geometries at its stated threshold. That negative result is retained, not relabelled as successful novelty detection.
- Seismic colour gain clips only the display. Canvas interpolation does not increase numerical resolution.
- The browser and VPS do not claim to provide GPU computation.

## Rendered and deployment gates

The exact browser and deployed checks are recorded separately in `browser.md` and `deployment.md` after execution. Until those records exist, this numerical report alone is not release completion evidence.
