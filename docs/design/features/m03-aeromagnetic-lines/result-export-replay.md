# Full-survey result, custody and replay / Resultado, custodia y reproducción

## Original acquisition through a result / Adquisición original hasta un resultado

**EN.** The local `run` entry point reads the original CSV, metadata document,
scientific request and explicit auxiliary closure from external storage. No
decoded magnetic values are accepted from a client. The controller creates a
fresh owned workspace and the fixed worker proves its actual containment before
geometry intake. Navigation is aligned before partitioning, source centroids,
crossovers and support. Only after the value-free geometry seal does the worker
decode original measurements, apply the ordered physical DAG, execute every
declared inner candidate and the single selected global final fit, evaluate the
retained outer partition, and predict the full exported grid. Chunking is bounded
operator evaluation against **all** sources, not independent local models.

**ES.** La entrada local `run` lee el CSV original, documento de metadatos,
solicitud científica y cierre auxiliar explícito desde almacenamiento externo.
No acepta valores magnéticos decodificados desde un cliente. El controlador crea
un espacio propio nuevo y el trabajador fijo comprueba su contención real antes
de leer la geometría. La navegación se alinea antes de particiones, centroides,
cruces y soporte. Solo después del sello geométrico sin valores se decodifican
las mediciones originales, se aplica el DAG físico ordenado, se ejecuta cada
candidato interno y el ajuste global final seleccionado, se evalúa la partición
externa conservada y se predice toda la malla exportada. Los bloques evalúan el
operador con **todas** las fuentes: no son modelos locales independientes.

**EN.** Representation/2 is distinct from science-policy v2. A result explicitly
tagged `fixed_basis_v1` contains the unchanged Request/1, Geometry/1 and Fit/1
contracts and exactly 24 inner plus one final fit. New typed metre axes use
ArrayManifest/2; old descriptors are not reinterpreted. `resolution_v2` is a
different prospective policy: widths 400/200/100/50 m, depths 200/500 m, four
positive dampings, three training folds, 96 complete inner fits and one final
fit. Its integer planner reserves each exact inner shape and the worst final
shape before any winner is known, including independent final-model verification.
The planner alone is not an executed v2 seal, native resource proof or host
admission. An optional comparator requires its separately reserved 98th fit.

**ES.** Representación/2 y política científica v2 son distintas. Un resultado
marcado `fixed_basis_v1` contiene los contratos Request/1, Geometry/1 y Fit/1 sin
cambios y exactamente 24 ajustes internos más uno final. Los nuevos ejes en
metros usan ArrayManifest/2; no reinterpretan descriptores antiguos.
`resolution_v2` es otra política prospectiva: anchos 400/200/100/50 m, profundidades
200/500 m, cuatro amortiguamientos positivos, tres particiones de entrenamiento,
96 ajustes internos completos y uno final. El planificador entero reserva cada
forma interna exacta y la peor forma final antes de conocer al ganador, incluida
la verificación independiente del modelo final. El planificador no constituye
un sello v2 ejecutado, prueba nativa de recursos ni admisión del host. Un
comparador opcional requiere reservar por separado el ajuste número 98.

## Cross-object semantics / Semántica entre objetos

**EN.** A valid JSON shape is insufficient. Verification binds actual metadata
and request bytes, dataset/original identities, all declared auxiliary rights,
the actual installed engine/license/source/native inventory, every finite member
and transitive chunk/page SHA, and the original source-row order. Every channel
QC target is resolved from its explicitly declared mask ID, with exact role,
unit, shape and row identity. Original channel hashing and each length-prefixed
`m03-correction-row-edge/1` edge are independently reconstructed, including
aligned coordinates, nullable values and QC flags. A changed lineage hash or
permission cannot pass by retaining the old parent receipt.

**ES.** La forma JSON válida no basta. La verificación vincula los bytes reales
de metadatos y solicitud, identidades del dataset y original, permisos de todos
los auxiliares declarados, inventario instalado real de motores, licencias,
fuentes y binarios nativos, cada miembro finito y SHA de bloques/páginas, y el
orden de filas original. Cada máscara QC se resuelve mediante su ID declarado,
con rol, unidad, forma e identidad de filas exactos. Se reconstruyen de manera
independiente el hash del canal original y cada arista `m03-correction-row-edge/1`
prefijada por longitud, incluidas coordenadas alineadas, valores nulos y flags
QC. Cambiar un hash de linaje o permiso no pasa conservando el recibo anterior.

**EN.** Every selected-sensor row must occur in exactly one disposition per fold;
nonselected sensors cannot enter the fit. Candidate order, completeness, scored
and excluded counts, numerical gate receipts and the frozen training-only tie
rule are checked. Observed minus predicted must equal each retained residual;
compensated sums reconstruct RMSE and signal RMS. Axes are increasing float64
metres with original index order, exact origin/spacing, prescribed height and
datum. Unsupported cells remain masked, never filled. Contained `verify`
additionally rebuilds selected training-only source centroids, normalized
operator scales and independent stationarity/objective, and recomputes the
observed-row predictions and every supported exported grid cell against all
sources at unchanged 1e-12 comparison tolerances. A cheap custody check explicitly
reports that native model recomputation was **not executed**.

**ES.** Cada fila del sensor seleccionado pertenece exactamente a una disposición
por partición; los otros sensores no entran al ajuste. Se comprueban orden,
completitud, conteos evaluados/excluidos, recibos numéricos y desempate congelado
solo de entrenamiento. Observado menos predicho debe coincidir con cada residuo;
sumas compensadas reconstruyen RMSE y RMS de señal. Los ejes son float64 crecientes
en metros, con orden original, origen/espaciado exactos, altura y datum prescritos.
Las celdas sin soporte permanecen enmascaradas, sin relleno. `verify` contenido
reconstruye además centroides solo de entrenamiento, escalas del operador y
estacionariedad/objetivo independientes, y recalcula predicciones y todas las
celdas exportadas con soporte frente a todas las fuentes, con tolerancias de
comparación 1e-12 sin cambios. La comprobación económica de custodia informa
explícitamente que la recomputación nativa **no se ejecutó**.

## Immutable export and real replay / Exportación inmutable y reproducción real

**EN.** Export refuses an existing destination. Private processing permission is
required across the acquisition and every auxiliary identity. Public export of
the complete result requires transitive raw/location **and** derivative rights:
derivative permission alone does not grant coordinates, original IDs, QC masks,
metadata, request or auxiliary series. Without that grant only a closed redaction
receipt is written, using constant withheld names and no data-bearing member.
Original bytes are included only if every raw grant allows it, the immutable
request asks for inclusion, and the caller supplies the genuine original CSV.
The stream verifies size, SHA and file identity before/after copying and fsync.
Export verification rechecks the result and the actual recorded rights; a forged
`replay=available` receipt cannot authorize a denied original.

**ES.** La exportación rechaza destinos existentes. Exige procesamiento privado
permitido para la adquisición y cada identidad auxiliar. Exportar públicamente
el resultado completo exige permisos transitivos sobre originales/ubicación
**y** derivados: el permiso de derivados no concede coordenadas, IDs originales,
máscaras, metadatos, solicitud ni series auxiliares. Sin ello solo se escribe un
recibo cerrado de redacción, con nombres constantes y ningún miembro con datos.
Los bytes originales se incluyen únicamente si todos los permisos lo permiten,
la solicitud inmutable pide incluirlos y se proporciona el CSV original genuino.
El flujo comprueba tamaño, SHA e identidad antes/después de copiar y fsync.
La verificación vuelve a comprobar resultado y permisos registrados: un recibo
falso `replay=available` no autoriza un original denegado.

**EN.** `replay=available` means required original bytes were retained, not that
replay passed. Actual `replay` starts a new cold contained execution. The recorded
environment is checked inside the Job **before opening geometry or values**;
changed code, engine, license or native binary refuses. Original bytes,
metadata/request/auxiliaries are then processed again. Every scientific array,
mask, geometry, channel, final fit and candidate score/diagnostic is compared;
only measured solver timing/resource counters may differ. Re-reading an opened
outer score creates neither a new untouched label nor a new selection opportunity.
Absent or denied originals remain unresolved; they are never regenerated from
an exported result, simulator truth or a filename.

**ES.** `replay=available` indica que se conservaron los originales necesarios,
no que la reproducción pasó. `replay` inicia otra ejecución fría contenida.
Comprueba el entorno registrado dentro del Job **antes de leer geometría o
valores**; cambios de código, motor, licencia o binario nativo rechazan. Luego
procesa nuevamente originales, metadatos, solicitud y auxiliares. Compara cada
arreglo científico, máscara, geometría, canal, ajuste final y puntuación/diagnóstico
de candidatos; únicamente pueden variar tiempos y contadores medidos del solver.
Releer una evaluación externa abierta no crea una reserva intacta ni otra
oportunidad de selección. Originales ausentes o denegados quedan sin resolver:
nunca se regeneran desde resultados, verdad simulada ni nombres de archivo.

## Explicit external roots / Raíces externas explícitas

Use the paired `scripts/magnetic-line-survey.ps1` or `.sh` wrappers with an
existing Python executable and `GEOPHYSICS_EXISTING_PACKAGE_ROOT`. No environment
is installed by these commands. `--data-root` / `GEOPHYSICS_LOCAL_DATA_ROOT` and
`--temp-root` / `GEOPHYSICS_LOCAL_TEMP_ROOT` must resolve outside repositories and
system temp. The current measured Windows controller requires its fresh
`--output-root` beneath that external temporary root, so indexes, native cache,
staging, result, fsync and drain are counted. Export may persist the completed
verified closure in an explicitly selected external data destination.

Use los scripts pareados con un ejecutable Python existente y el entorno
instalado declarado. Los comandos no instalan dependencias. Las raíces de datos
y temporales deben estar fuera de repositorios y temp del sistema. El controlador
Windows medido exige la salida nueva bajo la raíz temporal externa para contar
índices, caché nativa, staging, resultado, fsync y drenaje. La exportación permite
conservar el cierre verificado en un destino externo de datos explícito.

```text
run --csv <original> --metadata <metadata.json> --request <request.json>
    --auxiliary-root <closure> --data-root <external-data>
    --temp-root <external-temp> --output-root <fresh-owned-temp> --run-id <ID>
verify --result-root <result> --temp-root <external-temp> --output-root <fresh-temp>
export --result-root <result> --destination <fresh-external-data>
       --scope private|public --temp-root <external-temp> [--original-csv <original>]
replay --bundle-root <permitted-export> --data-root <external-data>
       --temp-root <external-temp> --output-root <fresh-owned-temp>
```

## Scientific boundary / Límite científico

**EN.** Numerical completion is not predictive, field or host acceptance. Original
S1 and the opened 100/50 m refinements retain their adverse fixed-threshold
verdicts. G and normalization units, distance convention and independent source
geometry agree with the inspected engine; a forensic constant does not justify
a production intercept. The separately approved prospective basis may use only
declared training partitions and its fresh pre-value seal. An unauthenticated
8201-row field source remains unverified. Authored rights-scoped replay controls
are not a substitute for provider originals or independent field truth. The
offline ceilings remain 192 logical members, 4 GiB raw/auxiliary and RSS/committed
memory limits, 32 GiB scratch, 21600 CPU seconds, 43200 wall seconds, one child,
one thread, and 10 CPU/10 wall stop reserves. Logical roots and physical chunk
files are separate counts; all physical bytes still count. A component lifetime
does not prove the complete maximum-cap native or Linux/VPS envelope.

**ES.** Terminar numéricamente no demuestra predicción, campo ni admisión del
host. S1 original y refinamientos abiertos 100/50 m conservan sus fallos con
umbrales fijos. Unidades de G y normalización, distancias y geometría independiente
coinciden con el motor inspeccionado; una constante forense no justifica un
intercepto productivo. La base prospectiva aprobada usa únicamente particiones
de entrenamiento declaradas y su nuevo sello previo a valores. Un original de
campo de 8201 filas no autenticado sigue sin verificar. Controles de reproducción
con permisos autorados no sustituyen originales del proveedor ni verdad de campo.
Se mantienen los límites de miembros, bytes, memoria, scratch, CPU, tiempo,
procesos, hilos y reservas de parada. Raíces lógicas y archivos físicos de bloques
son conteos distintos; todos los bytes físicos cuentan. Un recibo de componente
no demuestra el perfil nativo máximo completo ni la admisión Linux/VPS.
