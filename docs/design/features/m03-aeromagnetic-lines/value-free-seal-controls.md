# Full original geometry, no-lag seal / Geometría original completa, sello sin desfase

## English

The owner stages are `magnetic_line_survey_geometry`,
`magnetic_line_survey_crossovers`, `magnetic_line_survey_support`, and
`magnetic_line_survey_seal`. These extend the new streamed namespace only.
The bounded scientific processor, result/replay schemas, actual negative
controls and frozen S1 thresholds are unchanged.

`seal_geometry` independently checks the original geometry inspection before
any stage, validates the closed SurveyInput/SurveyRequest, rejects provider
grids/images as flight lines, checks private-processing permission, authored
versus field classification, raw/dictionary/geometry references, dataset
identity, datum, acquisition gap limits, subset IDs and height consistency.
It runs all four whole-line partitions, training-only source blocks, complete
candidate enumeration and geometric support before decoding any magnetic or
uncertainty value. A lag request explicitly refuses this no-lag entry point;
original coordinates cannot be advertised as navigation-aligned geometry.

The coordinate digest is the original canonical `{datum,rows}` identity in
source order, produced incrementally, not a caller hash accepted on trust.
Only independently verified array/table member closures are copied into the
fresh external seal directory. Conflicting identities, existing destinations,
case collisions, links, unknown members and corrupted manifests refuse.
The public GeometrySeal is closed; the owner stage mappings returned in memory
are not hidden extra serialized keys. Capacity remains `unmeasured`: neither
a formula nor a seal is host admission or scientific acceptance.

Crossovers retain original adjacencies and all candidate pairs within the
frozen bounding-box tolerance. The R-tree is conservative float32 indexing
only; exact float64 overlap and the protected native intersection follow.
Candidate max-plus-one refuses before native intersection; no truncation.
Height, time, sensor, collinear, gap and shared-endpoint reasons remain.
Measurement/partition admission and per-fold representatives must still be
reconstructed before global incidence leveling; a geometric representative
alone does not authorize a training constraint.

Hull stacks, acquisition gaps, row ordinals and line summaries use fresh
external producer SQLite indexes. No omitted CV row invents an acquisition
hole. Grid support combines the closed training hull, exact radius and
closed original broken-adjacency tubes. Original flight-line spacing and
orientation qualify sampling; `sampling_unresolved` remains informational,
distinct from unsupported cells. It grants neither wavelength recovery nor
hole fill. Spectrum qualification ignores this informational bit but never
ignores actual geometric exclusions.

The Windows lifetime receipt includes its own serialized bytes by an exact
byte-count fixed point. Its source closure now binds all these stages and the
measurement decoder. Actual native zero/cancellation controls are component
evidence only, never genuine field or useful-request evidence.

Tests compare partitions, sources, coordinate digests, support and sampling
with the unchanged independent original implementations; retain candidate
overflow, datum/policy refusal, real acquisition ordinal gaps, and corrupted
custody negatives. The original 158-test regression retains the S1 failure;
no changed tolerance or synthetic fixture can supply missing provider bytes.

Still required: lag/navigation seal, immutable streamed correction DAG,
fold-local global incidence leveling, complete 24-inner-plus-final owner
fit/result/export/replay, transform integration, actual geometry-specific
cold/useful/cancel admission and verified supplied field attachments. Do not
read this component milestone as completion of MS01–MS15 or online activation.

## Español

Las etapas propietarias son `magnetic_line_survey_geometry`,
`magnetic_line_survey_crossovers`, `magnetic_line_survey_support` y
`magnetic_line_survey_seal`. Extienden exclusivamente el espacio de nombres
streamed nuevo. Se conservan el procesador acotado, sus resultados/replay,
los controles negativos reales y los umbrales congelados de S1.

`seal_geometry` verifica independientemente la inspección original, valida
SurveyInput/SurveyRequest cerrados y rechaza grillas/imágenes del proveedor
como líneas de vuelo. Comprueba permisos de procesamiento privado,
clasificación sintética/campo, referencias originales y diccionarios,
identidad del conjunto, datum, límites de discontinuidad, subconjuntos y
consistencia de altura. Construye las cuatro particiones de líneas completas,
fuentes exclusivas de entrenamiento, todos los candidatos de cruce y soporte
geométrico antes de decodificar magnetismo o incertidumbre. Este acceso sin
desfase rechaza una solicitud de lag: no presenta coordenadas originales
como navegación alineada.

La huella de coordenadas reproduce incrementalmente `{datum,rows}` original
en orden de adquisición. No confía en una huella declarada por el usuario.
Solamente copia cierres de miembros verificados a un directorio externo nuevo.
Rechaza identidades incompatibles, destinos existentes, colisiones de nombres,
enlaces, archivos desconocidos y manifiestos corruptos. GeometrySeal permanece
cerrado y su capacidad `unmeasured`; el sello no admite el host ni demuestra
validez científica.

El índice espacial conserva todos los pares candidatos y adyacencias
originales. Sus cajas float32 solamente podan conservadoramente; siguen la
prueba exacta float64 y la intersección nativa protegida. Superar el máximo
rechaza antes del trabajo nativo, sin truncar. Se mantienen razones de altura,
tiempo, sensor, colinealidad, discontinuidad y extremos compartidos. Las
restricciones y representantes deben reconstruirse por partición tras admitir
valores; un representante geométrico no autoriza calibración de entrenamiento.

Envolventes, discontinuidades, ordinales y resúmenes de líneas usan SQLite
externo creado por el productor. Omitir filas para validación no inventa huecos
de adquisición. El soporte combina envolvente cerrada, radio exacto y tubos
cerrados alrededor de adyacencias originales rotas. Espaciado y orientación
califican el muestreo; `sampling_unresolved` es informativo y no permite
recuperar longitudes de onda ni rellenar huecos. El espectro ignora ese bit
informativo, nunca exclusiones geométricas reales.

El recibo Windows incluye sus propios bytes mediante un punto fijo exacto y
vincula fuentes de todas estas etapas. Los controles nativos de objetivo cero
y cancelación son evidencia de componentes, no campo real ni solicitud útil.
Las pruebas comparan particiones, fuentes, coordenadas, soporte y muestreo con
implementaciones originales intactas. Retienen desbordamientos, rechazos de
datum/política, discontinuidades ordinales y corrupción. La regresión original
de 158 pruebas conserva el fallo S1, sin relajar tolerancias.

Faltan navegación/lag, DAG streamed inmutable, nivelación global por partición,
flujo propietario completo de 24 ajustes internos y uno final, resultado,
exportación/replay, transformaciones, admisión real con geometría propuesta y
adjuntos de campo verificados. Este hito no cierra MS01–MS15 ni activa online.
