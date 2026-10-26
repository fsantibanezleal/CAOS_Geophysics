# M01 scientific course: research before sub-SDD

Date: 2026-10-03. Research-only milestone at develop `4db6a1613373d139e4496b6392e605c36adfa978`. No course implementation, numerical execution, field acceptance or browser/job activation. [Source inspection and receipts](m01-course-sources-2026-10-03.md) distinguish inspected mathematics, bibliography, downloaded bytes and existing code.

## 1. The teaching problem and existing boundary

The existing [station guide](../methods/gravity-processing/01_station-corrections.md), [transform guide](../methods/gravity-processing/02_equivalent-source-transforms.md) and [ordinary adapter guide](../guides/13_local_station_adapter.md) already describe real local operations. The missing course should teach why those operations are justified, where they cease to be justified, and how a user supplies their own eligible inputs without relabelling processed principal facts. It must not add another correction engine, generic density inversion, source acquisition or authenticated API.

The current M05/M06 course demonstrates question-led bilingual chapters, captioned equations, physical diagrams and genuinely executed static worked records labelled replay. Its recorded output is not a live owned job. M01 should retain that separation, not copy MT physics, error definitions or residual signs. Course completeness does not close any method/source/host gate.

## 2. What is the gravity reference?

Let geodetic latitude be phi, ellipsoidal receiver height h in metres and observed calibrated gravity g positive downward in mGal. A normal rotating ellipsoid supplies gamma = |grad U|, with gravitational plus centrifugal potential U. It is neither a uniform-density ellipsoid nor an empirical subtraction from a sea-level measurement. Boule evaluates the closed-form reference on/above the ellipsoid; see its [normal gravity guide](https://www.fatiando.org/boule/v0.5.0/user_guide/normal_gravity.html) and [Ellipsoid API](https://www.fatiando.org/boule/v0.5.0/api/generated/boule.Ellipsoid.html).

On the ellipsoid, Somigliana's formula is

\[
\gamma(\phi,0)=\gamma_e\frac{1+k\sin^2\phi}{\sqrt{1-e^2\sin^2\phi}},\qquad
e^2=2f-f^2,\quad k=\frac{b\gamma_p}{a\gamma_e}-1,\quad b=a(1-f).
\]

Here a,b are equatorial/polar semi-axes, f flattening, gamma_e/gamma_p equatorial/polar normal acceleration. SI acceleration converts to mGal by 10^5. WGS84 rounded independent surface constants already used in the core oracle are a=6378137 m, f=1/298.257223563, gamma_e=9.7803253359 and gamma_p=9.8321849378 m/s^2. Rounded constants are not a replacement for Boule's closed-form height implementation or an exact-bit oracle.

The actual core computes co-located disturbance

\[
D=g-\gamma(\phi,h)
 =g-\gamma(\phi,0)+[\gamma(\phi,0)-\gamma(\phi,h)].
\]

The two recorded history additions therefore sum to one reference subtraction. Adding a further approximate +0.3086h would repeat the elevation-reference effect. The station has not been relocated to a geoid or sea level. Classical provider free-air anomaly is not automatically D. [Li and Gotze's primary tutorial](https://geored2.sgc.gov.co/Articulos%20y%20documentacion/Li_G_Tut.pdf) distinguishes reference surfaces and anomalies; this research inspected its introductory reference discussion, not a new reproduction of its entire appendix.

Learning test: if latitude, height, datum and processing state are unknown, does knowing a gravity scalar suffice? No. If an already corrected CBA is declared absolute observed gravity, do correct formulas rescue it? No: the input quantity is wrong.

## 3. Which height and which topography?

The conventional relation h=H+N connects ellipsoidal height h, orthometric height H and geoid undulation N only for compatible reference frames, tide conventions, epochs and geoid definitions. The core requires an explicitly supplied geoid model, N and its SD for orthometric inputs; it does not query a service. NOAA's [GEOID18 technical documentation](https://www.ngs.noaa.gov/GEOID/GEOID18/geoid18_tech_details.shtml) concerns NAD83(2011)/NAVD88, not a universal WGS84 conversion. A provider column named zWGS84 or elevation_ft_NVD29 does not independently resolve vertical datum. A quoted 95% geoid interval is not already a one-SD input.

For land with receiver above a nonnegative surface height t measured from the declared ellipsoid, the infinite plate gives B=2*pi*G*rho*t. For a receiver at h>=t the cylindrical Newton integral is

\[
G\rho\int_0^t\int_0^\infty
\frac{2\pi R(h-z)}{[R^2+(h-z)^2]^{3/2}}\,dR\,dz
=2\pi G\rho t.
\]

Thus B_mGal=C*rho*t with C=2*pi*G*10^5 and G=6.67430e-11 m^3 kg^-1 s^-2. It depends on plate thickness, not receiver clearance above the plate. The core subtracts B: D_B=D-B. The [Harmonica plate API](https://www.fatiando.org/harmonica/v0.7.0/api/generated/harmonica.bouguer_correction.html) supplies the engine; its additional ocean capability is not an implemented core lane.

Define actual topographic attraction A_topo positive downward. The signed supplied residual is T=B-A_topo, so D_T=D_B+T=D-A_topo. The exact core terrain object declares `additive_residual_to_plate`, density, ellipsoidal reference, station order, additions, SDs, method and source hash. It is not an unsigned DEM relief height, nor an arbitrary existing TTC column. A separately modelled DEM requires horizontal/vertical reference, resolution, extent, density, receiver geometry, boundaries and approximation lineage; [Harmonica topographic modelling](https://www.fatiando.org/harmonica/v0.7.0/user_guide/topographic_correction.html) illustrates that different calculation. This course must not promise it is performed by the supplied-residual core. Curvature, ocean, isostasy, raw instrument calibration/drift/tides and network adjustment are not new implemented operations.

## 4. What does an error number mean?

Let a be the gradient of a scalar reduction f with respect to its primitive measured quantities, and Sigma their covariance. First-order uncertainty is

\[
\delta f\simeq a^T\delta x,\qquad \sigma_f^2\simeq a^T\Sigma a.
\]

Independence reduces this to sum(a_i^2*sigma_i^2). Without known covariances, Cauchy-Schwarz gives sigma_f <= sum(|a_i|*sigma_i) for the linearized model. The latter is an upper bound on linearized SD, not a measured SD, deterministic nonlinear error bound, geological uncertainty or confidence interval. Missing uncertainty is not zero. This follows [JCGM 100 section 5](https://www.bipm.org/documents/20126/2071204/JCGM_100_2008_E.pdf). Its [2026 amendment](https://www.bipm.org/documents/20126/2071204/JCGM_100_Amd1_2026.pdf) explicitly cautions against insufficient first-order treatment of significant nonlinearity. The unchanged core remains first-order; no new Monte Carlo solver is promised.

For f=g-gamma(phi,h_r)-C*rho*h_s, derivatives are 1, -gamma_phi, -gamma_h, -C*rho and -C*h_s for g,phi,h_r,h_s,rho respectively. Latitude SD is in degrees because the engine derivative uses degrees. If one primitive N converts both receiver and surface orthometric heights, its derivative is -gamma_h-C*rho: combine that shared primitive once before RSS or marginal summation. Do not treat the two uses of N as independent errors or independently sum their absolute contributions first.

Across stations a common density error induces Cov(f_i,f_j)=C^2*h_si*h_sj*sigma_rho^2. Geoid covariance likewise requires an actual spatial error model, not guessed independence or guessed perfect correlation. Supplied terrain residual depends on the plate; current core therefore requires `conservative_marginals`. Components and propagated SD/bounds must remain distinctly labelled.

## 5. What field does the equivalent layer represent?

The actual transform fits a scalar 1/r basis, not the Newton vertical acceleration kernel G*delta_z/r^3:

\[
J_{ij}=\frac{1}{\|x_i-s_j\|},\qquad d_i\simeq\sum_jJ_{ij}c_j.
\]

Coordinates are local easting, northing, upward in metres; d is the admitted downward component in mGal. Sources use training XY and the plane min(training z)-depth. Coefficients have units mGal*m, not kg or kg/m^3. [Harmonica EquivalentSources](https://www.fatiando.org/harmonica/v0.7.0/api/generated/harmonica.EquivalentSources.html) supports this scalar harmonic representation. Its default placement underneath individual observations is not the custom common plane used here.

Away from sources, laplacian(1/r)=0. Fixed Cartesian gravity components are harmonic in source-free space; a gravity magnitude or arbitrary reduced/reference residual is not automatically an exact harmonic component. The current admitted `g_z_downward` approximation and `source_free_citation` need physical justification consistent with the local projection and reductions. A citation is a declaration, not proof of an empty subsurface/air volume. Terrain remaining above a target or inconsistent reference removal invalidates naive continuation assumptions.

Verde scales columns to unweighted unit SD without mean subtraction. With S that diagonal scale, A=J*S^-1, W=diag(1/sigma_i^2), the actual objective is

\[
\min_q\|W^{1/2}(Aq-d)\|_2^2+\lambda\|q\|_2^2,
\quad Q=A^TWA+\lambda I,\quad c=S^{-1}Q^{-1}A^TWd.
\]

Lambda is the existing Ridge alpha, not its square and not a source-density prior. This exact convention is visible in [Verde's least-squares source](https://www.fatiando.org/verde/v1.9.0/_modules/verde/base/least_squares.html). Damping improves solvability but adds bias; a finite damped condition number does not establish unique geological structure. Supplied covariance is used for propagation; fitting still uses diagonal weights, not generalized least squares.

## 6. What is independently validated and continued?

Freeze an outer spatially blocked train/holdout split using geometry and seed. Candidate depth/damping choice uses inner blocked folds on outer training only; source locations and plane are rebuilt from each fit's training rows. Pooled inner scores use supported validation rows and normalized residuals. Outer holdout values evaluate the selected method and do not tune depth, damping, height, mask, radius or precision ceiling. [Verde BlockKFold](https://www.fatiando.org/verde/v1.9.0/api/generated/verde.BlockKFold.html) and [BlockShuffleSplit](https://www.fatiando.org/verde/v1.9.0/api/generated/verde.BlockShuffleSplit.html) define block-shape ordering and count-based balancing; a fraction of blocks is not an exact station fraction.

For fixed geometry/selected parameters, target transfer L=J_target*S^-1*Q^-1*A^T*W propagates covariance as L*Sigma_train*L^T. Its diagonal supplies conditional prediction variance. It excludes geometry uncertainty, model bias, parameter-selection uncertainty and geological nonuniqueness. `independent_stations` additionally requires independent core errors with no nonzero shared density/geoid component; otherwise a cited supplied covariance must satisfy the actual admission checks.

For an ideal flat source-free plane, Fourier amplitudes obey

\[
\widehat d(k,z+\Delta h)=e^{-|k|\Delta h}\widehat d(k,z),\qquad k=2\pi f.
\]

This [official upward-continuation kernel](https://www.fatiando.org/harmonica/v0.7.0/api/generated/harmonica.filters.upward_continuation_kernel.html) explains short-wavelength attenuation. It is not the irregular equivalent-source algorithm implemented here. Negative Delta h amplifies noise and is forbidden by the local transform contract. Configured heights are absolute ellipsoidal upward coordinates, all at/above the highest original receiver, even a masked one. Selection takes the lowest covered candidate meeting the predeclared training-noise ceiling, not the best held-out fit. Failure produces `unmet_height_precision`, not a green result.

No extrapolation: support requires both the training convex hull and maximum horizontal nearest-neighbour radius. Unsupported predictions, SDs and residuals are null with reasons, not zero or hidden samples. Grid spacing is sampling, not geological resolving power. Current roughness is specifically RMS adjacent-easting differences in mGal, not an isotropic 2D derivative. Residuals are prediction-minus-observation, opposite the MT export convention. Original corrected input and masks remain unchanged.

## 7. Source-bound teaching evidence, not new acceptance

The existing control generator has three noncentral, translated/rotated irregular surveys, 196 stations, variable heights, four retained masked rows and buried positive/negative-density prisms. It uses independent Newton-volume quadrature and known authored noise, not the fitted 1/r kernel. Current numerical tests supply independent formula/sign/oracle checks; their historical receipts are not a newly executed course gate. A future recorded lesson must regenerate actual inputs and outputs under explicit approval, retain source/config/runtime/receipt identities and publish only authored controls.

The actual author archive remains useful for a QC/contract-rejection exercise only: processed principal facts, unresolved vertical datum, absent primitive SDs and incomplete original lineage do not become eligible by selecting fewer than 400 rows, inventing errors or treating CBA/ISO as absolute observed gravity. No acquisition or private-byte redistribution belongs to this course unit. A neural approximation is not needed to explain this chain; no M13 model, training set, score or activation is proposed.

Recommendation: six question-led lessons with four visibly explanatory scalar calculators, static source-bound recorded controls after separate approval, and genuine existing local Python user-file workflows. Keep authenticated physical jobs as MAIN-owned future integration, default closed. The prospective feature SDD must be reviewed completely before lesson authoring or any course code.
