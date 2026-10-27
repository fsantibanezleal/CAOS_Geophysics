# M12 nullspace-constrained residual refinement v1.1

Status: implemented protocol, not yet scientifically evaluated. The v1
implementation record is invalidated because it used an incompatible model
feature normalization; see [the v1 erratum](nullspace-v1-protocol.md).
The v3.1 checkpoint remains a failed held-out comparator. This study does
not claim to repair it or establish field-data validity.

## Question

Does projecting the v3.1 learned slowness correction into the null space of
the acquisition's straight-ray cell-length matrix reduce held-out velocity
error and independent travel-time error at the same time?

## Method

For each acquisition matrix `A`, compute a full-SVD orthonormal basis `N` for
`ker(A)` with tolerance `eps * max(m, n) * largest_singular_value`. Given a
classical velocity `v0` and learned velocity `vL`, form the slowness correction
`delta_s = 1/vL - 1/v0`, then use `delta_s_null = N N.T delta_s`. Candidate
velocity is `clip(1 / (1/v0 + alpha * delta_s_null), 1400, 4000)` m/s.
Receipts record basis rank/nullity, `max(abs(A @ N))`, projected residual,
and clipping fraction. The reciprocal and bounds are nonlinear, so the
null-space projection alone does not guarantee unchanged travel times; every
candidate is evaluated with the independent bilinear-slowness oracle.

The CNN input is created only with
`velocity_physics_refinement.input_features`, the exact feature contract used
to train the source checkpoint. The corrected implementation has a dedicated
parity test against that function. The checkpoint is hash-verified against
its original v3.1 receipt and copied into each immutable output directory.

## Split and selection

Calibration uses 160 seeded synthetic realizations (base seed 417001). It
selects the classical regularization parameter by calibration velocity RMSE,
then selects `alpha` from `0, 0.25, ..., 2.0` only when both calibration
velocity and oracle-time ratios improve on the classical result. The minimum
mean of those two ratios wins; ties prefer the smaller alpha. Otherwise alpha
is exactly zero. After selection, four disjoint fixed-size cohorts are
evaluated: 160 in-distribution cases (427001), 80 family-only cases (437001),
80 acquisition-only cases (447001), and 160 joint-OOD cases (457001). These
seed ranges are disjoint from the earlier M12 studies and invalid v1 cohort.
No parameter is selected on these test cohorts.

## Reproduction

From the repository root, using the pinned Linux M02 environment and an
external output directory:

```sh
python scripts/run_m12_nullspace_v1_1.py \
  --source-run /path/to/verified-v3.1-run \
  --output /external/research/m12-nullspace-v1_1 \
  --device cpu
python scripts/run_m12_nullspace_v1_1.py \
  --output /external/research/m12-nullspace-v1_1 --verify
```

`--fixture` is only a 12-case calibration smoke check and cannot produce a
scientific verdict. Outputs are immutable; reruns require a new directory.
The receipt binds method, runner, feature contract, forward/inverse code,
checkpoint, input manifests, environment, selection metrics, held-out
per-case results, and elapsed time. No notebook or browser animation is
treated as a solver result.

## Acceptance boundary

An improved joint-OOD score is necessary for this synthetic hypothesis to
survive, but is not sufficient for product acceptance. Report all cohorts,
paired errors, confidence intervals, acquisition limitations, and numerical
invariance diagnostics before any interpretation. Even a passing synthetic
result does not establish field superiority, geological recovery, or
deployment readiness. A failed result remains a useful negative result and
must not be tuned against its test cohort.
