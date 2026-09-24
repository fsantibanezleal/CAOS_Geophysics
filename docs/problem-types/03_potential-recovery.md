# Noise-aware potential-field and joint inversion

The 10,752-cell integral operator is retained. The independent model variables
are density contrast in g/cm³, susceptibility in SI, or three magnetization
components normalized by the inducing field. A fine numerical mesh does not
provide 10,752 independently resolvable geological quantities from 256 stations.

The scalar inverse minimizes `||diag(1/sigma)(Gm-d)||² + beta m'Qm`.
`Q = diag(w²) + sum(length² D' diag(w_face²) D)` uses forward differences
in metres, with 240 m horizontal and 140 m vertical correlation lengths.
Weights are proportional to `(depth + dz)^(-0.375)` and normalized to unit RMS.
Beta is selected by mean squared whitened residual equal to one, then multiplied
by the explicitly exported experimental strength. Neither selection nor stopping
reads display-case truth. IRLS applies four smoothed L1 smallness updates while
retaining the physical spatial L2 term. It is not a total-variation inverse.

## Independent depth-prior calibration

Before freezing the new prior, twelve separate ellipsoid/dyke/basin/contact
realizations were generated with seed 67081, noise seed 67082 and observation
noise of 2.5% of their combined standard deviation. The model generator is the
reproducible `learning.generate`; these seeds do not occur in training, validation,
test or displayed cases. Selection minimizes mean zero-model RMSE ratio.

| Depth exponent | Mean RMSE / zero-model RMSE | Median ratio |
| --- | ---: | ---: |
| 0 | 0.900054 | 0.935493 |
| 0.375 | 0.874551 | 0.892559 |
| 0.75 | 0.882384 | 0.868855 |

This small calibration establishes a reproducible choice, not a universal best
prior. Held-out stations, support/background errors, centroid displacement and
vector-direction error are evaluated separately from training-data residuals.

## Structural and petrophysical coupling

The uncoupled, cross-gradient and GMM inverses share observations, uncertainty,
initial estimates, spatial precisions and an 80-step strong-Wolfe L-BFGS budget.
Cross-gradients use derivatives in metres; their squared norm is scaled by
`240^4` and divided by its value at the matched independent initialization
(floor `1e-12`). This balances the penalty without inspecting known truth.
The optimizer uses a diagonal quadratic-Hessian preconditioner. The gravity and
magnetic regularization coefficients are selected separately by discrepancy.

PGI here means an explicit negative-log Gaussian-mixture petrophysical prior,
not the SimPEG PGI optimizer. A two-class full-covariance mixture is fitted by EM
to 640 original synthetic laboratory-like density/susceptibility pairs with seed
68121. Samples, SHA-256, fitted weights/means/covariances and EM loss are exported.
The samples do not use voxel labels. The decoupled case deliberately violates the
shared-density/susceptibility prior and is retained as a negative control.
Responsibilities are conditional mixture membership, not geological certainty.

## Conditional observation-noise ensembles

Thirty-two Gaussian data perturbations repeat the linear estimator with fixed
mesh, acquisition, spatial prior and selected beta. Exported 2.5–97.5% quantiles
describe estimator repeatability. They do not include regularization bias,
geological ambiguity, forward-model error or beta-selection uncertainty. The
known-reference pointwise/support coverage is shown explicitly, even when poor.
It must not be described as a calibrated 95% geological posterior interval.
