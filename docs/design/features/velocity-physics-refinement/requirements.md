# Geometry-normalized learned tomography

This repairs a dimensional input-conditioning defect without rewriting the
original failed experiment, checkpoint or test receipts. The original input
`A.T residual / A.T 1` has units of seconds, not slowness; multiplying it by
velocity squared cannot produce a velocity perturbation. Normalize each
ray residual by its path length before backprojection. This choice follows
the straight-ray integral, not a search over the old held-out scores.

| ID | Frozen requirement | Gate in tests/learning/test_velocity_physics.py |
| --- | --- | --- |
| VPR-01 | A spatially constant slowness perturbation must map to its exact coverage-weighted slowness at every covered cell; units/sign and zero coverage must remain explicit. | test_uniform_slowness_feature_oracle |
| VPR-02 | Use new disjoint realization seed namespaces for all six cohorts, freeze geometry/families/counts before training, and never select on test metrics. | test_fresh_cohorts_and_original_preservation |
| VPR-03 | Train the actual residual CNN on corrected physical features; output must remain1400..4000 m/s with the exact reference represented at zero network output. Save/reload real weights with bounded finite state checks. | test_network_reference_bounds_and_checkpoint |
| VPR-04 | Report every matched classical and independent bilinear-forward metric, original negative comparator and all new failures; no guarantee of improvement. | test_scientific_verdict_preserves_failure |
| VPR-05 | Execute the full fixed40-epoch protocol on the local GPU when available and independently re-evaluate selected weights on CPU; a short fixture is not qualification. | test_frozen_receipt_and_replay |

This is a revised implementation study, not a novel inverse algorithm, an unseen
geological-family claim or field validation. Primary method basis:
[Adler and Oktem](https://arxiv.org/abs/1707.06474), explicit physical operators
in learned reconstruction; the bounded travel-time approximation and independent
ray/quadrature laws are detailed in the original M12 design.
