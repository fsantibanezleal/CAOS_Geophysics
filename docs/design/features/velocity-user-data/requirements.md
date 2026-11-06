# First-arrival user-data tools

This extends the approved local M09/M12 data-tools scope. It does not change the
frozen learned benchmark, train a new checkpoint or assert field accuracy.

| ID | Requirement | Gate in tests/data/test_velocity_user_data.py |
| --- | --- | --- |
| VUD-01 | Reject excessive bytes/depth, duplicate keys, unknown fields, nonfinite values, missing physical units/frame/rights, invalid ray geometry and count/shape mismatch before scientific imports. | test_bounded_physical_contract |
| VUD-02 | Preserve original bytes/hash, every ray ID, declared uncertainty and acquisition geometry; no amplitude thinning, invented truth or training. | test_identity_and_original_order |
| VUD-03 | Execute actual error-weighted slowness least squares using supplied times, ray-cell intersections, explicit lambda and the existing physical smoothness/reference; solve the physical velocity box constraints inside the objective rather than clipping an unconstrained result; expose coverage, predictions, signed residuals, objective, active bounds and projected KKT diagnostics. | test_weighted_inverse_and_parameter_effect; test_active_velocity_bounds_match_independent_qp_oracle |
| VUD-04 | Optional learned inference must use a hash-verified existing checkpoint on the same supplied observations/geometry, never classical substitution; retain failed benchmark and out-of-training-domain warnings. | test_actual_checkpoint_inference |
| VUD-05 | Export finite arrays, physical axes, configuration, engine/source hashes and nonclaims to a fresh local generation. New v2 exports must have a serialized-model projected KKT residual within the frozen gate and pass producer-side physics verification. Historical v1 generations remain readable with their solve-then-clip status intact. An interrupted or altered generation is not successful. | test_bundle_roundtrip_and_corruption; test_legacy_v1_result_remains_reopenable_as_historical_data |
| VUD-06 | The CLI must execute user bytes without downloads, uploads, implicit installs or overwrite; malformed input exits nonzero without a partial success. | test_cli_actual_input_and_no_overwrite |

Numerical controls: homogeneous cell-ray time agrees with distance/velocity to
1e-10 s. An independent SciPy bounded least-squares oracle matches interior and
active-limit solutions; the v2 projected KKT relative residual is at most
1e-9 after reconstructing the model from its serialized velocities. The browser
and Python active-limit control agree on 127 active cells, 134 active-set
iterations and selected velocity cells. Changed times/uncertainties/lambda
must change the corresponding actual result. This establishes the declared
quadratic solve on controls, not field accuracy. No known-truth error or
held-out score is invented for an unlabelled user survey.
