# Global streamed computation / Cálculo global por bloques

## English

One global equivalent-source model uses every admitted training row and source.
Blocks bound memory for kernel actions; they are not separate fitted geological
tiles. With sample locations x and source locations p, G=1/|x-p| has units m^-1.
Each source column has its training-only, unweighted population standard
deviation s. The fit uses A=sqrt(W)G/s, b=sqrt(W)y and minimizes
||Ac-b||²+lambda||c||². There is no mean subtraction, intercept, normalized row
weight or data thinning. Physical coefficients q=c/s have units nT*m and do
not measure geological susceptibility, magnetization or body depth.

Harmonica's pinned float64 Jacobian is called on at most 4096 rows and 128
sources at a time. Forward and adjoint actions sum all source/row blocks in
fixed order. SciPy LSMR uses sqrt(lambda), atol=btol=1e-12, conlim=1e8,
maxiter=2000, a zero start and one native thread. An independent direct 1/r
calculation reconstructs the regularized gradient and objective after the
solve. Relative stationarity must be <=1e-9 without an arbitrary absolute
physical-unit floor. A finite prediction or acceptable stop code alone is not
convergence. The reported gradient/lambda coefficient bound is numerical,
not measurement uncertainty or a geological confidence interval.

`global_operator(..., job_handle=None)` preserves the small uncontained
2..128-row/1..32-source algebra-control boundary. Larger work requires actual
current-process membership in a Windows Job with the offline limits; a boolean
or caller-written resource receipt cannot open it. The original bounded
magnetic processor, local320 contract and their resource/scientific thresholds
are unchanged. `solve_global` keeps its 14-key internal algebra return; real
LSMR recurrence estimates are retained separately on the operator for the
owner's SolverReceipt adapter. That internal return is not SurveyResult.

The offline controller starts the fixed worker suspended and assigns it before
interpreter imports. It admits one child, forbids descendant/breakaway escape,
sets native thread variables before imports and uses an explicitly selected
existing CPython binary and existing package directory. Windows App Execution
Aliases are not executable provenance: the worker queries its actually loaded
module filename and hashes that binary. No environment installation or package
fallback occurs. Source identities are captured before launch and checked
again after drain; changing executing code cannot produce a current-origin
receipt for an older execution.

Actual Job CPU, terminal exit state, process lifetime peak RSS and Job committed
peak are queried, not supplied by a caller. Failed queries refuse. Cold limits
are 21600 CPU seconds, 43200 wall seconds, 4GiB RSS and committed memory each,
32GiB owned scratch, one child and one native thread. Stop triggers retain
60 CPU/wall seconds of drain reserve; cancellation must stop within 10 CPU
and 10 wall seconds. Parent CPU through drain is bounded at 300 seconds;
final parent receipt writing has separately reported timings. A component
resource pass does not establish useful-request, thirty-run tail/headroom,
VPS, persistence, GUI, predictive or field admission.

The fixed zero probe consumes independently verified typed coordinate/source
arrays of the proposed full shape. The cancellation probe first completes the
zero solve, then repeats real global forward and adjoint native work until the
parent terminates the Job. Zero signal is intentionally a resource control,
never nonzero-signal predictive evidence. Both tests use the complete 8201-row,
66-source shape; they do not fit 4096-row pieces as independent models.

The disk planner preserves original-order row indexes, complete flight-line
validation sets, anchors and buffered tie endpoints. It builds source blocks
by the frozen half-open floor convention and computes XY representatives with
fsum in sorted row-ID order. It refuses a source-cap overflow rather than
coarsening the source mesh. Its internal partition/source receipt explicitly
does not claim the navigation/crossover/support-complete GeometrySeal.

The independent measurement pass rechecks actual original bytes and geometry,
then parses every original row. Missing magnetic values or sigma use masked
positive-zero binary placeholders, not measurements or invented error bars.
Nonfinite, underflowed or nonpositive supplied sigma refuses. The original
8201-row NaN/Infinity ingestion negative therefore remains a refusal at the
measurement boundary. A typed raw channel is still not physical eligibility,
correction review, sealed predictive acceptance or a full scientific Result.

## Español

Un solo modelo global usa todas las filas y fuentes admitidas para entrenamiento.
Los bloques limitan memoria, pero no son modelos ajustados por separado.
G=1/|x-p| tiene unidades m^-1; s es la desviación estándar poblacional de cada
columna, sin ponderar y calculada solamente con entrenamiento. Se minimiza
||Ac-b||²+lambda||c||² con A=sqrt(W)G/s y b=sqrt(W)y, sin restar la media,
añadir intercepto, normalizar pesos ni reducir filas. q=c/s tiene unidades
nT*m; no representa susceptibilidad, magnetización ni profundidad geológica.

El Jacobiano float64 de Harmonica se calcula en bloques acotados. Las acciones
directa y adjunta acumulan todas las contribuciones globales. LSMR conserva
sqrt(lambda), atol=btol=1e-12, conlim=1e8, máximo 2000 iteraciones, inicio
cero y un hilo nativo. Una evaluación independiente de 1/r reconstruye
objetivo y gradiente regularizado; la estacionariedad relativa debe ser
<=1e-9. Predicciones finitas y códigos de terminación no bastan. La cota
numérica de coeficientes no es incertidumbre instrumental ni geológica.

La ejecución grande exige pertenencia real del proceso a un Job de Windows.
No la autoriza un booleano, un informe escrito por el usuario ni una fórmula
de memoria. El controlador crea el hijo suspendido, lo asigna antes de
importar bibliotecas, impide procesos descendientes y fija un hilo nativo.
Usa binario y paquetes preexistentes explícitos, sin instalar ni seleccionar
otro entorno automáticamente. La identidad del binario cargado se consulta
al sistema; un alias de ejecución no sustituye esa evidencia. Las identidades
del código se comprueban antes y después de la ejecución.

Se consultan CPU real, estado final y máximos de memoria conservados por el
sistema. Una consulta fallida rechaza la ejecución. Se mantienen los límites
de 21600 segundos de CPU, 43200 de reloj, 4GiB de RSS y memoria comprometida,
32GiB de temporales propios y un hijo. Cancelar debe detenerlo en <=10 segundos
de CPU y reloj. La escritura final del informe del controlador se mide aparte.
Superar un control de recursos no habilita el VPS ni demuestra persistencia,
aceptación predictiva, interfaz terminada o validación de campo.

El control cero y la cancelación usan las 8201 filas y 66 fuentes completas.
La cancelación interrumpe acciones nativas globales después de un ajuste
terminado; no simula trabajo con una espera. La señal cero es evidencia de
recursos, nunca evidencia predictiva de señal real.

El planificador en disco conserva índices originales, líneas completas de
validación, anclas y extremos de líneas de amarre excluidos por buffers.
Las fuentes mantienen bloques semiabiertos y medias XY calculadas con fsum
en orden de identificadores. Exceder el límite de fuentes se rechaza; no se
aumenta el tamaño de bloque para ocultarlo. El informe parcial distingue las
etapas de navegación, cruces y soporte necesarias para el sello completo.

El segundo recorrido vuelve a verificar bytes y geometría y decodifica todas
las mediciones originales. Ausencias son máscaras explícitas, no ceros
observados ni errores inventados. Se rechazan valores no finitos, subdesbordados
y sigmas suministradas no positivas. Por eso se conserva el rechazo del
control histórico de 8201 filas con NaN/Infinity. Decodificar un canal no
establece elegibilidad física, correcciones válidas ni aceptación de campo.
