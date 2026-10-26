# One global objective per fit / Un objetivo global por ajuste

## English

`magnetic_line_survey_fit` is the streamed numerical adapter, distinct from
the protected bounded `magnetic_lines` processor. `select_candidate` retains
the frozen inner-only mean-RMSE rule: ties within 1e-9 nT prefer larger
damping and then larger depth. It receives no outer score. `predict_global`
streams all source contributions in fixed source order using the installed,
source-pinned Harmonica Jacobian, with bounded 4096-by-128 blocks and
compensated sums. It is not a per-chunk geological model. Small independent
kernel controls are distinguished from full contained execution.

`blocked_global_diagnostic` requires a real queried native Job before loading
engines. It independently verifies sealed and measured member closures, exact
original custody, request identity, original channel hash and missing masks.
Raw inverse-variance fitting requires admitted independent one-sigma errors;
unknown SDs are not normalized or invented. Geometry-only source blocks and
all four partitions stay frozen. Every depth/damping candidate runs inside
each of the three inner folds, then the selected candidate runs exactly once
on final training. Only then does the outer score get evaluated once.

The actual operator derives unweighted population column scales from each
fold's training coordinates, keeps every training row and source in one
global scaled Ridge objective, and records real LSMR recurrence estimates,
independently reconstructed objective and relative stationarity. Receipts
retain actual Job CPU, wall and lifetime RSS/commit peaks. The latter peaks
are cumulative worker peaks, not invented per-fit resets. Scratch accounting
is stage inventory at the query, not a whole-request peak/admission claim.
Failed solves retain a safe candidate failure record and are not selected;
the adapter never emits zero-filled fictional successful SolverReceipts.

CandidateFit/FitReceipt member tables and final source/scales/coefficients are
typed, immutable, chunked and source-bound. The complete diagnostic envelope
is explicitly `m03-global-blocked-diagnostic/1`, NOT SurveyResult. It admits
only the already-opened uncorrected authored control lane. Correction requests
refuse until fold-local independent correction/leveling is integrated.
Missing reference admission remains `not_established`, field acceptance
`unresolved`, regardless of finite predictions or computational convergence.

`magnetic_line_survey_diagnostic.run_opened_s1` binds the original 45,539-byte
S1 acquisition SHA256
`ac28e5f7c8344b94ebe0c408484eede8ade5a4074c8ef44661bcfe774ff0bfae`.
It performs complete original geometry sealing, strict decoding and all
24-inner-plus-one-final global solves inside the same contained worker.
The original S1 predictive gate remains RMSE <= max(0.05 * signal RMS,
1e-6) nT, independently of numerical stationarity. Existing evidence is
18.799740861734186 versus 0.25966396538773057 nT: FAIL. The new test requires
that honest failure, not a weakened bound. A numerical diagnostic is neither
an 8201-row real-field execution nor the full owner CLI/result/export/replay.

Before implementation, retain `fit-red.xml` missing-symbol failures and
`full-s1-red.xml` actual contained worker refusal of the not-yet-supported
plan. Green evidence must be recorded at exact executed source pins; this
document's executable descriptions alone are not evidence of test completion.
The original 158-test regression and real S2–S6 negatives remain unchanged.

## Español

`magnetic_line_survey_fit` es el adaptador numérico streamed, distinto del
procesador acotado protegido `magnetic_lines`. La selección usa solamente el
RMSE interno medio; empates dentro de 1e-9 nT prefieren mayor amortiguación y
luego mayor profundidad. No recibe el error externo. La predicción acumula
contribuciones de todas las fuentes en orden fijo con el Jacobiano Harmonica
instalado y verificado, bloques 4096×128 y sumas compensadas. Los bloques no
son modelos geológicos independientes.

El diagnóstico exige un Job nativo real antes de cargar motores. Verifica
cierres de miembros, originales, solicitud, huella del canal y máscaras.
Ponderación inversa requiere desviaciones independientes de una sigma
admitidas; no inventa ni normaliza incertidumbres. Fuentes y cuatro particiones
se congelan por geometría. Ejecuta cada candidato en tres particiones internas,
ajusta el seleccionado una sola vez sobre entrenamiento final y evalúa el
conjunto externo una sola vez después de seleccionar.

El operador calcula escalas poblacionales no ponderadas exclusivamente con
entrenamiento y mantiene todas sus filas y fuentes en un único objetivo Ridge
global. Registra estimadores LSMR reales, objetivo reconstruido y estacionaridad
relativa independiente. Los picos RSS/commit pertenecen a toda la vida del
worker, no son reinicios ficticios por ajuste. Los bytes scratch corresponden
al inventario consultado, no prueban un pico ni admisión de solicitud completa.
Un ajuste fallido conserva su error y no participa en selección; no se inventa
un SolverReceipt exitoso lleno de ceros.

Las tablas CandidateFit/FitReceipt y fuentes/escalas/coeficientes son tipados,
inmutables y fragmentados. El sobre es explícitamente diagnóstico, no
SurveyResult. Solamente procesa controles sintéticos ya abiertos sin
correcciones; solicitudes corregidas requieren integración independiente por
partición. La referencia física queda no establecida y campo unresolved,
independientemente de convergencia o predicciones finitas.

`run_opened_s1` vincula los 45.539 bytes y la huella original S1 indicada
arriba; sella geometría, decodifica y ejecuta 24 ajustes internos y uno final
en el mismo Job. Conserva RMSE <= max(0,05 * RMS de señal, 1e-6) nT.
La evidencia original es 18,799740861734186 frente a 0,25966396538773057 nT:
FAIL. La prueba nueva exige conservar ese fallo honesto. No constituye una
ejecución de campo real de 8201 filas ni el flujo completo propietario de CLI,
resultado, exportación y replay.

Se conservan los recibos rojos anteriores a implementación. La evidencia
verde debe identificar las fuentes ejecutadas exactas; describir una función
no demuestra su ejecución. La regresión original y los negativos S2–S6 se
mantienen íntegros.
