# M02 validation protocol and gate ledger

Status: planned. No new numerical execution, field fit, training, resource
benchmark or API/UI acceptance exists for this feature. Every test below is a
future implementation gate; a skip/unavailable result cannot close a requirement.
Requirements: [requirements](requirements.md). Model/protocol: [design](design.md).
Research/source access: [dossier](../../../research/m02-survey-inversion-2026-10-03.md).

## Frozen proposed numerical policy

These thresholds are proposals for independent main review before implementation.
They do not alter existing physics/canonical/source gates. Failed experiments
retain bytes, command, source revision, config/seed, diagnostics and terminal
reason. No passing summary after relaxing a failed threshold or replacing a seed.

- Float64 Geoana versus direct Choclo prism acceleration, away from singular
  boundaries: rtol 1e-7, atol 1e-10 mGal. Test signed density, positive/negative
  coordinates, varied cell sizes and off-axis receivers; include a clear boundary
  domain policy rather than silently omit an engine failure.
- Exact unit/sign/linear scaling: rtol 1e-10, atol 1e-12 mGal. Verify density
  Jacobian factor 1/1000, not merely that two mislabeled outputs agree.
- Independent volume quadrature: at least three refinement levels at receivers
  separated from the body; convergence to relative 1e-5. Far-field point mass at
  distance >=100 body dimensions: relative 1e-3 and inverse-square ratio. Include
  analytic exterior sphere sign/amplitude, using independently declared SI G.
- Linear adjoint identity: relative 1e-10; objective/gradient directional tests
  across several perturbation sizes: relative 1e-6. Hessian-vector versus gradient
  difference: relative 1e-6 on well-conditioned small L2 problems. Verify the
  unhalved objective, factor two and bounded projected-gradient criterion.
- Covariance whitened identity and mask/permutation alignment: relative 1e-10;
  non-SPD, wrong-unit, unbound and oversized matrices reject. Independent scoring
  uses each partition's marginal covariance, with cross-partition dependence
  disclosed rather than eliminated by assertion.
- Tiny strictly convex bounded L2 reference: independent dense KKT or SciPy
  bounded reference, model/prediction relative 1e-5 and KKT residual <=1e-5.
  This is an optimizer oracle, not uniqueness of subsurface geology.
- Bundle independent forward physics: rtol 1e-9, atol 1e-10 mGal for serialized
  float64 arrays; check residual identity separately against validated stored
  prediction at the same tolerance. Source/config/unit/mesh/hash mismatch is a
  hard rejection, not a floating-point exception. Producer provenance stays exact.
- Default proposed stopping limits and projected-gradient/change criteria are
  defined in design. Match actual pinned API behavior before accepting code;
  save capped/nonconverged and line-search failures instead of declaring success.

## Requirements to exact planned tests

| Requirement | Planned test ID(s) | Required evidence / negative |
| --- | --- | --- |
| M02-01 | `tests/data/test_gravity_survey.py::test_correction_state_no_double_processing` | Immutable raw/parent hashes and rights; reject raw gravity, ambiguous CBA, double terrain/normal correction, broken M01 replay |
| M02-02 | `tests/data/test_gravity_survey.py::test_exact_units_sign_and_density_conversion` | mGal/SI/microGal, metres/two foot definitions, up/down and kg/m3/g/cc; reject absent units; original values reversible |
| M02-03 | `tests/data/test_gravity_survey.py::test_crs_datum_geometry_rejection` | Unknown vertical datum, geographic degrees, absent grids/surface, incompatible local axes and excessive projection error rejected |
| M02-04 | `tests/data/test_gravity_survey.py::test_masks_duplicates_and_station_order` | Stable ID/permutation roundtrip, excluded reasons/null prediction, masked values never zero fit data, repeat ambiguity rejected |
| M02-05 | `tests/data/test_gravity_survey.py::test_covariance_whitening_and_partition` | Known correlated noise, independent principal-block whitening, heldout values unavailable to fit; conservative bounds not SD |
| M02-06 | `tests/numerics/test_gravity_inverse.py::test_prism_sign_units_and_linearity`; `tests/numerics/test_gravity_inverse.py::test_volume_quadrature_and_far_field` | Actual engine called; separately implemented prism and physical limits pass proposed tolerances |
| M02-07 | `tests/numerics/test_gravity_inverse.py::test_topography_active_mesh_and_padding` | Air/active mapping, x-fast volume and cell bounds verified; uncovered topography rejected; refinement/padding outcomes retained |
| M02-08 | `tests/numerics/test_gravity_inverse.py::test_objective_gradient_and_hessian`; `tests/numerics/test_gravity_inverse.py::test_l2_matches_bounded_reference` | Weighted factor-two derivatives, bounded KKT, physical volume/ref/length weights and source/version pins |
| M02-09 | `tests/numerics/test_gravity_inverse.py::test_irls_weights_objectives_and_epsilon` | L2 initial state, actual stage weights/beta/epsilon, ordering, zero model floor and fixed-objective transitions replay |
| M02-10 | `tests/numerics/test_gravity_inverse_selection.py::test_buffered_groups_are_disjoint`; `tests/numerics/test_gravity_inverse_selection.py::test_test_data_cannot_choose_regularization` | Spatial groups/buffers disjoint; poison test values/permuted truth leave fit selection/model hashes unchanged |
| M02-11 | `tests/numerics/test_gravity_inverse_selection.py::test_matched_l2_irls_inputs_and_budgets` | Same frozen data/mesh/bounds/covariance and search cap; all candidates/failures stored; all-data refit separately labelled |
| M02-12 | `tests/numerics/test_gravity_inverse.py::test_stopping_and_state_identity` | Accepted model equals terminal exported state; max iterations/time, cancellation and nonconvergence remain literal negatives |
| M02-13 | `tests/numerics/test_gravity_inverse_selection.py::test_conditional_bootstrap_is_actual_refits`; `tests/numerics/test_gravity_inverse.py::test_null_negative_and_nonuniqueness` | Refits counted/hashed; conditioning/coverage nonclaims, near-null models and misleading sparse/diffuse cases retained |
| M02-14 | `tests/data/test_gravity_inverse_bundle.py::test_roundtrip_independent_physics`; `tests/data/test_gravity_inverse_bundle.py::test_tamper_source_units_masks_and_model` | Two independent replay checks, array/state seams and all tamper dimensions reject |
| M02-15 | `tests/data/test_gravity_inverse_bundle.py::test_no_overwrite_and_private_raw_rights` | Existing/empty destinations preserved, archive path rejection, private raw not mirrored, bounded caches source-bound |
| M02-16 | `tests/numerics/test_gravity_inverse_resources.py::test_preflight_limits_cancel_and_cleanup`; `tests/numerics/test_gravity_inverse_resources.py::test_measured_local_envelope` | Measured memory/scratch/time/headroom, conservative estimator, deterministic cancellation and isolated cleanup |
| M02-17 | `tests/numerics/test_gravity_inverse.py::test_prism_oracle_and_heldout` | Approved parent gate aggregates independent physics plus complete locked synthetic/holdout receipts, all method outcomes |
| M02-18 | `tests/numerics/test_gravity_inverse_field.py::test_ineligible_bartlett_metadata`; `tests/numerics/test_gravity_inverse_field.py::test_field_holdout_and_alternative_models` | Actual current source stays ineligible; distinct eligible measured field survey admission and conditional holdout/mesh/beta receipt required |
| M02-19 | `tests/numerics/test_gravity_inverse.py::test_local_recipe_and_limits` | Other-data guide, equations, contractual rejection examples, source licences, limits, no-training state and full-M02 nonclaims |

## Locked independent synthetic matrix

Propose eight families, six conditions, two inverse methods: **48 controls,
96 method outcomes**, plus independent forward/derivative oracles. Controls are
new local test evidence, not new canonical cases and not existing product scores.

Families: off-axis compact positive prism; signed bipolar bodies; diffuse body;
deep broad body; contrasting two depths with similar field; null anomaly;
known topography; two separated bodies with edge/padding challenge. Generate
observations with direct independent Choclo calls to continuous prisms whose
boundaries do not align with the inversion mesh; analytic sphere and quadrature
checks separately anchor physical amplitude. Never generate and recover the same
cell vector with the same sensitivity matrix and call that realistic recovery.

Conditions: nominal credible independent noise; known correlated noise;
station-gap/mask geometry; explicitly wrong height/sign/unit request (admission
negative); small domain/inadequate padding; gross outlier or regional-background
mismatch. Freeze immutable generation seeds, SD/covariance and expected admission
classes before evaluation; use disjoint calibration-control families/seeds for
candidate policy. Every condition retains its expected outcome. Admission
negatives are successful rejection tests, not recovered models. Mismatch and
resolution failures need literal warning/fail outcomes, not forced fits.

For nominal off-axis and bipolar controls, proposed fit and locked-test WRMS
<=2, and volume-weighted model RMSE below the declared zero/reference baseline
(ratio <1). Both methods must satisfy these limited model-positive controls;
these are not universal recovery criteria for diffuse/deep/null families.
Publish synthetic RMSE, mass/centroid/depth errors, correlations and mesh/beta
sensitivity with units even when they are poor. IRLS has no automatic advantage.
Null controls require no invented signal or divisions by zero. Demonstrate a
distinct depth/density model consistent with the observation noise; predictive
agreement does not prove density identifiability.

Fit/test WRMS changes from wrong uncertainties, conditioning or errors must be
visible. No training truth or outer observations enter optimizer selection.
Buffer/group feasibility failures stay failures. Evaluate covariance-aware
marginal metrics and inspect spatial residual structure rather than rely on a
single fit scalar. All receipt counts include rejects/nonconverged outcomes.

## Field and resource acceptance

Field source gate is currently BLOCKED: the author Bartlett member's existing
SHA/profile is recorded in research, but height reference, errors, processing
lineage and duplicates do not pass admission. Do not rewrite that failure, mask
it into eligibility or use a synthetic replacement as measured-field acceptance.
Main/source owner must supply exact eligible bytes/metadata/rights or explicitly
approve another measured source. Preserve original source gap as historical fact.

An eligible field receipt includes strict admission, blocked tuning/locked outer
test, covariance/error rationale, residual maps/structure and alternatives for
mesh/padding/beta/bounds/start. Proposed nominal test WRMS <=2 applies only to
credible declared errors; a poor result remains a poor result. No model RMSE or
known subsurface truth is asserted. Final all-data maps are labelled refit, not
holdout models. Actual station processing/height uncertainty must be evaluated,
not inherited from tutorial floors or old synthetic percentage noise.

Local resource gate requires small/nominal/maximum admitted geometry and reject
above-cap tests. Measure at least 20 nominal repeats for p95, one-thread CPU
identity, peak RSS, scratch and timings; 4 GiB/2 GiB/30 min budgets proposed in
design and nominal <=70% of budgets. Count full candidate/uncertainty workflow,
not just G construction. Preflight and per-job runtime limits both enforced.
Cancellation, timeout and crash must preserve input/output rights and unrelated
directories. RAM/disk-cache configurations get separate fingerprints/receipts.
Host/GPU gates stay NOT RUN, and current public-host disk headroom is not accepted.

## Review/evidence progression

1. Main independently reviews this plan and freezes schema/thresholds/owners.
2. Implement new local modules/tests only with separate code authority; collect
   fast independent unit/physics gates before any inversion-quality assertion.
3. Freeze calibration and locked controls; run the complete 48/96 protocol and
   measured local resource gates, retain commands/source/config/bytes/counts.
4. Independent reviewer replays bundles and selection/admission negatives.
5. Field and product API/UI/course/host acceptance remain separate open gates.

Docs-only checks are reported below when executed; they verify syntax, scope and
traceability, not numerical acceptance. Existing full-product convergence failures
and unresolved requirements remain untouched.

## Executed docs-only review, 2026-10-03

At aligned develop `66952f32b6ce86d5a752cf56d3e4ca8481c8b4da`, with these six
new docs staged, the following commands completed with exit zero using the
existing pipeline Python, `PYTHONDONTWRITEBYTECODE=1`:

```text
python scripts/check_content_standards.py
python scripts/check_template_residue.py
python scripts/check_ci_budget.py
python scripts/check_sdd_convergence.py
git diff --cached --check
```

An inline stdlib-only audit verified six-path docs scope, strict source SHA256
equality for all 11 inspected files, 19 EARS requirements mapped to 26 distinct
planned/nonexistent tests, 26 existing relative links, 17 distinct primary
references, valid research JSON and clean scoped content. The original private
backup has 137 files, zero tracked paths and remains ignored; no backup/candidate/
receipt content was changed. This check is not a fresh numerical or backup
inventory digest claim.

The first repository content check at `46bd5e7` failed on six pre-existing
upstream MT frontend em-dashes. That failure is retained here. Main's independently
merged PR117 fixed those separators; the later aligned check above passed. This
sidecar did not edit frontend or weaken the content check. Convergence structural
check still reports **one fail, 18 unresolved**; no ledger/scientific claim changed.

Main's independent six-file/source read approves this as a plan only, with CPU
Geoana/separate Choclo/volume/unit principles. Exact survey schema/binding,
seeds/candidates/epsilon/null policy and pinned optimizer stopping mapping remain
unresolved. All proposed numerical tests, measured resources and field/product
gates remain NOT RUN. No broad inverse code authority follows from docs checks
or plan merge; a narrow forward-operator amendment is the next review unit.
