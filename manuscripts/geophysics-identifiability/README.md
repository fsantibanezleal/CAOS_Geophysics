# Inverse Earth Studio: synthetic geophysical inversion and numerical diagnostics

Technical software report · version 0.04.001 · 2026-09-26

Status: executable synthetic study, not a peer-reviewed manuscript. No algorithmic novelty, publication priority or field interpretation accuracy is claimed. The software integrates established methods to make their assumptions and failure modes inspectable.

## Abstract

Geophysical inverse results can appear convincing while remaining non-unique, prior-sensitive or poorly transferable. We present a reproducible instrument linking geological truth, observations, inverse models, residuals, conditional ensembles and recorded optimizer states across 20 distinct geological cases. Six conditions per case yield 120 experiments and 348 method results. The implemented methods include noise-weighted spatial potential-field inversion, bounded layered magnetotellurics and EDI ingestion, differentiable acoustic full-waveform inversion, cross-gradient and mixture-prior joint inversion, a learned column-density inverse and an observation autoencoder. Every method result states its physical target, units and recovery verdict. Static hosts replay hashed outputs from local computation. The release retains failed and unresolved results. Its contribution is an auditable experimental interface and reproducible composition of established methods, not a new inverse algorithm.

## 1. Motivation and related work

An inverse image is conditioned on a forward model, acquisition, noise model, parameterization and regularization. These conditions are frequently less visible than the resulting image. SimPEG's modular approach [1] makes those components explicit; established FWI analysis [2] explains how illumination and nonlinearity limit reconstruction. Physics-guided MT [3] shows how differentiable physics can constrain neural optimization without supervised model labels. Learned inversion benchmarks such as OpenFWI [4] emphasize the diversity of geological distributions that a learned method may encounter.

The source geophysics course [5] provided a coherent pedagogical sequence, but its notebooks are not redistributed. This implementation uses original geological constructors and independent code paths. It replaces an earlier inadequate interface that reused a single central anomaly. The rebuild treats visual differentiation as insufficient unless the underlying geological arrays, physics and results also differ.

## 2. Experimental design

The suite contains four gravity cases (intrusive stock, asymmetric basin, opposing contrasts, faulted dipping layer), four magnetic cases (dyke swarm, remanent slab, deep lens, crossing dykes), four MT soundings, four acoustic sections, two joint-structure hypotheses, and two withheld learned geometries. Each has reference, increased contrast, increased noise, changed acquisition, reduced coverage and increased regularization conditions. The acquisition perturbation is family-specific: height for potential fields, low-frequency extension for MT and source frequency for seismics. These are not claimed to be physically equivalent perturbations.

Every reference truth is hash-distinct. Each condition is independently forward-modelled and inverted. The canonical release records the exact method output arrays and metrics. Comparisons are made within a physical family and unit system; no aggregate accuracy score combines magnetic, gravity, resistivity and velocity errors.

## 3. Methods

### 3.1 Potential fields

SimPEG [1] supplies rectangular-prism gravity and magnetic sensitivity matrices on 10,752 cells (80 × 80 × 70 m) with 256 surface observations. Each active data row is divided by its supplied noise standard deviation. A positive spatial precision combines depth-weighted smallness and physical first differences at 240 m horizontal and 140 m vertical correlation scales. A data-space L2 solve selects its tradeoff by discrepancy; four smoothed-L1 smallness IRLS updates retain the spatial L2 term. The choice of depth exponent 0.375 used twelve independent calibration models, not the displayed truths. Vector magnetic inversion estimates three components per cell. The remanent case violates the scalar induced-field direction. Independent Choclo prism values check sign and physical scaling. Thirty-two conditional Gaussian-data perturbations measure estimator repeatability at fixed mesh, prior and tradeoff; they are not posterior geological samples.

### 3.2 Magnetotellurics

The standard complex impedance recursion propagates upward through isotropic layers from a homogeneous half-space. Layer thicknesses are known. Bounded trust-region least squares, direct Adam and a per-sounding tanh neural parameterization minimize the same mean squared real-component residual with the same resistivity bounds and adjacent-log-resistivity penalty. The neural method is conceptually related to [3], not a numerical reproduction of that paper. Half-space and homogeneous-layer splitting identities test physics; automatic-differentiation gradients and the browser forward model are checked independently. The local EDI path uses mt-metadata after strict input preflight, records native E/B to E/H conversion, time/sign, component orientation and stated variance conventions, preserves ancillary tipper missing-value masks, and rejects unsupported rotation or non-1D inversion. Three original analytic fixtures and separately seeded coverage experiments have distinct known-truth evaluation records; generic supplied EDI output has no truth field. A separate measured Clear Lake station is published as a tensor-screening record, not a layered inversion.

### 3.3 Seismics

Deepwave [6] computes constant-density acoustic propagation and gradients on 128×96 nodes with 12.5 m spacing. Three Ricker shots illuminate 40 receivers; the coverage condition uses 20. Time integration is 0.5 ms for 1.6 s with 300 m absorbing boundaries. Every fifth receiver, starting at index two, is withheld from optimization. Both methods use the same independent depth-trend initialization, data-derived coarse 1D background, 9×12 to 33×48 control grids and 28 strong-Wolfe L-BFGS calls per stage. One method uses full-band misfit throughout; the other applies 3, 5, 8 and 14 Hz low-pass stages before final full-band evaluation. Velocity is bounded to 1,400-4,400 m/s. Saved final model, prediction, residual and last replay state are evaluated together. Recovery labels require whole-model and active/withheld waveform improvement plus active and withheld WRMS no greater than two; improving the initial model alone is not sufficient. A CUDA directional difference and refined-grid forward comparison check the propagator separately. Pressure frames and receiver traces originate from the same physical simulation.

### 3.4 Joint and learned methods

Joint inversion compares uncoupled, cross-gradient and petrophysically guided solves on identical observations, uncertainty weights, independent L2 initialization and 80 strong-Wolfe L-BFGS calls. Cross-gradients use derivatives in metres. PGI here is an explicit negative-log two-property Gaussian-mixture prior fitted to 640 independently seeded synthetic laboratory-like density/susceptibility pairs, not the SimPEG PGI optimizer. Coupled methods are evaluated against the optimized uncoupled model for both density and susceptibility, not only against their common starting model. A deliberately conflicting case is a negative control for both structural and petrophysical coupling. Mixture memberships are conditional model diagnostics, not geological certainty.

The learned inverse predicts column density rather than non-identifiable depth-resolved structure. It uses two convolutions, adaptive pooling and two dense layers. The observation autoencoder has a 12-dimensional bottleneck. Four procedural training geometry families generate 800 training, 160 validation and 160 test realizations from disjoint seeds. The CNN and classical spatial inverse receive identical seeded noisy observations and are scored against the same column target. Validation selects weights; a separate 160-model calibration split fixes the autoencoder's 99th-percentile threshold; 80 withheld ring/cross geometries test it. Checkpoints and normalization are serialized and reloaded for parity tests. Case-level threshold flags are raw score comparisons, not validated geological classifications under changed contrast, acquisition, noise or station coverage. With omitted stations, reconstruction error is computed against the interpolated network input; raw-station discrepancy is reported separately. A regularization condition does not retrain either frozen network.

## 4. Results

The full reference-condition table is generated directly from artifacts in [results.md](../../docs/validation/results.md); all six conditions are available in the app and catalogue. These selected observations describe this fixed run, not a general ranking of algorithms.

Across all 348 method/condition results, the declared evaluator labels 133 recovered, 170 unresolved, 15 failed and 30 negative controls. These are case-specific diagnostic criteria, not comparable success probabilities. The layered reference velocity RMSE falls from 229.095 to 126.806 m/s with full-band FWI and 120.575 m/s with continuation. The normal-fault reference falls from 301.203 to 211.442 and 212.614 m/s respectively; the channel reference falls from 340.618 to 242.703 and 202.039 m/s. The salt/cycle-skipping reference remains a negative control: even at 629.456 m/s with continuation, deep recovery is poor. Full-band and continuation use matched background and update budgets; continuation does not win every comparison.

For the shared joint reference, independent L2 density RMSE is 0.1717462 g/cm³, cross-gradient 0.1722296 and PGI 0.171158. The PGI difference is about 0.34% relative to the matched uncoupled solution; the structural coupling is slightly worse. The conflicting case is a declared mixture-prior mismatch control. Its PGI density RMSE equals the independent 0.08154663 g/cm³ and is not presented as a petrophysical gain. The asymmetric-basin gravity L2 RMSE improves from the zero-model 0.2141267 to 0.1744869 g/cm³, but model correlation is only 0.2831, so that case remains unresolved. Reduced-coverage magnetic dykes have withheld residual near 11.64 noise standard deviations.

The held-out CNN column-density MSE is 680.15173 (g/cm³ m)² versus 1466.23818 for a spatial L2 baseline on identical noisy observations and the identical column target. Neither baseline is exhaustively tuned; this is a comparison within the fixed synthetic generator, not a state-of-the-art ranking. Withheld oblique and ring reference cases have CNN column RMSEs of approximately 91.19 and 89.06 g/cm³ m.

The autoencoder's threshold is fixed at the 99th percentile of a separate 160-model in-distribution calibration set. At that threshold it detects 0 of 80 withheld-family realizations, with one false alarm among 160 in-distribution tests and ROC AUC 0.4311. A changed-contrast display case can exceed the same threshold, but its score is not a validated causal diagnosis of unfamiliar geology; its case-level geological verdict is unresolved. The interface displays the aggregate failure and does not treat reconstruction error as a general detector of geological novelty.

Six sensitivity variants per case are independent controlled conditions, not uncertainty samples. The potential-field conditional intervals use 32 noise perturbations at fixed prior and tradeoff. On sixteen independently seeded evaluation models, only 0.0988 of voxel truth values fall inside nominal 95% intervals on average; support-region coverage is zero. MT half-space and two-layer interval coverage experiments are separate and condition on fixed thickness. Neither ensemble is a calibrated geological posterior.

### 4.1 Spatial discretization diagnostic

The local diagnostic compares original 14×12×8 and refined 28×24×16 potential-field grids with a 56×48×32 discretization at 36 common receivers. Uniform-prism subdivision agrees within 1.73×10⁻⁹ relative difference. Ten of twelve geological responses move closer to the fine-grid reference. The basin and opposing-body responses do not: cell-centre sampling of discontinuous boundaries is not monotonically convergent. The fine grid is a numerical reference, not exact geological truth. Results are preserved in [refinement.json](../../docs/validation/refinement.json).

An independent seismic forward comparison at refined space/time increments gives relative receiver-trace L2 difference 0.00268063 for the declared test section. This is a bounded discretization check, not a full dispersion or geological convergence study. The current 0.04 inverse uses 1.6 s traces; the earlier 1.1 s display-case result is not carried forward as a current recovery metric.

## 5. Visualization as an inspection instrument

Potential fields provide cell geometry and piecewise-linear surfaces of the selected property model, camera rotation, northing cuts and a surface observation plane. MT uses thickness-scaled layers and frequency-dependent response plots. Seismic playback advances computed pressure states with geological interfaces and a synchronized gather time cursor. A separate replay advances inverse-model updates. The learned views compare the correct 2D target or observation reconstruction instead of borrowing an unrelated 3D surface.

Colour scales carry units. Paired models use shared scales; seismic display gain is fixed and explicitly clips colours at legend bounds. Pointer readouts retain original numerical cell values. Interpolation is a display operation and is not advertised as increased resolution. The six-condition selector changes the experiment, whereas camera and opacity controls only alter inspection. All downloadable records preserve that distinction.

## 6. Reproducibility and provenance

Scripts, original constructors, requirements, learned weights, source hashes and computed experiment artifacts are public. The bake uses local CUDA where supported; static hosts do not imply GPU execution. Artifact validation checks all 120 conditions, 348 method cells, identities, hashes, sizes, final state alignment and the EDI bundle. The complete numerical suite passed 93 tests, including independent physical identities, withheld-data separation, solver state identity and CUDA derivatives. The release validator recalculates model and data diagnostics from exported arrays and records all verdicts. Frontend tests establish offline/live MT parity, volume orientation and display-state contracts. Browser and external deployment checks remain separate gates.

Two external SimPEG tutorial archives were downloaded and preprocessed locally, each with 289 observations. They serve as ingestion examples, not validation of field performance. Their pinned source and preprocessing hashes are public metadata, but observation values remain ignored pending redistribution review. An independently downloaded 42-frequency Clear Lake MT station is screened from a hash-pinned EDI and cited to the USGS release and EarthScope EMTF collection. Its diagonal and antisymmetry WRMS greatly exceed the necessary 1D limits, so no layered inverse is exported. Original public synthetic inversion observations remain independently generated.

## 7. Limitations and next research questions

The suite does not include realistic correlated noise, uncertain source wavelets, field terrain correction, anisotropy, elastic or attenuating wave physics, posterior inference or demonstrated learned field-data transfer. Known layer thickness simplifies synthetic MT and EDI inversion. The single measured EDI screen is not a field inversion or a validation of recovered geology. The fitted mixture prior uses authored independent samples and does not establish transferable rock-physics relationships. Limited seismic illumination and update budgets constrain velocity recovery. Cross-gradient and mixture-prior results depend on fixed normalization and sample choice. The learned/classical baseline is noise-matched, but not hyperparameter-exhaustive. Runtime values include implementation-specific overhead and are not performance benchmarks against external systems.

A defensible future study would pre-register broader acquisition/noise ensembles, evaluate calibration under forward-model and geological uncertainty, vary training families and use license-cleared field datasets. A user study could test whether linking wavefields, residuals and explicit negative results improves interpretation. Those investigations have not been conducted here and no educational-efficacy claim is made.

## 8. Conclusion

The instrument makes several established inverse-problem failure modes directly inspectable with real computed outputs. The reported counterexamples show why model images, data misfit and learned scores must be considered together. Reproducibility and bounded claims are the software contribution; visual quality is necessary for inspection but is not scientific validation.

## References

1. Cockett et al. (2015), [SimPEG](https://doi.org/10.1016/j.cageo.2015.09.015).
2. Virieux and Operto (2009), [FWI overview](https://doi.org/10.1190/1.3238367).
3. Goyes-Peñafiel et al. (2025), [Physically Guided Deep Unsupervised Inversion for 1D Magnetotelluric Models](https://doi.org/10.1109/LGRS.2025.3528767).
4. [OpenFWI project](https://github.com/lanl/OpenFWI).
5. [Theoretical-practical geophysical inversion course](https://github.com/Anagabrielamantilla/inversion-geofisica-python), audited commit recorded in the research review.
6. [Deepwave FWI documentation](https://ausargeo.com/deepwave/example_fwi).
7. [SimPEG PGI documentation](https://docs.simpeg.xyz/dev/content/api/generated/simpeg.regularization.PGI.html) and [Astic et al.](https://arxiv.org/abs/2002.09515), used to distinguish mixture priors from structural cross-gradients.
8. [SciPy bounded least squares](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html) and [MTpy-v2 EDI documentation](https://mtpy-v2.readthedocs.io/en/latest/notebooks/mt_object.html).
9. [USGS Clear Lake data release](https://doi.org/10.5066/P14KAQ3M) and [EarthScope EMTF transfer-function collection](https://doi.org/10.17611/DP/EMTF/GMEG/Clearlake), sources for the measured `cl061` screening record, not for synthetic inversion validation.

Further primary-source mappings and explicit deviations are in [the research review](../../docs/research/review.md).
