# Ordinary submitted-survey L2 requirements

Status: planned. MAIN complete sub-SDD read and explicit code/test authority
pending. All gates below are prospective and NOT RUN; no new named test exists.
This does not close the [parent's 19 requirements](../m02-survey-inversion/requirements.md).
[Typed protocol](contract.md), [design](design.md), [controls](validation.md).

L2-01 THE local unit SHALL reject nonexact types/hooks/unknown keys, enforce
all metadata/count/storage caps before scans/copies/digests/engines and preserve
input arrays and original row identity.
Gate: tests/data/test_gravity_survey_l2.py::test_metadata_first_exact_contract

L2-02 WHEN normalized observations are admitted, THE unit SHALL bind original
source/rights/processing declarations, common metric frame and physical quantities,
reject ambiguous correction/unit/datum inputs and never infer field eligibility.
Gate: tests/data/test_gravity_survey_l2.py::test_source_frame_sign_and_processing

L2-03 IF masks, unknown geometry or duplicate identities violate the ordinary
contract, THEN THE unit SHALL retain exclusions/reasons upstream or reject, never
impute zeros/NaN scores or silently deduplicate observations.
Gate: tests/data/test_gravity_survey_l2.py::test_masks_missingness_duplicates_and_order

L2-04 THE inverse SHALL use the unchanged accepted source-bound float64 Geoana
operator, physical density/Jacobian units and actual verified geometry, without
changing its local geometry-fidelity or frozen prediction tolerances.
Gate: tests/numerics/test_gravity_l2.py::test_real_engine_forward_and_geometry_identity

L2-05 WHEN positive SD or SPD covariance is supplied, THE unit SHALL use the
declared noise units/assumptions, symmetric precision whitening compatible with
the pinned Hessian and independent marginal partition scoring, with no guessed SD.
Gate: tests/numerics/test_gravity_l2.py::test_covariance_whitening_hessian_and_marginals

L2-06 THE unit SHALL use official unhalved L2DataMisfit and explicitly normalized
physical-volume smallness/first-derivative WeightedLeastSquares, with factor-two
gradient/Hessian and density chain independently verified.
Gate: tests/numerics/test_gravity_l2.py::test_objective_regularization_and_physical_derivatives

L2-07 WHEN finite signed density bounds/start/reference are supplied, THE unit
SHALL preserve their physical units and official bounded optimizer optimum,
without implicit positivity, bound clipping of caller input or fallback solver.
Gate: tests/numerics/test_gravity_l2.py::test_bounded_l2_independent_bvls_and_kkt

L2-08 BEFORE values are delivered, THE planner SHALL allocate deterministic
group/block/seed/buffer partitions, reject infeasible count/coverage and expose
compact development rows separate from sealed outer observations.
Gate: tests/numerics/test_gravity_l2_selection.py::test_frozen_geometry_blocks_groups_buffers

L2-09 WHEN candidates are evaluated, THE calibration SHALL retain every fold
outcome, use the exact beta grid/effective scaling/tie rule, select only complete
converged candidates and retain a failed selected refit without substitution.
Gate: tests/numerics/test_gravity_l2_selection.py::test_exact_candidates_scores_failures_and_refit

L2-10 WHILE calibration runs, THE unit SHALL remain invariant to absent/poisoned
outer values, errors and truth; each fold's fit SHALL not use its validation values,
and final evaluation SHALL perform no optimization or all-data refit.
Gate: tests/numerics/test_gravity_l2_selection.py::test_sealed_outer_and_inner_value_leakage

L2-11 WHEN optimization stops, THE unit SHALL map the pinned official API to
the declared KKT/change/null policy, preserve exact accepted/terminal states and
distinguish convergence from line-search/CG/stall/iteration/wall failures.
Gate: tests/numerics/test_gravity_l2.py::test_pinned_stopping_null_and_terminal_state

L2-12 WHEN rank/sensitivity/resolution is reported, THE unit SHALL retain
underdetermination/zero columns/coverage/conditional-noise diagnostics and actual
nonuniqueness controls without implying density confidence or geological truth.
Gate: tests/numerics/test_gravity_l2.py::test_rank_coverage_nullspace_and_nonclaims

L2-13 THE local unit SHALL bind exact output/model/prediction/residual/config
identities and report unavailable metrics as None, with tamper rejection and
independent physics replay rather than fabricated producer/source fingerprints.
Gate: tests/data/test_gravity_survey_l2.py::test_native_result_identity_and_tamper

L2-14 IF a request exceeds the frozen local projected resource budget or stops
under time caps, THEN THE unit SHALL reject or retain nonconvergence without silent
coarsening; CPU/GPU/host operational acceptance SHALL require separate measurements.
Gate: tests/numerics/test_gravity_l2_selection.py::test_preflight_caps_and_measured_local_envelope

L2-15 THE unit SHALL have no application I/O/public callbacks/API/environment
mutation, use actual loaded versions plus external trusted-source verification
and preserve all parent source/artifact/history bytes.
Gate: tests/numerics/test_gravity_l2.py::test_no_io_hooks_runtime_or_legacy_mutation

L2-16 WHEN ordinary inverse quality is reviewed, THE reviewer SHALL retain the
complete predeclared control matrix, all negative/noise/geometry/model outcomes
and untouched sealed scores, never relax thresholds or treat synthetic truth as field.
Gate: tests/numerics/test_gravity_l2_selection.py::test_complete_locked_l2_control_matrix

Each requirement's numerical or data gate is named in validation but absent.
Documentation/source inspection checks establish reviewability, NOT numerical
implementation, field admission, IRLS, API, GPU, host or full-M02 acceptance.
