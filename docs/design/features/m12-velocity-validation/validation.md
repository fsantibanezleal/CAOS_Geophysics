# Adversarial validation: M12 learned velocity experiment

These tests target leakage, operator agreement, checkpoint integrity, metric recomputation, negative-result retention, and pipeline isolation. The measured method result remains a failed synthetic comparison; the tests do not promote it to field or product acceptance.

| requirement | adversarial check | gate |
| --- | --- | --- |
| VEL-01 | Plant overlapping realization seeds or a training/test acquisition ray; the frozen cohort contract must reject leakage. | `tests/learning/test_velocity_inversion.py::test_adversarial_family_acquisition_partition_and_hashes` |
| VEL-02 | Compare homogeneous analytic travel times and cell lengths to an independent quadrature operator, then require a heterogeneous operator-mismatch control. | `tests/learning/test_velocity_inversion.py::test_adversarial_independent_oracle_and_ray_geometry` |
| VEL-03 | Append bytes to the checkpoint without updating the expected digest; loading must fail before inference. | `tests/learning/test_velocity_inversion.py::test_adversarial_checkpoint_digest_and_forward_consistency` |
| VEL-04 | Reuse the identical noisy observations for the reference and learned method and keep test records out of regularization selection. | `tests/learning/test_split_and_benchmark.py::test_adversarial_disjoint_groups_and_matched_inputs` |
| VEL-05 | Recompute validation threshold, cohort means, family totals, and detection counts from per-record metrics; any mismatch must fail. | `tests/learning/test_velocity_inversion.py::test_adversarial_receipt_metrics_recompute` |
| VEL-06 | Plant a worse learned model score and a worse forward score independently; either failure must preserve the negative verdict. | `tests/learning/test_velocity_inversion.py::test_adversarial_negative_verdict_is_not_suppressed` |
| VEL-07 | Run the one-epoch fixture pipeline in a fresh directory; it must write only local fixture artifacts, refuse production verification, and refuse overwrite. | `tests/learning/test_velocity_inversion.py::test_adversarial_local_pipeline_scope` |
