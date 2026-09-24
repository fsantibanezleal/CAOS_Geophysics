# GPU boundary

The canonical bake was executed with PyTorch 2.14.0+cu126 and Deepwave 0.0.27 on an NVIDIA GeForce RTX 4070 Laptop GPU. Deepwave uses its compiled CUDA propagator, including adjoint gradients. Neural training, neural MT and joint optimization also use CUDA. SimPEG operators and SciPy solves use CPU.

`tests/run_validation.py` requires CUDA for the release gradient check, runs a double-precision directional derivative comparison, and records device/runtime metadata. A GPU availability label is not accepted as evidence on its own. The learning ledger records the training device and held-out results.

The public ML VPS is a static host. It does not expose GPU compute or accept uploaded datasets. The live MT browser calculator runs on the viewer's CPU. Full FWI retraining/recalibration must run locally and be exported as a new experiment.
