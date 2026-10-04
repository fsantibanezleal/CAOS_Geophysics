# Retained representation refinement: training-only diagnosis

These are two distinct prospectively defined100m/50m source-block requests,
not a replacement of original S1. Both keep200/500m depths, damping
0.0001/0.01/1/100, the inner-only tie rule, and the5% signal-RMS/1e-6nT
floor. Geometry and both partitions preceded independent SI dipole values.
Neither representation is chosen from the opened outer observations.

## Exact scientific identities

Original CSV SHA256874cf7a13a0cef023122b7d18b69fa735f098b37e9a490ea2eadf4d5c2a0438f;
sidecar4778b64cbd1e104d322632b7fd288a178166a8d6b0a5a0437e7603f514f99edb.
Executed magnetic_lines source SHA256
f9bebd28df1319768582dc1e9b4eef49fc3a489bac8869911a5d840013a9f168.
Original100m Result SHA256
255c1e7f6ec927ea12c9be98236c73d64dd23696f74fc0cd0d2cdb8b73df3a11;
50m Result fddfa1709f8bdb71049a2f3b30d989c45d1b4184af63d1c2fb6a7b31dfcba84d.
Later parser/resource changes do not rewrite these recorded source identities.
These are authored synthetic controls, not provider measurements.

| Fixed request | Final sources | Inner-selected depth / damping | Outer RMSE nT | Frozen limit nT | Verdict |
|---|---:|---|---:|---:|---|
|100m|227|500m /1|4.523829180141187|0.33114843034021674|FAIL|
|50m|287|500m /1|4.398834333896642|0.33114843034021674|FAIL|

Both have294 final training rows,33 outer rows, geometric coverage1,25
production fits and one outer evaluation. The shared outer signal RMS is
6.622968606804334nT. Numerical convergence and coverage do not waive either
predictive failure. Original S1 independently remains18.799740861734186nT
versus0.25966396538773057nT. Empty inner-A crossover calibration remains
ineligible under the original geometry seal.

## Independent linear algebra, without a new outer fit

Verify all original export member sizes/hashes before calculation. Use only
the recorded final training IDs, their original XYZ/declared channel, recorded
source positions and selected damping. Independently construct
G_ij=1/|x_i-s_j|, population column scale s_j=std(G_:j), and A=G/s.
There is no implicit mean removal or intercept. In this unweighted fixed-nT
convention, c has nT, q=c/s has nT*m, and lambda is dimensionless.
Solve the independent augmented system [A;sqrt(lambda)I]c=[y;0] with
SciPy SVD least squares, not Harmonica/Verde/sklearn fitting internals.
Compute training predictions Gq and the full raw objective, not a normalized
row-average objective. This diagnostic makes no new outer fit or parameter
selection. [Verde's pinned scaling/objective source](https://raw.githubusercontent.com/fatiando/verde/v1.9.0/verde/base/least_squares.py)
defines the production convention.

| Training-only observation |100m|50m|
|---|---:|---:|
|Maximum oracle/library prediction difference nT|5.4793253267959585e-12|4.442946011096183e-12|
|Independent augmented objective nT^2|1065.491692664982|954.5119716904778|
|Recorded augmented objective nT^2|1065.4916926649835|954.511971690479|
|Selected damped training RMSE nT|1.4698539630635026|1.3703239060334638|
|Numerical training-column-space projection RMSE nT|0.029724931746714395|0.0037743483670142895|
|Augmented condition number|490.2113739366449|556.2903793821109|

The independent scales agree within8.881784197001252e-16 relative.
Numerical projection ranks are227/287 under the explicitly reported
eps*max(N,M)*largest-singular-value cutoff, respectively
3.200147792682235e-11/3.6315196913527796e-11. These are floating numerical
projections, not rigorous interval-certified lower bounds. The fixed selected
source plane is-444.84239409854206m in the authored engineering datum.

The agreement rules out an observed sign, missing-intercept or column-scale
implementation discrepancy at this test's precision; it does not prove every
possible implementation error absent. The finer bases can reproduce training
data much more closely without damping than the inner-selected fit does.
Consequently these observations do NOT establish that every1/r representation
is scientifically incapable. Regularization, representation depth and sparse
cross-line constraints remain coupled. Selecting weaker damping because it
fits training or the already opened outer data better is not a legitimate
predictive repair. Any new predictive claim needs independently fixed physics,
geometry/candidates and genuinely untouched evaluation, not reuse of these
opened studies.

[Harmonica's equivalent-source model](https://www.fatiando.org/harmonica/v0.7.0/api/generated/harmonica.EquivalentSources.html)
is a harmonic scalar representation, not geological magnetization/depth.
Actual dipole controls differ from fitted source positions/operator.
Coverage/pixel size do not establish resolving power. No density/vector
inversion, field error estimate, independently evaluated IGRF, provider
acceptance, full-survey resource envelope or online admission follows.
