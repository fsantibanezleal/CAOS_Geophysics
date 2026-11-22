# M12 geometry-normalized velocity refinement notebook replay

**Run date:** 2026-10-30
**Scope:** the English and Spanish Level 4 notebook pair for the frozen residual-CNN velocity-refinement experiment. This is notebook execution and reproducibility evidence, not scientific acceptance of M12 or the product.

## Reproduction

The fresh-kernel run used the repository's `.venv-notebooks` with NumPy 2.2.6, SciPy 1.15.2, Matplotlib 3.10.8, and CPU PyTorch 2.14.0+cpu. The notebooks regenerate fixed-seed synthetic surveys, verify the frozen checkpoint and source receipt, construct validation and held-out groups, select the classical regularization on validation only, and evaluate both methods on the same input picks. The inverse maps are scored against synthetic velocity truth and an independent bilinear quadrature travel-time operator. No OpenFWI arrays are loaded.

```powershell
.venv-notebooks\Scripts\python.exe scripts\run_notebooks.py --only notebooks\en\08-learning\07-physics-conditioned-velocity-refinement.ipynb notebooks\es\08-learning\07-physics-conditioned-velocity-refinement.ipynb
```

Both notebooks completed in fresh kernels. Each contains six executed code cells and seven saved cell outputs, including both figures, with matching metrics. The notebook data, checkpoint, and receipt are hash-checked; checkpoint training is not repeated in this inference replay.

## Measured result

For the joint geology-and-acquisition shift cohort (`n = 160`), the learned/classical RMSE ratios were **2.1875** for velocity and **5.4173** for independently forwarded travel time. The predeclared criterion requires both ratios below 1.0; it fails. **0 of 160** paired surveys improved on both measures. The frozen model is therefore inferior to the validation-selected regularized ray baseline on this synthetic cohort. This negative result is retained without tuning on the held-out cohorts.

The aggregate comparison figure now places its legend above the plotting area and labels the plotted quantity as a learned-to-classical RMSE ratio. The paired-survey figure plots both ratios on logarithmic axes and marks the joint-improvement quadrant boundaries.

## Limits and gates

These tests establish that the two lessons execute and reproduce this bounded synthetic result. They do not establish field accuracy, an advantage over state-of-the-art methods, external-data rights, or M12 scientific acceptance. The result remains `scientific_acceptance=false`; the convergence ledger and adversarial scientific gates remain authoritative.
