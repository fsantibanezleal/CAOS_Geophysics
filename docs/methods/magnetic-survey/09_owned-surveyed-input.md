# Owned surveyed input, local calculation and replay custody

## What the supplied-input tool actually consumes

The acquisition original and the physical inversion request are distinct byte
objects. The former is retained read-only by its owner; the latter declares the
measurement quantity, ENU frame and height datum, uniform inducing field,
correction lineage, original row IDs, uncertainties, mesh, susceptibility bounds
and frozen tuning policy. A magnetic CSV label is insufficient to infer any of
these declarations. Absolute total intensity is not automatically an anomaly.
Projected-secondary TMI is not the exact norm-minus-background observable.

The owned adapter checks the original byte count and SHA256 against both the
RawAsset and its actual SourceRecord, their project and owner, and the physical
request. Source-record UUID and the declared scientific acquisition ID have
different meanings and remain separate. Permission to keep user bytes privately
is not a redistribution licence, nor verification of their geological meaning.
Only explicit private-user-supplied, complete-acquisition requests enter this
owned bounded protocol. Other rights/fullness cases retain their separate
scientific inventory/acquisition obligations rather than being silently relabelled.

The exact lexical request is retained, including whitespace and decimal spelling.
Its parser version is `mag-survey/v1:<request SHA256>`. A change in field,
uncertainty, mesh, prior or any other request bytes creates a distinct immutable
dataset. Repeating the same bytes returns only the fully reverified original
receipt. Nothing updates an old dataset in place or manufactures a new raw file
to bypass uniqueness.

## Geometry, likelihood and actual fitting remain separate

Let \(r\) denote the original closed request, \(b\) the acquisition bytes, and
\(S(r)\) its geometry-only seal. The durable dataset binds
\(H(r),H(b),S(r)\), not merely coordinates rendered in the browser. The seal
depends on original IDs, declared groups and geometry, never signal amplitudes.
Likelihood values are not given to the planner. Full covariance is a principal
partition covariance with its own Cholesky factor, not a subset of a previously
whitened full survey or a diagonal uncertainty replacement.

For eligible linear quantities, local fitting minimizes
\(\|W(H(q)-d)\|^2+\beta\phi(q)\), where \(q=\chi/0.01\), observations are nT,
and exported residuals are \(d-H(q)\). The native component kernel and Jacobian
come from the actual [version-pinned SimPEG magnetic simulation](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/potential_fields/magnetics/simulation.py).
L2 and IRLS use the actual [regularizer definitions](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/regularization/sparse.py),
the frozen beta candidates, eight positive epsilon stages and independently
checked stationarity. A wall cap is failure; it cannot become an approximate
success, skipped stage or second-best model. The detailed local tool and public
optimizer binding are described in [local calibration](06_local-calibration.md).

The source-backed method mapping names actual parser, geometry, calibration,
local-tool, bundle-validator and numeric-export functions and hashes their
current file bytes. It does not mistake the presence of those functions for
scientific acceptance or native admission. Online submission is explicitly
ineligible in this version. A local recipe executes supplied bytes in the
reviewed local environment; replay inspects a previously produced generation.
Neither is an online server inverse.

Direct source admission also parses the station CSV using explicitly declared
row/line/ENU and quantity-specific value columns. Every original row must match
the request's row ID, source group, coordinates and measured components; no
signal-based filtering or decimation occurs. Duplicated/missing headers, changed
values under recomputed hashes, shortened files and quantity mismatches refuse.
Float conversion is finite, preserves the retained binary64 value/sign and
rejects nonzero underflow to zero. Recorded timestamps need their original
column; unavailable times are declared, not invented. Upstream frame conversion
or corrections cannot enter this direct identity codec by changing a label.

## Verified local replay is not a new scientific experiment

The importer accepts a genuinely complete local NPY generation through the
strict existing numeric bundle validator. Its recovered request must equal the
owned dataset's complete converted request, not only geometry or configuration
hashes. Every retained member, dtype, shape, physical unit, original ordering,
residual sign, candidate inventory and likelihood metric is checked. Failed
ledgers, partial generations, unexpected files, arbitrary paths and raw originals
are not successful replay bundles.

The server retains one deterministic uncompressed ZIP, not a projection plus
unaccounted numeric siblings. Existing job result SHA/count cover all retained
numeric bytes. The ZIP is written exclusively with private permissions, fsynced
and read back before the owned SQLite transaction publishes a successful
reference. A failed pre-commit flush removes only the exact file created by that
attempt. An uncertain commit retains the file for reconciliation, because an
exception is not proof that the database failed to commit. Original bytes and
older result pointers are never overwritten. File fsync/readback and portable
transaction controls do not establish OS-crash, volume durability or host limits.

Every read/export resolves the owner/project/dataset/job/source again, verifies
current original bytes and source permissions, checks the closed request and
preflight bindings, and hashes the stored ZIP. Fresh external scratch is used for
bounded reimport; exact known members are removed after rechecking their hashes.
Unexpected bytes remain recovery debt, not a directory to sweep. The original
acquisition is excluded from numeric export.

An owner-imported replay is content-validated, not independent attestation of
the owner's external execution. Its claims remain false for full-method
acceptance, verified field source, geological truth and online admission. A
regularized susceptibility image is not proof of absent remanence, correct
field direction, unique depth or an identified ore body. Failed adversarial
controls and unresolved field metadata remain visible obligations.

## Existing protected client and assembly

The client uses same-origin cookie/CSRF transport. It submits the physical
request as an exact UTF8 string, obtains authenticated dataset/job receipts and
binds a result to the selected job, request, generation and original acquisition.
Native descriptors are rehashed by WebCrypto before the linked scientific view
is made available. An aborted/obsolete request cannot return a late usable view.
ZIP transfer parity hashes the actual downloaded bytes against authenticated job
state; it is not browser fitting or a floating-point reserialization of a result.

The existing owner dispatcher must integrate magnetic dataset, method, local
replay import, read/export, restart inventory and deletion cases together.
`install_dataset`, `install_replay`, `read_replay` and `exact_zip_inventory` are
executable additive seams. This leaf does not silently install a competing
server, auth layer or shared-worker branch. A numeric ZIP is not the existing
gravity JSON result, so generic validators cannot be reused by casting its
method string. The shared workbench/course and its protected navigation remain
separate assembly gates; no replay-only data authorizes a verified online view.

Public input/method reads are `read_dataset` and `read_method`; both recheck the
same source/original custody before returning information. Every public
install/read requires the selected `project_id`, not just an account match.
Switching between two projects owned by the same account cannot redirect
original or result access. A route does not obtain authority from a generation
path supplied by a browser. The parent resolves uploaded/local replay bytes
through its own checked staging and admission boundary.

## Español: entrada original, ajuste y custodia

El original adquirido y la solicitud física son objetos de bytes distintos.
El original se conserva sin modificación; la solicitud declara magnitud medida,
marco ENU, datum de altura, campo uniforme, linaje, IDs originales, ruido, malla,
cotas de susceptibilidad y política congelada. Un nombre CSV no identifica la
magnitud ni convierte intensidad absoluta en anomalía. La proyección del campo
secundario no es la anomalía exacta del módulo total.

La entrada privada verifica propietario/proyecto/RawAsset/SourceRecord, SHA256
y número real de bytes. UUID del registro API e ID científico de adquisición
permanecen distintos. Los permisos privados no verifican geología ni autorizan
redistribución. Esta vía exige adquisición completa declarada y derechos
`private_user_supplied`; otras vías conservan sus requisitos propios.

El CSV declara columnas de fila, vuelo, E/N/U y valores escalares o componentes
ENU ordenadas. Cada fila original debe coincidir con sus IDs, grupo, posición y
observación, después de la misma conversión binary64 finita y conservando el
signo del cero. Cabeceras duplicadas, filas omitidas, valores cambiados aun con
hashes recalculados y subdesbordamiento no nulo a cero se rechazan. Fechas
registradas requieren la columna real; fechas ausentes no se inventan. No se
aplica transformación, corrección, resta de media ni estimación de errores por
etiqueta. El validador directo acepta un nodo `original`, no recetas externas
sin el validador de procesamiento correspondiente.

Se preserva UTF8 léxico exacto: espacios y escritura decimal incluidos. El
parser `mag-survey/v1:<SHA256 de solicitud>` hace inmutable cada configuración.
Cambiar campo, ruido, malla, prior o bytes produce otro dataset, sin reescribir
el original ni el dataset previo. Un reenvío idéntico devuelve sólo el recibo
revalidado. El sello geométrico depende de IDs/grupos/posiciones, nunca de señal;
no demuestra inversión ni condicionamiento del ruido. La covarianza de una
partición es su principal con Cholesky propia, no filas de un blanqueo global.

Para magnitudes lineales se ajusta
\(\|W(H(q)-d)\|^2+\beta\phi(q)\), con \(q=\chi/0.01\), nT y residual
exportado \(d-H(q)\). Kernel/Jacobiano, regularización L2/IRLS y ocho epsilons
positivos corresponden a las fuentes versionadas citadas arriba. El límite
temporal es fallo, nunca ajuste aproximado aceptado o etapa omitida. La tabla de
métodos nombra y hashea las seis funciones reales; no convierte su existencia
en aceptación científica o admisión nativa. La ejecución online permanece
cerrada. Reproducir un resultado local no es enviar una inversión al servidor.

El importador acepta sólo una generación NPY local realmente completa y
verificada: miembros, tipos, formas, unidades, orden original, signo residual,
candidatos e historia final. Su solicitud recuperada debe coincidir con TODA la
solicitud convertida del dataset, no sólo un hash de geometría. Ledgers fallidos,
parciales y miembros extra no crean resultado exitoso. La generación no define
propietario/proyecto.

Se retiene un ZIP numérico determinista sin compresión; SHA/bytes del job cubren
todo el archivo, sin hermanos numéricos no contabilizados. Creación exclusiva,
modo privado, fsync y lectura posterior preceden la publicación SQLite. Fallo
anterior al intento de commit elimina sólo bytes exactos creados por ese intento.
Commit incierto conserva el archivo como deuda; una excepción no prueba que la
base de datos no confirmó. No se sobreescriben originales ni resultados previos.
Esto no afirma durabilidad de volumen, caída de SO ni límites del host.

Cada lectura/exportación revalida propietario/proyecto/dataset/job/fuente,
permisos actuales, original, solicitud/preflight cerrados y hash/bytes del ZIP.
Scratch externo nuevo se elimina sólo tras revalidar inventario y hashes;
miembros desconocidos quedan como deuda. El original adquirido no se exporta.
Todas las funciones públicas exigen el proyecto seleccionado: dos proyectos de
una misma cuenta no son intercambiables. `read_dataset`/`read_method` revalidan
la entrada antes de informar. El cliente conserva cookies del mismo origen,
CSRF, abort y recibo del job seleccionado; WebCrypto rehashea descriptores y los
bytes ZIP, sin reinterpretar floats como bytes originales.

El replay importado verifica contenido, no certifica ejecución externa ni
verdad de campo. Aceptación de método completo, fuente de campo, geología y
admisión online siguen falsas. Una imagen regularizada de susceptibilidad no
demuestra ausencia de remanencia, campo correcto, profundidad única ni mineral.
El dispatcher protegido, inventario/reinicio/borrado, vistas y despliegue del
parent conservan sus gates distintos; esta implementación no crea otro servidor
ni sustituye esos gates con un resultado nulo de control.
