# GPU lane

The local compute record targets an NVIDIA GeForce RTX 4070 Laptop GPU with the CUDA PyTorch wheel. Use scripts/setup.ps1 -Gpu, then run the pipeline and inspect data/derived/release.json for the engine inventory. GPU availability is evidence only when the import and CUDA capability are observed. The ML VPS is CPU-only; it does not receive the environment or train models.

The web artifact is intentionally backend-independent. A GPU failure does not erase the CPU-safe analytic bake, but the release record must state whether the accelerator was used.
