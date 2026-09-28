# Methods and interpretation

## Potential fields

SimPEG integral operators map rectangular-prism density in g/cm³ to gz in mGal, or scalar susceptibility to linearized TMI in nT. The coordinate convention is ENU. Surface receivers sample a 16×16 grid. Model dimension is 28×24×16. Acquisition variants change receiver height; coverage variants use alternate stations.

The inverse minimizes ||diag(1/σ)(Gm−d)||² + βmᵀQm. The positive sparse precision Q combines depth-weighted smallness with first differences divided by physical cell spacing; horizontal/vertical correlation lengths are 240/140 m. The depth exponent 0.375 was frozen using independent calibration models, not chosen from displayed truth. β is selected so the mean squared whitened residual is one before the exported variant strength multiplier. L2 uses one solve. IRLS uses four smoothed-L1 smallness updates while retaining the spatial L2 term; it is neither pure model-norm sparsity nor total variation. The canonical survey has one σ per condition; custom CSV inversion supports row-wise σ. [Full objective, calibration and limitations](03_potential-recovery.md).

Magnetic vector inversion estimates three components using SimPEG's vector operator. Scalar susceptibility assumes induced direction; the remanent case violates it deliberately. Additional vector freedom is not independent evidence for magnetization direction.

## Magnetotellurics

For angular frequency ω, permeability μ and resistivity ρ, the half-space impedance is sqrt(iωμρ). Each finite layer uses propagation constant sqrt(iωμ/ρ), characteristic impedance sqrt(iωμρ), thickness h and the standard complex tanh recursion. Apparent resistivity is |Z|²/(μω); phase is atan2(Im Z, Re Z).

Three solvers fit complex observations: bounded log-resistivity least squares, Adam on log resistivity, and a tanh neural parameterization differentiated through the same recursion. The layer thicknesses are known. A first-difference log-resistivity penalty controls roughness. The neural solution is optimized per sounding and is not a pretrained general inverse. Objective evaluations are labelled as such; they are not necessarily accepted least-squares iterations.

Measured EDI transfer functions require a separate source, geometry, error and full-tensor admission before those layered solvers apply. The [M06 AusLAMP C15 study](mt-field-admission.md) documents a rights-cleared station with an upstream phase-tensor `1-D` screening label that nevertheless fails the predeclared complex-tensor gate. No field 1D inverse or geological truth is claimed.

## Acoustic FWI

Deepwave solves constant-density 2D acoustics with fourth-order spatial differences, 12.5 m sampling and 0.5 ms integration. Three known Ricker shots and 40 (or 20) receivers produce 1.6 s records. Every fifth receiver is withheld from inversion. Exported gathers retain 4 ms sampling and pressure frames 24 ms spacing.

Both corrected methods start from the independent 1800+0.88z m/s trend. A data-only 3 Hz one-dimensional background solve precedes three two-dimensional control-grid stages. Bounded velocity parameterization permits 1400 to 4400 m/s; L-BFGS uses a declared finite budget of 28 calls per stage. The continuation method uses actual 5, 8 and 14 Hz Butterworth-amplitude FFT cutoffs; the matched comparator uses full-band data after the shared background. Spatial regularization uses physical gradients. The final evaluated model is exactly the final stored frame, and predictions/history are paired to that state. Whole-model recovery relative to the initial trend and active/withheld waveform errors are separate acceptance criteria. Salt remains a cycle-skipping challenge, not a promised recovery. [Full equations, calibration, contracts and validation](02_fwi-recovery.md).

## Joint inversion

Gravity and magnetic properties are standardized by 0.5 g/cm³ and 0.03 SI. Independent L2 solutions initialize three matched 80-call L-BFGS branches: uncoupled, cross-gradient-coupled, and a fixed Gaussian-mixture petrophysical prior fitted to separate synthetic property samples. Every branch retains both whitened data losses and the same spatial terms. Cross-gradients use the physical 80, 80 and 70 m cell spacings; the objective divides their squared mean by the fixed initial cross-gradient scale. Displayed cross-gradient magnitude uses unstandardized physical properties and is not dimensionless. Coupled results are compared with the optimized uncoupled solution for both density and susceptibility. Conflicting-boundary cases are explicit negative controls for the coupling assumptions. A small cross-gradient can also arise from a flat model.

## Learned inversion

A CNN maps a normalized gravity map to depth-integrated density. Two convolutions, GELU, adaptive 4×4 pooling and two dense layers output 12×14 column values. An autoencoder compresses 256 observations through a 12-dimensional bottleneck. Training uses 800 models, validation 160, testing 160, with disjoint generation seeds and duplicate-model checks. Weights are chosen only by validation loss. The oblique and ring geological cases are outside the training geometry classes.

The classical comparator estimates the same column target from the same held-out models and receives exactly the same seeded noisy observations as the CNN (Gaussian noise at 2% of the training-observation scale). This is not a comprehensive hyperparameter-tuned SOTA benchmark. A separate 160-model set calibrates the autoencoder's 99th-percentile reconstruction-error threshold; an independent 80-model withheld-geometry set tests it. The tested detector misses all 80 withheld geometries. Case-level threshold flags are raw score comparisons, not validated geological classifications: contrast, acquisition, noise and station interpolation can change the score. Under reduced coverage, error is computed against the interpolated network input, while the raw-observation discrepancy is reported separately. No probabilistic confidence is claimed.

Primary sources and methodological differences are recorded in [the review](../research/review.md). The UI methodology page contains the same implementation-specific assumptions in EN/ES.

## Earthquake phase picking, approved design

Classical M08 onset detection and learned M13 PhaseNet-family P/S picking are distinct from the current synthetic FWI and learned-inversion methods. Their units, equations, disjoint evaluation protocol and unimplemented release gates are documented in the [phase-picking design record](phase-picking.md). This is not a reported field-picking result.
