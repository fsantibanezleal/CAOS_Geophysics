# Scalar magnetic lines, corrections and held-out prediction

## The measured quantity is part of the problem

A scalar magnetometer records an intensity in nanotesla, not magnetic
susceptibility, vector magnetization or a three-dimensional geological body.
The main field, instrument/platform response and regional perturbations must
remain distinguishable. A processed anomaly, a gradient in nT/m, a magnetic
potential in nT-km and an RGB image are different observations. A column name
cannot make them interchangeable.

For a total-intensity measurement T and a documented reference intensity F,
define the scalar anomaly

$$
\Delta T=T-F,\qquad [T]=[F]=[\Delta T]=\mathrm{nT}.
$$

The reference is evaluated at specified coordinates, height convention, epoch
and model generation. IGRF describes the main field and secular variation,
not local geology or storm removal. NOAA's independent vector/evaluation
receipt and altitude interpretation remain necessary; a downloaded model
routine is not an evaluated survey reference.
[NOAA IGRF](https://www.ncei.noaa.gov/products/international-geomagnetic-reference-field),
[official IGRF14 source](https://www.ngdc.noaa.gov/IAGA/vmod/igrf14.f).

The reference basis is explicit. For NOAA's north/east/down components X,Y,Z,
the east/north/up vector is (Y,X,-Z). Declination is east-positive; inclination
is down-positive. Datum compatibility is separate from component sign.
Survey-reference scalar epochs and actual per-row UTC decimal years cannot
silently replace each other.

An existing anomaly can be re-referenced only by

$$
\Delta T_{\mathrm{new}}=\Delta T_{\mathrm{old}}+F_{\mathrm{old}}-F_{\mathrm{new}}.
$$

The old applied reference and both evaluated arrays must be recoverable.
Subtracting a new reference from an already reference-subtracted anomaly
double-corrects the data. Unknown contractor processing remains unknown.
[USGS processing example](https://pubs.usgs.gov/of/2002/0098/APPENDIX.HTM).

## Original line records and geometry

Original UTF-8 CSV bytes and the complete physical sidecar retain separate
SHA256 identities. Derived float serialization is not the original file.
Every original row, line, sensor, ordinal and timestamp remains inventoried.
Secondary indexes do not reorder reversed acquisition lines. Missing values
are null, never zero; duplicate locations are diagnostics, not permission
to average sensors.

The exact scalar line header is:

```text
row_id,line_id,line_kind,sensor_id,ordinal,utc,easting_m,northing_m,upward_m,terrain_upward_m,clearance_m,magnetic_nT,uncertainty_nT,heading_deg
```

Metric XY and an explicit upward vertical datum are necessary for physical
height transfer. Clearance is not altitude: only compatible terrain and
height can establish clearance=upward-terrain. A survey mean clearance is
not a per-row height or error estimate. When supplied height, terrain and
clearance disagree, a documented consistency tolerance is necessary.

Segments join original consecutive records within one line/sensor. A missing
interior record or excessive gap breaks adjacency; removing it then joining
its neighbours invents a different acquisition. Geometric preflight can
count conservative candidate adjacencies without admitting missing magnetic
values for fitting.

The Charleston provider documents real processed flight lines, but its
three-band0..255 TIFF is an image, not a numerical nT grid. The actual
dictionary, attachment identities, processing/vertical metadata and permissions
remain necessary. Bartlett's merged200m grid has no original flight/tie
identities or clocks. Neither image pixels nor grid cells become flight
records by adding synthetic line IDs.
[Charleston primary metadata](https://data.usgs.gov/datacatalog/metadata/USGS.5f4da2c182ce4c3d1231922e.xml),
[Bartlett primary metadata](https://data.usgs.gov/datacatalog/metadata/USGS.64188a2ed34eb496d1d1d359.xml).

## Time alignment and independent instrument calibration

The signed lag convention is

$$
t_{\mathrm{position}}=t_{\mathrm{measurement}}+\tau.
$$

Positive tau chooses navigation at a later time. It changes the assigned
coordinates, not the value's measurement time. Interpolate only within
genuine same-line navigation brackets with admitted clock synchronization
and maximum bracket gap. Outside overlap remains masked; no endpoint fill,
wrapping or guessed aircraft speed is allowed.

For synchronized base intensity b(t) and its declared reference b_ref,

$$
T_{\mathrm{diurnal}}(t)=T(t)-[b(t)-b_{\mathrm{ref}}].
$$

Subtracting the absolute48000nT base instead of its perturbation has a
different physical meaning. The heading model, with clockwise-from-north
degrees converted to radians internally, is

$$
h(\theta)=a_0+a_c\cos\theta+a_s\sin\theta,\qquad
T_{\mathrm{heading}}=T_{\mathrm{diurnal}}-h(\theta).
$$

Coefficients and lag must come from independent calibration. Fitting them
to outer-training data outside the inner folds is not leakage-safe model
selection. A sealed test sample cannot become calibration data.
[USGS base, lag and heading procedures](https://pubs.usgs.gov/of/2002/0098/APPENDIX.HTM).

The local alignment operator returns an explicit validity array. Its NaN
entries are internal unaligned-coordinate sentinels, not publishable JSON
numbers; a complete export must preserve nulls and reasons. The base/heading
operator takes only already synchronized finite arrays. Synchronization,
clock/rights custody and correction-state lineage are separate prerequisites,
not conclusions from its arithmetic.

## Scalar projection versus exact intensity

For an inducing unit vector u, intensity F and vector perturbation b,

$$
\Delta T_{\mathrm{weak}}=\mathbf u\cdot\mathbf b,\qquad
\Delta T_{\mathrm{exact}}=\|F\mathbf u+\mathbf b\|-F.
$$

For norm(b)<F, their difference is bounded by

$$
\left|\Delta T_{\mathrm{exact}}-\Delta T_{\mathrm{weak}}\right|
\leq \frac{\|\mathbf b\|^2}{2(F-\|\mathbf b\|)}.
$$

This is a mathematical approximation bound, not instrument uncertainty.
Nonparallel magnetic moments are permitted in the authored controls; their
existence does not establish actual field remanence. The scalar harmonic
approximation requires a sufficiently constant direction over the admitted
domain. Reduction to pole additionally requires magnetization direction and
cannot be inferred from scalar observations alone.
[Harmonica projected anomaly](https://www.fatiando.org/harmonica/v0.7.0/api/generated/harmonica.total_field_anomaly.html),
[RTP assumptions](https://www.fatiando.org/harmonica/v0.7.0/api/generated/harmonica.reduction_to_pole.html).

## Crossovers are physical constraints only when comparable

For two finite XY segments, solve

$$
\mathbf p_0+a(\mathbf p_1-\mathbf p_0)
=\mathbf q_0+b(\mathbf q_1-\mathbf q_0),\qquad a,b\in[0,1].
$$

Translate coordinates by a common origin before the solve. Numerical
coordinate tolerance has metres, determinant tolerance has square metres,
and crossing sine/segment-parameter tolerances are dimensionless. Large
absolute origins can make very short segments numerically unresolved;
translation does not recover information already lost in their binary64
coordinates. A refused tiny segment is not repaired by relaxing the
declared tolerance.

The signed comparison is flight-minus-tie. Bracket weights interpolate
observations, height and real time separately. An XY crossing at different
heights can have a genuine geological magnetic difference; it is not
automatically an offset calibration. Physical height/time comparability
limits are independent of floating-point solve tolerances.

With independently documented row errors, the difference variance is

$$
\operatorname{var}(d)=
(1-a)^2\sigma_{f0}^2+a^2\sigma_{f1}^2+
(1-b)^2\sigma_{t0}^2+b^2\sigma_{t1}^2.
$$

Correlated or unknown errors do not justify this expression as a calibrated
field variance. Shared-endpoint comparisons retain all original pair
identities but contribute only one physical constraint.

An exact planar exercise separates geometry/offset signs from magnetic
height gradients. On the authored common80m plane let
d(e,n)=10+0.002e-0.003n nT. Add2(i-3)nT to flightFi, i=0..7, and zero to
ties. Linear interpolation of this plane is exact at each comparable
crossing. The flight-minus-tie constraints recover offsets
[-6,-4,-2,0,2,4,6,8]nT relative to the lexicographically first tie gauge.
Subtracting those offsets recovers d; it does not establish an absolute
magnetic datum. This is the original S2 synthetic control, not field data.

The local crossover inventory retains original adjacency IDs and rejected
candidate pairs. Missing middle rows are not removed before joining their
neighbours. Shared-endpoint segment pairs have one representative equality;
their repeated pairs remain diagnostic. Training-ID exclusions precede
value interpolation, so a sealed line's measurements do not calibrate its
offset. A line absent from the training graph remains null/uncalibrated,
never zero-filled. Distinct connected components have separate relative
gauges and cannot be treated as one common datum for gridding.

For an admitted training graph, C has+1 at the flight and-1 at the tie:

$$
\min_{\mathbf o}\|W^{1/2}(C\mathbf o-\mathbf d)\|^2,\qquad
T_{\mathrm{levelled}}=T-\mathbf o_{\mathrm{line}}.
$$

Fix one lexicographically first tie offset to zero per connected component.
This establishes a relative gauge, not an absolute magnetic datum. Separate
components cannot acquire relative zeros from gridding. Solve by rank-checked
QR, not normal-equation inversion. A line absent from its calibration graph
remains uncalibrated, including a held-out line.

## A reproducible instrument-correction exercise

The authored S3 acquisition supplies synchronized navigation and base samples,
independent heading coefficients and an engineering-datum constant reference.
It is not a field survey or an evaluated IGRF model. For measurement UTC t,
navigation supplies the position at t+0.25s. The recorded position corresponds
to navigation at t; the scalar measurement itself is never time-shifted.
Exact UTC differences are computed in nanoseconds before interpolation, avoiding
the loss of subsecond information from a large absolute floating-point epoch.
Outside a same-line bracket, no endpoint fill or extrapolation is permitted.

The independently injected total-intensity control is

$$
T(t)=48000+d(\mathbf x(t+0.25))
 +3\sin(2\pi t/120)+2\cos h-\sin h\quad\mathrm{nT}.
$$

Here h is clockwise-from-north heading, converted from degrees to radians;
d is the direct dipole weak projection, not the nonlinear vector-norm anomaly.
Subtract the base perturbation b(t)-48000, the heading model
2cos(h)-sin(h), then the independently supplied constant reference48000.
The result is d at the aligned position. Subtracting the absolute base would
remove the main field twice. A heading term of+2nT at north and-1nT at east
provides a simple sign/degree exercise.
[USGS acquisition-correction description](https://pubs.usgs.gov/of/2002/0098/APPENDIX.HTM),
[Harmonica scalar projection](https://www.fatiando.org/harmonica/v0.7.0/api/generated/harmonica.total_field_anomaly.html).

For actual user files, the existing bounded loader can supply the three exact
byte strings to `apply_corrections(raw, metadata, request)`. The returned original
rows and separate derivative channels bind actual parent/output identities,
parameters, signs and masks. Applied or unknown corrections refuse replay.
This internal correction result is not the complete fitted/exported M03 Result.
The implemented authored-auxiliary lane verifies its embedded content and
clock definition; it does not authenticate provider sources. Field auxiliary
review and evaluated IGRF remain separate eligibility requirements.

Leveling must be calibrated again using each fold's training brackets. A
sealed line absent from that graph stays null/uncalibrated unless a separately
verified independent offset and the same tie gauge are supplied. Its offset
applies to the immediate derivative channel, not the original raw total.
Exercise: apply an independent heading offset3nT before S2 leveling. Why must
the final plane be7+0.002e-0.003n, rather than silently return10+0.002e-0.003n?
Explain why changing held-out observations cannot establish their line offset.

## Harmonic sources and the exact weighted objective

The physical dipole control uses

$$
\mathbf b(\mathbf r)=\frac{\mu_0}{4\pi}
\left[\frac{3\mathbf r(\mathbf m\cdot\mathbf r)}{\|\mathbf r\|^5}
-\frac{\mathbf m}{\|\mathbf r\|^3}\right].
$$

Moments have A*m^2 and SI output is tesla before conversion to nT. The
authored control fixes mu0/(4pi)=1e-7 as its analytic definition, not as a
new precision-metrology assertion. Different generating dipoles and fitted
source blocks avoid using the same model to generate and recover data.
[Official dipole engine](https://www.fatiando.org/harmonica/v0.7.0/api/generated/harmonica.dipole_magnetic.html).

Equivalent sources instead represent a harmonic scalar using

$$
d_i\simeq\sum_jG_{ij}q_j,\qquad
G_{ij}=\|\mathbf x_i-\mathbf s_j\|^{-1}.
$$

G has1/m and q has nT*m. These coefficients are not susceptibility,
magnetization or a unique geological depth. Training-only half-open source
blocks use floor((coordinate-origin)/block_size), including negative and
maximum edges. Sort signed block pairs and row IDs explicitly; representatives
are unweighted fsum means. Every observation remains in the fit and maps
once to a block. Source elevation is minimum training elevation minus the
declared depth, refitted inside every fold.
[Harmonica equivalent sources](https://www.fatiando.org/harmonica/v0.7.0/api/generated/harmonica.EquivalentSources.html).

Verde scales each column by its unweighted population standard deviation
s_j without subtracting its mean. Let A=G/s and c=s*q. Then A is
dimensionless and c has nT. The actual objective is

$$
\|W^{1/2}(A\mathbf c-\mathbf d)\|^2+\lambda\|\mathbf c\|^2.
$$

For unweighted W=I, both terms have nT^2 and lambda is dimensionless.
For admitted inverse variance W=diag(1/sigma^2), the data term is
dimensionless and lambda has nT^-2. No row-count or mean-weight normalization
is applied. Scaling W by a only preserves the minimizer if lambda is also
scaled by a. Changing data units changes the weighted penalty convention.
[Actual Verde least squares](https://www.fatiando.org/verde/v1.9.0/_modules/verde/base/least_squares.html).

A constant/nearconstant source column is refused before the library's
numerical StandardScaler fallback. Numeric1 is not a physical1/m scale.
An independent oracle constructs G and its std directly, stacks
[sqrt(W)*A;sqrt(lambda)*I] and solves the augmented system by QR.
Agreement verifies numerical implementation, not field geology.

## Sealed line validation and the failed worked control

Random neighbouring points do not independently test flight-line prediction.
The actual geometry seal excludes complete outerF04, retains boundary
anchorsF00/F07 and excludes both endpoints of original tie segments
intersecting closed buffered validation rectangles. Inner folds refit
sources and scaling on their own training observations. Other flight lines
remain interpolation neighbours; this is not an all-observation spatial
moat. Verde's groups argument does not enforce flight identity by itself.
[Verde BlockKFold](https://www.fatiando.org/verde/v1.9.0/api/generated/verde.BlockKFold.html).

The original authored geometry has363 rows. Outer validation/training is
33/294; inner A/B/C is66/168,66/195,33/249. Buffer/support is470m; candidates
are depths200/500m and damping0.0001/0.01/1/100, fixed before magnetic truth.
All geometric support fractions are1.0 for this geometry only. Inner RMSE
selection chooses one candidate; final fitting opens the outer observations
once. Residual sign is observed-minus-predicted nT.

The [actual byte-bound S1 investigation](../../design/features/m03-aeromagnetic-lines/evidence/s1-intake-bound-investigation.json)
reports depth500m/damping0.0001 selected from inner data, held-out
RMSE18.799740861734186nT and signal RMS5.1932793077546116nT. The unchanged
5% positive-control limit is0.25966396538773057nT: this control FAILS.
Geometric coverage and independent implementation agreement do not make
its predictive quality acceptable. No candidate or threshold was changed
after this outer result. Its magnetic truth is original synthetic physics,
not provider observations.

Exercise: inspect the eight inner means in the actual receipt. Which
candidate did the declared tie rule select? Compute RMSE/signal RMS.
Explain why changing depth using the outer residual would destroy the
sealed-test interpretation, and why a source-code oracle pass cannot waive
the failed predictive target.

## Sampling, continuation and conditional filtering

Output pixels are not survey resolution. Ideal uniform spacing s has
Nyquist wavelength2s; irregular line spacing, gaps and height require
separate support diagnostics. A50m grid cannot restore a150m wavelength
from much wider flight spacing. Interpolation is not physical height
transfer; SciPy's geometric comparator requires compatible heights and
does not recover a vector field.
[SciPy LinearNDInterpolator](https://docs.scipy.org/doc/scipy-1.15.2/reference/generated/scipy.interpolate.LinearNDInterpolator.html).

On an admitted complete level, source-free grid, positive upward
displacement delta_z multiplies each Fourier coefficient by

$$
\exp[-\sqrt{k_e^2+k_n^2}\,\Delta z],\qquad
\mathbf k=2\pi\mathbf f.
$$

The zero mode remains unchanged. Missing cells cannot be silently filled
with zero. Padding, taper and crop are boundary assumptions, not measured
geology; finite-grid interior and edge errors must be separated.
Downward continuation is unsupported.
[Harmonica upward continuation](https://www.fatiando.org/harmonica/v0.7.0/api/generated/harmonica.upward_continuation.html).

For demeaned grid d, window w, N cells and C2=mean(w^2), full two-sided
bin power is |DFT(w*d)|^2/(N^2*C2), in nT^2 per bin. Its sum obeys the
corresponding windowed Parseval identity; it is not spectral density or a
validated depth estimate. Directional microlevel filtering can remove
both acquisition stripes and real line-parallel geology. Removed/retained
arrays and transfer functions must remain diagnostic, with no automatic
promotion to corrected field observations.
[USGS documented directional-processing example](https://cmgds.marine.usgs.gov/catalog/pcmsc/DataReleases/ScienceBase/DR_F7GT5K8R/B-04-12-NC_Magnetic_metadata.html).

## Worked spectral and geological-loss controls

An exactly periodic supplementary plane uses40 east cells at25m and32 north
cells at30m, origin(0,0), so the periodic lengths are1000m and960m:

$$
d(e,n)=7+2.3\cos[2\pi(3e/1000+2n/960)+0.31]\quad\mathrm{nT}.
$$

At upward displacement100m, its cosine amplitude becomes
2.3exp[-100sqrt((6pi/1000)^2+(4pi/960)^2)] while its mean remains7.
This independently derived amplitude/phase agrees with the official Harmonica
operator. No padding is hidden in that periodic oracle. Reflection or zero
padding plus a named taper changes the boundary model and is recorded separately.
[Harmonica FFT height transfer](https://www.fatiando.org/harmonica/v0.7.0/api/generated/harmonica.upward_continuation.html).

After subtracting7, rectangular two-sided power has two nonzero conjugate bins,
(north2,east3) and(-2,-3), each2.3^2/4nT^2. Their sum2.3^2/2 equals variance.
Hann-window power instead uses its measured C2; it is not silently called the
original variance. Frequency axes are cycles/m; multiplication by2pi gives
rad/m without changing power units. The zero mode belongs to no directional
sector, avoiding an invented orientation.
[NumPy Fourier conventions](https://numpy.org/doc/2.2/reference/routines.fft.html).

For east-west flights, consider genuine geology cos(2pi*n/960) and an acquisition
stripe cos(8pi*n/960), both of authored unit1nT amplitude. With kc=2pi/960 and
ka=2pi/1000rad/m, the prescribed directional filter removes fractions
1/sqrt(2) of the geology and4^4/sqrt(4^8+1) of the stripe. Thus stripe removal
cannot be advertised as preserving line-parallel geology. Removed+retained
reconstruct the input; a separately declared clipping cap affects its own
diagnostic array/spectrum, not the unclipped transfer or physical truth.
Oppositely acquired headings90/270degrees describe the same undirected flight
orientation. Nonparallel lines and a gapped rectangle are ineligible.

The recorded S5 family adds1nT*sin(2pi*n/150m) to the independent dipole field.
Its authored flights have330..450m nominal perpendicular spacing;50m output
cells cannot resolve that150m cross-line wavelength. A supplementary uniform
400m sampling oracle shows cos(2pi*n/150) and its aliased frequency
1/150-3/400 give identical samples. No scalar gridding method can uniquely
distinguish them from those samples. Irregular jitter changes exact alias
equality but does not justify a universal Nyquist-resolution claim.

S6 adds explicit unit1nT geology cos(2pi*n/1600m) and a stripe
cos(2pi*n/800m), both invariant east, to the dipoles. These are known authored
negative controls, not fitted field components or a new unopened validation
target. S4 separately retains edited inspection records with missing values,
duplicate XY, mixed/missing heights and missing UTC; their coordinates do not
become a new valid forward acquisition merely because the CSV still parses.

## Support versus approximation

The local support operator intersects the closed training hull with the nearest
training-distance policy. It preserves every grid cell and uses null plus
exclusion reasons, never a filled-zero estimate. Actual broken ORIGINAL
adjacencies produce conservative closed support-radius tubes; this masks gaps
rather than joining around them. A complete-line CV exclusion is a partition
decision, not an acquisition gap, so it does not manufacture those tubes.
Sampling_unresolved is separately diagnostic and does not itself fabricate a
hole. Local along/perpendicular spacings remain in the output.

Corrected fitting accepts no arbitrary claimed parent hash. It independently
replays the exact original CSV/sidecar/request and compares the derivative rows,
then recomputes corrections inside each fold. The source/hash definitions stay
distinct even when request whitespace changes but its typed meaning does not.
[The original calibration-support diagnosis](../../design/features/m03-aeromagnetic-lines/calibration-support-diagnosis.md)
shows why frozen fold A cannot estimate training crossover offsets: it has
zero admitted constraints. That refusal does not change the original S1
predictive threshold or authorize selecting geometry from its opened test.

The source-bound local `fit_grid` orchestration produces real corrected rows,
blocked fits, comparator applicability, supported grid and higher-plane
predictions. It reports S1 quality failure explicitly. It is an internal
numerical mapping. The separate `run_result` boundary produces the complete
serialized `magnetic-result/1` only with its additional typed reference,
array/runtime/custody prerequisites. See the [local-file workflow](02_local-files-and-replay.md).
FFT requires a complete declared supported plane; source-free=True on the
ordinary transform is a physical caller assertion, not provider authentication.
Strict float64 axes/padding/cell/byte preconditions and known datum/sign remain
necessary. Field reference/auxiliary review and genuine full-survey execution
are not established by these controls.

## Bounded user-file inspection

Use an existing declared compatible interpreter. Supply actual files;
the following inspection neither creates input nor guesses metadata:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path("data-pipeline").resolve()))
from magnetic_line_contract import MAX_CSV_BYTES, MAX_METADATA_BYTES, load_lines, read_bounded

raw = read_bounded("survey.csv", MAX_CSV_BYTES)
metadata = read_bounded("survey.metadata.json", MAX_METADATA_BYTES)
request = read_bounded("survey.request.json", MAX_METADATA_BYTES)
intake = load_lines(raw, metadata, request)
print(intake["csv_sha256"], len(intake["rows"]))
print(intake["eligibility_reasons"])
```

Valid structural inspection does not authorize every correction or fitting
operation. Preserve explicit independent private-processing, derivative-
publication and raw-mirroring permissions. A source hash establishes identity,
not ownership, license or provider authentication. The bounded contract has
400 rows/16MiB original CSV,2MiB combined metadata,26 fits and16384 total
exported cells; it is not a full Charleston-survey executor. The complete
independent IGRF evaluation, full-survey field evidence and native activation
remain unaccepted. Local correction/export/replay controls do not close those
gates. The
actual frozen S1 failure must not be presented as a successful field example.
