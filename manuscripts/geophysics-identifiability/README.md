# Inverse Earth Studio: synthetic geophysical inversion and numerical diagnostics

Technical software report · version 0.03.000 · 2026-09-24

Status: executable synthetic study, not a peer-reviewed manuscript. No algorithmic novelty, publication priority or field interpretation accuracy is claimed. The software integrates established methods to make their assumptions and failure modes inspectable.

## Abstract

Geophysical inverse results can appear convincing while remaining non-unique, prior-sensitive or poorly transferable. We present a reproducible instrument linking geological truth, observations, inverse models, residuals and recorded optimization states across 20 distinct geological cases. Six controlled conditions per case yield 120 experiments and 324 method results. The implemented methods include integral potential-field inversion, layered magnetotellurics, differentiable acoustic full-waveform inversion, structural joint inversion, a learned column-density inverse and an observation autoencoder. Numerical computations are separated from public visualization through hashed artifacts. A small live MT operator is parity-tested against its offline equivalent. The study demonstrates measurable data-fit improvement without assuming model recovery, and retains negative results from a learned novelty detector. Its contribution is an auditable experimental interface and reproducible software composition, not a new inverse algorithm.

## 1. Motivation and related work

An inverse image is conditioned on a forward model, acquisition, noise model, parameterization and regularization. These conditions are frequently less visible than the resulting image. SimPEG's modular approach [1] makes those components explicit; established FWI analysis [2] explains how illumination and nonlinearity limit reconstruction. Physics-guided MT [3] shows how differentiable physics can constrain neural optimization without supervised model labels. Learned inversion benchmarks such as OpenFWI [4] emphasize the diversity of geological distributions that a learned method may encounter.

The source geophysics course [5] provided a coherent pedagogical sequence, but its notebooks are not redistributed. This implementation uses original geological constructors and independent code paths. It replaces an earlier inadequate interface that reused a single central anomaly. The rebuild treats visual differentiation as insufficient unless the underlying geological arrays, physics and results also differ.

## 2. Experimental design

The suite contains four gravity cases (intrusive stock, asymmetric basin, opposing contrasts, faulted dipping layer), four magnetic cases (dyke swarm, remanent slab, deep lens, crossing dykes), four MT soundings, four acoustic sections, two joint-structure hypotheses, and two withheld learned geometries. Each has reference, increased contrast, increased noise, changed acquisition, reduced coverage and increased regularization conditions. The acquisition perturbation is family-specific: height for potential fields, low-frequency extension for MT and source frequency for seismics. These are not claimed to be physically equivalent perturbations.

Every reference truth is hash-distinct. Each condition is independently forward-modelled and inverted. The canonical release records the exact method output arrays and metrics. Comparisons are made within a physical family and unit system; no aggregate accuracy score combines magnetic, gravity, resistivity and velocity errors.

## 3. Methods

### 3.1 Potential fields

SimPEG [1] supplies rectangular-prism gravity and magnetic sensitivity matrices on 10,752 cells (80 × 80 × 70 m) with 256 surface observations. An explicit sensitivity-weighted parameterization leads to data-space L2 and eight-step IRLS solves. IRLS regularizes model amplitude, not spatial smoothness. Vector magnetic inversion estimates three components per cell. The remanent case prescribes a direction inconsistent with the induced scalar model. Independent Choclo prism values check sign and physical scaling.

### 3.2 Magnetotellurics

The standard complex impedance recursion propagates upward through isotropic layers from a homogeneous half-space. Layer thicknesses are known. The three inverse parameterizations are bounded least squares in log resistivity, direct Adam optimization and a small tanh neural mapping differentiated through the same recursion. The neural method is conceptually related to [3], not a numerical reproduction of that paper. Half-space and homogeneous-layer splitting identities test physics; automatic-differentiation gradients and the browser implementation are checked independently.

### 3.3 Seismics

Deepwave [6] computes constant-density acoustic propagation and gradients on 128×96 nodes with 12.5 m spacing. Three Ricker shots illuminate 40 receivers; the coverage condition uses 20. Time integration is 0.5 ms for 1.1 s with absorbing boundaries. Two methods perform 28 bounded Adam updates: direct waveform misfit and a moving-average continuation schedule. The initial velocity is a declared depth trend independent of the true model. The retained solution has the smallest evaluated full-band waveform loss. A CUDA double-precision directional finite difference checks the adjoint derivative. Pressure frames and receiver traces originate from the same physical simulation.

### 3.4 Joint and learned methods

Joint inversion combines gravity and magnetics with normalized cross-gradients. Shared and conflicting geological boundaries expose the structural prior. The optimization is deliberately explicit: 180 Adam updates from independent L2 models with fixed property normalizers and coupling weights.

The learned inverse predicts column density rather than non-identifiable depth-resolved structure. It uses two convolutions, adaptive pooling and two dense layers. The observation autoencoder has a 12-dimensional bottleneck. Four procedural training geometry families generate 800 training, 160 validation and 160 test realizations from disjoint seeds. Duplicate-model hashes are checked across all splits. Validation selects weights before held-out evaluation. Oblique and ring geometries are excluded from training. Checkpoints and normalization are serialized and reloaded for prediction parity tests.

## 4. Results

The full reference-condition table is generated directly from artifacts in [results.md](../../docs/validation/results.md); all six conditions are available in the app and catalogue. These selected observations describe this fixed run, not a general ranking of algorithms.

For the normal-fault reference seismic case, multiscale relative waveform MSE decreases from 0.09798975 to 0.002459818, while velocity RMSE remains approximately 332.04 m/s. This juxtaposition is more informative than presenting the improved data fit alone. Every exported seismic method/condition is checked for final data improvement over its starting model; none is described as complete geological recovery.

For shared joint structure, the gravity-only L2 model RMSE is about 0.212835 g/cm³ and the joint value about 0.212952 g/cm³. The slightly larger joint model error does not indicate improved density recovery, despite improved data fit. For conflicting structure, joint gravity WRMS improves from 0.494249 to 0.0158755 while model RMSE worsens from 0.0772172 to 0.0787640 g/cm³. The prior can improve one diagnostic while increasing geological error.

The held-out CNN column-density MSE is 680.151805 (g/cm³ m)² versus 3122.019272 for the declared classical baseline. This is not a SOTA comparison: the classical baseline receives clean observations, the CNN evaluation includes training-scale noise, and neither baseline receives an exhaustive tuning budget. Results apply to this generator distribution only. Withheld oblique and ring cases have column RMSEs of approximately 91.19 and 89.06 g/cm³ m.

The autoencoder's 99th-percentile validation threshold is 0.0740333 normalized squared error. The oblique reference scores 0.0369666 and the ring reference 0.0103305. Neither crosses the threshold despite being outside the training geometry families. Thus reconstruction error does not reliably identify these geological novelty cases. The interface preserves this failure instead of presenting a generic anomaly badge.

### 4.1 Spatial discretization diagnostic

The local diagnostic compares original 14×12×8 and refined 28×24×16 potential-field grids with a 56×48×32 discretization at 36 common receivers. Uniform-prism subdivision agrees within 1.73×10⁻⁹ relative difference. Ten of twelve geological responses move closer to the fine-grid reference. The basin and opposing-body responses do not: cell-centre sampling of discontinuous boundaries is not monotonically convergent. The fine grid is a numerical reference, not exact geological truth. Results are preserved in [refinement.json](../../docs/validation/refinement.json).

The acoustic refinement preserves source positions, duration and 300 m absorbing-layer thickness while halving space and time increments. The smallest 1,550 m/s velocity at a 9 Hz peak frequency corresponds to 13.78 nodes per wavelength, compared with 6.89 previously. This is a sampling diagnostic, not a full dispersion or convergence study.

## 5. Visualization as an inspection instrument

Potential fields provide cell geometry and piecewise-linear isosurfaces of the computed field, camera rotation, northing cuts and a surface observation plane. MT uses thickness-scaled layers and frequency-dependent response plots. Seismic playback advances computed pressure states with geological interfaces and a synchronized gather time cursor. A separate replay advances inverse-model updates. The learned views compare the correct 2D target or observation reconstruction instead of borrowing an unrelated 3D surface.

Colour scales carry units. Paired models use shared scales; seismic display gain is fixed and explicitly clips colours at legend bounds. Pointer readouts retain original numerical cell values. Interpolation is a display operation and is not advertised as increased resolution. The six-condition selector changes the experiment, whereas camera and opacity controls only alter inspection. All downloadable records preserve that distinction.

## 6. Reproducibility and provenance

Scripts, original constructors, requirements, learned weights, source hashes and compact experiment artifacts are public. The bake uses local CUDA where supported; static hosts do not imply GPU execution. Artifact validation checks identities, hashes, sizes and finite arrays. Numerical tests verify independent physical identities and derivatives. Frontend tests establish offline/live MT parity and volume orientation. Browser and deployment checks are separate from numerical tests.

Two external SimPEG tutorial archives were downloaded and preprocessed locally, each with 289 observations. They serve as ingestion examples, not validation of field performance. Their pinned source and preprocessing hashes are public metadata, but observation values remain ignored pending redistribution review. Original public synthetic observations are independently generated.

## 7. Limitations and next research questions

The suite does not include realistic correlated noise, uncertain source wavelets, field terrain correction, anisotropy, elastic or attenuating wave physics, posterior inference, learned field-data transfer or petrophysical mixture priors. Known layer thickness simplifies MT. Limited seismic illumination and update budgets constrain velocity recovery. Cross-gradient magnitudes depend on normalization. The learned baseline comparison is not noise-matched or hyperparameter-exhaustive. Runtime values include implementation-specific overhead and are not performance benchmarks against external systems.

A defensible future study would pre-register acquisition and noise ensembles, match baseline tuning budgets, evaluate calibrated uncertainty, vary training geological families, and include license-cleared field datasets. A user study could test whether linking physical animation, residuals and explicit negative results improves interpretation. Those investigations have not been conducted here and no educational-efficacy claim is made.

## 8. Conclusion

The instrument makes several established inverse-problem failure modes directly inspectable with real computed outputs. The reported counterexamples show why model images, data misfit and learned scores must be considered together. Reproducibility and bounded claims are the software contribution; visual quality is necessary for inspection but is not scientific validation.

## References

1. Cockett et al. (2015), [SimPEG](https://doi.org/10.1016/j.cageo.2015.09.015).
2. Virieux and Operto (2009), [FWI overview](https://doi.org/10.1190/1.3238367).
3. Goyes-Peñafiel et al. (2025), [Physically Guided Deep Unsupervised Inversion for 1D Magnetotelluric Models](https://doi.org/10.1109/LGRS.2025.3528767).
4. [OpenFWI project](https://github.com/lanl/OpenFWI).
5. [Theoretical-practical geophysical inversion course](https://github.com/Anagabrielamantilla/inversion-geofisica-python), audited commit recorded in the research review.
6. [Deepwave FWI documentation](https://ausargeo.com/deepwave/example_fwi).

Further primary-source mappings and explicit deviations are in [the research review](../../docs/research/review.md).
