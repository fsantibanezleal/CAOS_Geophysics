# M13 real-waveform task gates

- [x] Pin and hash-verify the STEAD metadata; reject its published trace-level split for event/station independent claims.
- [x] Finish waveform download, verify exact bytes and SHA-256, and record HDF5 format/source receipt.
- [x] Select event/station-disjoint quake and station-disjoint noise inventories by fixed metadata-only hash rule; validate the full manifest and report exclusions. This is metadata-only: 60,000/5,000 training quake/noise, 5,000/1,000 each for dev and untouched test. Of 1,265,657 rows, 498,116 passed strict manual-label/noise and split eligibility; 44 had unsupported identity/slice and 275,132 candidate quakes lacked two manual picks. No waveforms were opened.
- [x] Verify bucketed HDF5 reader and failure-retaining private extractor against real source traces and an independent SeisBench read; retain train/dev/test QC exclusions.
- [x] Train an actual GPU model from scratch with recorded seed, configuration, environment, optimizer, losses and checkpoint hash; choose threshold on dev only.
- [x] Run M08 and M13 on identical untouched real test traces, preserving misses and noise false alarms; report stratified timing and degradation.
- [x] Export that exact checkpoint for the browser; verify local/browser probability and peak parity on the same held-out traces in Playwright Chromium.
- [x] Independently rerun the frozen ONNX through CPUExecutionProvider and the product WASM runtime on all 23 QC-valid browser traces; compare probability tensors, P/S peaks and accepted/abstained picks while preserving the rejected record. The 2026-10-27 receipt records maximum absolute probability error 5.07e-6 and zero peak-sample difference. This is runtime parity for one checkpoint, not an independent PyTorch comparison or an accuracy claim from the selected subset; see [validation record](../../../validation/m13-browser-population-parity-2026-10-27.md).
- [x] Complete the scoped source and derivative rights review for the committed STEAD browser package and its attributed real-trace case; public release remains subject to product and VPS gates. See [rights review](rights-review-2026-10-28.md) and the package [attribution](../../../../data/derived/phase/browser-assets/stead/ATTRIBUTION.md).

The PhaseNet 100-trace sample is an engineering fixture, never training or benchmark evidence. The completed boxes above have local source, computation, browser-test, and scoped asset-rights evidence; full product and VPS release acceptance remain open.
