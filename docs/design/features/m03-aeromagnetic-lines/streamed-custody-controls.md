# Streamed M03 custody controls / Controles de custodia

## English

The streamed profile is separate from the ordinary 400-row processing contract.
`magnetic_line_survey_contract` validates closed objects without changing that
contract. `magnetic_line_survey_io` produces and independently reads immutable
little-endian arrays and canonical JSON-lines tables. This layer is custody,
not a complete scientific Result, field acceptance or host admission.

Each array reference binds its role, units, dtype, shape and original-order ID
hash. Root manifests bind bounded pages; pages bind chunks with continuous row
and sequence counts. Readers verify actual size and SHA256 before decoding,
then independently reconstruct the content digest. Table content uses the
length-prefixed canonical row encoding, not a hash of Python representations.
Row/source membership stores original row positions, not selected-row numbers.
Two-dimensional source positions and membership keep their explicit column
counts. An empty exclusion is an explicitly zero-length index array with the
empty-byte digest, not an all-zero measurement or a missing file.

Changing a value, manifest shape, role/unit/dtype, root basename or undeclared
file invalidates custody. Boolean counts, float-as-integer shapes, extra or
missing keys, nonfinite cells and case-colliding names refuse. Native finite
numeric input is required; a string containing a number is not coercible input.
The unchanged bounded contract remains independently loaded and pinned.

Storage is explicit: `GEOPHYSICS_LOCAL_DATA_ROOT` or a supplied absolute data
root, and `GEOPHYSICS_LOCAL_TEMP_ROOT` or a supplied absolute temporary root.
There is no repository-relative fallback. Both must resolve outside Git
checkouts and the ordinary system-temp directory; links, reparse points and
hardlink substitutions refuse. No code/ledger root is reinterpreted as a data
root. This module does not edit the source-acquisition owner's `sources.ROOT`
or its CLI. Execution evidence, caches and pytest temporary directories belong
under the external device root resolved by management's workspace tooling.

The new controls exercise 8,201 ordered numeric cells across two complete
4,096-row chunks and a nine-row tail, typed source/member matrices, empty
exclusions, mutation rejection and explicit storage. This is a custody control,
not a measured field survey. The historical 8,201-row raw ingestion control has
`NaN` magnetic values and `Infinity` uncertainties intentionally left unopened
by the geometry-only pass. It must not be relabeled as actual field data.

Physical eligibility requires separate source rights, exact original CSV and
metadata, acquisition dictionaries, known datum/clock/quantity, explicit
correction history and an independently evaluated reference where required.
Convergence requires the frozen independent global stationarity test. Predictive
acceptance additionally needs whole-line sealed validation; original S1 remains
a genuine negative (18.799740861734186 nT versus 0.25966396538773057 nT).
Neither custody nor finite predictions can turn that result into a pass.

## Español

El perfil de levantamiento completo es distinto del contrato ordinario limitado
a 400 filas. El contrato nuevo comprueba objetos cerrados sin modificar ese
límite. Las matrices binarias little-endian y las tablas JSON por líneas tienen
manifiestos inmutables y verificación independiente. Esta capa establece
custodia de bytes, no un resultado científico completo, aceptación de datos de
campo ni habilitación del servidor.

Cada referencia conserva función física, unidades, tipo, dimensiones e
identidad de las filas en el orden original. Los manifiestos enlazan páginas y
bloques acotados; el lector comprueba tamaños y SHA256 reales antes de decodificar
y reconstruye la identidad del contenido. Las tablas usan filas canónicas con
prefijo de longitud. La pertenencia a una fuente conserva el índice original,
no un índice renumerado después de seleccionar datos. Una exclusión vacía es
una matriz de índices de longitud cero con identidad explícita, nunca una
medición de valor cero ni un archivo ausente.

Cambios de bytes, dimensiones, unidades, tipos, nombres o archivos no declarados
invalidan la custodia. Se rechazan claves adicionales o ausentes, booleanos
usados como cantidades, enteros escritos como flotantes, valores no finitos y
colisiones de nombres. No se convierten cadenas numéricas automáticamente.

Los datos y temporales requieren raíces absolutas externas indicadas mediante
argumento o `GEOPHYSICS_LOCAL_DATA_ROOT` y `GEOPHYSICS_LOCAL_TEMP_ROOT`.
No hay almacenamiento alternativo dentro del repositorio. Se rechazan rutas
dentro de un checkout Git, el temporal ordinario del sistema, enlaces y puntos
de redirección. La raíz del código y del registro de fuentes no se convierte
en raíz de datos. Las cachés y pruebas también usan almacenamiento externo.

Los 8.201 elementos del control prueban orden, bloques y cola parcial; no son
un levantamiento de campo. El control histórico de ingestión contiene `NaN`
e `Infinity` deliberadamente: inspeccionar geometría sin abrir mediciones no
demuestra que estas sean válidas. No se pueden presentar como evidencia real.

La elegibilidad física exige originales verificables, permisos, diccionarios,
datum, reloj, cantidad, historial de correcciones y referencia independiente.
La convergencia necesita la comprobación de estacionariedad global congelada;
la aceptación predictiva requiere particiones de líneas completas selladas
antes de usar valores. El S1 original sigue fallando: 18,799740861734186 nT
frente a 0,25966396538773057 nT. La custodia correcta o una predicción finita
no cambian esa conclusión ni justifican relajar la tolerancia.
