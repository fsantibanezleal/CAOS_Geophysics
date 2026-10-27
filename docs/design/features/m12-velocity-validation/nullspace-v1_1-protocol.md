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

## Fresh held-out result: 2026-10-27

The frozen v1.1 implementation ran on CPU in 16.32 seconds. The 160-case
calibration selected classical lambda `100` and nullspace correction scale
`alpha=1.0`. All 480 held-out cases were evaluated after selection, with zero
forward-threshold exceedances. The receipt reports
`supported-within-bounded-synthetic-protocol`:

| Cohort | n | Velocity RMSE ratio | Paired bootstrap 95% interval | Oracle-time RMSE ratio | Paired bootstrap 95% interval |
| --- | ---: | ---: | ---: | ---: | ---: |
| ID | 160 | 0.8035 | 0.7796–0.8269 | 0.9841 | 0.9810–0.9860 |
| Family-only | 80 | 0.9718 | 0.9685–0.9792 | 0.9962 | 0.9942–0.9988 |
| Acquisition-only | 80 | 0.8023 | 0.7698–0.8371 | 0.9842 | 0.9789–0.9881 |
| Joint OOD | 160 | 0.9701 | 0.9703–0.9770 | 0.9967 | 0.9951–0.9986 |

Ratios below one favor the refined method. Intervals are percentile paired
case-bootstrap intervals over the fixed synthetic generator, 20,000 draws,
seed `6122026`; they quantify resampling variation within these cohorts, not
uncertainty across natural geology. The joint-OOD travel-time improvement is
small. For acquisition C, the ray matrix has rank 127 and nullity 129;
`max(abs(A @ N)) = 1.52e-13` and the projected correction residual is
`4.56e-18`, with no physical-bound clipping. Nonlinear velocity conversion
still means this linear null-space result is not a general data-invariance
guarantee.

The full immutable receipt and checkpoint are retained outside the checkout
at `E:\_worktrees\_runs\m12-nullspace-v1_1-full-20261027b`. Receipt
SHA-256: `30df0c2ad495bd850dda602b1c96725be8290dd086119fb3e8e75355fe9dea22`.
Independent `--verify` replay regenerated all four held-out cohorts and
reproduced their stored metrics; the scientific verdict reproduced as
`supported-within-bounded-synthetic-protocol`. This result supports further
controlled research only; it does not
validate field data, establish geological recovery, or change overall M12 or
product release acceptance.
