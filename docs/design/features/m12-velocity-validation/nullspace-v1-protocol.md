# M12 nullspace-constrained residual refinement v1

Status: predeclared experiment. It is not an accepted method, a field result,
or a claim that v3.1's failed test has been repaired. The v3.1 receipt and
checkpoint remain immutable.

## Hypothesis and algorithm

The v3.1 CNN predicts a bounded slowness/velocity correction from a classical
straight-ray inverse, a measured-geometry backprojection and ray coverage.
The failed v3.1 joint holdout showed that unconstrained learned corrections
could improve the model map slightly while worsening the independent travel-
time oracle. This protocol tests whether restricting that correction to the
null space of the cell-length ray operator retains useful structure while
preserving the observed-ray response to first order.

For acquisition matrix \(A\), obtain an orthonormal basis \(N\) for
\(\ker A\) from a full SVD, with rank tolerance
\(\epsilon\max(m,n)\sigma_{\max}\). For the learned-minus-classical slowness
correction \(\delta s\), use

\[
\delta s_{\perp}=NN^T\delta s,\qquad
v_{\alpha}=\operatorname{clip}_{[1400,4000]}
\left((s_{\rm L2}+\alpha\delta s_{\perp})^{-1}\right).
\]

The implementation records \(\|A\delta s_{\perp}\|_{\infty}\), basis rank,
nullity, and clipping fraction for each geometry. The nonlinear reciprocal and
physical clipping can perturb exact invariance; final scores therefore use
the independent bilinear-slowness travel-time oracle, not the linearized
nullspace argument.

The source checkpoint is the exact v3.1 checkpoint, whose original scientific
verdict remains failed. Its training receipt and weights are copied into each
run directory and hash-bound. This v1 experiment adds no training step.

## Selection without test access

The classical L2 lambda and correction scale are selected on a fresh
calibration cohort only. Calibration seeds are 317001–317160, with the
training families and acquisition layouts A/B. Lambda minimizes mean
per-case velocity RMSE. Alpha is selected from
\(\{0,.25,.5,.75,1,1.25,1.5,1.75,2\}\) by minimizing the arithmetic mean
of the velocity-RMSE and independent-oracle time-RMSE ratios, requiring both
ratios below one. Ties choose the smaller alpha. If no candidate improves both
calibration metrics, alpha zero (the exact classical result) is selected.

Only after those values are fixed does the runner generate its new test
cohorts: ID 327001–327160; family-only 337001–337080; acquisition-only
347001–347080; and joint family-plus-acquisition OOD 357001–357160. Test
families, seeds, picks and truth are absent from calibration. All records and
noisy inputs are hashed in the receipt. Acceptance requires both mean learned
to classical ratios below one on every joint OOD case, with all per-record
results retained. The held-out run is executed once after the code and
selection rule are frozen; a failed result is not tuned against.

## Reproduction

Run from the pinned M12 environment with the failed v3.1 run directory:

```bash
python scripts/run_m12_nullspace_v1.py \
  --source-run <external-v3.1-run> \
  --output <new-external-run-directory> \
  --device cpu
python scripts/run_m12_nullspace_v1.py \
  --output <new-external-run-directory> --verify
```

`--fixture` is limited to a 12-record calibration smoke check and deliberately
does not score a test cohort. Output directories must be new and outside every
checkout. The receipt records hashes for this implementation, runner, forward
operator, feature contract, base network and checkpoint. Replay regenerates
the calibration and all test cohorts and checks the frozen selection and
reported metrics.

## Limits and references

This remains synthetic 16x16 straight-ray tomography with three fixed layouts,
known synthetic geology families, and a previously trained model. It does not
model ray bending, waveform FWI, field noise processes or field geology. A
positive result would be bounded evidence for this protocol only; it would not
close M12 or R-008 without the approved source, browser, resource and release
gates.

Background references: [SimPEG straight-ray tomography API](https://docs.simpeg.xyz/latest/content/api/generated/simpeg.seismic.straight_ray_tomography.Simulation2DCellCentered.html)
and [Kamilov et al. (2023), Plug-and-Play Methods](https://doi.org/10.1109/MSP.2022.3199595).
Neither source evaluates this nullspace projection or validates its results.
