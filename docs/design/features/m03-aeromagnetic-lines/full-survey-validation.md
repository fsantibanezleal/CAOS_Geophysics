# Streamed M03 requirements and verification

Revision1. Prospective named tests below do not claim an executed result.
Read [contract](full-survey-contracts.md), [algorithm](full-survey-algorithms.md)
and the retained [scientific failures](representation-refinement-diagnosis.md).
These requirements extend the complete M03 local workflow, not replace it with
a small operator example. Old source/results/seals/thresholds stay immutable.

## Requirements with exact gates

Tests are new tests/data/test_magnetic_line_survey.py (D) and
tests/numerics/test_magnetic_line_survey.py (N). None edits M04 tests or the
ordinary M03 modules. Ordinary tests continue under their original names.

| ID | EARS requirement | Named gate |
| --- | --- | --- |
| MS01 | THE streamed intake SHALL retain original bytes and every source-order row under the closed schema. | D::test_closed_input_and_original_identity; D::test_source_order_chunk_custody |
| MS02 | IF an actual read, record, token, node/depth or duplicate bound fails, THEN intake SHALL refuse before allocation/numerical import. | D::test_max_plus_one_and_scan_before_materialize |
| MS03 | IF units, correction state, clock, datum, reference or rights are ambiguous, THEN numerical eligibility SHALL stay closed. | D::test_physical_vs_structural_eligibility; N::test_unknown_reference_and_double_correction |
| MS04 | WHEN geometry is sealed, THE split/source/scale/crossover construction SHALL use no validation/outer observations. | D::test_geometry_seal_precedes_value_access; N::test_outer_perturbation_no_training_change |
| MS05 | THE operator SHALL include every eligible training row/source in a single global scaled Ridge objective. | N::test_global_dense_augmented_oracle; N::test_chunk_order_and_sizes; N::test_adjoint_dot_oracle |
| MS06 | WHERE inverse-variance weights are included, THE fit SHALL use only admitted independent SDs, no row/weight normalization. | N::test_raw_weight_lambda_scaling; N::test_unknown_sigma_refused |
| MS07 | IF LSMR is unconverged or independent regularized stationarity fails, THEN fit SHALL refuse even for finite predictions. | N::test_lsmr_stop_and_stationarity; N::test_corrupt_coefficient_and_wrong_damp_refused |
| MS08 | THE capacity planner SHALL count LSMR full vectors, block temporaries, mapped pages and stage lifetimes before native work. | D::test_phase_allocation_capacity; D::test_no_dense_global_or_hidden_tiles |
| MS09 | WHEN correction/leveling is requested, THE DAG SHALL preserve signed history and independent fold calibration. | N::test_full_dag_and_global_crossover_components; N::test_empty_fold_calibration_retained |
| MS10 | THE workflow SHALL execute original S2..S6 and retain original S1/new100/50 failures separately. | D::test_old_source_and_failure_pins; N::test_original_negative_regimes_unchanged |
| MS11 | WHEN transforms are requested, THE workflow SHALL preserve support/gaps, source-free planes and complete-spectrum qualification. | N::test_higher_plane_and_fft_oracles; N::test_downward_gap_alias_refusals |
| MS12 | THE exporter SHALL enforce fresh-directory custody and rights for every data-bearing member. | D::test_immutable_export_replay; D::test_denied_raw_location_and_auxiliary |
| MS13 | WHEN a full-study shape is proposed, THE controller SHALL prove actual cold lifetime/cancel limits before new values. | D::test_actual_geometry_resource_and_cancel; D::test_counter_failure_refuses |
| MS14 | WHEN provider data are used, THE workflow SHALL verify actual original attachments, dictionary, datum/error/reference and numeric comparator. | D::test_provider_source_gate; N::test_full_provider_blocked_comparison |
| MS15 | THE local user-file/GUI workflow SHALL distinguish structural inspection, local computation, replay and online CLOSED state. | D::test_paired_user_file_recipe; frontend/e2e/magnetic-line-instrument.spec.ts::source_bound_linked_views |

## Frozen independent controls

Dense oracle is independent broadcast/math1/r + SciPy augmented QR/SVD, not
Harmonica/Verde internal least-squares. Use a noncentral tilted XY/heterogeneous
height survey, explicit negative/positive source blocks, nonuniform admitted
SDs and nonzero values of both signs. At least six small geometries have different
source depth/row aspect/support configurations, each2..128rows/1..32sources,
one fixed test definition before generation. Dense work is never a full-survey
execution. Real Harmonica block actions must be invoked and compared; mocking
the engine is permitted only for pre-native refusal negatives.

All scales derive from training alone and are unweighted population SDs.
Compare unweighted and inverse-variance objectives, multiplication of W and
lambda by the same positive constant, and the wrong sqrt-lambda negative.
Use the exact thresholds in algorithms: no relaxation after seeing a failure.
Adjoint/chunk-order tests include partial final blocks, varied source and row
chunk sizes below their maximum, and interleaved original line IDs; no reordered
output identity. A test that merely passes the same action through both sides
is not an independent oracle. Numerically rank-deficient/nearconstant columns,
wrong dtype, bool shapes, huge coordinates losing separation, collision with
source position, nonfinite/high-noise/unknown-SD inputs and foreign module pins
must be represented. High noise is not automatically malformed: retain high
heldout errors and do not call a converged noisy result predictive PASS.

Actual SciPy stop-code controls cover zero b, nonzero orthogonal b, successful
regularized solve and forced iteration/condition refusals. Independently altered
returned coefficients and falsely successful stop metadata must fail gradient
checks. The documented coefficient error bound is checked against a small
dense reference, never advertised as field uncertainty. Instrument uncertainty
and numerical solver tolerance remain different domains.

## Evidence sequence and kill criteria

1. Commit this closed schema/capacity/tolerance definition before new numerical
   code and value access. Named tests first: preserve genuine missing-symbol or
   failing-contract red receipts, then green at exact executed source pin.
2. Implement strict streaming/custody/index planning, geometry-only full seal,
   capacities and no-dense preallocation tests. Never open new study values to
   estimate a capacity or choose a source width. No scope-changing adapter or
   unknown external format automatically qualifies.
3. Implement pinned Harmonica block LinearOperator/LSMR and independent dense,
   adjoint, chunk/scaling/stationarity controls. The source/source-count/operator
   contract and exact timings precede whole-study values. Zero/native-workload
   resource/cancel probes use actual cold processes/counters, not supplied JSON.
4. Complete immutable DAG/global crossings/leveling and original S2..S6,
   transforms/support/spectrum, paired scripts/export/replay. Keep old S1 and
   original two opened studies with their existing source/17 original receipts.
   New larger operator results never retrospectively relabel those attempts.
5. Run prospectively sealed distinct useful-survey controls and eligible
   rights-reviewed real user/provider files through the full pipeline. Keep
   timing, raw byte/source pins, all failures, scored/excluded/coverage/per-line
   metrics and quantitative comparator definition. No synthetic substitution
   for field gate or use of already opened outer values as a fresh holdout.
6. Verify linked GUI/rendered readouts/ENES/themes/keyboard/phone at actual
   integrated source and arrays. Preview/test presence is not GUI acceptance.
   Native-host/persistence/security/admission have separate integration owners.

Every measured run records actual command, original input/source/runtime/native
identity, strict result/custody and original unmodified test/resource evidence.
Source-byte hashes are distinct from canonical typed hashes; generated timestamps
are not deterministic scientific identity. Original receipts remain historic,
not updated to a current origin. Device-local proof and unmeasured full-cap
limits stay explicitly separate. A failed counter or cancellation refusal cannot
be recast as zero usage, and iteration/CPU exhaustion never becomes convergence.

Implementation seam: new ordinary data-pipeline/magnetic_line_survey.py and
new D/N test files above; paired existing user scripts need an explicit schema
dispatch extension only after the new schema passes. No M04 magnetic_survey
files, old science modules, old caps/Results, shared API/storage/frontend routes,
environment installs or deployment mutation. Full field bytes/dictionary,
independent evaluated reference, error/datum, useful full-run resources,
source-bound GUI and host admission remain open until actual evidence.
