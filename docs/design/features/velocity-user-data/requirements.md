# First-arrival user-data tools

This extends the approved local M09/M12 data-tools scope. It does not change the
frozen learned benchmark, train a new checkpoint or assert field accuracy.

| ID | Requirement | Gate in tests/data/test_velocity_user_data.py |
| --- | --- | --- |
| VUD-01 | Reject excessive bytes/depth, duplicate keys, unknown fields, nonfinite values, missing physical units/frame/rights, invalid ray geometry and count/shape mismatch before scientific imports. | test_bounded_physical_contract |
| VUD-02 | Preserve original bytes/hash, every ray ID, declared uncertainty and acquisition geometry; no amplitude thinning, invented truth or training. | test_identity_and_original_order |
| VUD-03 | Execute actual error-weighted slowness least squares using supplied times, ray-cell intersections, explicit lambda and the existing physical smoothness/reference; expose coverage, predictions, signed residuals, objective and bounds. | test_weighted_inverse_and_parameter_effect |
| VUD-04 | Optional learned inference must use a hash-verified existing checkpoint on the same supplied observations/geometry, never classical substitution; retain failed benchmark and out-of-training-domain warnings. | test_actual_checkpoint_inference |
| VUD-05 | Export finite arrays, physical axes, configuration, engine/source hashes and nonclaims to a fresh local generation. Re-import must recompute identities/shapes; an interrupted or altered generation is not successful. | test_bundle_roundtrip_and_corruption |
| VUD-06 | The CLI must execute user bytes without downloads, uploads, implicit installs or overwrite; malformed input exits nonzero without a partial success. | test_cli_actual_input_and_no_overwrite |

Numerical controls: homogeneous cell-ray time agrees with distance/velocity to
1e-10 s; a separately constructed dense normal equation matches the estimate
to 1e-10 in scaled slowness, and the recorded weighted objective to 1e-9 relative.
Changed times/uncertainties/lambda must change the corresponding actual result.
No known-truth error or held-out score is invented for an unlabelled user survey.
