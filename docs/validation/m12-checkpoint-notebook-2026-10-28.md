# M12 learned velocity checkpoint notebook pair

Added and freshly executed the English and Spanish Level 3 notebook pair
`notebooks/{en,es}/08-learning/05-m12-velocity-checkpoint.ipynb`. Both lessons
run the actual fixed 40-epoch CPU training protocol into external scratch,
reload the checkpoint, verify its SHA-256 and source receipt, reconstruct all
six declared cohorts, compare the learned and same-input classical maps, and
score both with the independent quadrature forward operator. The notebook
outputs are regenerated from the code; model weights and temporary inputs are
not committed or published.

The run used NumPy 2.2.6, SciPy 1.15.2, Matplotlib 3.10.8, and PyTorch
2.14.0+cu126 with the declared CPU device. Training selected epoch 39 of 40.
The checkpoint SHA-256 is
`119cc3c9b33d952ce5884fc7067d8b32ab00373e69743d33dd5364267acef9fb`; the
verified experiment status is `failed-held-out-comparator`.

On the 160 joint family-and-acquisition holdouts (fault/salt, layout C),
learned/classical velocity RMSE is 536.99/95.62 m/s (ratio 5.616), and
independent-oracle travel-time RMSE is 28.61/2.34 ms (ratio 12.231). The
predeclared criterion fails both comparisons. The notebook preserves that
negative result and does not use the test cohort to tune the model or classical
regularization.

Verification: each language notebook executed top-to-bottom in a fresh
`caos-pipeline` kernel; the structural gate accepts 58 mirrored notebooks, and
the source-to-content matrix binds both notebook files to M12. A separate
fresh-output `--check` replay is recorded independently. This teaches and
reproduces the failure; it does not close M12, R-008, field validation, or
product/release acceptance.
