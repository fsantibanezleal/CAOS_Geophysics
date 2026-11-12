# Browser model artifact contract

**Contract:** `browser-model-assets/v1`
**Owner:** M13 asset exporter and the product data-copy hook
**Consumers:** the M13 browser workbench and the exploratory M12 inference view

## M13 phase picker

The repository stores the PhaseNet-family ONNX model as `data/derived/phase/browser-assets/stead/model.onnx.gz`. The gzip stream is deterministic and lossless. Its manifest records `source_file`, compressed byte count and SHA-256 separately from the runtime model's `file`, uncompressed byte count and SHA-256. The current compressed source is 5,080,687 bytes; the decompressed ONNX is 5,739,696 bytes and retains SHA-256 `4e5962ed0a9037e545991c218ae770ae7aff2c01f1e6a919c338705780ce5f4c`.

The build hook verifies the compressed identity and the decompressed identity, then writes the original `model.onnx` bytes to the ignored frontend data overlay. The browser fetches only that manifest-named same-origin file and checks its uncompressed hash before inference. Gzip changes repository storage only; it does not quantize weights, alter scores, change picks, or change the frozen held-out benchmark. The output therefore remains subject to the existing CPU/browser parity gate and STEAD attribution.

The corresponding model's storage limit is 5 MiB for the committed compressed source. The uncompressed 5,739,696-byte model exists only in generated build output and the external release bundle. A missing source or either hash mismatch fails the asset check and build; the application must not fall back to another checkpoint.

## M12 exploratory checkpoint

`models/experimental/m12-physics-cuda-20261004/m12-physics.onnx` is a separate 137,305-byte browser checkpoint with its own training and parity receipts. It is exposed only with its failed held-out-comparator verdict. It is not the M13 phase model, a field-validated velocity estimator, or evidence that the learned method outperforms the classical comparator.

## Missing data and replacement

The browser shows M13 inference as unavailable when the manifest or any named asset is absent or fails its hash. Model replacement requires a new checkpoint identity, a new benchmark/review record and new CPU/browser parity evidence. Reusing a path does not preserve the prior model's acceptance.
