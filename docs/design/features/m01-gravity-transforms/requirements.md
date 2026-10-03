# M01 local transform requirements

Status: local gates passed; integration/field/online acceptance open. Authorized continuation of approved M01, 2026-10-03; no product-scope amendment.

R-T01 WHEN a transform input is admitted, THE processor SHALL verify the replayable corrected state, source/unit/datum/component/error/metric geometry contract and preserve the original result and masks unchanged. Gate: tests/numerics/test_gravity_transforms.py::test_contract_lineage_and_originals

R-T01a THE processor SHALL validate the entire exact-key deterministic processing receipt, including a reconstructed earlier input hash, without requiring patch-equal recorded Python or falsely authenticating its origin. Bounded canonical known-stage resumes SHALL be verified; other input identities SHALL reject explicitly. Gates: tests/numerics/test_gravity_transforms.py::test_full_processing_identity, tests/numerics/test_gravity_transforms.py::test_reconstructable_resume_and_python_provenance

R-T02 THE processor SHALL call pinned Harmonica EquivalentSources and validate its physical kernel and upward predictions against independent volume-prism controls on varied noncentral surveys. Gate: tests/numerics/test_gravity_transforms.py::test_independent_prism_and_continuation

R-T03 WHEN parameters are compared, THE processor SHALL freeze spatial outer holdout and inner training-only blocks and select without using outer-heldout values. Gate: tests/numerics/test_gravity_transforms.py::test_blocked_selection_no_holdout_leakage

R-T04 WHEN grids and errors are exported, THE processor SHALL retain training-only hull/distance masks, height/depth/damping comparisons, coverage, condition and conditional covariance propagation without extrapolation or geological confidence claims. Gate: tests/numerics/test_gravity_transforms.py::test_masks_condition_and_covariance

R-T05 IF units, component, datum, geometry, error, state, resource or upward-continuation requirements fail, THEN THE processor SHALL reject explicitly without changing input or publishing a successful result. Gate: tests/numerics/test_gravity_transforms.py::test_strong_negative_controls

R-T05a THE CLI SHALL cap actual bytes read, JSON nesting and numeric/encoding validity before invoking the processor, including growing-file/duplicate-key/nonfinite/overflow inputs. Gate: tests/numerics/test_gravity_transforms.py::test_bounded_strict_request_reader

R-T06 THE result SHALL distinguish nonunique equivalent coefficients from physical geology and preserve alternative training fits. Gate: tests/numerics/test_gravity_transforms.py::test_nonuniqueness_is_not_density

R-T07 WHEN a local bundle is exported, THE recipient SHALL obtain replayable request/result/model/axis/mask/diagnostic figures and hash receipts, with paired scripts and overwrite rejection. Gate: tests/numerics/test_gravity_transforms.py::test_export_and_paired_scripts

R-T08 THE wiki SHALL provide source-linked theory, limits, other-data workflow, worked controls, exercises and a theme-aware diagram with honest open field gates. Gate: tests/numerics/test_gravity_transforms.py::test_theory_and_svg
