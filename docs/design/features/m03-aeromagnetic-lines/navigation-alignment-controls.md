# Value-free navigation edge / Alineamiento de navegación sin valores

## English

`magnetic_line_survey_navigation.align_geometry` independently verifies the
original geometry and all four typed navigation arrays, then aligns every
original measurement-row position without opening magnetic values or numerical
engines. It returns a distinct immutable alignment receipt, not a renamed raw
inspection or completed GeometrySeal. Original raw arrays remain unchanged.

The existing reviewed authored S3 lane is admitted only with actual original
synthetic provenance, matching metric coordinate/datum declaration, total
intensity before lag/main-field subtraction, explicit not-applied states and
the original independently authored shared UTC clock evidence. It verifies
the canonical original navigation-record digest, actual authored source digest,
rights and receipt body; a claimed reviewed field auxiliary is NOT promoted to
authentic provider calibration. Private processing and raw mirroring remain
separate permissions. No provider original, clock or physical datum is invented.

Navigation row IDs are explicit input identities, unique and disjoint from
measurement IDs. Actual ordered row-ID hashes bind all four arrays. Their roles,
shapes, masks and member closure are checked; line indexes resolve through the
original verified dictionary. Within each line, UTC is strictly increasing.
A fresh external SQLite index holds all knots and original rows, with bounded
cache/spill paths, rather than collecting a survey in Python lists.

For lag tau, position time is measurement UTC plus tau. Absolute UTC remains
an arbitrary-precision integer nanosecond timestamp. SQLite stores only signed
int64 relative nanoseconds from the first knot; out-of-range differences refuse.
Target relative time is the exact binary64 Fraction(tau) times 10^9 plus the
integer measurement offset. Query the same line's immediate preceding/following
knots using integer floor/ceil. An exact knot returns its original coordinates;
otherwise require both knots and a gap no larger than the declared bound, with
no extrapolation. Fractional interpolation weight is converted to float only
after subtraction/division; coordinates use the original compensated formula
(1-w)p_left+w*p_right. Never round an absolute UTC to binary64.

Unbracketed rows retain their original geometry payload and explicit QC
unsupported-time bit5; they are not invented coordinates or usable corrected
measurements. The subsequent owner DAG must exclude that unsupported edge and
recompute clearance from admitted aligned height and actual original terrain.
The alignment receipt independently hashes row-ID/aligned-coordinate/datum
identity, binds original byte/geometry and operation identities, and retains
unsupported count, value_access=not_opened, field_acceptance=unresolved.

Tests compare all original S3 aligned coordinates and the coordinate hash exactly
with the unchanged protected bracket/correction oracle, including a sub-nanosecond
fractional lag. A separately declared out-of-range lag marks every original row
unsupported without dropping or renumbering it. Invalid clock, valid-grammar
already-subtracted input and changed authored-record identity refuse before any
output directory. The initial prospective oracle-call/quantity-grammar test
errors are retained, then repaired; neither is a scientific tolerance change.
The owner `seal_geometry(..., navigation_root=...)` now builds this alignment
inside its own external scratch lifetime. Every partition/source, geometric
crossover and support stage verifies the same stored alignment closure before
using those coordinates in its freshly rebuilt original-row index. Fully
unsupported or partially unsupported alignment refuses the current seal path;
it never deletes unsupported original
rows to claim eligibility. Original acquisition geometry identity remains
separate from the aligned coordinate/datum identity and lag-request hash.
Auxiliary and aligned typed arrays are copied into the closed final seal member
set, auxiliary byte/row capacity is counted, and all stages bind the same
navigation receipt digest. The native source closure includes navigation and
the protected original bracket/intersection/partition modules.

The original S3 owner-seal test compares all four source maps and training
partitions to the independently corrected original oracle, verifies final member
closure and rechecks the original CSV hash. This still does not qualify field
navigation, correct measurement values, create SurveyResult or activate online
computation. The no-lag original path and its preserved original S1 FAIL have
separate regressions; no earlier receipt is re-labelled as this source revision.

## Español

`align_geometry` verifica geometría original y cuatro arreglos tipados de
navegación antes de alinear cada posición original, sin abrir magnetismo ni
motores numéricos. Produce un recibo de alineamiento distinto; no renombra la
inspección original ni declara GeometrySeal completo. Los originales no cambian.

Sólo admite el carril S3 sintético revisado con coordenadas/datum coincidentes,
intensidad total antes de lag/campo principal, estados explícitos no aplicados y
evidencia original de reloj UTC compartido. Verifica huellas de registros,
fuente authored, derechos y cuerpo del recibo. No autentica automáticamente
auxiliares de campo ni inventa reloj/datum. Procesamiento privado y copia pública
de originales son permisos separados.

IDs auxiliares son explícitos, únicos, ajenos al espacio de IDs de medición y
vinculados a los cuatro arreglos por hash ordenado. Se verifican roles, formas,
máscaras, cierre de miembros e índices de líneas originales; UTC aumenta
estrictamente por línea. SQLite externo nuevo conserva todos los nodos/filas,
con caché y temporales acotados, sin listas Python de encuesta completa.

Tiempo de posición es UTC de medición más tau. UTC absoluto conserva enteros
de precisión arbitraria; SQLite sólo recibe nanosegundos relativos int64 y
rechaza rango excesivo. El objetivo usa Fraction exacta de tau binary64 por
10^9. Se buscan nodos inmediatamente anterior/posterior de la misma línea
mediante piso/techo enteros. Un nodo exacto conserva coordenadas; interpolar
exige ambos nodos y separación dentro del límite declarado, sin extrapolación.
Sólo después de restar/dividir se convierte el peso a float, usando la fórmula
compensada original. Nunca se redondea UTC absoluto a binary64.

Filas sin soporte conservan payload geométrico original y bit5 de tiempo no
soportado; no son coordenadas corregidas ni mediciones utilizables. El DAG
posterior debe excluir esa arista y recalcular clearance con altura alineada y
terreno original reales. El recibo vincula hashes geométricos/operación y datum,
cantidad no soportada, sin acceso a valores y campo sin resolver.

Las pruebas comparan exactamente todas las coordenadas S3 originales y hash
con el oráculo protegido, incluso lag fraccional sub-nanosegundo; conservan
todas las filas ante un lag sin soporte y rechazan reloj, estado ya restado con
gramática válida y huella alterada antes de crear salida. Se conservan los
errores iniciales de pruebas prospectivas; corregirlos no cambia tolerancias.
El sellado propietario ahora construye alineamiento dentro de su temporal
externo. Cada etapa de particiones/fuentes, cruces y soporte verifica el mismo
cierre antes de usar las coordenadas en su índice original nuevo. Alineamiento
parcialmente o totalmente sin soporte rechaza el carril de sellado actual; no
elimina originales para aparentar elegibilidad. Se separan identidad de
adquisición original, coordenadas/datum alineados y hash de solicitud lag.
Arreglos auxiliares/alineados se copian al cierre del sello, con capacidad de
filas/bytes auxiliar contada; las etapas vinculan el mismo hash de navegación.
El cierre de fuentes nativas incluye navegación y módulos originales protegidos.

La prueba de sellado S3 compara las cuatro particiones/mapas de fuentes con el
oráculo original corregido, verifica todos los miembros y revalida hash CSV.
Todavía no admite navegación de campo, corrige magnetismo ni crea SurveyResult
o activación online. La regresión sin lag conserva S1 FAIL y su evidencia propia;
no se promueve retrospectivamente un recibo previo a la revisión actual.
