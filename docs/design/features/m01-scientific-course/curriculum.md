# Six question-led lessons and literal definitions

Status: proposed curriculum, not authored wiki lessons or course PASS. Mathematical derivations and primary citations are in the [research dossier](../../../research/m01-course-research-2026-10-03.md). All equation captions, diagrams, controls, exercise answers and non-claims must have equivalent EN/ES content after approval.

## Q1. What quantity and reference did the station measure?

ES: ¿Qué magnitud y referencia midió la estación? Introduce absolute calibrated downward gravity, original units, geodetic latitude, receiver height, gravity datum, tide convention and instrument-processing declarations. Derive surface Somigliana and show that Boule's full gamma(phi,h) is required off the ellipsoid. Decompose D=g-gamma(phi,h) into the two recorded additions without moving the observation. Explain why a sea-level free-air anomaly or processed CBA is not interchangeable with this disturbance.

Exercise: predict the sign of the reference-height addition, then explain why adding approximate free-air again is wrong. Inspect a known already-corrected principal-fact schema as a declaration challenge, not a newly eligible station. Figure1: ellipsoid/geoid/surface/receiver drawn separately with labelled h,H,N and a downward component arrow. No guessed conversion between historical provider datums. User-file task: audit every declaration before any processing call. References: Boule, Li/Gotze, NOAA.

## Q2. Which mass contribution are we subtracting?

ES: ¿Qué contribución de masa estamos restando? Derive the infinite-plate Newton integral, its independence from receiver clearance and the separate receiver/surface heights in the core. Explain D_B=D-B and T=B-A_topo, with D_T=D_B+T. A supplied signed residual is a documented upstream calculation, not an on-demand DEM query or unlabelled terrain height. Discuss density as a supplied reduction assumption, not density learned from the station data.

Exercise: double plate thickness at fixed density and predict B; raise a receiver at fixed surface and distinguish changes in gamma from unchanged plate B. Reverse T's sign and trace the result. Figure2: infinite plate compared with finite relief at the same receiver; label attractions and algebraic residual, not an unsigned relief correction. User-file task: check terrain density/datum/station ordering/source/error lineage and reject repeated or mismatched application. References: Harmonica plate/topographic APIs.

## Q3. Is the error an SD, a covariance or only a bound?

ES: ¿El error es una desviación estándar, una covarianza o solo una cota? Derive a^T*Sigma*a, independent RSS and the conservative sum from covariance bounds. Follow one geoid primitive into both heights before combining it. Show shared density error across stations. Explain why terrain residual dependence forces conservative core treatment and why a spatial transform needs an actual covariance rather than treating that bound as an independent SD.

Exercise: for fixed marginal SDs compare positive, zero and negative correlation; identify which calculation is known without covariance. Distinguish an absent error from a defensibly zero component and a two-sided interval from one SD. Explain why a MAD flag neither estimates sigma nor establishes an instrument error, and why fewer than5 rows or zero MAD makes the screen unassessable. Figure3: one primitive N branching to two height contributions and reconverging in one derivative; a separate station pair shows shared density. User-file task: inspect components, retain original flags/rows and choose/reject the declared station error model without guessing. References: JCGM100 and 2026 amendment, current core/transform contracts.

## Q4. What does the equivalent layer fit, and what does it not recover?

ES: ¿Qué ajusta la capa equivalente y qué no recupera? Derive J=1/r, harmonic-domain assumptions, coefficient units and actual scaled ridge objective. Contrast independent buried-prism G*delta_z/r^3 integration with the fitted scalar basis. Explain the current common source plane and why an accepted scalar disturbance still needs a defensible local component/source-free approximation. Separate damped matrix conditioning, unregularized design singular values and geological nonuniqueness.

Exercise: compare training-only candidate layers of different depths and coefficients; explain why similar fits cannot locate a body or recover rho. Figure4: irregular above-ground receivers, known authored buried prism and a differently located mathematical layer, with distinct legend meanings. User-file task: read the selected model, source pins, coefficient units and uncertainty exclusions rather than plotting coefficients as density. References: Harmonica EquivalentSources, Verde least-squares source; Dampney as further reading only.

## Q5. What did spatially blocked validation actually test?

ES: ¿Qué evaluó realmente la validación por bloques espaciales? Derive normalized residual and pooled supported inner score. Freeze an outer spatial split before fitting; every inner training set defines its own sources/support. Select depth/damping using only inner training-validation on the outer training subset, then evaluate the untouched outer holdout. Explain geometry-count balancing and block fractions. A holdout is an interpolation/transfer experiment conditional on support, not an IID or universal future-survey guarantee.

Exercise: identify leakage when the outer score chooses the winning layer or unsupported rows disappear from the denominator without coverage counts. Figure5: blocks, inner folds, outer holdout, training hull and nearest-neighbour-radius gaps; all missing support stays visible. User-file task: inspect split hash, source indices, invalid-candidate reasons, coverage counts and signed prediction-minus-observation residuals. References: Verde block APIs and structured-CV primary discussion.

## Q6. At what height can we report the field, and with what limits?

ES: ¿A qué altura podemos informar el campo y con qué límites? Derive ideal Fourier attenuation e^(-|k|*Delta h) with k in radians/m and distinguish it from actual irregular-source evaluation. Derive conditional transfer variance diag(L*Sigma*L^T). Explain lowest covered height meeting the predeclared training-noise ceiling, absolute height semantics, source-free volume and forbidden downward continuation. Show hull/radius null masks, retained original exclusions and station/grid axis orders.

Exercise: predict wavelength-dependent attenuation, then diagnose high noise, a target below one masked receiver, missing coordinates and unmet precision. Figure6: observation and target planes, short/long wavelength amplitudes and unsupported map cells, not a fabricated density section. User-file task: export the actual maps/diagnostics, check selection.status and conditional SD, and preserve failure instead of forcing a selected height. References: Harmonica upward kernel and unchanged transform implementation.

## EN/ES glossary: definitions are literal, not acceptance labels

| EN / ES term | EN literal definition | ES literal definition |
| --- | --- | --- |
| Gravity disturbance / Perturbación de gravedad | D=g-gamma at the same latitude and receiver height, in mGal; not automatically a classical free-air anomaly | D=g-gamma en la misma latitud y altura del receptor, en mGal; no es automáticamente una anomalía clásica de aire libre |
| Ellipsoidal height / Altura elipsoidal | Height above the stated reference ellipsoid, in m, positive upward | Altura sobre el elipsoide de referencia declarado, en m, positiva hacia arriba |
| Orthometric height / Altura ortométrica | Height associated with the stated physical vertical datum/geoid convention; no conversion inferred from a column name | Altura asociada al datum vertical físico y la convención de geoide declarados; el nombre de una columna no permite inferir una conversión |
| Supplied terrain residual / Residuo topográfico suministrado | Signed T=B-A_topo added after plate subtraction, with upstream method/error/density/datum lineage | T=B-A_topo con signo, sumado después de restar la placa, con trazabilidad del método, error, densidad y datum de origen |
| Standard deviation / Desviación estándar | One-SD uncertainty of a declared quantity under its error model; not confidence interval width | Incertidumbre de una desviación estándar de una magnitud declarada bajo su modelo de error; no es el ancho de un intervalo de confianza |
| Covariance / Covarianza | Joint error dependence in squared units, with explicit station/primitive ordering | Dependencia conjunta de los errores en unidades al cuadrado, con orden explícito de estaciones o variables primitivas |
| Conservative marginal bound / Cota marginal conservadora | Upper bound on first-order SD from marginal uncertainties; not independent SD or geological error | Cota superior de la desviación estándar de primer orden a partir de incertidumbres marginales; no es una desviación estándar independiente ni un error geológico |
| Equivalent source / Fuente equivalente | Mathematical harmonic basis coefficient; not an identified geological body, mass or density | Coeficiente de una base armónica matemática; no es un cuerpo geológico, una masa o una densidad identificados |
| Spatial holdout / Conjunto reservado espacial | Frozen outer blocks used only for evaluation, with supported counts reported | Bloques externos fijados y usados solo para evaluación, informando las cantidades con y sin soporte |
| Upward continuation / Continuación ascendente | Field evaluation at a higher admitted absolute coordinate in a justified source-free volume | Evaluación del campo en una coordenada absoluta superior admitida dentro de un volumen sin fuentes físicamente justificado |
| Signed residual / Residuo con signo | M01 prediction minus observation, in mGal; standardized by fit SD; MT export uses the opposite convention | Predicción menos observación de M01, en mGal; se normaliza por la desviación estándar del ajuste; la exportación MT usa la convención opuesta |
| Conditional prediction uncertainty / Incertidumbre condicional de predicción | Propagated declared input noise for fixed geometry and selected model; excludes bias, selection and geological uncertainty | Ruido de entrada declarado y propagado para geometría fija y modelo seleccionado; excluye sesgo, incertidumbre de selección e incertidumbre geológica |
| Recorded replay / Reproducción registrada | View of actually executed pinned authored-control output; no live owned job | Vista de la salida de un control analítico definido y ejecutado realmente en una revisión fijada; no es una tarea activa de un propietario |

Final full lesson translation still requires scientific review; this bilingual definition table is a contract, not finished chapter prose. No learning question is answered by a fabricated field result or a claimed neural capability.
