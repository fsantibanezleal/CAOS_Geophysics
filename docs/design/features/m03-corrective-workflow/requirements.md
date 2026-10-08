# M03 corrective workflow requirements

Status: reviewed prospective contract, 2026-10-08; gates remain prospective.
Product baseline `a5cbe702cc9c9fb851d64355d38f6b8bd1d0c303`. Approved separate v2
96-candidate/97-mandatory/98-maximum fits and typed grid-axis/microlevel-transfer
corrections do not change the original v1 policy or retained controls. Existing
v1 completion continues independently. Technical review findings must be closed
before new value access; approval does not establish a test or scientific PASS.

R-C01 THE diagnosis SHALL independently test metric distance, units, translation
and homogeneous rescaling on the retained ORIGINAL training geometry without
new outer evaluation, truth access or production parameter selection.
Gate: tests/data/test_magnetic_line_survey_forensics.py::test_original_training_units_geometry_and_constant

R-C02 THE pipeline SHALL retain the original fixed-basis S1 and both opened
refinement predictive failures, their immutable source bytes and thresholds.
Gate: tests/data/test_magnetic_line_survey_forensics.py::test_no_predictive_upgrade_or_outer_read

R-C03 WHERE reviewed representation selection is enabled, THE pipeline SHALL
seal the complete width/depth/damping matrix before values, select using three
inner folds only, and evaluate a fresh unopened acquisition's whole-line outer
partition once. Already opened originals are labelled diagnostic attempts and
never become an untouched predictive holdout by rerunning a new basis.
Gate: tests/data/test_magnetic_line_survey_resolution.py::test_training_only_selection_and_all_candidates

R-C04 WHEN physical corrections are requested, THE pipeline SHALL bind exact
original auxiliary bytes, canonical records, row/time identities, clock, datum,
reference epochs and DAG edges without guessed physical metadata.
Gate: tests/data/test_magnetic_line_survey_corrections.py::test_complete_original_s3_correction_edges

R-C05 THE full workflow SHALL emit and independently verify a semantic
SurveyResult, every source row/disposition, global fit, masks, grid, requested
transforms, rights-specific export and replay from permitted originals.
Gate: tests/data/test_magnetic_line_survey_workflow.py::test_full_result_export_replay_not_diagnostic

R-C06 IF source rights, physical metadata, calibration, predictive or resource
gates fail, THEN THE workflow SHALL retain the factual adverse evidence without
subsampling, fabricated arrays, successful partial result or tolerance change.
Gate: tests/data/test_magnetic_line_survey_workflow.py::test_actual_negative_controls_and_missing_original

R-C07 WHEN an owner starts a survey, THE owner adapter SHALL resolve immutable
owner asset UUID/hash references, execute the real full worker, persist lifecycle
and authorize result/member/export/cancel/deletion on the same project.
Gate: tests/api/test_magnetic_line_survey_workflow.py::test_real_owned_job_lifecycle_and_cross_owner

R-C08 THE client instrument SHALL display source-bound linked line/grid/crossover/
validation views, actual lifecycle and scientific limits in EN/ES and both themes
using the existing shell, without modifying the shared Workbench.
Gate: frontend/src/features/magneticLineSurvey/SurveyInstrument.test.tsx::source_bound_workflow
Gate: scripts/check_magnetic_line_survey_browser.py

R-C09 THE provider intake SHALL use the existing reviewed catalogue/allowlist,
exact official object links and rights, external device data/temp roots, and
immutable actual byte/hash receipts, never claim metadata or grids are lines.
Gate: tests/data/test_magnetic_line_survey_provider.py::test_reviewed_provider_original_and_no_grid_substitute

Every named gate above is prospective, not a test-pass claim. The original
8201-row field source is still not verified; an authored resource/control CSV is
not that source. Local execution, owner integration and host activation are
distinct milestones. MAIN alone owns public activation.
