# M13 current browser parity and sensitivity lesson

Status: current browser/runtime parity passes for the exact committed STEAD manifest and ONNX bytes. The bilingual lesson executes, and each language now contains a selector sensitivity grid plus a bounded own-waveform contract. This is scoped M13 evidence, not product or deployment acceptance.

## Current parity

On 2026-11-05, `frontend/scripts/verify-phase-browser-parity.mjs` ran the frozen model through ONNX Runtime Web WASM in Playwright Chromium and compared the outputs with the repository's CPU ONNX reference arrays on the same 23 QC-valid traces. The preselected 24th row remains QC-rejected and was not inferred. The current manifest SHA-256 is `3e8fac54427eeb5525c70317c508d1f55188deac3a5964ad78931561fe3c32f0`; model SHA-256 is `4e5962ed0a9037e545991c218ae770ae7aff2c01f1e6a919c338705780ce5f4c`.

All 23 passed: maximum absolute sample-score difference `5.066394805908203e-6` against tolerance `0.001`, zero P/S peak displacement, and pick agreement within one sample. Mean browser inference time was `111.65 ms` per trace on this local Chromium run. The full per-trace receipt is [m13-browser-parity-current-2026-11-05.json](m13-browser-parity-current-2026-11-05.json). The manifest's `browser_parity_verified: false` remains the immutable export-state marker; this later receipt records the independently measured runtime parity.

## Lesson and sensitivity

The EN/ES lesson reuses each CPU probability tensor and the production `pick_probabilities` selector. It sweeps class thresholds `{0.4, 0.6, 0.8, 0.9}` and minimum P–S separation `{0.2, 0.4, 0.6, 0.8}` seconds. Every cell uses the same 23 valid records and the declared ±0.5 s analyst-reference tolerance; misses, outside-tolerance picks and false picks without analyst references remain separate. It does not alter the locked 6,000-record benchmark or select a new operating point from test data. Raw arrays and the sensitivity CSV are written under `CAOS_TEMP_ROOT`.

The own-data section documents the present inference contract: 60 seconds, 100 Hz, 6,000 aligned samples, E/N/Z, unrestituted counts, exact centering/float32 peak normalization, and fail-closed QC for gaps, invalid channels and incompatible sampling. It explicitly states that the notebook does not implement a general MiniSEED/StationXML ingestion path or browser resampling.

## Validation

- `python scripts/run_notebooks.py --only ...` executed EN and ES in fresh kernels, including the new probability export, sensitivity score table and heatmap.
- `python scripts/check_notebooks.py` passed all 66 notebooks in both language trees.
- CAOS_MANAGE depth measurements for M13: EN 1,584 prose words, 3 figures, 2 display equations, 4 references; ES 1,744 prose words, 3 figures, 2 display equations, 5 references. Both contain sensitivity and own-data sections.
- Current browser parity verifier: 23/23 valid traces passed; 1 QC-rejected row retained and excluded.

This evidence does not establish population accuracy beyond the separate locked benchmark, independent model quality, field generalization, public hosting, protected VPS workflow, or full release readiness.
