# Geometry-normalized learned tomography

This repairs a dimensional input-conditioning defect without rewriting the
original failed experiment, checkpoint or test receipts. The original input
`A.T residual / A.T 1` has units of seconds, not slowness; multiplying it by
velocity squared cannot produce a velocity perturbation. Normalize each
ray residual by its path length before backprojection. This choice follows
the straight-ray integral, not a search over the old held-out scores.

| ID | Frozen requirement | Gate |
| --- | --- | --- |
| VPR-01 | WHEN observations contain a constant slowness perturbation, feature construction SHALL recover its coverage-weighted value with the declared sign and units, and SHALL represent unsupported cells as zero. | `tests/adversarial/test_velocity_physics_adversarial.py::test_adversarial_vpr_01_refutes_dimensional_feature_errors` |
| VPR-02 | WHEN the six revised cohorts are generated, their realization seeds SHALL be disjoint from each other and the original study, with the frozen family and acquisition separation preserved. | `tests/adversarial/test_velocity_physics_adversarial.py::test_adversarial_vpr_02_refutes_cohort_overlap` |
| VPR-03 | WHEN the residual CNN is initialized or a checkpoint is reopened, the zero-network state SHALL equal the physical reference and every prediction SHALL remain within 1400 to 4000 m/s. | `tests/adversarial/test_velocity_physics_adversarial.py::test_adversarial_vpr_03_refutes_unbounded_or_unreopenable_weights` |
| VPR-04 | WHEN held-out learned-to-classical or independent-forward ratios fail, the scientific verdict SHALL remain failed and the receipt SHALL retain the original comparator. | `tests/adversarial/test_velocity_physics_adversarial.py::test_adversarial_vpr_04_preserves_negative_comparator` |
| VPR-05 | WHEN a one-epoch fixture is presented as qualification, verification SHALL reject it; the fixed 40-epoch CUDA receipt SHALL replay its cohorts and selected weights on CPU. | `tests/adversarial/test_velocity_physics_adversarial.py::test_adversarial_vpr_05_rejects_fixture_as_qualification` |

This is a revised implementation study, not a novel inverse algorithm, an unseen
geological-family claim or field validation. Primary method basis:
[Adler and Oktem](https://arxiv.org/abs/1707.06474), explicit physical operators
in learned reconstruction; the bounded travel-time approximation and independent
ray/quadrature laws are detailed in the original M12 design.
