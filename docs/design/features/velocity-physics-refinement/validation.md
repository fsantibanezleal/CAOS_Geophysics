# Geometry-normalized learned tomography adversarial validation

| requirement | adversarial check | gate |
| --- | --- | --- |
| VPR-01 | Plant a spatially uniform slowness perturbation, reverse its sign, and remove coverage from one cell; reject wrong dimensional scaling or nonzero unsupported features. | `tests/adversarial/test_velocity_physics_adversarial.py::test_adversarial_vpr_01_refutes_dimensional_feature_errors` |
| VPR-02 | Compare every revised cohort's seeds against the prior experiment and the other cohorts; reject overlap, changed frozen IDs, or nondeterministic manifests. | `tests/adversarial/test_velocity_physics_adversarial.py::test_adversarial_vpr_02_refutes_cohort_overlap` |
| VPR-03 | Force extreme network logits and serialize/reopen weights; reject predictions outside the physical box or a changed checkpoint result, and verify zero output is the reference model. | `tests/adversarial/test_velocity_physics_adversarial.py::test_adversarial_vpr_03_refutes_unbounded_or_unreopenable_weights` |
| VPR-04 | Plant held-out ratios on opposite sides of one; reject any verdict that turns a failed learned comparator into success or drops the original failure receipt. | `tests/adversarial/test_velocity_physics_adversarial.py::test_adversarial_vpr_04_preserves_negative_comparator` |
| VPR-05 | Plant the one-epoch, 12-record fixture and attempt to verify it as the full study; reject qualification while replaying the retained 40-epoch CUDA receipt on CPU. | `tests/adversarial/test_velocity_physics_adversarial.py::test_adversarial_vpr_05_rejects_fixture_as_qualification` |
