# M11 joint-survey inversion requirements

These requirements refine M11 and parent requirements R-002, R-003, R-004,
R-008, R-009 and R-011. They do not amend a parent verdict. Each named gate is
an executable local test; a passing component test does not establish full M11,
field or release acceptance. The current scoped status and source-bound receipt
are recorded in [integration status](integration-status-20261025.md) and
[the M11 receipt](evidence/m11-final-precision-20261025.json).

| ID | Requirement | Gate |
| --- | --- | --- |
| JS-001 | WHEN a joint survey request is admitted, THE planner SHALL enforce exact native keys, types, units, frame and source-rights declarations without arbitrary hooks or inferred values. | `tests/numerics/test_joint_survey_plan.py::test_exact_contract` |
| JS-002 | BEFORE scanning, copying, hashing or invoking an engine, THE planner SHALL check all shapes, metadata, byte caps, empty containers and logical aliases. | `tests/numerics/test_joint_survey_plan.py::test_preallocation_rejection` |
| JS-003 | WHEN building mesh and receiver geometry, THE planner SHALL preserve nonuniform x-fast cell order, faithful bounds and volumes, and the declared closed-box outside policy. | `tests/numerics/test_joint_survey_plan.py::test_geometry_and_order` |
| JS-004 | WHEN partitioning survey observations, THE planner SHALL preserve explicit masks and reasons and enforce global acquisition-block train/validation/sealed separation. | `tests/numerics/test_joint_survey_plan.py::test_global_blocks_and_masks` |
| JS-005 | WHEN binding input sources, THE planner SHALL preserve distinct source records and immutable byte-bound snapshots without claiming verification it did not perform. | `tests/numerics/test_joint_survey_plan.py::test_source_and_snapshot` |
| JS-006 | WHEN evaluating potential-field operators, THE method SHALL compare gravity and magnetic predictions with independent Choclo, volume, sign and unit controls. | `tests/numerics/test_joint_survey_oracles.py::test_prism_oracles` |
| JS-007 | WHEN computing cross-gradient coupling, THE method SHALL validate face-averaged values, gradients and exact Hessian-vector products against independent assembly, autograd and finite differences; it SHALL test the PSD approximation separately. | `tests/numerics/test_joint_survey_oracles.py::test_cross_gradient_derivatives` |
| JS-008 | WHEN forming the joint objective, THE method SHALL apply independent diagonal/SPD marginal whitening, physical scale transformations and the declared pairwise regularizer. | `tests/numerics/test_joint_survey_objective.py::test_objective_chain` |
| JS-009 | WHEN comparing joint and uncoupled models, THE optimizer SHALL independently solve both baselines and compare a bounded same-input tiny case with a BVLS oracle. | `tests/numerics/test_joint_survey_optimizer.py::test_all_actual_fits_and_stationary_separate_baselines` |
| JS-010 | WHEN solving within physical bounds, THE optimizer SHALL validate bound starts/releases, ordinary CG, line search, KKT and finite-state controls and retain truthful failure traces. | `tests/numerics/test_joint_survey_inverse.py::test_actual_physical_bound_paths` |
| JS-011 | WHEN selecting candidates and regularization, THE workflow SHALL freeze candidate, beta and start choices using development data only, without reading sealed values or truth or refitting on them. | `tests/numerics/test_joint_survey_inverse.py::test_sealed_selection_and_changed_development_actual_fits` |
| JS-012 | WHEN evaluating the case matrix, THE workflow SHALL retain co-structural, disjoint, null, undercoverage, remanence and wrong-frame outcomes, including all failures. | `tests/numerics/test_joint_survey_cases.py::test_refined_matrix_original_identity_and_no_production_generator` |
| JS-013 | WHEN running within declared resource limits, THE workflow SHALL measure actual caps, deadline, scratch and attributable CPU/GPU lane behavior rather than infer total memory from operator bytes. | `tests/numerics/test_joint_survey_resources.py::test_actual_rss_and_scratch_receipt` |
| JS-014 | WHEN importing or exporting serialized results, THE pipeline SHALL enforce exact local intake, exclusive publication, rights/source/shape/hash checks, replay and stale-source rejection. | `tests/numerics/test_joint_survey_optimizer.py::test_calibration_exclusive_export_and_frozen_replay` |
| JS-015 | WHEN the local M11 pipeline is invoked, THE named CLI SHALL execute the nonlearned workflow on real files and changed scientific input SHALL change the computed result. | `tests/numerics/test_joint_survey_optimizer.py::test_full_cli_evaluate_and_validate_real_files` |
| JS-016 | WHEN publishing method summaries, THE evaluator SHALL bind method, source and model interpretation and preserve provisional/nonclaim flags that agree with the receipts. | `tests/numerics/test_joint_survey_evaluation.py::test_actual_marginal_metrics_and_result_roundtrip` |

## Acceptance boundary

The gates above are local implementation checks, not a claim that the complete
matrix has passed or that the science is accepted. Parent M11 verdict, field
eligibility, GPU parity, host capacity and product release remain separate
acceptance decisions. The case matrix must retain nonconvergence, ineligibility,
unresolved and poor-fit outcomes; a zero CLI exit establishes workflow execution
only.
