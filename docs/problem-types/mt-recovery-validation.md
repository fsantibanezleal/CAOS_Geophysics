# MT / EDI recovery validation receipt · 2026-09-24

Scope: CPU-only targeted validation of the scientific-recovery MT vertical.
This is not a claim that the entire application, canonical bake or deployment
has been validated. No branch change, commit, push or canonical-data write was
performed by this work unit.

## Tests actually executed

Final command:

    .venv-pipeline/Scripts/python -m pytest tests/test_mt_recovery.py tests/test_edi.py tests/test_rebuild.py::test_mt_halfspace_and_split_homogeneous_layer tests/test_rebuild.py::test_mt_autodiff_parity_and_directional_derivative

**57 passed in 34.85 seconds.** The two added existing tests check homogeneous
layer splitting, NumPy/Torch forward parity and directional derivatives. The
55 new test cases include:

- Independent half-space recovery by all three algorithms, common physical
  bounds and initial model, objective parity with masked frequencies and
  heteroscedastic errors.
- Every saved frame paired with its own complete objective; regression against
  the post-update model/pre-update loss alias; identical final model/last frame
  and direct final-model predictions/residuals.
- Independent two-layer reflection-coefficient recovery; withheld frequencies;
  weak deep-layer resolution and active-bound diagnostics.
- CPU RNG restoration, deterministic neural execution, strict invalid-input
  rejection, conditional bootstrap reproducibility and independent coverage.
- Failure-retaining bootstrap records, including all members failing rather than
  manufacturing an interval. Bound-rounding regression at 6000 Ω m.
- Real EDI parsing, native/SI units, complex/per-real variance distinction,
  negative-time convention, xy/yx signs, malformed blocks, numeric sentinels,
  missing components/errors, duplicate frequencies, channel orientation and
  explicit interpretation provenance.
- Exact 90° tensor/error permutations with unequal component variances; arbitrary
  rotation rejected without covariance, but preserved-frame 1D inversion supported.
- CLI success/rejection and frontend bundle hashes, relative filenames,
  synthetic provenance, null generic truth and separate known-fixture targets.

Ruff passed for both implementation modules, both test modules and the original
fixture generator. Pip check reported no broken requirements. The shared
requirements file was not edited. See the dependency receipt in
[the method document](mt-recovery.md).

## Direct reference-case probes

Executed the unchanged solve_case(case, "reference") interface for all four MT
cases, saving only to ignored data/experiments/mt-recovery/. These probes use
36 frequencies, 2.5% per-real-component noise, β=0.001 and the same 100 Ω m start.

| Case | TRF log-model RMSE / initial ratio | Adam RMSE / ratio | Neural RMSE / ratio |
|---|---:|---:|---:|
| Resistive cover | 0.173233 / 0.107424 | 0.173205 / 0.107406 | 0.215293 / 0.133505 |
| Conductive aquifer | 0.098159 / 0.054603 | 0.098159 / 0.054603 | 0.098159 / 0.054603 |
| Alternating layers | 0.924574 / 0.620259 | 0.425197 / 0.285248 | 0.040128 / 0.026921 |
| Deep conductor | 0.031593 / 0.016772 | 0.030791 / 0.016346 | 0.031593 / 0.016772 |

All twelve improve over the independent initial model. That does **not** mean
all twelve are identified geological solutions. The alternating-layer TRF model
is approximately [75.36, 1033.19, 8.82, 2422.82, 34.59] Ω m for the synthetic
[80, 500, 9, 350, 35] Ω m target. Its second and fourth layers are marked
unresolved despite component WRMS 0.913944. Neural's fourth layer is also flagged
unresolved even though that particular realization has low model error. These
results preserve the nonuniqueness warning instead of hiding it.

Component WRMS ranges 0.903438–1.023063 across these twelve outputs. Each TRF
probe completed 128 conditional resamples. Elapsed CPU times were 20.38, 19.24,
29.46 and 22.58 seconds respectively, under concurrent CPU activity. These are
observed timings, not a performance guarantee. All six variants per case still
belong to the integration owner's canonical bake and release validation gate.

## Actual EDI inverse results

The three original fixtures were inverted by the CLI/bundle path with the
official parser, the strict preflight and the real bounded 1D optimizer.

| EDI fixture | Independent synthetic target | Recovered resistivity | Fitted / other component WRMS |
|---|---|---|---|
| Native half-space | 100 Ω m | 100.00000000000004 Ω m | <10⁻¹³ / <10⁻¹³ |
| SI, negative-time half-space | 500 Ω m | 499.999999999999 Ω m | <10⁻¹³ / <10⁻¹³ |
| Noisy 27° two-layer tensor | [120, 12] Ω m | [123.9757567, 11.9645644] Ω m | 1.079692 / 1.169046 |

Every fixture ensemble completed 128 members. The two-layer thickness is the
explicit 350 m operator input, not estimated from data. Generic EDI artifacts
retain truth=null. The bundle manifest labels the independent synthetic target;
there is no external field dataset, field-ground-truth or licensed-field-data
claim.

## Independent conditional coverage experiment

The coverage experiment uses models distinct from the fixtures and separate
observation/bootstrap seeds. For each model: 48 observation realizations,
128 conditional bootstrap members per realization, 24 frequencies over
0.01–100 Hz, 4% per-real-component Gaussian noise, β=0.001 and a 100 Ω m start.
No hyperparameter was selected using these coverage outcomes.

| Calibration target | Measured pointwise coverage | Wilson 95% interval for coverage | Mean interval width | Estimator bias |
|---|---:|---:|---:|---:|
| 230 Ω m half-space | 44/48 = 91.67% | 80.45–96.71% | 13.9013 Ω m | −0.12046 Ω m |
| 180 Ω m cover, h=450 m | 42/48 = 87.50% | 75.30–94.14% | 46.5339 Ω m | +0.04353 Ω m |
| 20 Ω m basement | 48/48 = 100% | 92.59–100% | 1.66548 Ω m | +0.02752 Ω m |

There were **zero optimizer/ensemble failures** in these calibration experiments.
The nominal interval level was 95%; the observed coverage is plainly not
identically 95%. The 180 Ω m result indicates undercoverage for this small
experiment. Zero empirical Monte Carlo standard error at 48/48 does not imply
certainty; the Wilson interval is included to avoid that misinterpretation.
No calibration coverage is copied into arbitrary sounding intervals or labelled
posterior probability.

Reproduce the complete bundle and these calibration records:

    .venv-pipeline/Scripts/python data-pipeline/edi.py --fixture-bundle --bootstrap-samples 128 --calibration-realizations 48 --output data/experiments/edi

The manifest contains relative paths and SHA-256 for source EDI, inverse
artifacts and calibration records. Its calibration members retain each
observation seed, bootstrap seed, selected model, interval, inclusion result and
any failures.

## Integration handoff

- Own edited files: data-pipeline/electromagnetics.py, data-pipeline/edi.py,
  tests/test_mt_recovery.py, tests/test_edi.py, data/fixtures/edi/* and these two
  MT documents under docs/problem-types/.
- Direct new dependency pin: mt-metadata==1.0.10, installed only in the existing
  .venv-pipeline. Exact newly installed transitive versions are in the method doc.
- Public-copy candidate: **entire data/experiments/edi directory**. Main chooses
  the committed/published data/edi destination. Relative manifest paths require
  no host-specific rewrites.
- Frontend must not cast the generic EDI schema to a synthetic v2 run with known
  truth. Use truth_ohm_m from the labelled fixture manifest for fixture comparisons.
  The generic artifact records target_known=false.
- Preserve the additive method evaluation, target, uncertainty and state_identity
  fields during canonical export. Include evaluation in catalogue summaries.
- Full direct JSON exports retain exact final-model/last-frame identity. If the
  shared exporter rounds floating values, its numerical checks must acknowledge
  that rounding rather than asserting bit-exact forward re-evaluation.
- No claims of GPU execution for MT, field generalization, posterior coverage,
  arbitrary EDI formats or joint thickness recovery.
