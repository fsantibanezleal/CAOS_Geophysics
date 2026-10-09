# M02 submitted-survey gravity research and source audit

Date: 2026-10-03. Status: research verified where explicitly stated; feature
design proposed for review, no new numerical execution or implementation.
Baseline: develop `0a10b5517b025cfa4330f205946ddf918f4b0f8f`, after PR97/101.
Handoff base: latest develop at alignment `66952f32b6ce86d5a752cf56d3e4ca8481c8b4da`.
The branch fast-forwarded over upstream MT frontend/review, separator repair and
MT course and ops source-bundle changes; all inspected
scientific module and parent-SDD hashes remain unchanged. Those upstream changes
are not authored by this sidecar and are excluded from its diff.
Branch: `task/geophysics-m02-survey-sdd`. This work changes research and the
M02 feature SDD only. The retained private FWI backup/candidate/receipts are
not input to a new bake and remain ignored. No new raw data were acquired.

## Approved basis and actual gap

The approved [product SDD](../design/SDD.md), M02 row, requires 3D gravity prism
forward modelling and weighted L2/sparse inversion on survey geometry, with
independent prediction, sensitivity and mesh/beta comparisons. Its layered
source/forward/inverse/field oracles cannot be replaced by one synthetic fit.
Management research dossiers 02-05 and the approved replacement plan were read;
their old dates/source leads are retained as history, not new access evidence.
The local [source review](bartlett-source-review-2026-10-03.md),
[intake evidence](potential-source-intake-evidence-2026-10-03.json),
[M01 seam](../design/features/m01-gravity-corrections/bartlett-integration.md),
[recovery research](recovery-2026-09-24.md) and
[implementation record](scientific-implementation.md) inform this unit.

Actual source inspection, not an execution claim:

- `potential.py` constructs a fixed 16x16 synthetic survey and Geoana-backed
  SimPEG kernels on a 10,752-cell volume. It calls the custom spatial inverse.
- `spatial_inverse.py` uses a data-space eigensystem, fixed prior lengths,
  calibrated depth power 0.375, discrepancy beta, four sparse-smallness updates
  and conditional fixed-prior noise ensembles. These are recorded synthetic
  decisions, not general priors for all uploaded surveys.
- `ingest.py::invert_csv` genuinely fits uploaded five-column data on a
  14x12x8 mesh, but has no full CRS/datum/correction/mask/topography contract,
  field eligibility proof, training-only selection, outer holdout or safe
  complete bundle publication. It is not a fake solver, nor complete M02.
- M01 corrections and equivalent sources are distinct processes. A Harmonica
  equivalent-source coefficient is not a 3D density contrast. The existing
  shared API parser/flag worker is not this proposed local inverse.

Exact inspected module/parent-document hashes and observed installed versions
are in [the research receipt](m02-survey-inversion-evidence-2026-10-03.json).
The base runtime contains SimPEG 0.25.2, Geoana 0.8.1, discretize 0.12.0,
Choclo 0.3.2, NumPy 2.2.6, SciPy 1.15.2 and pyproj 3.8.0. Verde is absent
from that base runtime; its separately pinned M01 target is not silently
treated as a shared environment change. No installation was performed.

## Verified primary references and precise use

P01/P02. [Versioned SimPEG gravity API](https://docs.simpeg.xyz/v0.25.2/content/api/generated/simpeg.potential_fields.gravity.Simulation3DIntegral.html)
and [pinned engine source](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/potential_fields/gravity/simulation.py)
establish g/cc input, mGal acceleration output and upward-positive `gz`.
Source inspection distinguishes Geoana prism kernels from the Choclo path.
Choose Geoana for the production comparison; check sensitivity dtype/storage
explicitly. Its forward-only mode does not provide all inverse sensitivity
operations, so do not promise a matrix-free Geoana inversion merely from an
API storage option. SimPEG's [pinned MIT licence](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/LICENSE)
is software permission, not permission to mirror tutorial or survey data.

P03. [Choclo gravity_u](https://www.fatiando.org/choclo/latest/api/generated/choclo.prism.gravity_u.html)
(documentation labelled 0.3.2) supplies a separately implemented rectangular
prism evaluator with metric coordinates, kg/m3 density and m/s2 upward
acceleration. The planned certificate compares it to the Geoana engine with
explicit conversions. Shared Newtonian assumptions mean this is implementation
independence, not independent field truth; add sphere/point-mass and numerical
volume-integration checks rather than calling two names a geological oracle.

P04. [Pinned data-misfit source](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/data_misfit.py)
computes `||W(d_pred-d_obs)||^2` with no half factor; derivatives include two.
Default weights are reciprocal declared SD. The setter accepts a square
weight matrix. This supports a proposed explicit Cholesky whitening path;
the adapter's covariance, permutation and transpose correctness still needs
new tests. No tutorial-derived floor becomes measured instrument uncertainty.

P05/P14. [Sparse regularization](https://docs.simpeg.xyz/v0.25.2/content/api/generated/simpeg.regularization.Sparse.html)
and [WeightedLeastSquares](https://docs.simpeg.xyz/v0.25.2/content/api/generated/simpeg.regularization.WeightedLeastSquares.html)
provide separate smallness and smoothness terms, active-cell/reference-model
choices and length scales. Sparse norms and stabilizers must be declared.
Propose matched meshes/bounds/weights and sparse smallness with L2 spatial
derivatives; do not call that total variation or assume sparse models always
beat diffuse L2 models. Unit changes must leave physical predictions invariant.

P06/P12. [Pinned UpdateIRLS source](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/directives/_regularization.py)
and [ProjectedGNCG](https://docs.simpeg.xyz/v0.25.2/content/api/generated/simpeg.optimization.ProjectedGNCG.html)
are actual official optimization components. The directive initializes with
L2, can modify beta/epsilon, and constrains preconditioner/directive order.
Export each stage's actual weights and stopping state. Beta changes mean
successive objective totals are not one fixed-objective descent curve.
The pinned implementation can derive a zero threshold for a zero model;
an explicit positive-floor policy must be designed/tested, not silently assumed.

P07/P08. The official [gravity tutorial](https://simpeg.xyz/user-tutorials/inv-gravity-anomaly-3d/)
and [weighting comparison](https://simpeg.xyz/user-tutorials/weighting-strategies/)
show L2/IRLS, topography, regularization and alternative weighting. Their
data are labelled synthetic; they are not a field acceptance receipt. The
current first tutorial says 2.5% in prose but uses 0.02 in its floor example.
Do not copy either as an uploaded survey's measured errors. The weighting
tutorial output names 0.25.0, not an executed 0.25.2 run by this worker.

P09. Li and Oldenburg, [3-D inversion of gravity data](https://gif.eos.ubc.ca/sites/default/files/Li_1998a.pdf),
[DOI 10.1190/1.1444302](https://doi.org/10.1190/1.1444302), Geophysics 63,
109-119 (1998), gives rectangular-cell density inversion with model/prior and
depth weighting. Title/authors/abstract and an initial 11-page PDF response
were verified; later full-text fetches failed. This is not a claim that every
derivation was re-read or reproduced. The 1996 DOI 1.1443968 is the magnetic
paper and must not be substituted for this gravity reference.

P10/P11/P13. [Verde BlockKFold 1.9.0](https://www.fatiando.org/verde/v1.9.0/api/generated/verde.BlockKFold.html)
documents spatial groups, not guaranteed independence; buffered nested selection
is a proposed additional protocol. [pyproj Transformer](https://pyproj4.github.io/pyproj/stable/api/transformer.html)
documents axis handling and refusal of ballpark/missing best operations;
actual datum-grid availability remains an admission gate. The page is 3.7.2,
not this runtime's 3.8.0 receipt. [discretize active_from_xyz](https://discretize.simpeg.xyz/en/latest/api/generated/discretize.utils.active_from_xyz.html)
documents node/centre activity and nearest extrapolation outside the surface
hull. A field adapter must reject uncovered geometry before that implicit
extension, and record topographic discretization error rather than hide it.

P16/P17. Fournier and Oldenburg, [Inversion using spatially variable mixed lp
norms](https://academic.oup.com/gji/article/218/1/268/5420370),
[DOI 10.1093/gji/ggz156](https://doi.org/10.1093/gji/ggz156), GJI 218,
268-282 (2019): publisher title/abstract and displayed methodology/introduction
were verified. They motivate retaining L2 initialization, gradient scaling and
alternative solutions; the field example is magnetics, not a gravity acceptance
receipt. This design chooses a narrower fixed sparse-smallness policy, not their
full spatially varying norm-selection workflow. A separate author-hosted PDF
returned an internal error; no new reproduction is claimed.

Cockett, Kang, Heagy, Pidlisecky and Oldenburg,
[SimPEG framework publication](https://sgkang.github.io/papers/simpeg_2015.html),
[DOI 10.1016/j.cageo.2015.09.015](https://doi.org/10.1016/j.cageo.2015.09.015),
Computers & Geosciences 85, 142-154 (2015): author abstract and publisher search
text verified. It supports separating physics, misfit, regularization and
optimization for interrogation; it is not a timing or solver-quality result for
the installed 0.25.2 version. Versioned source controls the actual proposed adapter.

## Unavailable, attributed and not yet measured

The fresh browser returned internal errors for original USGS/FGDC pages,
generated IRLS/Geoana pages and later full-paper reads. No HTTP 403 is inferred
from an internal browser error. Historical ScienceBase 403 and previously
retrieved XML/author archive remain attributed to the existing source receipt,
not freshly acquired by this worker. Pinned SimPEG source supplied the relevant
IRLS/engine fallback. An initially guessed weighting URL failed; the correct
linked official tutorial was then verified. The research JSON retains these
negative access outcomes. No provider challenge was bypassed.

The already verified author gravity member is 335,377 bytes, SHA
`7cb3ed0c3cbac60f896a11f213ba40209c3083cb7635ab80ab7c0fd0382a1055`.
The existing source profile records 2,929 rows, missing FAA/SBA values,
duplicate IDs/geometry, absent errors, ambiguous `zWGS84`, and unresolved
station-level processing lineage. Source access and CC BY 4.0 do not resolve
these physics gaps or prove equality to original USGS bytes. It remains
modelling-ineligible; no field inversion or invented subsurface truth follows.

M02 timings, RSS, scratch, cancellation, GPU advantage, numerical tolerances,
synthetic recovery and measured-survey holdout performance are **NOT RUN**.
The [feature design](../design/features/m02-survey-inversion/design.md) and
[validation plan](../design/features/m02-survey-inversion/validation.md)
set reviewable gates, not measured results. CPU is the proposed initial local
lane for the documented engine; moving to GPU/online requires independent
implementation/parity/resource evidence and separate owner approval.
