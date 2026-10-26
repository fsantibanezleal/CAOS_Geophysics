# M04 survey inversion requirements

Status: planned

These are literal EARS requirements for the full continuation, not an acceptance
record. Ordinary input/geometry foundation paths are implemented; numerical and
full-generation/integration paths remain planned. The planned status remains
until the complete continuation converges, not merely its foundation. Frozen details
and all error semantics are in [contracts](contracts.md) and [algorithms](algorithms.md).

R-401 THE magnetic survey reader SHALL reject excess bytes, tokens, depth,
duplicate keys, nonfinite numbers and closed-schema violations before NumPy or
engine allocation/import.
Implementation: data-pipeline/magnetic_survey_json.py.
Gate: tests/data/test_magnetic_survey_json.py::test_preallocation_closed_protocol.

R-402 WHEN survey metadata is admitted, THE planner SHALL preserve every original
row and its identity, declared geometry, QC reason and grouping without thinning.
Implementation: data-pipeline/magnetic_survey.py.
Gate: tests/data/test_magnetic_survey.py::test_original_inventory_and_masks.

R-403 IF quantity, frame, datum, units, uniform field or correction lineage is
ineligible, THEN THE survey SHALL reject modelling with a typed reason without
inventing missing metadata.
Implementation: data-pipeline/magnetic_survey.py.
Gate: tests/data/test_magnetic_survey.py::test_physical_eligibility_and_rights.

R-404 WHEN geometry is sealed, THE planner SHALL create the exact group/block
union, deterministic outer/inner memberships and unchanged exclusion buffers
before loading observations or uncertainties.
Implementation: data-pipeline/magnetic_survey.py.
Gate: tests/data/test_magnetic_survey.py::test_sealed_geometry_and_value_independence.

R-405 THE calibrator SHALL fit only declared secondary ENU, linear TMI or exact
total-field anomaly using the actual physical component kernel and its matching
unit-SI Jacobian.
Implementation: data-pipeline/magnetic_inverse.py.
Gate: tests/numerics/test_magnetic_inverse.py::test_quantity_specific_physics_and_jacobian.

R-406 WHERE full covariance is provided, THE calibrator SHALL use principal
partition covariances, full whitening and full weighted sensitivity norms without
diagonal substitution, nugget or inferred errors.
Implementation: data-pipeline/magnetic_inverse.py.
Gate: tests/numerics/test_magnetic_inverse.py::test_full_covariance_whitening.

R-407 THE inverse SHALL use a separately accepted M02 optimizer binding with
unchanged convergence/certification semantics and no private gravity constructor
or local substitute.
Implementation: data-pipeline/magnetic_optimizer_adapter.py.
Gate: tests/numerics/test_magnetic_inverse.py::test_accepted_optimizer_binding.

R-408 WHEN an L2 model is fitted, THE inverse SHALL record physical chi bounds,
q scaling, start/reference, volume-normalized SimPEG regularization, dimensionless
beta and independently recomputable objective, gradient and KKT diagnostics.
Implementation: data-pipeline/magnetic_inverse.py.
Gate: tests/numerics/test_magnetic_inverse.py::test_l2_bvls_and_physical_objective.

R-409 WHEN sparse fitting is selected, THE inverse SHALL execute actual SimPEG
Sparse weights with the frozen positive threshold schedule, fixed beta per
candidate and independent final fixed-objective stationarity checks.
Implementation: data-pipeline/magnetic_inverse.py.
Gate: tests/numerics/test_magnetic_inverse.py::test_irls_null_weights_and_stationarity.

R-410 WHILE tuning a candidate, THE calibrator SHALL expose only its fitting
observations and score it on predetermined validation rows without sealed values,
truth or masks derived from signal amplitude.
Implementation: data-pipeline/magnetic_inverse.py.
Gate: tests/numerics/test_magnetic_inverse.py::test_nested_selection_no_leakage.

R-411 WHEN candidate selection is complete, THE evaluator SHALL predict original
eligible rows, retain observed-minus-predicted residuals and evaluate the sealed
partition exactly once without retuning.
Implementation: data-pipeline/magnetic_inverse.py.
Gate: tests/numerics/test_magnetic_inverse.py::test_sealed_prediction_and_metrics.

R-412 THE synthetic validation SHALL distinguish recorded acquisition controls
from field observations and use independent off-grid Choclo truth, remanent,
wrong-field, null, resolution and coverage negatives.
Implementation: tests/fixtures/magnetic_survey/generate.py.
Gate: tests/numerics/test_magnetic_inverse.py::test_independent_case_matrix.

R-413 IF any allocation, convergence, resource or numerical guard fails, THEN THE
workflow SHALL preserve a non-success result and shall not change bounds,
buffers, meshes, thresholds or data counts.
Implementation: data-pipeline/magnetic_inverse.py.
Gate: tests/numerics/test_magnetic_inverse.py::test_caps_and_no_fallback.

R-414 WHEN a local user runs the tool, THE workflow SHALL execute on the supplied
bytes and persist reproducible configuration, model, predictions, residuals,
history and hashes without provider downloads.
Implementation: data-pipeline/run_magnetic_survey.py.
Gate: tests/data/test_magnetic_survey_cli.py::test_actual_user_bytes_and_reproduction.

R-415 WHEN a result is exported or re-imported, THE bundle SHALL preserve all
original inventory, rights, units, masks, partitions, arrays and hashes, use
bounded safe members and never publish a partial generation as successful.
Implementation: data-pipeline/magnetic_survey_bundle.py.
Gate: tests/data/test_magnetic_survey_bundle.py::test_roundtrip_and_interrupted_generation.

R-416 WHILE online admission is unaccepted, THE server SHALL expose eligibility
and local/replay recipes without executing an online inverse or labelling replay
as computation.
Integration: api magnetic method adapter, using existing jobs and ownership.
Gate: tests/api/test_magnetic_survey.py::test_owner_job_boundary_and_online_closed.

R-417 WHEN an accepted magnetic result is selected, THE workbench SHALL link
map, original line samples, observed/predicted/residual, chi volume/slices,
coverage, objective history and applicable residual spectrum by original IDs.
Integration: frontend magnetic result adapter using the shared shell.
Gate: frontend/e2e/magnetic-survey.spec.ts::linked_physical_views.

R-418 THE magnetic wiki and course SHALL explain actual L2/IRLS algorithms,
source eligibility, worked local tools, negatives and limitations in EN/ES
with real citations, shared fonts/tokens and both-theme figures.
Integration: docs/methods/magnetic-survey and existing course content modules.
Gate: scripts/check_magnetic_docs.py::main and frontend/e2e/magnetic-course.spec.ts.

R-419 THE field evaluation SHALL retain source-rights, metadata, full-survey
coverage and independently withheld predictive gates without fabricated geology.
Integration: existing catalogue/case matrix.
Gate: tests/data/test_magnetic_field_cases.py::test_full_source_eligibility_and_holdout.

R-420 WHEN convergence is reported, THE method SHALL enumerate all gates
including unresolved optimizer, field, native containment, durability and UI
requirements without promoting a forward pass into full method acceptance.
Integration: existing convergence guard, no new score.
Gate: scripts/check_magnetic_method_matrix.py::main.
