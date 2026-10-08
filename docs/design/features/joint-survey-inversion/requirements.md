# M11 requirements and named gates

Requirements refine M11/R-008, R-002/003/004/009/011; none changes a parent
verdict. Initial filenames are prospective, not evidence of execution.

| ID | Required behavior | Paired gate under tests/numerics/ |
|---|---|---|
| JS01 | Exact native keys/types/units/frame/source rights; no hooks or guessing | test_joint_survey_plan.py::test_exact_contract |
| JS02 | All shapes/metadata/bytes/caps before scan/copy/hash/engine, including empty containers/aliases | test_joint_survey_plan.py::test_preallocation_rejection |
| JS03 | Actual nonuniform x-fast geometry, faithful bounds/volume, closed-box outside policy | test_joint_survey_plan.py::test_geometry_and_order |
| JS04 | Explicit masks/reasons, global acquisition-block train/val/sealed separation | test_joint_survey_plan.py::test_global_blocks_and_masks |
| JS05 | Distinct source records and immutable byte-bound snapshots, no fictitious verification | test_joint_survey_plan.py::test_source_and_snapshot |
| JS06 | Real public gravity/magnetic operators vs independent Choclo/volume/sign/unit columns | test_joint_survey_oracles.py::test_prism_oracles |
| JS07 | Actual face-averaged coupling/gradient/exact Hv vs independent assembly/autograd/FD; PSD approximation tested separately | test_joint_survey_oracles.py::test_cross_gradient_derivatives |
| JS08 | Independent diagonal/SPD marginal whitening, physical scale chain and pairwise regularizer | test_joint_survey_objective.py::test_objective_chain |
| JS09 | Two independently optimized baselines, same-input bounded BVLS tiny oracle | test_joint_survey_optimizer.py::test_all_actual_fits_and_stationary_separate_baselines; scripts/validate_joint_matrix.py::run_cell |
| JS10 | Bound-start/release/ordinary-CG/line-search/KKT/finite controls and truthful failure traces | test_joint_survey_inverse.py::test_actual_physical_bound_paths; test_joint_survey_inverse.py::test_optimizer_controls_reject_forged_trace; test_physical_nonlinear_optimizer.py |
| JS11 | Candidate/beta/start freeze and validation selection; no sealed/truth read or refit | test_joint_survey_inverse.py::test_sealed_selection_and_changed_development_actual_fits; test_joint_survey_optimizer.py::test_adverse_abort_retains_genuine_states_without_reading_sealed |
| JS12 | Complete co-structural/disjoint/null/undercoverage/remanence/wrong-frame matrix; all failures retained | scripts/validate_joint_matrix.py::main; test_joint_survey_cases.py |
| JS13 | Actual cap/resource/deadline limits and attributable CPU/GPU lane | scripts/validate_joint_resources.py::main; test_joint_survey_resources.py |
| JS14 | Exact local serialized intake, exclusive export, rights/source/shape/hashes/replay and stale-source negatives | test_joint_survey_optimizer.py::test_calibration_exclusive_export_and_frozen_replay; test_joint_survey_optimizer.py::test_actual_replay_rejects_forged_pass; test_joint_survey_evaluation.py |
| JS15 | Full named nonlearned pipeline/CLI, changed scientific input changes actual results | test_joint_survey_optimizer.py::test_full_cli_evaluate_and_validate_real_files; test_joint_survey_optimizer.py::test_real_cli_entrypoint_evaluation_in_fresh_process; test_joint_survey_inverse.py::test_sealed_selection_and_changed_development_actual_fits |
| JS16 | Method/source/model interpretation and provisional/nonclaim flags match receipts | test_joint_survey_evaluation.py; test_joint_survey_optimizer.py::test_full_cli_evaluate_and_validate_real_files |

The parent's `test_joint.py::test_coupling_against_independent_baselines` is a
declared gate, not currently an implemented gate in this feature. JS09/JS12 are
its scoped prospective evidence. Updating parent convergence/release matrices
requires integration review and is outside this feature's write scope.

The current executable names replace prospective JS09..JS16 filenames only.
They do not amend any predicate, tolerance, case, cap or parent verdict. The
matrix records each original BVLS/prediction/model/objective/KKT predicate
separately; a zero CLI exit means complete workflow execution, not that every
scientific predicate passed. GPU remains unaccepted in this CPU-only epoch.
