# M02 submitted-survey local inversion requirements

Status: planned. Main review and implementation authorization are pending.
No numerical gate below has been executed for this feature. This is the complete
local forward/L2/IRLS vertical plan, not approval of full product M02 or a field
survey. Approved parent: [product SDD](../../SDD.md). Evidence: [research](../../../research/m02-survey-inversion-2026-10-03.md).

M02-01 WHEN a survey is submitted, THE local worker SHALL bind exact original
bytes, rights, source identity, processing lineage and configuration before
admission; it SHALL reject unknown or already-applied gravity corrections.
Gate: tests/data/test_gravity_survey.py::test_correction_state_no_double_processing

M02-02 WHEN units or signs are converted, THE worker SHALL preserve original
values and apply declared exact coordinate, acceleration and density conversions
once, including upward engine gz and exported observed-minus-predicted residuals.
Gate: tests/data/test_gravity_survey.py::test_exact_units_sign_and_density_conversion

M02-03 IF horizontal/vertical reference, axis order, topography or receiver
geometry is missing or incompatible, THEN THE worker SHALL reject rather than
infer a CRS, height datum, surface or measurement vertical.
Gate: tests/data/test_gravity_survey.py::test_crs_datum_geometry_rejection

M02-04 WHEN masks, repeated IDs or station order are supplied, THE worker SHALL
retain a reversible row map, excluded-row reasons and explicit null semantics;
it SHALL reject ambiguous duplicates and never turn missing observations into zero.
Gate: tests/data/test_gravity_survey.py::test_masks_duplicates_and_station_order

M02-05 WHEN weighted inversion is requested, THE worker SHALL require traceable
positive SD or SPD covariance and whiten each fitting partition independently;
it SHALL not treat conservative error bounds or guessed percentages as measured SD.
Gate: tests/data/test_gravity_survey.py::test_covariance_whitening_and_partition

M02-06 THE forward worker SHALL invoke pinned SimPEG with the Geoana prism engine
and meet separate Choclo, physical sign, scaling and volume-integral oracles.
Gate: tests/numerics/test_gravity_inverse.py::test_prism_sign_units_and_linearity
Gate: tests/numerics/test_gravity_inverse.py::test_volume_quadrature_and_far_field

M02-07 WHEN a 3D mesh is built, THE worker SHALL export physical cell bounds,
volumes, activity and flattening order, prevent implicit surface extrapolation,
and report topography, padding and mesh sensitivity separately.
Gate: tests/numerics/test_gravity_inverse.py::test_topography_active_mesh_and_padding

M02-08 WHEN L2 inversion is run, THE worker SHALL use official weighted data
misfit, physical-volume regularization and bounded projected optimization, with
tested objective factors, gradient, Hessian and independent small-problem optimum.
Gate: tests/numerics/test_gravity_inverse.py::test_objective_gradient_and_hessian
Gate: tests/numerics/test_gravity_inverse.py::test_l2_matches_bounded_reference

M02-09 WHEN IRLS is run, THE worker SHALL retain its L2 initialization and every
actual beta, norm, weight, epsilon and directive transition, guard zero thresholds
and distinguish fixed-subproblem convergence from changing-objective histories.
Gate: tests/numerics/test_gravity_inverse.py::test_irls_weights_objectives_and_epsilon

M02-10 WHEN parameters are selected, THE worker SHALL use only buffered spatial
training folds and preserve grouped acquisition identity; outer-test values and
synthetic truth SHALL NOT select priors, beta, mesh, bounds or stopping.
Gate: tests/numerics/test_gravity_inverse_selection.py::test_buffered_groups_are_disjoint
Gate: tests/numerics/test_gravity_inverse_selection.py::test_test_data_cannot_choose_regularization

M02-11 WHEN L2 and IRLS are compared, THE worker SHALL use matched admitted
observations, partition/covariance, mesh, bounds, candidates and resource policy;
it SHALL retain all failures, and label an all-data refit as unvalidated by holdout.
Gate: tests/numerics/test_gravity_inverse_selection.py::test_matched_l2_irls_inputs_and_budgets

M02-12 IF optimization is cancelled, capped, inconsistent or nonconverged, THEN
THE worker SHALL return that literal terminal reason, preserve partial evidence
and never label a resource/iteration stop as successful recovery.
Gate: tests/numerics/test_gravity_inverse.py::test_stopping_and_state_identity

M02-13 WHEN uncertainty or resolution is displayed, THE worker SHALL identify
conditioning assumptions, use actual perturbed-data refits for bootstrap results
and demonstrate nonuniqueness without claiming unique field density or posterior coverage.
Gate: tests/numerics/test_gravity_inverse_selection.py::test_conditional_bootstrap_is_actual_refits
Gate: tests/numerics/test_gravity_inverse.py::test_null_negative_and_nonuniqueness

M02-14 WHEN a result is exported, THE bundle SHALL retain admitted observations,
prediction/residual maps, 3D density, station partitions, optimizer state, physics
source/environment hashes and replayable immutable lineage with independent checks.
Gate: tests/data/test_gravity_inverse_bundle.py::test_roundtrip_independent_physics
Gate: tests/data/test_gravity_inverse_bundle.py::test_tamper_source_units_masks_and_model

M02-15 WHEN local outputs are published, THE worker SHALL preserve private raw
rights, reject existing destinations, and avoid canonical writes or cache reuse
without source/configuration identity checks.
Gate: tests/data/test_gravity_inverse_bundle.py::test_no_overwrite_and_private_raw_rights

M02-16 BEFORE solving, THE worker SHALL enforce explicit RAM, scratch, station,
cell, thread and wall-time limits; it SHALL measure the proposed local CPU lane
and not claim GPU or public-host admission from another method's receipts.
Gate: tests/numerics/test_gravity_inverse_resources.py::test_preflight_limits_cancel_and_cleanup
Gate: tests/numerics/test_gravity_inverse_resources.py::test_measured_local_envelope

M02-17 WHEN method quality is accepted, THE reviewer SHALL verify the locked
independent synthetic matrix, matched heldouts and every negative condition,
without weakening thresholds or substituting training controls for evaluation.
Gate: tests/numerics/test_gravity_inverse.py::test_prism_oracle_and_heldout

M02-18 IF field bytes lack required metadata, THEN THE worker SHALL preserve
modelling-ineligible status; full M02 field acceptance SHALL require a separately
admitted measured survey and reproducible holdout/alternative-model evidence.
Gate: tests/numerics/test_gravity_inverse_field.py::test_ineligible_bartlett_metadata
Gate: tests/numerics/test_gravity_inverse_field.py::test_field_holdout_and_alternative_models

M02-19 THE local method documentation SHALL describe equations, exact upload
contract, other-data recipe, resource limits and scientific nonclaims; learned
training SHALL be typed not-applicable and regularization selection SHALL be explicit.
Gate: tests/numerics/test_gravity_inverse.py::test_local_recipe_and_limits

Each named gate is specified in [validation](validation.md); existence and
execution are future tasks, not present passing evidence. Ownership and release
boundaries are explicit in [design](design.md) and [tasks](tasks.md).
