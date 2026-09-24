# Methods and interpretation

## Potential fields

SimPEG integral operators map rectangular-prism density in g/cm³ to gz in mGal, or scalar susceptibility to linearized TMI in nT. The coordinate convention is ENU. Surface receivers sample a 16×16 grid. Model dimension is 28×24×16. Acquisition variants change receiver height; coverage variants use alternate stations.

Let W be reciprocal column sensitivity with a 6% floor and A=GW/s where s is the mean row-energy scale. The inverse minimizes ||Aq-d/s||²+β qᵀDq, with m=Wq. The data-space solution is D⁻¹Aᵀ(AD⁻¹Aᵀ+βI)⁻¹d/s. L2 sets D=I; eight IRLS updates use weights proportional to (q²+ε²)^−1/2, normalized by their median, ε=0.12 max|q|. This is model-norm sparsity, not smoothness. All canonical stations have the same noise sigma; custom CSV inversion supports row-wise sigma.

Magnetic vector inversion estimates three components using SimPEG's vector operator. Scalar susceptibility assumes induced direction; the remanent case violates it deliberately. Additional vector freedom is not independent evidence for magnetization direction.

## Magnetotellurics

For angular frequency ω, permeability μ and resistivity ρ, the half-space impedance is sqrt(iωμρ). Each finite layer uses propagation constant sqrt(iωμ/ρ), characteristic impedance sqrt(iωμρ), thickness h and the standard complex tanh recursion. Apparent resistivity is |Z|²/(μω); phase is atan2(Im Z, Re Z).

Three solvers fit complex observations: bounded log-resistivity least squares, Adam on log resistivity, and a tanh neural parameterization differentiated through the same recursion. The layer thicknesses are known. A first-difference log-resistivity penalty controls roughness. The neural solution is optimized per sounding and is not a pretrained general inverse. Objective evaluations are labelled as such; they are not necessarily accepted least-squares iterations.

## Acoustic FWI

Deepwave solves the constant-density 2D acoustic equation with fourth-order spatial differences and absorbing boundaries. Three Ricker shots, 40 (or 20) receivers, 25 m cells and 1 ms integration produce 1.1 s records. Saved pressure frames are 24 ms apart; displayed gathers are sampled at 4 ms. Coordinates and dimensions are explicit.

A bounded sigmoid parameterization permits velocities 1400–4400 m/s. Adam makes 28 updates from the declared depth trend 1800+22×depth-index. The direct method fits waveforms; continuation uses moving-average low-pass windows 21,9,1. The retained model minimizes the full-band data loss over evaluated models. A squared neighbour-difference penalty discourages rough velocity. Automatic differentiation is checked against a double-precision directional finite difference on CUDA. Model error can remain large after a strong data-fit improvement.

## Joint inversion

Gravity and magnetic properties are standardized by 0.5 g/cm³ and 0.03 SI. Independent L2 solutions initialize 180 joint Adam steps. The objective combines both noise-normalized data losses, a cross-gradient penalty and weak model norms. Cross-gradients use cell-index derivatives; their displayed magnitude is dimensionless, not a physical spatial derivative. Shared-boundary and conflicting-boundary cases test the assumption. A small cross-gradient can also arise from a flat model.

## Learned inversion

A CNN maps a normalized gravity map to depth-integrated density. Two convolutions, GELU, adaptive 4×4 pooling and two dense layers output 12×14 column values. An autoencoder compresses 256 observations through a 12-dimensional bottleneck. Training uses 800 models, validation 160, testing 160, with disjoint generation seeds and duplicate-model checks. Weights are chosen only by validation loss. The oblique and ring geological cases are outside the training geometry classes.

The classical comparator estimates the same column target from the same held-out models. Its noise-free observation baseline is deliberately favourable to the classical model; the CNN test includes 2% training-scale noise. This is not a comprehensive hyperparameter-tuned SOTA benchmark. Acquisition-height changes are distribution shift, not a new trained model. No probabilistic confidence is claimed from the autoencoder's validation-quantile flag.

Primary sources and methodological differences are recorded in [the review](../research/review.md). The UI methodology page contains the same implementation-specific assumptions in EN/ES.
