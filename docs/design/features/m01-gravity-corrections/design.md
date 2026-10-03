# M01 local station processing design

Date: 2026-10-03. Review basis: approved product SDD section 4 M01 and the explicitly authorized bounded corrections unit. No product architecture or acceptance change.

## Interface and states

One ordinary module, `data-pipeline/gravity_processing.py`, exposes `process_survey(dataset, config)`. No package, installable project, API, worker or frontend change. JSON dictionaries form the serialized boundary, with strict keys and finite numeric/range validation. Output holds a round-trippable `dataset`, `processing` provenance and `qc` map/flag arrays. The CLI accepts input JSON and explicit output directory, writes new files exclusively and never overwrites an original. Paired scripts use the isolated `.venv-m01` interpreter and forward identical CLI arguments.

States are `observed_absolute -> gravity_disturbance -> bouguer_disturbance -> terrain_adjusted_disturbance`. Each boundary can be exported and resumed. The disturbance transition adds normal reference and elevation reference exactly once as an atomic stage; plate and residual-terrain additions are subsequent stages. Requested same/earlier states are errors. A history must exactly match the names/order for its state, reconstruct current values from untouched original values, and match each input/output value hash. Changing a prior density/reference/model during resume is rejected. Provider anomalies lacking this reconciled history are ineligible; never undo unspecified provider corrections.

Metadata names `EPSG:4326`, WGS84, geodetic degrees, tide-free gravity datum/citation, positive-up metre heights, gravity unit/sign, original gravity kind, calibration and tide status/citation, and synthetic/field truth status. Every station has ID, lat/lon, receiver and surface heights, original/current gravity, SD of original gravity in its declared unit, receiver/surface SD in metres, latitude SD in degrees and, for orthometric heights, geoid undulation/SD. Only land on/above ellipsoid with receiver on/above the surface is supported. Zero SD is a documented deterministic control, not estimated field precision. Duplicate IDs or positions fail for review.

## Mathematics and uncertainty

Equations and primary sources live in [research](research.md); read before implementation. Pins: Boule 0.5.0, Harmonica 0.7.0, NumPy 2.2.6, SciPy 1.15.2. A dedicated pinned environment is needed: inspected existing product environments do not contain Boule/Harmonica. Use existing local Python 3.12 and cached official wheels where available; never modify an environment owned by another agent.

Independent propagation computes the first-order gradient of the **final combined** expression in original gravity, latitude, receiver height, surface height, geoid and density. The geoid contribution uses the sum of the receiver and surface derivatives because it moves both. Preserve uncertainty components. The conservative model sums absolute gradient times marginal SD; this upper bound does not require input-error independence. A terrain residual may share density/plate errors, so only the conservative model is eligible with it. No geological confidence/posterior claim follows. Finite-difference normal-gravity derivatives use 0.1 m and 1e-4 degree; one-sided latitude differences at poles and a second-order forward height difference at the ellipsoid avoid invalid interior evaluation. Plate derivatives follow the exact analytical linear expression.

QC maps retain ID, lon/lat and original/output mGal for every station. Fixed configurable robust MAD threshold flags values, excludes none and does not affect numerics. Small/zero-MAD data return an explicit unassessable-outlier warning. There is no data-fit prediction or heldout metric without a fitted interpolation model.

## Verification and limits

Independent formula/value/sign/unit/datum controls precede synthetic chain closure. Canonical artifacts are untouched; all executable outputs use temporary/ignored local directories. Tests include malicious or ambiguous history, config change during resume, tide/drift missingness, supplied terrain semantics, real CLI failure codes and input immutability. Documentation diagram is checked structurally and rendered separately in both themes. Convergence records exact local tests/environment and open full method gates. User explicitly requests scoped commits, pushes, PR to develop and self-review, with no merge or deployment.
