# Corrective basis, navigation, reference and owner-workflow review

Date: 2026-10-08. Status: proposed before new corrective code; independent review
pending. This supplements, does not silently replace, the existing M03 SDD.

## Evidence and hypotheses

Original fixed request: 400m half-open XY blocks, 66 final sources, minimum
training height minus selected 500m, lambda0.0001, no intercept. Retained direct
training SVD projection RMSE3.560874605601467nT; damped oracle3.560876112655139;
matrix-free3.560876112655113. Scale discrepancy7.342847947156929e-16 and
full-objective discrepancy6.095961820535938e-16. These are numerical observations,
not interval-certified lower bounds or bounds on outer prediction.

Historical original S1 outer18.799740861734186nT and streamed repetition
18.799740863534037nT exceed the unchanged0.25966396538773057nT target: FAIL.
Opened independent100/50m refinements4.523829180141187/4.398834333896642nT exceed
their unchanged0.33114843034021674nT target: both FAIL. A new basis cannot rename
any of these outcomes PASS or restore an untouched-validation label.

| Hypothesis | Independent training-only discriminator | Claim boundary |
|---|---|---|
| Wrong G units/scale | G=1/hypot(dx,dy,dz) in m^-1; s=population SD in m^-1, c in nT, q=c/s in nT*m; compare pinned Harmonica Jacobian and independent direct metric distances | Common coordinate scale k changes G and s by1/k, q by k, while A=G/s and predictions are invariant; a pure common-unit factor alone cannot explain projection error |
| Wrong distance/axis/datum | Compare every training/source pair; common XYZ translation preserves G; swapping XYZ consistently preserves distances; unilateral datum/axis changes must fail | Numerical agreement does not establish field CRS/datum correctness |
| Source geometry inadequacy | Reconstruct every original half-open block and minimum-training-height source; publish distance ranges, rank and singular cutoff | Coarse selected basis is observed inadequate on training; no universal1/r impossibility or promised finer-basis pass |
| Constant/background offset | Numerically project training residual onto residualized constant vector orthogonal to the original basis; report improvement and identifiability of [A,1] | Forensic only, NOT production intercept, main-field subtraction or permission to choose an offset from outer data |
| Crossover/gauge offset | Trace operations of actual original S1: zero corrections, no leveling solve | A crossover offset not applied cannot be the causal numeric difference for S1; empty requested inner-A leveling remains an adverse calibration gate |

Forensics opens only retained training observations/indexes and sources. It may
hash outer members for custody but never decode them, predict on them or score
them. Dense SVD is restricted to the original294x66 control and [A,1]294x67;
the production full-survey method remains matrix-free and global. No truth-body
read, source-body rewrite, coefficient selection or predictive verdict upgrade.

Primary bases: [pinned Harmonica inverse-distance model](https://www.fatiando.org/harmonica/v0.7.0/api/generated/harmonica.EquivalentSources.html),
[pinned Verde scaling/objective](https://raw.githubusercontent.com/fatiando/verde/v1.9.0/verde/base/least_squares.py),
[SciPy1.15.2 SVD](https://docs.scipy.org/doc/scipy-1.15.2/reference/generated/scipy.linalg.lstsq.html).
Equivalent-source strengths are a harmonic representation, not dipole moments,
susceptibility, density or inferred geological depth.

## Prospective training-only basis resolution, separate v2

Do NOT mutate v1 SurveySources/GeometrySeal/FitReceipt/profile limits. New literal
discriminators `magnetic-line-survey-request/2`, `magnetic-line-survey-geometry/2`,
`magnetic-line-survey-result/2`, `m03-offline-stream/2` identify a distinct method
request/result, not a repaired historical control.

Request-v2 uses all v1 required keys, but `equivalent_sources.source_geometry`
is replaced by `source_geometries:List(SurveySourceGeometry,4,4)` with the explicit
square block widths400/200/100/50m in that order, identical fixed origin and
representative/edge/vertical policies and max_sources<=65536. The initial review
definition retains depths200/500m and lambda0.0001/0.01/1/100, weights unchanged,
float64/no-intercept/unweighted population scaling, and fixed solver policy.
Other surveys must submit their own prospectively reviewed matrix; no default
borrowed from an opened outcome. Candidate order is literal
`width_descending_then_depth_then_damping_ascending`; tie rule is literal
`larger_damping_then_depth_then_block_width` within the existing1e-9nT rule.
Compare arithmetic mean of the three fold RMSEs; incomplete/ineligible candidate
matrix refuses selection, not a reduced opportunistic search.

Seal-v2 replaces four source_counts with `source_counts_by_geometry` four arrays
of four integers(final/A/B/C), binding all sixteen source maps before values.
CandidateFit-v2 adds `source_geometry_index:Int(0,3)`; candidate table cap96
(4x2x4x3). FitReceipt-v2 adds `selected_source_geometry_index:Int(0,3)`;
fit_count1..98, with97 mandatory fits and at most one separately named geometric
comparator. v1 remains24 candidates/25 mandatory/26 maximum fits. No winner
selected from final/outer/truth, no per-line/tile independent fits or thinning.

All other v1 limits remain:8m rows,65536lines/sources,4sensors,16m auxiliary rows,
8m candidate crossovers,128 arrays per closed object,192 logical export members,
1m TOTAL exported cells,4m internal FFT cells,4GiB raw and4GiB combined auxiliary
bytes,4GiB actual RSS and committed EACH,32GiB scratch,21600CPU/43200wall seconds,
one child/no descendants/thread1, cancellation10CPU/10wall seconds. Member192
counts logical arrays/tables/receipts, NOT arbitrary unlimited physical chunks;
chunk/page/profile bytes independently bounded. Exact kernel-pair planning sums
all97 mandatory fold shapes (not25 or max-source count echoed), plus prediction
and checks, still<=10^15. Same per-phase allocation formulas; candidate fitting
sequential, no97 cached prediction arrays. Source maps/candidate summaries may
raise scratch, which must be independently recalculated from actual retained
members and rejected before allocation if over original ceiling/headroom.

New v2 prediction requires a fresh independently reviewed value-free acquisition
seal and single unopened outer evaluation; opened originals may only supply
labelled diagnostic evidence. Do not generate a new source physics body merely
to chase a passed result. Keep the unchanged original positive control in the
regression suite, even when it fails. The requested genuine8201field file retains
all original rows; no presumed8201-to-Charleston identity.

## Navigation, auxiliary and reference identities

Existing v1 NAV uses explicit auxiliary IDs/UTC/line indexes/xyz. IDs have a
distinct namespace, no overlap with acquisition IDs, original order/hash is
SHA256 concatenated NUL-padded ascii64 IDs. Clock comparisons use UTC integer
nanoseconds relative to an anchor and exact float-rational lag; same-line
floor/ceil bracket, exact knots, no extrapolation/gap fill. Corrected coordinates
drive partitions, sources, crossovers, support and reference; original geometry
and original raw bytes remain immutable. Unsupported lag is explicitly masked;
current seal refuses unsupported rows rather than quietly dropping them.

SurveyBase-v1 has no row-ID field. Its two refs' ordered_ids_sha256 is explicitly
the SHA256 of concatenated original ASCII UTC cells padded to30 bytes, not
invented auxiliary row IDs or the measurement ID hash. Strict UTC order/unique
times, finite total intensity, station/clock/declared intervals and private
rights are required. canonical_records_sha256 is SHA256 canonical JSON original
list of {utc,intensity_nT}; authored source SHA must match those canonical bytes.
For field input original byte SHA and canonical record SHA are distinct and
must come from a reviewed adapter. Do not relabel a transport hash canonical.

Fixed heading coefficients remain independent calibration evidence; calibration
row IDs may be empty only for authored fixed coefficients, never fabricated
empty IDs for learned field calibration. Every learned fold calibration excludes
outer/inner labels. Operations preserve original requested channel identity,
parent-edge/output hashes, parameters/sign/units and evidence SHA. Output hash
uses length-prefixed canonical source-order row objects and masks in a newly
named streamed edge domain, never calls an old inline hash equivalent.

Reference arrays must cover ALL original corrected rows in original acquisition
ID order, exact nT ENU roles, F>0, vector magnitude/direction consistent at frozen
tolerances; row dates use actual Gregorian UTC or explicit survey epoch evidence.
Datum, height convention/unit/transform, original NED->ENU conversion(Y,X,-Z),
model generation, coefficient/evaluator/source/rights hashes remain mandatory.
Authored constant reference has a source identity of its original constant
definition; independently reconstruct scalar/vectors/date/coordinates, NOT
zero or guessed reference arrays. Streamed receipt hash is canonical closed
SurveyReference excluding receipt_sha256; inline predecessor receipt SHA is
retained separately in the provenance edge and is never silently reused.
IGRF14 nominal1900..2030 only; no extrapolation or guessed Charleston altitude
semantics. Existing reviewed evaluator/datum receipt is needed before field
reference admission; user-hash agreement is not evaluator verification.

Main-field subtraction accepts only total intensity. Rereference anomaly adds
old F then subtracts new F with exact old lineage recovered; no double reference
subtraction. Lag/reference disagreement refuses before native fit. NAV+base+
heading+reference original source identities and current derived edges must be
part of export/replay closure, not only a channel label.

Microlevel representation defect: introduce `microlevel_transfer` float64[Qn,Qe]
dimensionless, Q<=4194304, and permit spectrum_power/removed/retained at that FFT
shape only under explicit bound. Exported/clipped arrays remain within TOTAL
P<=1048576. Never reuse nT/grid_mask/source_scale roles for a dimensionless
transfer. This is a proposed typed role correction, not weakened filter physics;
geological_preservation_claim remains false and diagnostic_only promotion.

## Full result, CLI, owner wire and instrument

v1 completion need not wait for v2 representation selection. Preserve strict
SurveyInput/Request/Result-v1 fields. Add cross-object semantic validation:
counts exhaustive/disjoint; IDs/shapes/roles/unit/masks/parent DAG consistent;
geometry/partitions match seal; actual fit count/candidates and independent
gradient/control receipts; requested grid/continuation/support/spectrum correct;
outer observed/predicted/residual match selected FINAL model; rights enforce
every member and transitive data-bearing root. A diagnostic envelope must not
be cast or padded into SurveyResult. Numerics may succeed while predictive or
field gate fails: retain that distinction, never overall-pass if any gate fails.

Owned CLI candidate `data-pipeline/magnetic_line_survey_cli.py` commands:
`run --csv PATH --metadata PATH --request PATH --auxiliary-root PATH --data-root
EXTERNAL --temp-root EXTERNAL --output-root FRESH_EXTERNAL`, `verify --result-root
EXTERNAL`, `export --result-root EXTERNAL --destination FRESH_EXTERNAL --scope
private|public`, `replay --bundle-root EXTERNAL --temp-root EXTERNAL --output-root
FRESH_EXTERNAL`. No URL/module/expression/whole-file loader. No default repo/system
temp or repo data; resolve explicit root or GEOPHYSICS_LOCAL_DATA_ROOT. Full native
run starts actual controller before decode/import, lasts through export/fsync,
hashes code/runtime/all originals and terminal counters. Optional replay rights
missing -> unresolved, not fake verification. One global fit, chunks storage only.

Actual owner replacement candidate `app/magnetic_line_survey_workflow.py`, separate
from CLOSED port. Reuse current_user/get_session/_owned_project; owned ProcessingJob
method discriminator `magnetic_line_survey_v1`, no another method's recipe/result.
Proposed POST `/api/projects/{project_id}/magnetic-line-surveys/jobs` exact body:
schema literal`m03-owner-start/1`, dataset_id:UUID, original_asset_id:UUID,
metadata_asset_id:UUID, request_asset_id:UUID,
auxiliary_asset_ids:List(UUID,0,16), dataset_sha256:Hash,
original_sha256:Hash, metadata_sha256:Hash, request_sha256:Hash,
auxiliary_sha256:List(Hash,0,16). Corresponding auxiliary list lengths equal,
UUIDs unique; all refs same owner/project, immutable DB bytes/hash verified.
Never accept device paths, user worker modules or arbitrary URLs. Ownership and
CSRF/origin checks precede parse/storage dispatch. Admission rejects incompatible
metadata/budget without allocating a successful job.

GET `/jobs/{job_id}` exact response keys schema`m03-owner-job/1`, job_id:UUID,
project_id:UUID, dataset_id:UUID, method:`magnetic_line_survey_v1`,
state:Enum(queued,running,succeeded,failed,cancelled), cancel_requested:Bool,
request_sha256:Hash, result_sha256:Nullable(Hash), result_bytes:Nullable(Int),
error_code:Nullable(ID), created_at:UTC, started_at:Nullable(UTC),
finished_at:Nullable(UTC). Actual generic host lifecycle mapping must be reviewed
before mount, not guessed SQL state aliases. Scientific FAIL can be a completed
execution with failed scientific gates, shown explicitly. GET `/jobs/{job_id}/result`
returns verified SurveyResult; GET `/jobs/{job_id}/members/{member_id}` owner-checks
and streams only named verified permitted members. POST `/jobs/{job_id}/cancel`
has no body and returns same job response; actual worker cancellation and drain,
no mere state toggle. POST `/jobs/{job_id}/export` exact body schema
`m03-owner-export/1`, scope:Enum(private,public); returns an owner artifact UUID,
bytes/hash and download route only after real immutable export. GET/POST foreign
or nonexistent IDs404, no session401, unsafe mutation403. No path/traceback/raw
value leak. Restart abandons/drains interrupted attempt with retained counters,
never upgrades lost work. Delete project cancels/drains and removes owned magnetic
members, stale download404. Mount patch must replace, not install beside, CLOSED
POST. MAIN owns generic worker/supervisor/server assembly edits.

Client candidates `frontend/src/features/magneticLineSurvey/{contract.ts,api.ts,
SurveyInstrument.tsx,SurveyInstrument.test.tsx}`. Instrument owns source/correction
review, parameters/geometry preflight, real run/cancel, job/result/export/replay
navigation and linked spatial line/grid/crossover/validation selections. Show
units, axes, height/datum, mask reasons, selected candidates and adverse gates;
never fill unsupported cells. Use existing shell/language/theme/project auth;
no sharedWorkbench/source/FWI/Linux-supervisor edits. Parent integrates isolated
export through its current navigation. Actual browser QA must exercise source
selection -> job -> result -> linked cell/line -> export/cancel, both EN/ES themes,
phone/desktop, owner failures and restart; closed-port200/schema test is not this.

## Reviewed provider acquisition and honest remaining field gate

Existing source-ledger has Bartlett metadata and author derivative archive, not
a pinned Charleston flight-line fetch record. Bartlett magnetic cells cannot
become flight/tie IDs, UTC/heights/errors. The reviewed Charleston catalogue lead
is DOI10.5066/P9EWQ08L, magnetic child5f4da2c182ce4c3d1231922e. Fresh original
FGDC XML17806bytes SHA badd712ff0e169bd62ed70b34ce273ef9bea4b4ec7a206627b09eac55a98a1c2
matches retained metadata. Official names: Charleston_MagneticFlightLineData.csv,
DataDictionary_CharlestonMagnetic.csv and contractor report. Release CC0 and
metadata access constraints none; exact attachment/contractor notices remain
separate. Today official child JSON returned403; no measurement bytes obtained.

Follow only exact official attachment links discovered from the reviewed lead;
no constructed bucket URLs or arbitrary mirrors. Independently pin object URL,
actual bytes/SHA/HTTP status/retrieval and original dictionary/report before
adapter. Rounded2580MB is NOT exact byte pin. Existing generic fetch allowlist
does NOT include ScienceBase; any new fetch object/host/format needs the same
reviewed record, not bypassing sources.py. Owner may use legitimately acquired
original local file under explicit E_Datos with original provider receipt.
Never overwrite original, invent row metadata or download whole survey on VPS.
Current device resolver declares temp E_Temp only; explicit E_Datos user-named
data root is used until registry has one, not a repository fallback.

## Español: límites y flujo completo

Se conserva FAIL original S1 y ambos refinamientos: no hay nuevo PASS ni datos
externos intactos recuperados por volver a procesarlos. La proyección SVD interna
no es cota rigurosa ni prueba de imposibilidad de toda base1/r. Se comprueban
unidades métricas, distancias, traslación, escala común, fuentes originales y
constante residual sólo con entrenamiento. Una constante diagnóstica no autoriza
intercepto ni corrección física; S1 sin nivelación no cambia por cruces no usados.

La propuesta v2 sella las cuatro resoluciones y todos los96 candidatos antes de
valores, selecciona únicamente por tres particiones internas, ajusta una vez y
evalúa externa una vez:97 ajustes,98 sólo con comparador separado. No cambia
perfil-v1 ni tolerancias. Todos los topes de filas/fuentes/bytes/RSS/memoria
comprometida/FFT/celdas exportadas/scratch/CPU/tiempo siguen iguales; el costo se
recalcula para97 ajustes y todos los miembros retenidos, sin reducción de datos.

NAV, base, calibración y referencia conservan bytes originales, registros
canónicos, relojes/IDs/datum/fechas y aristas exactas. La base usa hash de UTC
originales, no IDs inventados; ENU=(Y,X,-Z) para NED; IGRF no se admite por hash
de usuario o datum supuesto. Microlevel requiere transferencia adimensional y
mantiene carácter diagnóstico sin afirmación de preservación geológica.

SurveyResult/CLI/exportación/replay deben ejecutar el DAG científico completo,
validar semántica y permisos transitivos, conservar cada fila original y un
operador global. El adaptador propietario necesita trabajos reales, UUID/hash,
cancelación medida, recuperación, resultados/miembros/exportación y eliminación;
el cliente necesita instrumento vinculado a los originales con EN/ES, temas y
QA real en navegador. CLOSED no equivale a implementación online. MAIN integra
y activa; no se toca Workbench, fuentes/ERT/traveltime, FWI ni supervisor Linux.

Charleston es una fuente revisada con derechos CC0 a nivel de publicación, pero
403 actual impide descubrir objetos originales; XML verificado no es campo.
El archivo original8201 solicitado sigue no verificado. No se sustituye por
grillas Bartlett, controles sintéticos, subconjuntos o metadatos fabricados.
