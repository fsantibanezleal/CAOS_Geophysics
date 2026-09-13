# Learned baselines

The release contains two learned baselines: a spatial convolutional field prior and a spatial autoencoder. Both are trained offline on the grouped synthetic geology registry, with case-level separation between training, validation, and held-out groups. The GPU bake records the backend, device, sample counts, train loss, and held-out loss in `data/derived/training.json` and each replay manifest.

Weights are intentionally regenerated from the seeded training stage rather than committed as an opaque binary. The exact architecture, seed, groups, and metrics are part of the release evidence, so a fresh environment can reproduce the checkpoint path with `scripts/precompute.ps1` or `scripts/precompute.sh`.

These baselines express spatial priors. They do not replace physics, acquisition geometry, uncertainty analysis, or expert interpretation.
