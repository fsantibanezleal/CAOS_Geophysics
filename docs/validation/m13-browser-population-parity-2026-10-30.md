# M13 browser parity on the current display manifest

Run: 2026-10-30, local Windows desktop; Chromium 153.0.8010.12, ONNX Runtime Web 1.30.0 WASM, ONNX Runtime 1.30.0 CPU reference.

The current manifest selected 24 traces before scoring: browser inference ran on all 23 QC-valid traces, and the one QC-rejected trace remained excluded. Every waveform, ONNX model, CPU reference array, and manifest hash was verified. The comparison used the same frozen ONNX checkpoint in CPU ONNX Runtime and browser WASM.

Result: **pass**. Maximum probability absolute error was 5.0664e-6 against a 0.001 tolerance; P/S probability peaks were identical for all 23 traces. Mean browser inference time was 125.03 ms per trace.

This establishes same-checkpoint runtime parity for the preselected display subset. It is not an independent PyTorch-oracle comparison and does not establish accuracy on a representative population. The reported accuracy evidence remains the separately locked 6,000-trace benchmark; the analyst picks in the display subset are not geological ground truth.

The full machine-readable report, including per-trace errors and inference times, is in `m13-browser-population-parity-2026-10-30.json`.
