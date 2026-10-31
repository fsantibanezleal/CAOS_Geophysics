# Exact scientific and teaching boundaries

Status: proposed course contracts; existing scientific contracts remain authoritative and unchanged. Read [design](design.md), [scenarios](scenarios.md) and [workflows](workflows.md). No serializer, parser, scientific input or receipt is implemented by this docs milestone.

## 1. Parent and configuration, not a CSV flag

The native physical parent has exactly schema_version, metadata, state, stations, history; schema_version is `gravity-stations-1`. Permitted state/history lengths are observed_absolute/0, gravity_disturbance/2, bouguer_disturbance/3 and terrain_adjusted_disturbance/4. Existing state/history/numerical replay determines which subsequent correction is possible; target must be strictly later, never the same or earlier. There is no course dropdown that relabels a provider anomaly into an observed parent.

Metadata has fifteen required keys: source_kind, source_sha256, source_citation, rights, crs, reference_ellipsoid, height_datum, height_unit, height_sign, gravity_unit, gravity_sign, gravity_quantity, gravity_datum, tide_system, instrument_processing. source_kind is field or synthetic_control; crs EPSG:4326; reference_ellipsoid WGS84; height_unit m; height_sign upward; gravity_quantity absolute_gravity; tide_system tide_free. gravity_unit is mGal, m/s^2 or microGal; gravity_sign downward or upward. Explicit source/datum/citation/rights declarations are not authenticated source facts. Orthometric heights additionally require geoid_model; ellipsoidal heights forbid it.

instrument_processing has exactly calibration, drift and tide; each has status and citation. Calibration must declare applied; drift/tide applied or justified not_applicable. The core does not estimate them from instrument readings or infer that a missing declaration means already processed.

Each station has eleven required keys: station_id, latitude_deg, longitude_deg, receiver_height_m, surface_height_m, original_value, value_mgal, gravity_sigma, receiver_sigma_m, surface_sigma_m, latitude_sigma_deg. Orthometric stations additionally require geoid_m and geoid_sigma_m; ellipsoidal stations forbid them. Original gravity and gravity_sigma use the original declared gravity unit; current value_mgal is converted downward mGal with the actual history already applied. Heights/height SDs use metres; latitude and its SD use degrees. Finite numeric values exclude booleans; missing/null sigma is not zero. IDs and physical positions must be unique according to core rules, including antimeridian and pole equivalences. After explicit geoid conversion, 0<=surface<=receiver; no negative-land/ocean lane is silently added.

CorrectionConfig requires target and uncertainty_model. Targets are gravity_disturbance, bouguer_disturbance and terrain_adjusted_disturbance; uncertainty_model is independent_first_order or conservative_marginals. Optional keys are density_kg_m3, density_sigma_kg_m3, outlier_z and terrain. Plate/terrain targets require the two explicit density keys; density 1..10000 kg/m^3, density SD 0..10000 kg/m^3, outlier_z>=1. The normalized core config contains exactly all six keys. Omitted terrain versus explicit null have distinct submitted identities even when their normalized nonterrain config agrees. A non-null terrain object is forbidden for a nonterrain target; terrain target requires a valid supplied object.

Terrain is exactly kind, unit, height_reference, density_kg_m3, source_sha256, method, station_ids, additions_mgal, sigma_mgal. Required literals: additive_residual_to_plate, mGal, WGS84_ellipsoid; density must equal selected plate density. IDs/order and every vector match the parent. Additions are signed T=B-A_topo; sigma is nonnegative and explicit; dependence requires conservative_marginals. Source SHA is supplied provenance, not retrieved DEM proof.

Each recorded history entry has exactly name, parameters, additions_mgal, input_values_sha256, output_values_sha256. The known name prefix is normal_reference, elevation_reference, bouguer_plate, terrain_residual. Core replay checks exact parameters, values and hashes. Do not create a course history record with an arbitrary field-source correction code.

Core QC screens absolute deviations from the median using1.4826*MAD and the declared outlier_z threshold (default6); fewer than5 rows or zero MAD gives null scores/false flags with an unassessable warning. No rows are removed and excluded_station_ids stays empty. This robust screen is not a noise-SD estimate, proof of an instrument error or permission to discard geology. A subsequent transform mask is a separate explicit user declaration retained in the request, not automatic trimming based on a plot or holdout residual.

## 2. Ordinary correction request, result and error

`run_station_corrections(request)` consumes an exact native plain object with six keys:

| Key | Value |
| --- | --- |
| schema_version | gravity-station-adapter-request-1 |
| method | gravity.station-corrections/v1 |
| dataset | Complete physical parent, not displayed/rounded values |
| config | Actual submitted explicit correction config |
| input_dataset_sha256 | Core scientific digest of that exact parent |
| submitted_config_sha256 | Core scientific digest of that exact submitted config |

Native bounds are depth16, nodes200000, UTF-8 key/value bytes128/8192, 1..400 stations, scientific canonical full-request bytes<=16 MiB. They are not raw acquisition bounds and not an upload envelope. Inputs must already have been strictly decoded in a separately suitable caller lane. The adapter checks source file identity, imported resolved __file__, CPython3.12 release compatibility and actual Boule0.5.0/Harmonica0.7.0/NumPy2.2.6/SciPy1.15.2 pins. No environment install/update is implied by calling it.

Result has exactly schema_version=`gravity-station-adapter-result-1`, method, correction_result and receipt. correction_result is the entire dataset/processing/qc core result. receipt has exactly thirteen keys: adapter_version, adapter_module_sha256, core_module_sha256, request_sha256, input_dataset_sha256, submitted_config_sha256, normalized_config_sha256, output_dataset_sha256, correction_result_sha256, engines, python, python_implementation, acceptance. acceptance is exactly host_approved=false, full_method_accepted=false, field_source_verified=false. Keep their names and values, not a merged course PASS.

`GravityStationAdapterError.to_record()` is the safe four-key error surface: code, field, message, retryable=false. Codes are adapter_contract, adapter_limit, input_identity, config_identity, scientific_contract, runtime_incompatible, result_integrity, execution_failed. Messages are fixed by the unchanged adapter; no arbitrary exception/traceback/private path is a course/web error record. Ordinary core/transform CLI errors are a different local surface, not assumed safe for transport.

## 3. Transform request and deterministic parent limitation

Transform request has exactly schema_version=`gravity-transform-request-1`, correction_result, geometry and config. correction_result is the complete core result described in design.md; unwrap only the adapter's correction_result. State must be one of the three corrected disturbances. At least20 and at most400 original rows, at least20 unmasked noncollinear rows, distinct metric XY and local extent<=20000 m are required. A source larger than the bound is not thinned automatically.

The known deterministic processing fields, errors/components, QC, warnings, config, engine/module/input/output identities and false acceptance are checked against replay. Recorded Python must be a compatible declared CPython3.12.x release; its patch string is preserved and not rewritten to the current runtime. The recorded core receipt does not itself specify/authenticate original interpreter implementation or origin.

Input identity can match only independently reconstructable converted-original or known earlier-stage history-prefix parents. Reconstruction emits float current values. Some otherwise valid initial or resumed integer-bearing parents therefore cannot be reconstructed with identical scientific bytes. The current transform receives no exact earlier input object. Preserve the exact actual parent/history/processing; report the bounded limitation. Do not recast integers, rewrite history/input hashes, manufacture an earlier parent or imply universal resume support. Resolving that seam would require a MAIN-approved scientific contract change, outside the course.

## 4. Exact geometry and configuration

Geometry has exactly sixteen keys: station_ids, easting_m, northing_m, upward_m, coordinate_unit, axis_order, vertical_reference, metric_crs, mapping_citation, component, data_unit, source_free_citation, geometry_error_model, geometry_error_citation, mask, mask_reasons.

Literals are coordinate_unit=m, axis_order=`easting,northing,upward`, vertical_reference=WGS84_ellipsoid, component=g_z_downward, data_unit=mGal and geometry_error_model=fixed_geometry_conditional. Metric CRS/mapping, source-free and geometry-error citations must be explicit; text alone does not prove their physical truth. No degrees-as-metres, inferred projection, elevation replacement or source-free assertion from a successful fit. Upward values exactly match core QC receiver_ellipsoidal_m. Mask is an original-row boolean vector; true means excluded with a nonblank reason, false requires null reason. Coordinates remain required even for masked rows; masked heights still bound allowed target heights.

Config has fifteen required keys and only the two conditional covariance keys below:

| Key | Inclusive bounds/semantics |
| --- | --- |
| depths_m | 1..8 distinct candidates, each10..10000 m below minimum fit-training height |
| dampings | 1..8 distinct candidates, each1e-8..1e8; depth*damping count<=12 |
| heights_m | 1..8 distinct absolute upward candidates between max(all original receiver heights) and that max+10000 m |
| region_m | [west,east,south,north], ordered; each horizontal span<=20000 m |
| grid_spacing_m | 1..20000 m; at least3 nodes/axis, total<=12000; not finer than median outer-training nearest neighbour/3 |
| coverage_radius_m | 1..20000 m horizontal nearest-training threshold, in addition to hull support |
| block_shape | [northing_count,easting_count], exact integers2..20 |
| holdout_fraction | 0.1..0.4 of blocks, not an exact row fraction |
| seed | Exact integer0..2^31-1; geometry/count-based split only |
| inner_folds | Exact integer2..5, on outer training only |
| min_validation_coverage | 0.1..1; additionally>=3 supported rows in each inner validation fold |
| max_input_sigma_mgal | 1e-9..100; retained input-SD ceiling |
| max_transfer_sigma_mgal | 1e-9..100; predeclared height-selection precision ceiling |
| max_condition | 1..1e12; damped full-fit and inner-fit stability limit |
| error_model | independent_stations or supplied_covariance |

Independent station errors require independent_first_order core propagation and zero shared density/geoid contributions. supplied_covariance requires covariance_mgal2 and covariance_citation: a finite symmetric station-ordered n*n matrix, PSD within the unchanged numerical tolerance, positive diagonal. Its marginal SD must match independent propagated SD or not exceed conservative core bounds, as applicable. These are existing tested tolerances, not new relaxed course defaults. Fit weights stay diagonal inverse marginal variances; propagation uses the supplied covariance, not full-covariance GLS. Zero fit SD is rejected.

Algorithm: freeze outer train/holdout using active geometry; require>=12 train/>=3 holdout. Inner folds need>=8 fit rows and sufficient support. Rebuild source XY/common plane per fit; fit and score candidate scaled ridge systems on inner data only. Pool supported standardized residuals; retain failed candidates/reasons. Check surviving candidates on full outer training for stability; choose minimum inner normalized RMSE with depth/damping as deterministic tie-break. Do not refit using the holdout. Evaluate holdout once with supported/unsupported counts. Generate hull-and-radius-covered grids, propagate training covariance, and select lowest covered candidate height meeting the fixed SD ceiling. None meeting it gives unmet_height_precision with height=null and preserved diagnostics; CLI exits3 rather than success. Missing/stale lineage or no viable candidate is rejection, not precision failure.

## 5. Scientific result display and replay contract

Read exact source result fields, not course-manufactured summaries. Preserve original_correction_result, geometry and config. stations contains observed_mgal, fit_sigma_mgal, predicted_mgal, signed_predicted_minus_observed_mgal, normalized_residual, prediction_covered and nearest_training_m in original station order. Display covered_count and unsupported_count next to any RMSE. grids are shape[northing,easting], C-order flattened; fields predicted_mgal/conditional_sigma_mgal are null outside coverage. Keep outside_hull/outside_radius/mask distinctions and units on every map.

Uncertainty kind is conditional_linear_noise_propagation. Show its exclusion list: geometry, parameter-selection uncertainty, bias and geological uncertainty. Current roughness is adjacent_easting_difference_rms_mgal, not a 2D isotropic gradient. Model coefficients_mgal_m and mathematical depths cannot be mapped to density. provenance keeps corrections_reapplied=false, field_gate=open, full_method_accepted=false; runtime compatibility is not authenticated origin.

`replay_grid(result, grid_index)` reconstructs a numeric checkpoint without pickle. It is not a general untrusted importer, structural validator or receipt verifier. A future course producer must validate/bind its own committed result before calling it; browser controls cannot accept arbitrary checkpoints or executable Python.

## 6. Separate course-record index

Use the exact proposed eight-key index in design.md, not a ninth acceptance/timestamp field. The catalogue file is exactly a three-element list of these objects, one for each base scenario in case0/1/2 order, without another envelope. scenario_id is restricted to the approved catalogue in scenarios.md; source_pins has exactly the five scientific/figure filenames in the research record with lowercase64-hex actual hashes. runtime has exactly python, python_implementation and engines; actual transform engines are the four core pins plus Verde1.9.0, scikit-learn1.9.1 and matplotlib3.10.8. Recording compatible Python is not an authenticated origin claim.

request_sha256/result_sha256 use the existing sorted compact ensure_ascii=True allow_nan=False UTF-8 scientific-object dialect. The emitted receipt's file entries, and each course artifacts.sha256, hash actual file bytes instead. Artifacts are exact role/path/bytes/sha256 objects; bytes is an exact positive integer measured from the original file. Require eleven unique roles/paths: request, result, export_receipt, map_light, map_dark, diagnostics_light, diagnostics_dark, map_light_png, map_dark_png, diagnostics_light_png, diagnostics_dark_png. Their exact basename mapping is request.json, result.json, receipt.json, maps-light.svg, maps-dark.svg, diagnostics-light.svg, diagnostics-dark.svg, maps-light.png, maps-dark.png, diagnostics-light.png, diagnostics-dark.png. Prefix each path with its scenario_id directory only; no traversal, external URL, private source name or dynamic role. The existing exporter emits those actual names; bind measured bytes/hashes, never invent them. The result contains the numeric model; no nonexistent model.json is promised.

The approved Python producer must verify scientific object hashes against parsed committed files, actual artifact byte lengths/hashes, receipt file manifest bindings, exact source/runtime pins and split/config within the result. Python serialization preserves int/float differences; JSON.stringify is not that dialect. A browser reads only approved catalogue paths, stops accumulated source-byte loading at the recorded bytes+1 before parsing, checks exact length/hash and index/receipt/result declared identities and schema/source/runtime constraints; it does not reserialize native parents or claim independent scientific replay. Content-Length alone cannot substitute for counting actual chunks. A changed index alone must conflict with the pinned catalogue or emitted receipt; a changed result must fail its bound byte hash. No provider authentication, universal browser-memory ceiling or security against replacement of an entire trusted application follows from a self-consistent unsigned teaching record.

Preserve original export executed_utc as historical provenance. A viewer may not change its meaning or assign current execution time. Unknown keys/roles/scenarios, absent files or mismatches fail closed. No index/data files are emitted now; MAIN must approve this separate teaching index before later producer implementation.
