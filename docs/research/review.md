# Research and implementation review · 2026-09-23

## Course as a source, not a product template

The [Mantilla course repository](https://github.com/Anagabrielamantilla/inversion-geofisica-python) was rechecked at commit `0084021fcc6c1d2f112b144e6e5f0a3d92f20dff`, unchanged from the 2026-09-13 audit. Its 17 notebooks connect inverse-problem foundations, 3D gravity/magnetics, physics-guided MT, FWI and learned subsurface characterization. Colab paths, mixed dependency assumptions and missing explicit redistribution licensing prevent treating it as a self-contained deployable product. No notebook, recorded class, course illustration or raw course dataset is copied into this repository.

The topic sequence is useful; the earlier app's repeated central anomaly and decorative angle animation were not an adequate realization. This rebuild replaces that implementation rather than defending it. Scientific questions now distinguish basins, faulted layers, opposing contrasts, dykes, remanence, conductors, salt and distribution shift.

## Source-to-implementation decisions

| Primary source | What it establishes | Applied here / difference |
|---|---|---|
| [Cockett et al. 2015](https://doi.org/10.1016/j.cageo.2015.09.015) | Modular simulation, sensitivities and inverse objectives | SimPEG integral operators; custom explicit data-space regularization, not a claim of reproducing all SimPEG directives |
| [SimPEG gravity inversion tutorial](https://simpeg.xyz/user-tutorials/inv-gravity-anomaly-3d/) | Cartesian upward-z convention, uncertainty weighting, regularized inversion | Exact prism operators, original geometry, L2 and IRLS; no terrain inversion claim |
| [SimPEG magnetic inversion tutorial](https://simpeg.xyz/user-tutorials/inv-magnetics-induced-3d/) | Inducing-field and susceptibility assumptions for TMI | Induced and deliberately remanent cases; separate vector parameterization |
| [Choclo kernels](https://www.fatiando.org/choclo/latest/overview.html) | SI potential-field prism kernels and coordinate conventions | Independent gravity certificate, converting kg/m³ and m/s² to g/cm³ and mGal |
| [Heagy et al. 2017](https://doi.org/10.1016/j.cageo.2017.06.018) | Electromagnetic simulation/inversion architecture | Context for complex response fitting and differentiable inversion |
| [Goyes-Peñafiel et al.](https://arxiv.org/abs/2410.15274v3), [published DOI](https://doi.org/10.1109/LGRS.2025.3528767) | Physics-guided unsupervised 1D MT inversion via a differentiable forward operator | Original small PyTorch per-sounding network; not a reproduction of their TensorFlow architecture or published accuracy claims |
| [MTpy-v2 documentation](https://mtpy-v2.readthedocs.io/en/stable/index.html) | MT metadata, EDI and processing workflows | Reference only. The v2 browser imports layered models, not EDI field data |
| [MTH5](https://doi.org/10.1016/j.cageo.2022.105102) | Structured MT data/provenance format | Reference for future field-data interoperability, not an implemented HDF5 pathway |
| [Virieux and Operto 2009](https://doi.org/10.1190/1.3238367) | FWI assumptions, illumination, nonlinearity and cycle skipping | Explicit acoustic/limited-shot scope; model error accompanies waveform loss |
| [Deepwave FWI documentation](https://ausargeo.com/deepwave/example_fwi) | Differentiable propagation, bounded velocity, frequency continuation | Compiled CUDA forward/adjoint; 28 Adam updates and moving-average continuation, not the tutorial's full multiband Butterworth/L-BFGS procedure |
| [Deepwave source](https://github.com/ar4/deepwave) | Runtime API and differentiable propagator | Pinned local 0.0.27 with actual CUDA gradient tests |
| [Devito FWI tutorial](https://www.devitoproject.org/examples/seismic/tutorials/03_fwi.html) | Symbolic finite differences and adjoint modeling | Alternative surveyed; not a v2 execution engine |
| [SimPEG joint inversion tutorial](https://docs.simpeg.xyz/latest/content/user-guide/tutorials/13-joint_inversion/plot_inv_3_cross_gradient_pf.html) | Structural coupling between potential-field models | Dimensionless cross-gradient penalty; shared and conflicting structures |
| [SimPEG PGI](https://docs.simpeg.xyz/v0.25.0/content/api/generated/simpeg.regularization.PGI.html) | Petrophysically guided mixture priors | Surveyed, not implemented or presented as an available method |
| [InversionNet](https://doi.org/10.1109/TCI.2019.2956866) | Learned observation-to-model inversion and training-distribution dependence | Conceptual comparison only; our network predicts gravity column density, not seismic velocity |
| [OpenFWI](https://github.com/lanl/OpenFWI) | Diverse benchmark families and learned baseline evaluation | Motivates held-out geometry tests. No OpenFWI accuracy, trained weights or field generalization is claimed |
| [Implicit representation FWI](https://doi.org/10.1029/2022JB025964) | Neural parameterizations as inverse priors | Related work; not implemented |
| [Physics-informed geophysical inversion review](https://doi.org/10.1190/geo2023-0615.1) | Broader physics-informed inversion context | Related work, not evidence validating this implementation |

## State-of-the-art boundary

Sparse regularization, vector magnetization, differentiable wave propagation, structural coupling and learned priors are established techniques. A polished interface does not make them new algorithms. Contemporary field-scale systems address terrain, anisotropy, elastic physics, realistic noise, instrument response, uncertainty and much larger acquisition/model spaces. This repository intentionally exposes a bounded synthetic investigation suite with exact provenance rather than implying parity with those systems.

The implemented CNN/autoencoder are compact baselines, not SOTA neural architectures. The CNN learns a depth-integrated target to avoid presenting a learned 3D reconstruction as identifiable from one gravity map. Its classical comparison is deliberately described in full, including the favourable noise-free baseline input. The autoencoder score is an empirical distribution-shift diagnostic, not calibrated epistemic uncertainty.

## Scientific demonstration and manuscript decision

The useful demonstration is the contrast between visually persuasive models and physical evidence: remanence breaks an induced assumption; joint coupling can bias incompatible structures; a better waveform fit can retain a large velocity error; a held-out geometry challenges a learned prior. These are established phenomena shown in an integrated, reproducible instrument. A technical software report is warranted. Algorithmic novelty or publication priority has not been established, so the manuscript explicitly makes neither claim.

## Acquisition and licensing

Two separately pinned SimPEG tutorial archives contain 289 observations each. Local preprocessing checks hashes, rejects nonfinite/duplicate data, assigns an explicitly assumed noise floor, and writes ignored NPZ files. No source archive or derived observation table is republished until upstream redistribution rights are resolved. Public experiments use original geological constructors and independently generated physical responses. URLs, SHA-256 and transformations are in `data/source-ledger.json` and `data/external-preprocessing.json`.

## Reproducibility versus illustration

The browser displays solver outputs, not substitute analytic patterns. The only independent online solver is the layered MT recursion, tested against every offline truth sounding. Three-dimensional orbit is a camera operation; wave replay represents acoustic time; inversion replay represents saved optimizer states. Interpolation/gain are labelled display operations. No animated overlay is used as evidence for resolution or uncertainty.

## Original-scope reconciliation, 2026-09-24

The older plan also mentioned PGI, EDI ingestion and ensemble uncertainty. They are not implemented in this release. A new review of the primary implementation references confirms that a cross-gradient penalty is not a petrophysical Gaussian-mixture prior, and model import for browser forward modelling is not an EDI observation workflow. Keep those boundaries explicit rather than treating UI labels as delivered algorithms.

- [SimPEG 0.25.2 PGI linear example](https://docs.simpeg.xyz/v0.25.2/content/user-guide/examples/10-pgi/plot_inv_0_PGI_Linear_1D.html): an actual mixture-prior inversion and its regularization/directive structure.
- [Astic et al., multi-physics inversion with a dynamic Gaussian mixture model](https://arxiv.org/abs/2002.09515): the multi-property PGI research reference.
- [MTpy-v2 core documentation](https://mtpy-v2.readthedocs.io/en/latest/mtpy.core.html): transfer-function tensors, impedance-unit choices and NED/ENU conventions that an EDI pipeline must preserve.
- [USGS legacy MT preservation software](https://www.usgs.gov/data/software-process-and-preserve-legacy-magnetotelluric-data): provenance-sensitive conversion into EDI; a surveyed resource, not an executed product adapter.
