# Scientific motivation

An inverse image can look geologically persuasive even when multiple models explain the data, the assumed physics are violated, or a withheld acquisition subset is poorly predicted. This is familiar across geophysics: potential-field inverses are non-unique; MT dimensionality and component quality condition whether a 1D interpretation is defensible; seismic inversion depends on illumination, bandwidth, starting model, and cycle skipping; and coupled or learned estimates inherit their structural or training priors. A low objective is evidence about a specified objective under a specified data model. By itself, it is not evidence of unique or accurate geology.

The topic sequence draws on the public theoretical-practical geophysical inversion course by Mantilla. Its notebooks, recordings, images, and raw data are not redistributed. The source commit was `0084021fcc6c1d2f112b144e6e5f0a3d92f20dff` (Mantilla course). The research survey distinguishes primary sources from implementation choices and identifies where the methods differ from cited work (`docs/research/review.md`). The aim is to connect domain assumptions, executable calculations, diagnostic evidence, and failure states within one inspectable project.

The method suite has three tiers. **Classical methods** establish data conventions and reproducible baselines. **State-of-the-art (SOTA) methods** implement established numerical or learned approaches with independent checks and explicit comparison criteria. **Beyond-SOTA (BS)** identifies a falsifiable research proposal, without implying a successful result or established novelty. Method definitions and numerical assumptions are in `docs/design/SDD.md`.

# Software and evidence design

### 2.1 Evidence chain

The intended data flow follows the path

`source → immutable raw asset → validated dataset → processing → model/survey → solve → evaluation → result/export`.

At each boundary the contracts carry modality, named dimensions and order, coordinate frame or specified local coordinates, units, geometry, masks and reasons, uncertainty, parent identities, code/environment information, and hashes as applicable. Unknown units, datum, signs, component orientation, rights, or response conventions are reasons to reject or quarantine an input rather than infer missing facts. Known truth is attached only to explicitly synthetic cases. Field observations may be screened and processed, but a synthetic constructor is never substituted for missing field provenance or truth.

The application separates three execution contexts. Visitors can inspect public material and use only those browser calculations whose client-side behavior has been validated. Authenticated project workflows are designed to isolate upload, ownership, and bounded worker execution on the single canonical ML VPS origin. Larger training, extensive FWI, and full bake workflows remain local CPU/GPU pipelines. A static or browser replay of a saved artifact is not represented as an online inverse solve. The specified deployment uses one bounded ML VPS service. Its capacity and numerical job behavior have not been measured on the live host.

### 2.2 Reproducible software artifacts

The software contains a Python data pipeline and solver implementations, generated and source-controlled scientific outputs, JSON contracts and validation outputs, frontend TypeScript/React instruments, and computational notebooks in English and Spanish. The user-facing browser is intended to display computed arrays and explicit physical axes, not to invent a second approximate result for animation. Physical result records distinguish observations, predictions, signed residuals, model values, objective terms, coverage and uncertainty diagnostics, stopping state, and provenance. Display interpolation or color mapping is a rendering operation and must not be mistaken for increased model resolution.

Notebooks are part of the research material, not merely screenshots. Their lessons explain assumptions, execute the named calculations, show numerical outputs, compare with independent identities or baselines when available, and retain unresolved results. The bilingual content was corrected where translations, counts, or numerical interpretations differed. Execution and translation checks establish neither field validity nor educational efficacy.

# Data and experimental scope

### 3.1 Authored synthetic experiments

The original canonical suite uses independently constructed geological geometries instead of repeating one centered anomaly. Its earlier 0.04 report describes 20 distinct cases and six controlled conditions per case (120 experiments, 348 method results). The conditions vary contrast, noise, acquisition, coverage, or regularization according to the physical family; they are not interchangeable perturbations and are not samples from a geological population. Later repository work adds separate survey, uploaded-data, learning, and source-screening experiments. Therefore the older 120-experiment suite is a defined artifact family, not a count of every experiment now present in the repository.

Synthetic constructors provide known truth for controlled tests of forward physics and conditional inversion behavior. They do not encode the full complexity of field geology. Noise perturbations at fixed mesh/prior/tradeoff measure conditional estimator repeatability, not posterior uncertainty. A held-out line, shot, family, or acquisition tests only the specified split and comparator. Repeated numerical trials from one generator do not establish field performance.

### 3.2 External data and eligibility

Two SimPEG tutorial archives are independently pinned and locally preprocessed as ingestion examples. The source documentation states that their derived observation tables are not redistributed while upstream redistribution rights remain unresolved. They are not field validation. The measured Clear Lake EDI station cl061 is hash-pinned and cited to the USGS and EarthScope data releases \cite{usgsClearLake,earthscopeClearLake}. Its impedance tensor fails the required 1D consistency screen; it remains a QC-only dataset, and no layered inversion or geological result is claimed.

Other data paths include provider-linked or rights-restricted data. For example, the Slagdump ERT raw asset is absent locally under its provider-link-only status; focused notebook checks consequently skip tests that require those bytes. The Koenigsee travel-time lesson is an authored synthetic method control and does not establish execution on the provider-linked case. The M13 STEAD excerpts \cite{mousavi2019} and associated project-trained checkpoint have a scoped redistribution decision with attribution; that decision does not generalize to other data or establish model accuracy. Rights, data custody, field eligibility, numerical correctness, and scientific validation remain separate decisions.

# Methods

The method identifiers below follow `docs/design/SDD.md`. Each entry names an implementation and its tests; this does not imply validated use for every input or a complete end-to-end workflow.

\begin{center}\small
\begin{longtable}{@{}p{0.12\textwidth}p{0.40\textwidth}p{0.41\textwidth}@{}}
\toprule
ID and tier & Executable method and purpose & Principal limitations \\
\midrule
\endfirsthead
\toprule
ID and tier & Executable method and purpose & Principal limitations \\
\midrule
\endhead
M-1 Classical & Gravity station corrections, datum and uncertainty lineage, and transforms with safeguards against duplicate corrections. & Field eligibility still depends on exact source, datum, instrument, and uncertainty lineage. A local adapter pass does not validate arbitrary field tables. \\
M-2 SOTA & Weighted 3D gravity prism forward/inverse calculations, including a bounded L2 survey inversion and comparison with independent prism physics. & Non-uniqueness persists; a good data fit or a visually compact body does not identify geology. Full-survey and field performance remain untested. \\
M-3 Classical & Aeromagnetic line/tie-line/height checks, blocked line holdout, support-aware gridding, and physically supported upward continuation. & Authored survey controls do not establish broad provider-data validation or field magnetic inversion. \\
M-4 SOTA & Induced-magnetization prism forward modelling and physical objective/derivative construction, checked against Choclo. & A full nonzero survey inverse with held-out evaluation is not included in the available evidence. Remanence violates the induced-direction assumption. \\
M-5 Classical & MT EDI component, variance, rotation, tipper, and dimensionality screening. & A tensor record is not automatically eligible for a 1D inverse. cl061 remains QC-only. \\
M-6 SOTA & Layered-earth complex-impedance response and bounded 1D inversion, with cross-checks against MTpy and browser/local analytic cases. & Known layer thickness and isotropic 1D assumptions constrain the synthetic inverse. The cl061 field screen fails. \\
M-7 SOTA & 2D ERT processing/inversion with electrode geometry, topography, reciprocal/QC logic, blocked holdout, and explicit failed-inverse states. & Rights-restricted raw data are not fabricated or represented as executed; independent comparison and some field paths remain open. \\
M-8 Classical & MiniSEED/StationXML waveform handling, response-aware filtering, STA/LTA or matched-arrival picks. & Response epochs, units, gaps, and channel orientation are strict eligibility conditions. Classical picks are not universal truth labels. \\
M-9 SOTA & First-arrival travel-time inversion with explicit source/receiver geometry, bounded velocity, ray coverage, and held-out-shot comparison against a baseline. & The executed teaching control is synthetic and uses a straight-ray/Dijkstra model; the synthetic control does not represent provider-linked field data. \\
M-10 SOTA & Acoustic constant-density FWI with Deepwave, bounded velocity updates, full-band and frequency-continuation schedules, active/withheld receiver diagnostics, and saved optimizer states. & Non-convexity, cycle skipping, limited illumination, inverse crime from using the same forward engine, and acoustic-only physics remain material limitations. Some cases improve model RMSE but fail the specified noise-consistency criterion. \\
M-11 SOTA & Joint potential-field inversion comparing uncoupled fits, spatial cross-gradient coupling, and an explicit Gaussian-mixture petrophysical prior. & The project Gaussian-mixture-prior implementation is not the SimPEG PGI optimizer. Coupling can trade one property against another; one calibration matrix does not establish general performance. \\
M-12 SOTA & A learned seismic-velocity inversion trained on disjoint procedural families and compared with a same-input classical solve and independent quadrature forward operator. & The frozen joint family/acquisition holdout fails both prespecified ratios; training success does not override the held-out result. \\
M-13 SOTA & PhaseNet-family P/S inference \cite{zhu2019}, matched classical comparison, and local browser ONNX inference with explicit preprocessing and abstention rules. & Curated browser parity is runtime consistency, not accuracy. Population metrics come from the separate locked test cohort and analyst references, not geological truth. \\
BS-1 research proposal & Geometry-normalized backprojection of travel-time residuals, divided by path length and cell coverage, supplied with a coverage channel to a bounded residual CNN. & It is a falsifiable refinement proposal. The initial checkpoint 3.1 failed the joint-shift comparison; the later null-space-constrained variant gives a narrow synthetic improvement but does not change the M12 checkpoint result or establish field transfer. \\
\bottomrule
\end{longtable}
\end{center}

### 4.1 Potential-field inverses

The gravity and magnetic experiments use SimPEG rectangular-prism sensitivity operators \cite{cockett2015,heagy2017}, explicit survey geometry, uncertainty-weighted data residuals, and spatial regularization. The canonical potential-field setup uses a 10,752-cell mesh and 256 surface observations (`docs/research/scientific-implementation.md`). L2 and smoothed-L1 IRLS solutions are distinct estimators, not interchangeable render styles. Magnetic cases include scalar induced assumptions and vector magnetization so that remanence can be exposed as model misspecification. Choclo prism values \cite{choclo} provide an independent physical check for sign and scale in specified comparisons. Sensitivity and conditional noise ensembles are not interpreted as calibrated geological posterior intervals.

The current result table includes a gravity deep-body example for which weighted WRMS is 1, while model correlation is only 0.283 and recovered centroid depth is approximately 570 m versus a synthetic truth near 282 m. This is not a paradox: the inverse fits the observations at the chosen noise scale while regularization and limited information admit a different model. The structure is unresolved despite the weighted data fit.

![M01 authored synthetic control. Upper left: original station disturbance and blocked holdout or masked locations. Upper right: harmonic continuation to 300 m. Lower left: propagated conditional noise standard deviation, with blank cells unsupported. Lower right: signed prediction residuals at original receiver locations. The figure is synthetic and does not represent field measurements.](figures/m01-height-continuation.png){width=95% fig-pos="!t"}

### 4.2 MT, ERT, and waveform processing

The MT response is calculated through the complex impedance recursion for isotropic layers; differentiable physics-guided inversion is a related approach \cite{goyes2025}. EDI ingestion is a transfer-function workflow and preserves conventions, units, rotations, masks, and stated variances; EDI is not treated as raw time-series data. Multiple optimizers (bounded least squares, Adam, and a small per-sounding neural parameterization) address matched objectives in synthetic fixtures. A neural architecture related conceptually to physics-guided inversion \cite{goyes2025} is not asserted to reproduce the cited paper's architecture or published results.

ERT workflows validate electrode/ABMN structure, QC and topographic factors before inversion, following established 2D methods such as PyGIMLi \cite{pygimli}. The numerical examples distinguish authored controls from absent or restricted field assets and retain failed inversions. Seismic preprocessing distinguishes instrument counts, response-corrected units, filters, gaps, and sample windows. Classical picking and M13 learned inference consume explicitly specified traces; analyst picks are reference annotations, not subsurface truth.

### 4.3 Travel-time tomography, FWI, and joint inversion

Travel-time inversion uses specified ray geometry and a training/withheld partition. Its velocity maps are interpreted together with ray support; unsupported cells do not receive equivalent evidential status. The M09 bilingual lesson calls the product inverse core on an authored refracting two-layer survey and compares complete withheld shots with a training-only homogeneous baseline. This is a bounded synthetic calculation.

The FWI implementation uses constant-density acoustic propagation \cite{virieux2009,deepwave}, a fixed acquisition family, bounded velocity, a data-derived coarse background, and matched update budgets for full-band and frequency-continuation schedules. Active and withheld receiver WRMS accompany model RMSE. A lower model RMSE can coexist with residuals above the specified noise level. The four-case computation includes a layered reflection, a fault, a salt/cycle-skipping negative control, and a low-velocity channel. Its case-level results are not generalized to field-scale FWI or elastic/attenuating physics.

Joint inversion compares uncoupled and coupled estimates against the same observations and independent baselines. Cross-gradient coupling promotes structural similarity, while a Gaussian-mixture prior adds a distinct petrophysical assumption \cite{simpegJoint,astic2020}. These mechanisms are reported separately. In the shared synthetic case, cross-gradient slightly improves susceptibility RMSE while worsening density RMSE relative to the optimized uncoupled solution; the mixture-prior method slightly improves density RMSE while slightly worsening susceptibility. Neither is a joint two-property recovery gain. In a deliberately conflicting case, the negative control rejects a general claim that structural or petrophysical coupling must help.

### 4.4 Learned methods and the beyond-established experiment

The original gravity CNN predicts column density rather than a depth-resolved volume, reflecting the non-identifiability of depth from one potential-field map. Learned inverse benchmarks also show sensitivity to the sampled geological families \cite{openfwi}. Its comparison with a spatial L2 baseline uses identical seeded noisy observations and a shared column target. The autoencoder's threshold is selected on a separate calibration set and tested on withheld geometries; its measured failure to detect the withheld family is retained. These models are compact baselines and are not described as state of the art.

M12 predicts seismic velocity from travel-time data and is evaluated by family/acquisition-disjoint cohorts. The 2026-10-28 M12 computation used 160 joint family/acquisition holdouts with learned/classical velocity RMSE 536.99/95.62 m/s (ratio 5.616) and independent-oracle travel-time RMSE 28.61/2.34 ms (ratio 12.231; source: `docs/validation/m12-checkpoint-notebook-2026-10-28.md`). Both pre-specified comparison criteria fail. A separate checkpoint 3.1 run also fails its specified joint-shift comparisons. The separate null-space-constrained residual study reports velocity RMSE ratio 0.9701 (paired case-bootstrap interval 0.9661–0.9737) and independent travel-time RMSE ratio 0.9967 (0.9950–0.9983); the aggregate ratios improve in all four fixed held-out cohorts. The v1.1 scorer used an infinite threshold, so the saved exceedance counts are not a valid threshold assessment and are not interpreted here. The paired intervals resample case IDs and compute the ratio of mean per-case RMSEs over 20,000 PCG64 draws (seed 6122026); the exact calculation is retained in `docs/validation/m12-nullspace-v1_1-bootstrap-2026-10-30.json`. These intervals quantify variation within the fixed synthetic cohorts, not natural-geology uncertainty. The result is specific to that protocol and cohort. It does not change the failing M12 checkpoint result, establish geological recovery, or demonstrate field transfer.

BS-1 asks whether a dimensionally consistent, coverage-conditioned learned residual improves on a matched classical inverse under geometry shifts. The proposal is falsifiable because model and independent forward-data ratios are frozen and both must be below one for an advantage claim. The differing outcomes show why protocol and checkpoint identity must accompany each comparison.

# Selected results and interpretation

### 5.1 Reference-condition outcomes

The reference-condition summary lists 122 recovered, 184 unresolved, 6 failed, and 36 negative-control method results (source: `docs/validation/results.md`). These are case-specific outcomes. They must not be summed into an overall accuracy or treated as success probabilities because the cases, units, target variables, and criteria differ. Failure and unresolved outcomes are first-class evidence in this project.

### 5.2 FWI case matrix

The bilingual case-matrix lesson reads four hash-verified full-run arrays (`notebooks/en/06-seismology/05-m10-fwi-case-matrix.ipynb`; Spanish counterpart). Layered reflection and fault are labeled recovered under the case-specific criteria; salt remains a cycle-skipping negative control; and the low-velocity channel remains unresolved. For the channel, model RMSE improves relative to the starting model (ratio 0.521 for the continuation result), but fitted/withheld WRMS are 2.071/2.213 against the specified unit noise scale. This contrast shows why improvement from a starting model is not sufficient. The notebook re-analyzes saved output rather than re-solving FWI, and an independent propagator comparison is needed to test sensitivity to using the same forward engine.

### 5.3 EDI screening and phase picker

The observed cl061 EDI tensor is screened against necessary 1D consistency conditions and fails them. It remains QC-only. It provides no 1D resistivity model for cl061 and makes no geological interpretation from that station. For M13, the 2026-10-27 local browser parity computation reports all 23 valid selected display traces matching CPU ONNX Runtime: maximum absolute probability difference 5.0664×10⁻⁶, no P/S peak displacement, and matching accepted/abstained picks within one sample. A twenty-fourth selected trace is QC-rejected and never inferred. The separate locked 6,000-trace benchmark, not this curated 23-trace subset, is the population-level performance record. Even that benchmark compares predictions with analyst annotations and should not be described as geological truth.

### 5.4 Nullspace-constrained learned refinement

The null-space-constrained computation uses a fixed cohort and reports velocity and independent forward-data ratios with paired case-bootstrap intervals. Each replicate resamples case IDs and computes the ratio of mean per-case RMSEs; 20,000 PCG64 draws use seed 6122026. The exact intervals, method protocol and receipt hash are archived with the computational outputs. For the joint-OOD cohort, velocity RMSE ratio is 0.9701 with interval 0.9661–0.9737; independent travel-time RMSE ratio is 0.9967 with interval 0.9950–0.9983. The metrics show a small synthetic aggregate difference and do not establish a practical gain across field settings. Field robustness, performance under realistic source/model error, and reproduction by an external group have not been evaluated. The v1 computation was invalidated by a dimensional feature error; the checkpoint 3.1 computation remains a failed comparison.

# Educational and visualization design

The bilingual notebook sequence covers inverse-problem foundations, gravity, magnetics, MT, ERT, seismology, joint inversion, and learning. Lessons include progressively deeper content: from units and forward physics to actual solver calls, held-out evaluation, sensitivity analyses, independent oracles, and negative controls. The notebooks are intended as research and teaching materials, but no educational efficacy study has been performed. The source course is cited as inspiration; its instructional materials are not copied into the product.

Scientific visualization is organized around the method's actual state variables. Potential-field scenes show geometry, cells, survey observations, cuts, and physical property scales; MT views show layer structure and frequency response; seismic instruments relate wavefields, receiver gathers, and inversion state; learned methods show their actual target arrays and comparison metrics. Camera rotation changes viewpoint, not physics. Time cursors and optimizer-state replay address different quantities and are labeled accordingly. A rendered state alone is not evidence of uniqueness, resolution, or uncertainty.

The scientific views expose physical geometry, survey support, and computed states. Their effect on interpretation has not been measured in a user study, and browser performance has not been characterized across devices, routes, languages, and themes.

# Computational reproducibility

All 60 bilingual notebooks were run from top to bottom in fresh kernels on 30 October 2026. The computation comprised 57 unchanged notebooks and three refreshed notebooks; none ended with an execution error. Focused fresh-kernel replays of the refreshed examples then passed. The complete replay used `scripts/run_notebooks.py --check` with external scratch storage. Notebook sources are under `notebooks/en/` and `notebooks/es/`.

Numerical outcomes are tied to their method-specific computation and date. The FWI case matrix reads hash-verified outputs and does not rerun the expensive inverse; its source is `notebooks/en/06-seismology/05-m10-fwi-case-matrix.ipynb` and the Spanish counterpart. The M12 notebook computation dated 28 October and browser-parity computation dated 27 October are documented computations in `docs/validation/m12-checkpoint-notebook-2026-10-28.md` and `docs/validation/m13-browser-population-parity-2026-10-27.md`. The null-space refinement results and cohort definitions are in `docs/design/features/m12-velocity-validation/nullspace-v1_1-protocol.md`. Reference-condition metrics are in `docs/validation/results.md`. Method equations, implementation details, and primary-source mapping are in `docs/research/scientific-implementation.md`, `docs/research/review.md`, and `docs/design/SDD.md`.

Notebook replay verifies execution for the recorded source and environment; it is not an independent physical oracle. Scientific replication requires using the method-specific data, environment, split, seed, operator, and comparison criteria together. A lesson that reads an archived computation must not be described as having recomputed that solve.

# Limitations and open research questions

1. **Field validation and eligibility.** Most quantitative recovery results are synthetic. Provider data with incomplete datum, uncertainty, rights, or provenance remain unresolved or ineligible. cl061 is a QC failure for 1D inversion, not a field inverse.
2. **Non-uniqueness and uncertainty.** Conditional ensembles do not sample geological posterior uncertainty. Potential-field structure remains prior- and parameterization-dependent. Coverage and sensitivity do not by themselves yield calibrated resolution.
3. **FWI scope.** The experiments use bounded acoustic physics and fixed synthetic acquisition families. Source uncertainty, realistic correlated noise, anisotropy, elasticity, attenuation, broader cycle-skipping regimes, and an independent propagator remain necessary research directions.
4. **Joint inversion.** Cross-gradient and mixture-prior outcomes depend on their scale, prior, and structural compatibility. The limited calibration matrix does not establish general superiority over optimized single-modality estimates.
5. **Machine learning.** The M12 learned-velocity calculation fails its pre-specified joint-shift comparison. The positive null-space variant is narrow synthetic evidence and needs external reproduction and broader cohorts. The phase-picker's 23-trace parity set is not an accuracy cohort; the separate 6,000-trace benchmark uses analyst annotations whose uncertainty limits the interpretation of timing scores.
6. **Data and reproducibility.** Some numerical tests require retained external inputs, including joint-inversion matrices and magnetic controls. Missing inputs are not replaced with synthetic stand-ins. Rights-limited source files are not copied merely to make a computation executable.
7. **Service capacity.** Local solver tests, builds, and browser parity do not establish worker admission, VPS capacity, cancellation, or recovery. Replacement-service capacity and operational behavior remain unmeasured.
8. **Educational effectiveness.** A bilingual executable notebook collection is a learning resource, but no controlled study establishes learning outcomes or comparative pedagogical effectiveness.

Useful next studies include preregistered geological-family and acquisition/noise ensembles; external reproduction of the BS-1 result; calibration under forward-model and geological uncertainty; independent FWI propagation; licensed field inversions with source/datum/error review; and user studies of whether linking assumptions, predictions, residuals, and uncertainty improves interpretation.

# Conclusions

Inverse Earth Studio combines source-linked geophysical processing and inverse methods with explicit assumptions, independent physical checks where available, and preserved negative evidence. Its central examples show that data fit, model recovery, transfer, and visual plausibility are different questions. The workbench includes synthetic and bounded real-data screening calculations, bilingual executable notebooks, and computational paths across multiple physical methods.

These computations do not establish field validity or generality across geological settings. Several method-specific comparisons, end-to-end user-supplied-data workflows, actual-host measurements, independent solver comparisons, and user-facing visual evaluations remain to be completed. The learned travel-time refinement has a narrowly positive synthetic result alongside failed variants and a separate M12 failure; no general learned advantage follows. The work provides a reproducible software and experimental framework that makes assumptions and counterexamples inspectable. Algorithmic novelty and publication priority are not established.

# Data and code availability

Source code is available at `https://github.com/fsantibanezleal/CAOS_Geophysics`. Scientific methods, notebooks, test data, computational records, and source-rights decisions are linked above and organized in `data/`, `data-pipeline/`, `docs/`, `notebooks/`, `tests/`, and `models/`. Some external raw observations are absent because redistribution rights or field eligibility remain unresolved. The intended application origin is `https://geophysics.ml.fasl-work.com/`. Local computations do not establish replacement-service capacity.


# Acknowledgements

The work uses and cites open scientific software and public geophysical data sources listed below and in the repository's research review. No endorsement by the cited software or dataset authors is implied.
