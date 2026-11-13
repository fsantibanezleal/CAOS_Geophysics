# M13 browser runtime parity on the STEAD display traces

Measured 2026-10-27 on the committed, preselected browser package. This verifies that the product’s ONNX Runtime Web WASM path reproduces the frozen ONNX model’s CPU ONNX Runtime output over every QC-valid waveform in that package. It is a numerical runtime-parity check; it does not independently validate the trained checkpoint, expand the accuracy population, establish rights for redistribution, or prove the VPS deployment.

## Population and identity

The asset manifest SHA-256 is `d4d2b5b1a98d3a7a2077baab7750c8a96e4b5152b6930e4a09ae4bdc97db8394`; the ONNX SHA-256 is `4e5962ed0a9037e545991c218ae770ae7aff2c01f1e6a919c338705780ce5f4c`. The 24 rows were selected before held-out scoring: 23 have hash-verified normalized STEAD inputs and one QC-rejected noise row has no waveform and is never inferred. The separate frozen benchmark contains 6,000 test rows and remains the only population-level accuracy result.

## Runtime comparison

For each valid row, the hash-checked product runtime imports `frontend/src/phase-runtime.ts`, creates an ONNX Runtime Web session on WASM and processes the exact `[1,3,6000]` E/N/Z array. A separately recomputed ONNX Runtime 1.30.0 `CPUExecutionProvider` run of the same model bytes supplies reference probabilities. The browser probabilities are compared sample-by-sample with absolute tolerance 0.001; P/S peak locations and threshold/separation picks are compared as well. The verifier retains the QC exclusion, rejects stale/mismatched hashes, checks output shape, and reads/writes probability arrays only under `CAOS_TEMP_ROOT`. No inference request is sent to an API.

Results: all 23 valid traces passed; maximum absolute probability difference was `5.0664e-6`, maximum P/S peak displacement was 0 samples, all accepted/abstained picks matched within one sample, and mean browser inference time was about 64 ms per trace in this local Chromium run. The complete per-trace record, runtime versions, hashes and tolerances are in [m13-browser-population-parity-2026-10-27.json](m13-browser-population-parity-2026-10-27.json). The manifest retains `browser_parity_verified: false` as its export-state value; the later measured parity is documented here and in the receipt.

## Reproduction

From the repository root in PowerShell, with `.venv-pipeline` and `frontend/node_modules` prepared:

```powershell
$env:CAOS_TEMP_ROOT = 'E:\_worktrees\_m13-parity-reproduction'
.venv-pipeline\Scripts\python.exe data-pipeline\stead_phase_browser_subset.py `
  --output "$env:CAOS_TEMP_ROOT\analysis.json" `
  --probability-output-dir "$env:CAOS_TEMP_ROOT\cpu-probabilities"
Push-Location frontend
node scripts/verify-phase-browser-parity.mjs `
  --assets ../data/derived/phase/browser-assets/stead `
  --analysis "$env:CAOS_TEMP_ROOT\analysis.json" `
  --references "$env:CAOS_TEMP_ROOT\cpu-probabilities" `
  --report ../docs/validation/m13-browser-population-parity-2026-10-27.json
Pop-Location
```

The 23-trace selection remains a display subset, not a representative accuracy sample. The CPU and WASM runs share the same exported ONNX checkpoint, so this test can detect runtime/preprocessing/output discrepancies but not a defect shared by both runtimes or a deficient model. Independent model validation remains governed by the locked 6,000-trace benchmark and its held-out protocol.
