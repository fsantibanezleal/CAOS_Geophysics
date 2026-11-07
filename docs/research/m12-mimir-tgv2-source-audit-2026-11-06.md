# MIMIR-TGV² source audit for M12 : 2026-11-06

## Decision

MIMIR-TGV² is a relevant recent comparator for travel-time inversion, not a
novelty claim for this product and not a drop-in replacement for the current
M12 experiment. The source implementation and manuscript need a leakage-safe,
same-forward re-evaluation before their headline metrics can be used as an
independent acceptance threshold. This audit records what the pinned public
sources support; it does not reproduce the paper.

## Source identity and publication status

- Kurosawa, *Total Generalized Variation regularization closes the gap between
  neural-field and classical methods in seismic travel-time tomography*,
  arXiv v1, submitted 2026-05-11, 15 pages, marked as submitted to the
  *Geophysical Journal International* when retrieved on 2026-11-06:
  [paper and version metadata](https://arxiv.org/abs/2605.09960).
- Public implementation: [ISAO9/mimir](https://github.com/ISAO9/mimir),
  default-branch commit `c7fb9c6a5839662ad2dd4a60869dec2dd74927a0` at audit
  time. The repository contains the numbered reproduction scripts and
  `src/mimir` implementation; the repository tree has no test directory.
- The repository's `LICENSE` is MIT, while `pyproject.toml` declares
  `Apache-2.0`. Resolve this metadata conflict before copying or redistributing
  source. An independent reimplementation does not inherit that ambiguity.

## Method and reported experiment

For a 2D velocity field `v(x,z)`, the network predicts velocity from
coordinate Fourier features and computes travel time using a trapezoidal
quadrature along the straight source-receiver segment:

\[
\widehat T_i = \int_{\text{straight segment }i}\frac{1}{v(x,z)}\,ds.
\]

The regularizer is the second-order total generalized variation

\[
\operatorname{TGV}^{2}_{\alpha_0,\alpha_1}(v)
 = \min_w \alpha_1\|\nabla v-w\|_1
             +\alpha_0\|\mathcal E(w)\|_1,
\qquad \mathcal E(w)=\tfrac12(\nabla w+\nabla w^T).
\]

The implementation represents both `v` and the auxiliary vector field `w` by
neural fields and jointly optimizes them. The paper describes 64 quadrature
points; the pinned code passes `n_samples=64` to an endpoint-inclusive
trapezoidal rule, which evaluates 65 points across 64 intervals. The code
configuration uses a 64×64 regularization grid, Huber data loss with
`delta=0.05 s`, `(alpha_0, alpha_1)=(1,2)`, Adam at `5e-3`, cosine scheduling,
200 warm-up steps, gradient clipping at 1, and 8,000 iterations. The underlying
TGV definition is established; the paper's proposed contribution is this
joint neural parameterization in the travel-time tomography setting.

The paper reports a 128×128, 10 km synthetic domain, three generated models
(Gaussian anomaly, layered with an embedded anomaly, and a curved-fault
lookalike), five seeds per model, and 5% travel-time noise. It reports a
classical FMM/curved-ray/LSMR baseline with per-benchmark damping and smoothing
tuned on the first seed. Reported TGV² RMSE differences are not significant on
the Gaussian model (`p=0.134`), and favor TGV² on the layered (`44%` reduction,
`p<0.0001`) and curved-fault (`33%` reduction, `p=0.0002`) models. These are
claims from the preprint, not independently reproduced results.

## Transfer and acceptance risks

1. **Truth-selected checkpoints.** `scripts/40_train_tgv.py` passes the exact
   generated `truth` grid into `TGVTrainer`. In the pinned
   `src/mimir/training/trainer.py`, `_validate` computes velocity-grid RMSE
   directly against `truth_grid`; `fit` saves the checkpoint with the minimum
   of those RMSE values. Thus the reported “validation-best” epoch is selected
   using the target model, not held-out observed travel times. This is oracle
   model selection on these synthetic cases. Re-evaluation should select
   checkpoints and hyperparameters from observation-only validation groups,
   then score the model and independent forward predictions once on untouched
   cases.
2. **Forward-model asymmetry.** The paper's data generator and classical
   baseline use fast marching. The neural-field data loss instead uses a
   straight-ray integral, which is exact for a constant velocity but is not
   the curved-ray/eikonal forward model in heterogeneous media. Results should
   be repeated with both methods using matched forward physics, and the
   original mismatch should be retained as its own experiment rather than
   silently removed.
3. **Acquisition description mismatch.** The manuscript describes 12 sources
   × 24 receivers. The pinned `cross_well_layout` called by script 40 creates
   12 left-wall sources and 12 top-wall sources, each with 12 receivers on the
   opposite wall: 24 source positions and 288 source-receiver pairs. Ray count
   alone does not make these geometries equivalent.
4. **Benchmark scope.** The curved-fault case is explicitly a generated
   `curvefault_lookalike`, not OpenFWI field or benchmark data. The paper's
   synthetic scores do not establish field generalization, uncertainty
   calibration, or performance on user-supplied travel-time picks.
5. **Grid-spacing convention.** The pinned TGV implementation takes forward
   differences in pixel-step units and does not divide by physical grid
   spacing. Preserve that convention for exact reproduction; a product
   implementation on physical coordinates must define and validate its own
   spacing-aware discrete operators and weights rather than reuse the paper's
   alpha values as physically invariant constants.
6. **Different M12 contract.** Product M12 currently uses a fixed 16×16
   straight-ray feature operator with disjoint ID, family-only,
   acquisition-only, and joint-OOD cohorts, plus an independent travel-time
   oracle. A MIMIR-style 128×128 neural field has different parameterization,
   regularization, compute, and target metrics; its published scores cannot be
   compared directly to the current M12 ratios.

## Reproduction protocol required before using it as a benchmark

An admissible product comparison must pin the upstream commit, resolve license
metadata, preserve the authors' original run separately, and define a new
predeclared protocol with source-grouped observation-only training and
validation, untouched synthetic model families and acquisition geometry,
matched forward operators for the primary comparison, and a separately
reported reproduction of the paper's original operator asymmetry. Report
velocity error, held-out travel-time error, residual-threshold exceedances,
coverage, runtime, peak memory, seed-level paired results, and all failed or
nonconverged runs. Compare against the current classical optimizer and at least
one independent grid-based TGV² implementation. No M12 acceptance, novelty
claim, or deployment decision follows from this source audit.

## Primary sources

- [Kurosawa (2026), arXiv:2605.09960 v1](https://arxiv.org/abs/2605.09960).
- [Pinned MIMIR repository commit](https://github.com/ISAO9/mimir/tree/c7fb9c6a5839662ad2dd4a60869dec2dd74927a0).
- [Pinned TGV training script](https://github.com/ISAO9/mimir/blob/c7fb9c6a5839662ad2dd4a60869dec2dd74927a0/scripts/40_train_tgv.py).
- [Pinned trainer and truth-grid checkpoint selection](https://github.com/ISAO9/mimir/blob/c7fb9c6a5839662ad2dd4a60869dec2dd74927a0/src/mimir/training/trainer.py).
- [Pinned acquisition generator](https://github.com/ISAO9/mimir/blob/c7fb9c6a5839662ad2dd4a60869dec2dd74927a0/src/mimir/data/acquisition.py).
- [Pinned license](https://github.com/ISAO9/mimir/blob/c7fb9c6a5839662ad2dd4a60869dec2dd74927a0/LICENSE) and [package metadata](https://github.com/ISAO9/mimir/blob/c7fb9c6a5839662ad2dd4a60869dec2dd74927a0/pyproject.toml).
