# Amargosa Desert aeromagnetic data: source, channels and M03 processing boundary

**Status:** source verified; one regional slice processed through M03; no geological interpretation or inversion accepted.
**Source:** USGS Open-File Report 00-188 and its accompanying fixed-width point archive.
**Recorded:** 11 November 2026.

## Research question

Can a public, measured aeromagnetic survey exercise the product's magnetic field-line geometry and spatial-processing contract without treating a processed anomaly as raw instrument data, confusing gridding with inversion, or leaking nearby flight-line segments between training and holdout?

The answer for a bounded teaching case is yes. The answer for reproducing the USGS provider grid, recovering subsurface magnetization, or claiming transfer to another survey is no. The adapter is an evidence-preserving M03 processing example; its score does not assess a geological model.

## Source records and rights

The source report is Blakely, Langenheim, Ponce and Dixon (2000), *Aeromagnetic Survey of the Amargosa Desert, Nevada and California: A Tool for Understanding Near-Surface Geology and Hydrology*, USGS Open-File Report 00-188, [DOI 10.3133/ofr2000188](https://doi.org/10.3133/ofr2000188). The [official report](https://pubs.usgs.gov/of/2000/of00-188/), [point archive](https://pubs.usgs.gov/of/2000/of00-188/data/amargosa.xyz.gz), [format note](https://pubs.usgs.gov/of/2000/of00-188/data/amargosa.info) and [data directory](https://pubs.usgs.gov/of/2000/of00-188/data/) are the source of record.

The USGS format note identifies the distributed gzip data files as public domain. The product ledger therefore authorizes an attributed local mirror of this exact object and public-domain-derived teaching figures. This does not indicate USGS endorsement or an accuracy warranty; the report's preliminary-status and purpose-specific caveats still apply.

The original gzip is external to Git at `data/downloads/usgs-ofr-00-188/amargosa.xyz.gz` under the device's configured data root. The pinned object is 8,226,743 compressed bytes with SHA-256 `2698b48a79822f28122f7f8bcd49d0d28c3c103340ddc0012fee0228866ec22c`. Its decompressed ASCII stream is exactly 26,963,280 bytes and 374,490 records. The acquisition script checks the original compressed bytes and emits an immutable local receipt; the source-specific reader checks the decompressed byte and record counts as well. No raw source or full observation array is committed.

## Survey design and physical quantities

The report describes a 1999 Sander Geophysics cesium-vapor magnetometer mounted on a fiberglass stinger, with differentially corrected GPS used to follow a planned terrain-relative surface. East-west flight lines were nominally 400 m apart, north-south tie lines 2.3 km apart, and target clearance was about 150 m above terrain where safety allowed. The report gives 23,333 line-kilometres flown. These are survey-design descriptions, not a guarantee that each local file segment contains a complete line or exactly the nominal altitude.

Each record is 71 fixed-width ASCII characters. Columns 1–8 are the source line identifier; 9–20 longitude; 21–30 latitude; 31–37 radar height; 38–44 barometric height; 45–53 uncorrected magnetic field; 54–62 total-field anomaly; and 63–71 levelled anomaly. Geographic coordinates are NAD27 longitude/latitude; heights are metres; magnetic channels are nT. The record stream contains every tenth datum from the more densely sampled line acquisition. The identifiers encode line, segment and quadrant information according to the source note; the adapter preserves the identifier as an opaque string and does not infer its inner grammar.

The three magnetic columns have different meanings. `uncorrected magnetic field` retains a large background field and is not the anomaly. `total-field anomaly` is a provider-produced anomaly. `levelled anomaly` additionally reflects flight/tie crossover levelling. The report says preliminary provider processing removed diurnal and IGRF fields, applied navigation corrections, and adjusted field values at flight/tie crossings. Accordingly this pipeline selects only the already levelled channel for interpolation. It never reapplies IGRF removal, diurnal correction, navigation correction, or levelling. Radar height is kept distinct from barometric height and is reported as above-terrain height, not as a geodetic elevation.

For a background inducing field vector \(\mathbf B_0\) and a small secondary perturbation \(\mathbf b\), the measured total-field perturbation is

\[
\Delta T = \lVert\mathbf B_0+\mathbf b\rVert-\lVert\mathbf B_0\rVert
\;\approx\; \widehat{\mathbf B}_0\cdot\mathbf b,
\qquad \lVert\mathbf b\rVert\ll\lVert\mathbf B_0\rVert.
\]

This first-order projection explains why scalar total-field anomaly is not equivalent to the three-component secondary vector. The released anomaly alone cannot reconstruct vector components, induced-versus-remanent magnetization, or a unique source body. The M03 interpolator does not solve any of those inverse questions.

## Coordinate and geometry handling

The adapter interprets the declared NAD27 angular coordinates as EPSG:4267 and uses an explicit x/y-order transformation to NAD27 / UTM zone 11N, EPSG:26711. A projected metric frame is required because line spacing, segment lengths, ROI bounds and cross-track grouping use metres. Coordinate transformation is not a datum correction to the measured field.

The selected example ROI is the half-open rectangle `[538462,543462) m E × [4067437,4072437) m N`, 5 km on each side. Its geometry audit finds 1,321 source points intersecting the rectangle and 29 source identifiers. Segment principal axes classify 24 identifiers as east-west-like and 5 as north-south-like under a 30° orientation boundary. Cross-track grouping with declared tolerances of 200 m for flights and 500 m for ties forms 12 and 4 apparent physical tracks. This local geometric classification is an algorithmic diagnostic; it does not replace the report's survey map or decode the source line-ID syntax.

Some physical transects appear as multiple source segments. To prevent a neighboring segment of one transect from entering both fitting and holdout as if it were a new line, the adapter makes one representative choice per cross-track group: retain the segment with the most points, then break ties by the exact source ID. The external result records every grouped ID, selected segment, omitted segment, threshold, ROI bound and sample count. For this ROI, the 12 flight and 4 tie representatives contain 1,194 points. This is a deterministic regional selection, not random truncation. The CLI exposes the bounds, clustering tolerances, orientation threshold, grid spacing, holdout fraction and seed.

## M03 operation and evidence

The M03 contract measures source geometry and radar-height QC, forms a whole-flight-line holdout, fits a Delaunay linear interpolation using flight lines only, and reports supported cells and interpolation residuals on held-out flight lines. Tie lines are retained for crossover geometry diagnostics and do not fit the interpolated surface. Points outside the training convex hull are explicitly masked rather than extrapolated. No source correction or tie-line levelling is performed by M03.

The pinned Amargosa run yielded 12 flight tracks, 4 tie tracks, and 1,194 selected records. At the default 100 m grid spacing, the lattice is 45 × 49 with 2,101 supported cells. Three entire flight tracks (226 samples) were held out; all 226 lie inside the training hull. Their spatial interpolation MAE is 18.676 nT and RMSE is 25.722 nT. Those figures are conditional on this ROI, track selection and linear interpolation. They are not an accuracy threshold, a universal estimator ranking, or evidence of model recovery.

Sensitivity runs held the source slice, line grouping and holdout at their default values while changing grid spacing to 50, 100 and 200 m. Supported-cell counts were 8,468, 2,101 and 523 respectively; the held-line RMSE remained 25.722 nT because M03 evaluates held-out observations independently of display-grid spacing. At 10% and 30% holdout fractions, the holdout contained 2 and 4 lines and RMSE was 40.981 and 32.786 nT, with supported coverage 1.000 and 0.997. Changing orientation tolerance from 20° to 40° changed accepted tie representatives from 3 to 4 while retaining all 12 flight tracks; the flight holdout RMSE was unchanged. These are design-sensitivity observations on one survey patch, not independent validation. The sensitivity record makes the effective holdout size visible rather than comparing scores as if the subsets were identical.

The original result is stored outside the checkout at `data/raw/magnetic/amargosa-m03-20261111.json`; its committed copy is `data/derived/field/amargosa/amargosa-m03-20261111.json`, 78,030 bytes, SHA-256 `4d7116d16239d1b5a29eff25bb7ae6c6066842479afda1ba232511f2e437e418`. It contains source hash and acquisition receipt, selected track manifest, split IDs, geometry summaries, measured interpolation scores, grid coordinates, values and support mask, and explicit limitations. The product research page reads this artifact through its hash-pinned field-study index. This candidate change does not alter the current deployed release.

## Reproduction

From the repository root, with Python 3.12 and the `data-pipeline/requirements.txt` pins installed:

```powershell
$env:GEOPHYSICS_LOCAL_DATA_ROOT = 'E:\_Datos\CAOS_Geophysics'
python data-pipeline/acquire.py --source-id usgs-amargosa-aeromagnetic
python data-pipeline/magnetic_amargosa.py --output "$env:GEOPHYSICS_LOCAL_DATA_ROOT/data/raw/magnetic/amargosa-m03-<new-run-id>.json"
```

The CLI refuses to overwrite an existing result. An omitted `--data-root` uses the environment variable, which must be absolute and outside the checkout. The acquired archive is immutable; a changed source hash, invalid gzip, unexpected row width, extra/missing records, nonfinite value, invalid coordinate, ambiguous/no-line ROI or M03 resource-bound failure stops the run.

## Limits and next scientific tests

The source report's anomaly is provider processed, so this case cannot demonstrate how to remove the main field from uncorrected observations. It also does not contain the base-station or navigation measurements needed to independently reproduce those upstream corrections. The local ROI is small and within one survey; its spatial holdout shares acquisition and provider processing with training. The linear grid is a descriptive interpolation whose support depends on line layout. Neither its colors nor its holdout error establish physical depth, body geometry, lithology, or a unique magnetization distribution.

Before claiming additional capability, a separate scientific vertical would need (1) a source-matched provider grid with compatible field channel and coordinate metadata for an independent reconstruction comparison; (2) survey geometry and uncertainty assumptions checked against the full report and original line records; (3) synthetic forward controls with known magnetization and inducing direction; (4) regularized inverse tests with resolution, null-space, remanence and depth-sensitivity analysis; and (5) spatially independent, preferably separate-survey validation. No output in this document satisfies those gates.

## References

1. Blakely, R.J. (1995). *Potential Theory in Gravity and Magnetic Applications*. Cambridge University Press. [DOI 10.1017/CBO9780511549816](https://doi.org/10.1017/CBO9780511549816).
2. Blakely, R.J., Langenheim, V.E., Ponce, D.A., and Dixon, G.L. (2000). *Aeromagnetic Survey of the Amargosa Desert, Nevada and California: A Tool for Understanding Near-Surface Geology and Hydrology*. USGS Open-File Report 00-188. [DOI 10.3133/ofr2000188](https://doi.org/10.3133/ofr2000188).
3. Cockett, R., Kang, S., Heagy, L.J., Pidlisecky, A., and Oldenburg, D.W. (2015). SimPEG: An open source framework for simulation and gradient based parameter estimation in geophysical applications. *Computers & Geosciences*, 85, 142–154. [DOI 10.1016/j.cageo.2015.09.015](https://doi.org/10.1016/j.cageo.2015.09.015).
4. Fedi, M. and Rapolla, A. (1999). 3-D inversion of gravity and magnetic data with depth resolution. *Geophysical Prospecting*, 47, 27–43. [DOI 10.1046/j.1365-2478.1999.00133.x](https://doi.org/10.1046/j.1365-2478.1999.00133.x).
