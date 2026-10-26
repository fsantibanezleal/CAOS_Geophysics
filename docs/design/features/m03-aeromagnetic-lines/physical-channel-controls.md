# Original-row physical channel and global-fit controls

## English

The streamed physical stage preserves the original intensity channel and every
source-order row. It applies the original S3 independent lag, base, heading and
authored-reference edges, rather than passing raw intensity into an anomaly fit.
The original S3 acquisition has 363 rows; it is an authored control, **not** the
missing 8201-row field acquisition. No original fixture, scientific assertion,
ordinary cap or predictive threshold changes.

### Geometry and independent originals

Lag evaluates position at measurement time plus the declared positive delay.
Independent navigation IDs/UTC/line membership/metric XYZ are verified. Relative
integer nanoseconds and fractional bracketing avoid rounding an absolute epoch
float. No extrapolation or cross-line interpolation is permitted. The owner
seals the aligned geometry before opening measurements; partition source blocks,
crossovers, support and reference coordinates bind that same geometry. Crossing
a JSON process boundary preserves this contract: explicit external strings are
validated and resolved as paths before packing verified navigation members.

The base station retains original UTC and intensity, strict increasing times and
the independently authored shared clock. Original UTC text padded to 30 ASCII
bytes defines ordered identity; no invented base row IDs are asserted. Canonical
original `{utc,intensity_nT}` records reconstruct the auxiliary source identity.
Subtract the interpolated base perturbation relative to the declared reference,
then subtract `a0 + ac*cos(h) + as*sin(h)` for clockwise-from-north heading.
Independent calibration with an empty acquisition-ID list is the original
authored coefficient branch. Nonempty/learned calibration cannot bypass the
required training-only estimator merely by supplying a coefficient hash.

The reference stage reads verified original F/D/I JSON, reconstructs ENU vector
components and magnitude, checks original datum/height and corrected geometry,
and independently verifies every stored vector/scalar/date entry. Gregorian row
UTC dates, validity interval and source rights are checked before subtracting F
from total intensity. The original constant is 48000 nT, D=12 degrees, I=55
degrees. This is not an IGRF evaluation. A field/IGRF branch is refused before
reading an authored substitute; field evaluator/datum/original custody remains
unresolved. Main-field subtraction and rereferencing are not interchangeable.

### Channel DAG and global fitting

Each derived channel has all original rows, explicit nT values, uint32 QC masks,
parent/output/evidence identities and signed operation history. Missing numeric
placeholders are only valid with their actual masks. The original channel SHA
retains the original canonical row-ID/value encoding. Derived edge identity uses
the explicit `m03-correction-row-edge/1` domain with length-prefixed original
row-ID, current metric XYZ, nullable value and QC, binding geometry as well as
values. It is deliberately not claimed equal to the older inline JSON DAG hash.
Arrays and manifests are immutable verified members, not arbitrary references.

`fit_corrected` verifies the physical producer output, every channel/mask/edge,
the current seal, measurement pass, original source and requested channel. It
uses actual aligned XYZ and final corrected anomaly, never rewrites metadata or
request into the opened-S1 diagnostic. It executes all 24 frozen inner fits,
selects only their validation scores, fits final training once and scores outer
once. Every fit includes all training rows and all sources in one global 1/r
objective. Chunks bound storage/kernel working sets, not independent models.
Depth/lambda candidates, half-open 400 m source blocks, scaling, no-intercept
rule and independent regularized stationarity threshold remain unchanged.

The physical channel, geometry, fit and evaluation receipts are components of
the full workflow. They are not padded into `SurveyResult`, a field PASS, online
admission or a completed CLI/export/replay. Rereference, fold-local leveling,
microlevel representation, semantic Result closure, actual owner lifecycle and
client instrument are distinct required stages. Unsupported requested stages
must refuse or retain their actual ineligibility; they are not silently skipped.

### Actual original controls

The in-process S3 control compares **every value in all five channels** against
the unchanged ordinary physical DAG and proves original bytes remain unchanged.
Wrong request lineage, geometry/source/epoch identity and field-reference
substitution have negative controls. No native numerical engine is needed for
these physical verifications. Actual cold worker execution covers seal, decode,
four physical edges and fsynced component receipts in one measured Windows Job,
with zero active child processes after drain. Counter results are resource
component evidence, not Linux/VPS admission.

The original S3 corrected global execution completed 25 fits and one outer
evaluation. All solver receipts passed the unchanged numerical checks. Outer
RMSE was 18.79974086240211 nT, signal RMS 5.193279307754436 nT. This is poor
prediction, not evidence that corrections repaired the equivalent-source basis.
The original S3 assertions establish correction accuracy, not a newly invented
predictive tolerance. Original S1 remains FAIL: 18.799740861734186 nT exceeds
0.25966396538773057 nT; its streamed repetition and opened 100/50 m studies remain
adverse historical attempts. Train-only metric/constant discrimination is
documented separately in [the root-cause controls](original-s1-training-root-cause.md).

## Español

La etapa física conserva el canal de intensidad original y todas las filas en
orden de adquisición. Ejecuta retardo, base, rumbo y referencia independiente del
S3 original, de 363 filas, sin presentar este control autoral como la adquisición
de campo ausente de 8201 filas. No modifica fixtures, afirmaciones, límites
ordinarios ni tolerancias predictivas. Las coordenadas corregidas se sellan antes
de abrir mediciones y gobiernan particiones, fuentes, cruces, soporte y referencia.
El retardo usa tiempo relativo entero en nanosegundos y fracciones; nunca
extrapola ni interpola entre líneas. La entrada JSON de rutas conserva la misma
validación externa que la ejecución local con objetos Path.

La base conserva UTC e intensidad originales y reloj independiente verificado.
Su identidad ordenada se obtiene del texto UTC original con relleno ASCII de 30
bytes; no se inventan identificadores. Se resta la perturbación de base respecto
de su valor declarado y después `a0 + ac*cos(h) + as*sin(h)`, con rumbo horario
desde el norte. La calibración autoral independiente vacía es el caso original;
coeficientes aprendidos o identificadores no vacíos necesitan estimación
exclusivamente de entrenamiento, no un hash declarado que simule independencia.

La referencia reconstruye F/D/I desde JSON original verificado, sus componentes
ENU, magnitud, geometría corregida, datum/altura, fechas gregorianas y validez.
Sólo entonces resta F de la intensidad total. La constante original es 48000 nT,
D=12 grados e I=55 grados; no es evaluación IGRF. El caso de campo/IGRF rechaza
una sustitución autoral antes de leer sus arreglos. La custodia de originales,
evaluador físico y datum de campo sigue sin resolver.

Cada canal derivado retiene todas las filas, valores nT, máscaras QC uint32 e
historial firmado de operación, padre, salida y evidencia. El SHA inicial
conserva la codificación original; las aristas derivadas usan explícitamente el
dominio `m03-correction-row-edge/1`, vinculando fila, XYZ actual, valor nullable y
QC. No se afirma igualdad falsa con el hash JSON inline anterior. Se verifican
todos los miembros y no se interpreta un placeholder numérico como dato válido.

El ajuste físico usa anomalía realmente corregida y XYZ alineado, no cambia
metadatos ni receta para convertirlos en diagnóstico S1. Ejecuta los 24 ajustes
internos congelados, selecciona sólo por validación interna, ajusta entrenamiento
final una vez y evalúa externo una vez. Cada ajuste es global con todas sus filas
y fuentes; los bloques sólo acotan memoria. Permanecen bloques de fuente de
400 m, candidatos, escalamiento sin intercepto y estacionariedad independiente.
El caso ejecutado completó 25 ajustes con controles numéricos PASS, pero RMSE
externo 18.79974086240211 nT y RMS de señal 5.193279307754436 nT: predicción pobre,
no reparación de la base. S1 y refinamientos conservan sus FAIL históricos.

Las pruebas comparan cada valor de los cinco canales contra el DAG ordinario
inalterado, identidad original y rechazos de linaje, geometría, fuente, fecha y
referencia de campo. El proceso frío real mide sellado, decodificación y cuatro
aristas, sin procesos activos tras drenaje. No equivale a admisión Linux/VPS,
SurveyResult completo ni CLI/exportación/replay o ciclo propietario e instrumento
cliente terminados. Referencia nueva, nivelación por partición, microlevel y
cierre semántico siguen siendo etapas distintas; una etapa pedida no se omite
silenciosamente ni se transforma su inelegibilidad en éxito.
