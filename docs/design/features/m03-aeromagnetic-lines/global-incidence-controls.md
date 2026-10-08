# Global incidence calibration controls / Controles de calibración global

## English

`magnetic_line_survey_leveling.solve_incidence` scans all owner-admitted fold
constraints into a new external SQLite index before numerical import. This
component does not itself admit geometric pairs or provider calibration.
Constraint discovery, missing-value/partition eligibility and representatives
must be reconstructed by the fold crossover stage. Empty calibration refuses;
unknown inverse-variance errors refuse. No supplied SQLite/pickle or arbitrary
executable plan enters the worker.

The global sparse matrix contains +sqrt(w) for the flight offset and -sqrt(w)
for the tie offset. Data are sqrt(w) * (flight minus tie) nT; raw
w=1/variance_nT2, with no normalization. Connected-component union-find proves
incidence rank |component|-1 independently of LSMR. Remove exactly the
lexicographically first tie column per component. The gauges are relative,
not absolute datums. Disconnected components return
`common_relative_gauge=False`; a full corrected single-datum fit must retain
that ineligibility rather than combine independent zeros.

Numerical solve uses one global CSR, not dense N×M, M×M normal equations,
per-window models or equivalent-source Ridge. No lambda is borrowed from the
1/r objective. Explicit preallocation counts 64 bytes per constraint,
512 per line, 128MiB cache and 1GiB native reserve, including possible index
conversion copies. Large graphs require an actual queried Job; small controls
stop at 4096 edges/32 lines without one. All paths and SQLite spills are
explicitly external. Rank/gauge summaries are bounded by 65536 lines.

The original condition ceiling 1e12 remains. A spanning-tree bound on the
grounded weighted graph gives condition <=
sqrt(2 * maximum_degree) * sqrt(k * (k-1)) * maximum_root_weight /
minimum_root_weight. Report this as `condition_upper_bound`, not an observed
SVD condition or a scientific uncertainty. Refuse a nonfinite or over-ceiling
bound; conservatism may reject a graph that a future independently reviewed
sharper bound could admit. It never loosens the original ceiling.

Before new calibration values, freeze sparse LSMR damp=0, atol=btol=1e-12,
conlim=1e12, maxiter=2000, x0=None and one native thread. Stop codes0/1/2/4/5
are necessary but not sufficient. Reconstruct unweighted residuals and the
weighted graph gradient independently, directly from original edges and
returned offsets, using compensated sums. Require relative infinity-gradient
<=1e-9 against max(|Bᵀb|∞,|BᵀBx|∞), with exact-zero branch and no dimensional
absolute floor. Nonfinite arithmetic or nonzero products underflowing to zero
refuse. The original S1 predictive threshold is unrelated and unchanged.

The dense weighted original QR solver is an independent small oracle. Tests
require offset/residual differences <=1e-9 nT, exact tie zeros, independent
rank, disconnected relative-datum refusal, actual empty-fold/unknown-sigma
negatives, max-plus-one before imports, and role/weight grammar negatives.
Retain the missing-module red receipt `leveling-red.xml` before implementation.
These controls are not a full M03 DAG, field, native-large-graph admission,
SurveyResult or online activation.

## Español

`solve_incidence` recorre todas las restricciones admitidas por la partición
propietaria y crea un índice SQLite externo antes de importar motores. Este
componente no admite por sí mismo cruces geométricos ni calibración de campo.
La etapa de cruces debe reconstruir elegibilidad, valores faltantes,
particiones y representantes. Rechaza calibración vacía e incertidumbres
desconocidas; no abre bases SQLite o planes ejecutables suministrados.

La matriz dispersa global contiene +sqrt(w) para vuelo y -sqrt(w) para amarre;
el dato es sqrt(w) por diferencia vuelo menos amarre, con w=1/varianza sin
normalizar. La conectividad prueba independientemente rango k-1. Se elimina
exactamente la columna del primer amarre lexicográfico de cada componente.
Son referencias relativas, no datums absolutos. Componentes desconectados
devuelven `common_relative_gauge=False`; un ajuste con datum único debe
conservar esa inelegibilidad.

Se usa una única CSR global, no matrices densas, ecuaciones normales, modelos
por ventana ni lambda del ajuste de fuentes equivalentes. La preasignación
cuenta 64 bytes por restricción, 512 por línea, 128MiB de caché y 1GiB de
reserva nativa. Gráficos grandes exigen Job real; controles sin Job se acotan
a 4096 aristas y 32 líneas. Rutas y temporales SQLite son externos.

Se conserva el máximo de condición original 1e12. La cota de árbol indicado
arriba es `condition_upper_bound`, no una condición SVD observada ni una
incertidumbre científica. Si es no finita o supera el límite, se rechaza;
ser conservadora no permite relajar el límite.

Antes de valores nuevos se congelan LSMR sin amortiguación, tolerancias 1e-12,
conlim 1e12, máximo 2000 iteraciones, inicio cero y un hilo. Los códigos de
parada aceptables no bastan: se reconstruyen residuales y gradiente ponderado
directamente con aristas originales, mediante sumas compensadas. El gradiente
relativo infinito debe ser <=1e-9, con rama de cero exacto, sin piso absoluto
dimensional. Se rechaza aritmética no finita o subdesbordamiento. S1 mantiene
su umbral predictivo independiente.

Las pruebas comparan con el QR denso original y exigen diferencias <=1e-9 nT,
ceros exactos de referencia, rango independiente y rechazo de desconexión,
calibración vacía, sigma desconocida, desbordamiento y roles/pesos inválidos.
Se conserva el recibo rojo anterior. No constituyen DAG M03 completo, campo,
admisión nativa de gráfico grande, SurveyResult ni activación online.
