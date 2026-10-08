# Exact local physical-root contracts

Status: approved frozen contract implemented by the local-only candidate; review/execution evidence is in the [review packet](review-packet.md). This is an ordinary function contract, NOT an API/wire/storage contract. All key sets below are exact; extra/missing keys reject, except conditional keys explicitly named. Native numbers mean exact int or float, never bool/string/None, finite and unchanged. Nonblank text is validated with a whitespace test but never trimmed. Hash text means exactly 64 lowercase hex characters, not authenticated provenance.

## 1. Fixed structural resource lane

| Quantity | Inclusive limit / exact accounting |
| --- | --- |
| Input | type(raw) is bytes, <=16777216 actual bytes; empty is invalid |
| Scientific canonical root | <=8388608 encoded bytes, sorted compact ensure_ascii=True allow_nan=False UTF-8 |
| Stations | 1..400, retained in original order |
| Container depth | <=16: root has value depth 1; each object-member/array-element value increments depth; only dict/list containers are depth-limited, matching the ordinary adapter; keys do not increase depth |
| Nodes | <=200000: each dict/list/scalar value counts 1, each object key counts 1; root counts 1; punctuation/whitespace do not count |
| Decoded keys | <=128 UTF-8 bytes, checked incrementally |
| Decoded string values | <=8192 UTF-8 bytes, checked incrementally |
| Numeric source token | <=128 ASCII characters including sign, decimal point, exponent sign/digits |
| Integer token | inclusive -9007199254740991..9007199254740991; no float-to-int rewrite |

String limits apply everywhere, including metadata, station IDs and history; decoded surrogate pairs count their real UTF-8 length. Finite float overflow rejects; finite rounding/subnormal/underflow follows ordinary native decoding. All scanner limits and canonical pre-count precede materialization. Later shape validation cannot bypass them. This is root depth, not shifted adapter-request/envelope depth. Existing adapter checks still independently apply if a future caller explicitly builds its request.

## 2. Root, metadata and instrument declarations

Root has exactly schema_version, metadata, state, stations, history. schema_version is gravity-stations-1. State/history count: observed_absolute/0, gravity_disturbance/2, bouguer_disturbance/3, terrain_adjusted_disturbance/4. All arrays are exact list; all objects exact dict.

Metadata required keys: source_kind, source_sha256, source_citation, rights, crs, reference_ellipsoid, height_datum, height_unit, height_sign, gravity_unit, gravity_sign, gravity_quantity, gravity_datum, tide_system, instrument_processing.

| Field | Accepted declaration |
| --- | --- |
| source_kind | field or synthetic_control, supplied and unchanged |
| source_sha256 | lowercase hash text; never assumed to equal raw SHA-256 |
| source_citation, rights, gravity_datum | nonblank text, not provider/rights authentication |
| crs / reference_ellipsoid | EPSG:4326 / WGS84 |
| height_datum / height_unit / height_sign | ellipsoidal or orthometric / m / upward |
| gravity_unit / gravity_sign | mGal, m/s^2 or microGal / downward or upward |
| gravity_quantity / tide_system | absolute_gravity / tide_free |
| geoid_model | ONLY for orthometric heights: required nonblank text; forbidden for ellipsoidal |

instrument_processing has exactly calibration, drift, tide. Each is exactly status, citation; status applied/not_applicable, citation nonblank. Calibration must declare applied. Unknown/pending/raw instrument reductions are not guessed or performed. These are declarations, not evidence of actual calibration/tide corrections.

## 3. Stations and primitive units

Each station has exactly station_id, latitude_deg, longitude_deg, receiver_height_m, surface_height_m, original_value, value_mgal, gravity_sigma, receiver_sigma_m, surface_sigma_m, latitude_sigma_deg.

- station_id: nonblank str, exact decoded-string uniqueness across stations; no casefold/trim/normalization.
- latitude_deg: native finite number in [-90,90]; longitude_deg in [-180,180]. No wrapping, projection or coordinate-equivalence test.
- receiver_height_m, surface_height_m, original_value, value_mgal: native finite number, no conversion or physical relationship test. original_value retains declared gravity unit/sign; value_mgal remains the supplied current scalar.
- gravity_sigma: finite >=0 in metadata.gravity_unit. receiver_sigma_m/surface_sigma_m: finite >=0 metres. latitude_sigma_deg: finite >=0 degrees. These are primitive error declarations, not newly propagated errors or geometric certainty.
- Orthometric only: geoid_m and geoid_sigma_m are required finite numbers, sigma >=0; both forbidden for ellipsoidal heights. No geoid calculation, height addition or uncertainty propagation.

No row mask, owner/job, metric XY, truth, processing receipt or eligibility key. All numeric types and Unicode contents survive unchanged. A missing/null error cannot become zero; zero remains legitimate structural input.

## 4. Exact historical record shapes

Every record has exactly name, parameters, additions_mgal, input_values_sha256, output_values_sha256. additions_mgal is a native finite-number list of station count; both hashes are hash-shaped text. Ordered name prefix is normal_reference, elevation_reference, bouguer_plate, terrain_residual, of the state's exact 0/2/3/4 length.

| Name | Exact parameters and structural constraints |
| --- | --- |
| normal_reference | ellipsoid=WGS84, height_reference=WGS84_ellipsoid, boule=0.5.0 |
| elevation_reference | same three keys/literals plus height_term=gamma(phi,0)-gamma(phi,h) |
| bouguer_plate | harmonica=0.7.0, density_kg_m3 finite1..10000, density_sigma_kg_m3 finite0..10000, geometry=land_infinite_plate, height_reference=WGS84_ellipsoid |
| terrain_residual | exactly kind, unit, height_reference, density_kg_m3, source_sha256, method, station_ids, additions_mgal, sigma_mgal |

Historical version literals are copied from the inspected current ordinary core's recorded contract; this does not import/check installed engines or authorize runtime. Changed scientific history versions require review of this static schema, not a wildcard parser suffix.

Terrain parameters: kind=additive_residual_to_plate, unit=mGal, height_reference=WGS84_ellipsoid; finite density1..10000 kg/m^3; source_sha256 hash text; method nonblank text; station_ids exact string list matching root station IDs/order; additions_mgal finite-number list of station count; sigma_mgal finite nonnegative list of station count. No checks that density equals earlier plate density or record additions equal parameter additions: these numerical/history relationships are core-authoritative. A well-shaped forged history can load structurally and must still fail numerical replay later.

There is no CorrectionConfig argument and no target/default application. A caller wanting subsequent processing separately supplies explicit config to the unchanged ordinary adapter/core, which can still reject this structurally accepted root.

## 5. Exact error surface

`GravityStationsJsonError(ValueError)` exposes exactly the public contract fields code:str, field:str, message:str. `str(error)` and its sole args entry are the fixed message. No returned error dict, retryability/HTTP status, raw text, offset excerpt, offending key/value, input hash or caller path. Reject before calling methods on non-exact input types.

| Code | Fixed message | Field |
| --- | --- | --- |
| gravity_json_type | Input must be exact bytes. | raw |
| gravity_json_limit | Input exceeds the local physical JSON bounds. | raw, document or a known bounded schema path |
| gravity_json_invalid | Input is not strict physical JSON. | document |
| gravity_json_contract | Input does not match the physical root contract. | root or a known bounded schema path |

Known paths consist only of literal schema names, dots and bracketed indexes (station/terrain arrays0..399, history0..3), <=160 ASCII characters; unknown/duplicate supplied keys map to document or the known containing object, never their actual key. Limits encountered before a schema path is known use document. Metadata text itself is never a path. Scanner/decode/cross-check expected failures map to these records; no retained decoder exception/document/context is exposed. Error raising is outside decoder catch context when necessary; `raise ... from None` alone does not remove __context__. Traceback locals are not a public serialization surface and are not promised erased.

For multiply-invalid input, exact type/raw-size checks run first; scanner grammar/token/limits fail at the first encountered violation; static schema checks use documented root/metadata/stations/history order. No global sorting/rewriting of the returned data is permitted merely to choose an error.

## 6. Identity and non-claims

Raw identity is SHA-256 of the caller's exact original bytes. The helper does not calculate or replace it. Scientific identity uses the existing Python sorted compact ensure_ascii=True allow_nan=False UTF-8 dialect, preserving native int/float types; it is not JCS, a JS JSON.stringify digest or the application ensure_ascii=False dialect. metadata.source_sha256 remains a supplied claim distinct from raw identity. There is no implicit equality assertion between these domains.

Success means only this fixed structural root lane was met. It grants no provider/rights/field/scientific eligibility, host/browser admission, job approval, M01/M02 acceptance or release. No API/storage/jobs/bundle/UI activation is included and no hold in the larger vertical SDD is waived.
