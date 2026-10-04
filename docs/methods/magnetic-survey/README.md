# Magnetic survey input and geometry seal / Entrada y sello geométrico magnético

[Recorded independent acquisition controls / Controles independientes](02_acquisition-controls.md)
describe the executable authored Choclo/Decimal/PCG64 inputs, not fitted inverse
success or field acceptance.

[Physical objective / Objetivo físico](03_physical-objective.md) explains
executable tiny kernel/covariance/active-face/sparse-weight controls and the
pinned vendor covariance-Hessian limitation, not a completed inverse fit.

The ordinary local **geometry foundation is executable**. L2, sparse IRLS,
quantity-specific fitting, held-out prediction, fitted-result bundles and linked
views remain the complete [continuation contract](../../design/features/m04-survey-inversion/research.md),
not results produced by this validator. The unchanged [physical forward unit](../magnetic-forward.md)
explains SimPEG/Geoana, Choclo, units and independent numerical controls.
There is no provider download, IGRF evaluator, correction, magnetic kernel or
optimizer invocation in the input/planner/export modules.

## English: assumptions and byte admission

Supply a local UTF8 `magnetic-survey-inversion-1` document with **all twelve**
root keys: schema, source, frame, inducing_field, acquisition, processing,
geometry, observations, noise, prior, policy, intent. Nested keys and tagged
processing parameters are closed, not hints. The [full tables](../../design/features/m04-survey-inversion/contracts.md)
define every enum, nullable field, unit, shape and cross-policy. Do not infer an
uncertainty, acquisition timestamp, height datum or redistribution licence.
Source SHA and byte count are declarations until the retained original is
independently verified; this geometry command does not open a provider original.

`parse_request(bytes)` accepts exact built-in bytes, not dicts, ndarray hooks,
memoryviews or arbitrary JSON-compatible objects. Byte cap is8,388,608 including
whitespace; depth12, token cap500,000, numeric lexeme64 bytes, decoded string2048
bytes, total decoded strings262,144. A token is each punctuation, key/string,
number or literal. Escaped duplicate keys and malformed UTF8/surrogates reject.
Overflow and nonzero decimals rounded to binary64 zero reject. Integral fields
require integer tokens, not boolean or `1.0`. Finite float payloads preserve
negative zero; geometry forbids it. No numerical library imports while parsing.

Each array is exactly `{dtype,shape,data,sha256}` with original C-order flat
tokens, little-endian binary64/int64/bool(0/1) payload SHA256. Shapes/counts,
every token type and every descriptor hash are validated before geometry/prior
materialization. Complete likelihood tokens are streamed and hashed, **not**
decoded to an observation/noise list. `handle.metadata()` omits those two data
lists while retaining their shapes/units/hashes; it returns a fresh independent
stdlib snapshot. Caller mutation of that copy cannot change the handle. This is
not a tamperproof Python security boundary or a numerical-array immutability claim.
Persisted hashes and original retained bytes establish durable identity.

## English: physical metadata and eligibility

Coordinates are resolved ENU metres, up positive, with explicit frame transform
and vertical datum. The frame origin records lineage; it is not translated a
second time. Mesh indexing is `i+nx*(j+ny*k)` and active columns increase full-cell
index. Mesh edges/centres must remain faithful to local widths at1e-10 relative
tolerance. Every usable receiver must lie **outside the closed full mesh box**,
including inactive cells. Excluded rows retain their coordinates and original
identity; no zero-coordinate substitution or hidden thinning.

The declared uniform inducing field uses positive-down inclination and
clockwise-from-north declination:

\[
 f=(\cos I\sin D,\cos I\cos D,-\sin I),\quad B_0=Ff.
\]

Secondary ENU vector, linear projection `f·b`, secondary amplitude `|b|`, exact
total anomaly `|B0+b|-F` and reduced-to-pole data are not interchangeable. The
schema admits the first, second and exact total anomaly with matching named
background relations. It **does not verify** that a supplied field is IGRF or
that a field survey is induced, isotropic, free of remanence or demagnetization.
Future physical predictions use the actual accepted SimPEG/Geoana operator.

Processing is a directed acyclic graph with one original root, earlier unique
parents, every node ancestral to the final node, and explicit canonical typed
parameter hashes. Original input binds source SHA; one-parent input binds its
output, multiple-parent input binds ordered output hashes joined by LF, no
trailing LF. The final output binds the observation descriptor SHA. Those
identities are not proof of physical correction. Non-original operations remain
`unresolved_lineage` until the actual approved upstream validator is bound.
There is no execution of client callbacks or named correction recipes.

Rights remain separate from science: private_user_supplied and provider_link_only
do not authorize raw mirroring; redistribution_permitted is not a field-validity
certificate; unresolved is inventory-only. Foundation `local_processing` means
declared metadata eligibility, **not** authorization for an unbound optimizer or
validated likelihood. SD positivity and full SPD covariance/condition gates are
separate future post-seal scientific checks. No noise floor, covariance nugget,
symmetrization, model fit or field acceptance is inferred here.

## English: exact geometry partition and independent S2 control

For usable rows, horizontal block index is `floor(E/wE),floor(N/wN)` anchored
at physical zero, including negative ENU. Union rows sharing a source group OR
block; transitive connected units are indivisible. A unit ID is SHA256 of sorted
original row IDs joined by LF. Sort units by SHA256 of
`magnetic-geometry-seal-1|104729|` followed by unit ID, then ID on ties. At least12
units are required. The first `ceil(U/5)` units form the outer set; remaining
units are assigned to validation folds by ordered position modulo3.

For each fold, fitting candidates are development minus validation, with every
row at horizontal distance **less than or equal to** buffer from validation or
outer excluded. Compare squared distances in square metres; equality is not a
tolerance waiver. Final development refit similarly buffers outer rows. No new
seed, smaller buffer or amplitude-derived mask repairs a failure.

Fold fit>=40 and validation>=10; outer>=10; final refit>=50. Fit/validation/outer have
at least two distinct E and N coordinates and rank3 of centered `[1,E,N]`,
retaining the constant column. Actual NumPy2.2.6 SVD uses relative cutoff1e-12,
only after full closed schema and capacity admission. Kernel/optimizer imports
remain absent. Insufficient coverage fails before likelihood materialization.

The fixture contains authored geometry, **never field acquisition**:12 flights,
24 samples per flight, `E=-200+80*s`, `N=600*l`, `U=120+10*(s mod3)` metres,
groups `S2-Lll`, IDs `S2-Lll-Sss`, blocks250/500m, buffer200m, seed104729.
There are288 original rows,12 units, outer flights01/04/11 (72 rows), development216,
each fold144 fit/72 validation/0 buffered, final refit216. Heterogeneous authored
heights are not metadata for any provider. The geometry fixture has no magnetic
truth generator. Tests' zero/SD payloads are labelled protocol controls, not
inversion or independent physics evidence.

Coordinate payload SHA256 is
`b784c2e62476cc8926a948fa3c20787df9dcf017a54497d1a696fddb2026538a`.
The independent frozen membership-table SHA256 is
`2336754f197bcf8470fdcf267df80af962f2483860bad37b5dacefb9691f2d45`.
It is a separate oracle encoding, not the runtime partition descriptor hash.
Reordering input changes original-order seal/indices but retains unit IDs and
row-ID memberships. Signal/uncertainty mutations change likelihood identities,
not geometry seal or partitions.

## English: local tools, exports and resource truth

From the checkout root, using the already approved isolated Python environment:

```text
python -B data-pipeline/magnetic_survey.py validate --request survey.json --export new-geometry.json
```

Both flags are mandatory; output must not exist. Exit0 is complete geometry
validation/export,2 invalid input/partition,5 local file/durability failure.
`calibrate`, invented flags and provider URLs as file inputs are not commands.
Stdout contains identities/eligibility/false claims, not observations or traces.
Inputs are read-only; no original bytes are published. Actual local tests read
two distinct configurations and verify changed configuration hash, unchanged
geometry seal, old export protection and no inverse-success claims.

Python composition uses the ordinary pipeline modules (no internal package):

```python
from magnetic_survey_json import parse_request
from magnetic_survey import plan_geometry
from magnetic_survey_bundle import write_geometry, read_geometry

# caller_raw is bounded local UTF8 bytes, not a provider URL.
handle = parse_request(caller_raw)
plan = plan_geometry(handle)
write_geometry("new-geometry.json", handle)  # exclusive new-file creation
assert read_geometry("new-geometry.json") == plan
```

Set `PYTHONPATH=data-pipeline` when composing outside the module directory.
The geometry export embeds the exact lexical request and plan, no provider
original/model/predictions. It is private local data, not a publication API.
Generation and request hashes bind exact bytes; import reruns all validation
and recomputes the plan, rejecting even rehashed forged claims/partitions.
16MiB export cap applies; traversal/path members and NPY/pickle are absent.
Flush/fsync/readback occur before successful return. Failure removes only the
newly created file, never a prior export. A transient partial file may be visible
while writing: this API provides no atomic pointer publication or process-crash
recovery proof. The future fitted-generation bundle and host durability have
their own required tests; do not relabel geometry roundtrip as their acceptance.

N<=2048, full cells<=4096, active A<=2048, full covariance D=N*C<=512,
3*N*A<=12,582,912. Additional combined descriptors96MiB/scalars500,000,
metadata256KiB and conservative bytes

\[
 B=8[18DA+6D^2+8A^2+64(D+A)+8N_{full}]\le805306368.
\]

For S2 vector geometry, B=120,112,128bytes. This is algebra, not measured RSS,
feasibility of upper counts or host admission. The online proposed sub-profile
does not activate computation. Current product SDD section8 instead requires
actual byte capacity for release/current/two rollback releases, retained project
bytes, configured scratch and worker memory without host exhaustion. There is
no30% whole-host criterion, off-host restore or provider SMTP prerequisite for
the owner-tested stage. Failed historical receipts remain failed historical
observations, not transformed passes.

## Español: supuestos, protocolo y geometría

La base local de lectura, elegibilidad y sello geométrico es ejecutable. No
calibra susceptibilidad, no ejecuta L2/IRLS y no valida geología ni datos de campo.
Se mantiene el alcance completo de inversión, evaluación independiente,
herramientas de usuario, exportación del ajuste y vistas enlazadas.

Entregue los doce campos raíz y todas las claves anidadas del contrato. No se
adivinan errores, alturas, datum, fechas, licencia o campo IGRF. La entrada es
UTF8 de hasta8MiB; profundidad12,500000 tokens, números de hasta64bytes,
cadenas decodificadas2048bytes y total262144bytes. Se rechazan duplicados
escapados, UTF8 inválido, desbordamiento, subdesbordamiento a cero, booleanos
numéricos y campos enteros como `1.0`. Los descriptores declaran tipo/forma/datos/
SHA256 de bytes little-endian en orden original. Se comprueban tipos, cantidades
y hashes sin cargar listas de observaciones/incertidumbres ni importar el motor.
La copia de metadatos no es memoria Python inviolable; la identidad durable
depende de hashes y originales retenidos.

La geometría es ENU en metros, U positivo, con datum y transformaciones explícitos.
El origen del marco no desplaza otra vez la malla. Orden de celdas:
`i+nx*(j+ny*k)`. Todo receptor utilizable debe estar fuera del volumen cerrado
completo de la malla, incluso celdas inactivas. Todas las filas excluidas siguen
en el inventario, con razón QC e identificador original; no hay eliminación
silenciosa, alturas inventadas ni coordenadas cero de relleno.

Campo inducente uniforme declarado: inclinación positiva hacia abajo,
declinación desde el norte en sentido horario, `f=(cosI sinD,cosI cosD,-sinI)`.
Vector secundario, proyección lineal y anomalía exacta del módulo total son
magnitudes distintas. Amplitud secundaria y reducción al polo no son entradas
de susceptibilidad por renombrarlas. La hipótesis inducida no demuestra ausencia
de remanencia, anisotropía o desmagnetización. Un DAG válido vincula identidades,
no demuestra una corrección física. Operaciones externas quedan
`unresolved_lineage` hasta vincular el validador aprobado real.

Derechos privados o enlace al proveedor no autorizan redistribución de bytes.
Derechos no resueltos permiten inventario, no modelado. La elegibilidad local de
metadatos no acepta un optimizador, una incertidumbre SPD ni ejecución en línea.
La base no calcula positividad SD, Cholesky o condicionamiento del ruido; esas
comprobaciones científicas ocurren después del sello y antes del ajuste futuro.

Bloques horizontales `floor(E/wE),floor(N/wN)` anclados en cero. Se unen filas
con mismo grupo O bloque; componentes transitivas son indivisibles. SHA256 de
IDs ordenados con LF identifica cada unidad; un segundo hash con nombre/semilla
104729 fija su orden. Se requieren12unidades. Primer `ceil(U/5)` para evaluación
externa; restantes se asignan por posición módulo3 a validación interna.
Se excluye ajuste a distancia horizontal<=buffer de validación o evaluación.
La igualdad se excluye; no se reduce buffer ni se cambia semilla para aprobar.
Mínimos: ajuste40,validación10,evaluación10,reajuste50; ajuste/validación/evaluación
requieren dos E/N distintos y rango3 de `[1,E,N]` con coordenadas centradas,
SVD NumPy2.2.6/corte1e-12.

S2 es adquisición **sintética de geometría**, no campo:12 vuelos/24muestras,
E=-200+80s,N=600l,U=120+10(s módulo3); bloques250/500m,buffer200m.
288filas,12unidades,evaluación vuelos01/04/11=72filas,desarrollo216;
tres folds144ajuste/72validación/0buffer;reajuste216. Cambiar valores y ruido
no cambia sello/partición. Reordenar conserva membresía por ID, no oculta que
el orden original y sus índices cambiaron. El fixture no genera verdad magnética.

## Español: uso local, exportación y límites

Ejecute el comando `validate --request survey.json --export new-geometry.json`
mostrado arriba con el entorno aislado aprobado. Ambas opciones son obligatorias;
archivo de salida nuevo. Código0 significa sólo validación/exportación geométrica,
2entrada/partición inválida,5fallo de archivo/durabilidad. No existe comando de
calibración en esta base. Dos configuraciones reales de prueba conservan sello
geométrico y cambian hash de configuración; no son resultados inversos.

Exportación JSON privada<=16MiB conserva bytes exactos del documento y plan,
no el original del proveedor, modelo ni predicciones. Importar valida otra vez
y recalcula todo; incluso hashes recalculados no habilitan afirmaciones falsas.
Creación exclusiva, flush/fsync y lectura posterior protegen archivos anteriores.
Un archivo parcial puede existir durante escritura: no se afirma publicación
atómica, recuperación ante caída ni durabilidad del host. El futuro bundle
NPY del ajuste conserva sus propios requisitos y pruebas pendientes.

Los límites geométricos, tipos, bytes conservadores y recursos son adicionales,
no sustituibles. S2 vectorial da120112128bytes algebraicos, no RSS observado.
En la etapa probada por el propietario, SDD§8 pide capacidad real en bytes
para release/actual/dos rollback, proyectos retenidos, scratch y memoria del
worker sin agotar host. No exige30% global, respaldo/restauración fuera del host
ni SMTP de proveedor. Los recibos fallidos históricos se conservan sin convertir
veredictos. Persisten pendientes físicos, campo/completo Charleston/Bartlett,
optimizador público M02, L2/IRLS, incertidumbre, UI, contención y despliegue.

## Source-linked continuation, not a numerical claim

Physical and inverse definitions remain tied to actual primary
[SimPEG magnetic source](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/potential_fields/magnetics/simulation.py),
[WeightedLeastSquares](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/regularization/base.py),
[Sparse](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/regularization/sparse.py)
and independently retrieved source hashes in the feature research. Those
operators are not executed by the geometry foundation. Planned fitting retains
full covariance whitening, physical chi=.01q scaling, unhalved objective,
frozen beta/positive-epsilon policies, independent Choclo/Decimal/BVLS oracles
and no convergence waiver. The public accepted M02 callback binding, including
nonlinear exact magnitude, must be named before composition. None of the four
plan claims (full method, verified field, geological truth, online admission)
can be changed by client data or reimport.
