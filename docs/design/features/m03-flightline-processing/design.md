# M03 mapped flight-line processing design

Date: 2026-10-25. Basis: approved product SDD section 4, the source-specific [Charleston intake research](../../../research/m03-charleston-flightline-research-2026-10-25.md), and the USGS provider record. This local vertical is a component of M03, not full method acceptance.

## Scope and data semantics

`data-pipeline/magnetic_processing.py` accepts a bounded CSV through an explicit user field map or the closed JSON request contract. It requires projected coordinates in metres, a declared CRS, a source SHA-256, citation, rights decision, processing-state description, value unit and sensor-height field. It does not infer columns, unit, CRS or correction history. The CSV adapter calculates SHA-256 over the input bytes and preserves the mapped observations as rows; unmapped columns remain in the source file and are not interpreted. The JSON entry point validates the declared digest's syntax but cannot prove that it is the digest of a separate original file, so its receipt explicitly leaves source-byte recomputation false.

The processor reports line sample counts, coordinate extents, line-centre spacing estimate and per-line height ranges/median/MAD. Height outliers are flagged beyond six scaled MAD; when MAD is zero, any nonzero deviation is flagged. These are screening flags, not instrument tolerance or a calibrated error model. Flagged observations remain in the input; none are deleted or corrected. Exact collocated values from distinct lines are summarized as exact-coincidence diagnostics. They are not substituted for geometric segment crossovers, whose interpolation is not implemented here.

## Split, interpolation and grid

The split unit is a whole flight line. Line centres are projected onto the estimated survey-normal axis, sorted, then a deterministic contiguous interior block is held out with a stable seed. At least two flight lines remain for fitting. Tie lines are retained for geometry/height reporting and excluded from fit. This supports a spatial prediction question without randomly scattering neighboring samples across fit and test.

Piecewise-linear Delaunay interpolation is fit to flight-line samples only. Grid spacing is an explicit metre parameter; output contains x/y physical axes, values and a separate support mask. Unsupported cells are encoded as zero only alongside a false mask. Grid values interpolate observations at their recorded sensor heights; they are not continued or corrected to a common elevation. Whole-line holdout predictions use the same interpolation without refitting. MAE/RMSE are reported only on supported held-out samples, with support count and coverage fraction. This is interpolation validation, not an inverse, geology estimate or comparison against a provider grid.

## Boundaries

No diurnal/IGRF/lag/height correction, line levelling, tie-line adjustment, regional removal, upward continuation, provider-grid comparison, upload/API job, frontend view or server admission is implemented by this vertical. This boundary is necessary because the Charleston deliverable is already-processed horizontal magnetic gradiometry and its dictionary/report have not been acquired in this environment. Do not call this output raw-to-corrected processing or use its values to claim Charleston validation.

The input ceiling is 256 MiB, 250,000 rows, 250,000 grid cells and 100 km grid spacing. SciPy `LinearNDInterpolator` and NumPy run in the local scientific environment; actual VPS timing, memory, cancellation and browser parity are not established. The source catalogue's estimated 2.58 GB CSV is outside this bounded online contract.

## Verification target

The method gate includes an analytic planar-field holdout control, deterministic split, height-outlier retention, duplicate-training-coordinate rejection, metric-coordinate rejection and explicit-mapping CSV import. These establish implementation behavior on authored controls only. The SDD's full M03 acceptance still additionally requires the acquired provider dictionary/report/CSV/grid, measured flight/tie crossover and height diagnostics, provider processing lineage, a source-specific blocked-line holdout, justified gridding and continuation controls, and a rights/provenance-bound case artifact.
