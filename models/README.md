# Learned weights

Canonical weights live in `data/derived/v2/models/cnn.json` and `autoencoder.json`; the colocated `training.json` is the model registry. It carries hashes, normalization, three split seeds, counts, per-test errors, training curves and device. JSON tensors are reconstructed with `learning.load_checkpoint`. The release tests reload those exact weights and compare predictions with exported artifacts.

MT's neural method is a per-sounding optimization parameterization, not a released pretrained inverse. No third-party learned weights are redistributed.

The [M12 experimental CPU checkpoint and full receipt](experimental/m12-velocity-cpu-20260928/README.md) are separate from canonical weights. That first-arrival synthetic experiment failed its held-out classical comparator; it is retained for reproducibility and is not a released web model or a waveform/field inverse.
