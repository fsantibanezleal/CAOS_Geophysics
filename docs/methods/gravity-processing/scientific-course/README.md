# M01: correction and equivalent-source course / Curso de correcciones y fuentes equivalentes

## English

This course asks six physical questions about a measured station, its reference field and a spatially transferable representation. It teaches the **existing local** correction and transform chain. It does not introduce a density inversion, process raw gravimeter drift/tides, retrieve a DEM, authenticate an upload or close the actual-field acceptance gate. The equations and diagrams are explanatory documentation; they are not interactive scientific jobs or recorded numerical results.

Read the chapters in order. Each contains a physical diagram, derivation, worked reasoning exercise, answer and a Python task on a file selected by the user. Numerical values in worked exercises are explicit teaching assumptions or hand arithmetic, **not outputs of an executed course job**. The diagrams are schematics, not measured stations, fitted maps or density sections. English and Spanish express the same definitions and limitations.

| Question | Chapter |
| --- | --- |
| What quantity and reference did the station measure? | [1. Quantity and reference](01_quantity-and-reference.md) |
| Which mass contribution are we subtracting? | [2. Plate and terrain](02_plate-and-terrain.md) |
| Is the error an SD, a covariance or only a bound? | [3. Uncertainty and covariance](03_uncertainty-and-covariance.md) |
| What does the equivalent layer fit, and what does it not recover? | [4. Equivalent layer](04_equivalent-layer.md) |
| What did spatially blocked validation actually test? | [5. Spatial validation](05_spatial-validation.md) |
| At what height can we report the field, and with what limits? | [6. Continuation and limits](06_continuation-and-limits.md) |

Prerequisites are vector derivatives, Newtonian attraction, covariance matrices and least squares. Distinguish four quantities throughout: measured downward gravity $g$, normal gravity $\gamma$, co-located disturbance $D=g-\gamma$, and the explicitly declared local component admitted by the transform. A scalar magnitude disturbance is not automatically an exact harmonic Cartesian component. A source-free citation is a physical declaration to substantiate, not proof that the volume is empty.

### Definitions and units / Definiciones y unidades

| Symbol / term | English | Español |
| --- | --- | --- |
| $\phi$ | Geodetic latitude; derivatives and supplied latitude SD use degrees | Latitud geodésica; derivadas y DE de latitud en grados |
| $h_r,h_s$ | Receiver and surface ellipsoidal heights, m upward | Alturas elipsoidales del receptor y superficie, m hacia arriba |
| $H,N$ | Orthometric height and geoid undulation; compatible references required | Altura ortométrica y ondulación geoidal; referencias compatibles obligatorias |
| $g,D,B,T$ | Downward gravity, disturbance, plate attraction, signed residual, mGal | Gravedad descendente, perturbación, atracción de placa, residual con signo, mGal |
| SD / DE | Standard deviation of a declared primitive error, not a missing-value filler | Desviación estándar de un error primitivo declarado, no un relleno |
| $\Sigma$ | Covariance, squared units of its paired primitive quantities | Covarianza, unidades producto de las magnitudes primitivas |
| $c_j$ | Scalar equivalent-source coefficient, mGal m; not density | Coeficiente escalar de fuente equivalente, mGal m; no densidad |
| $\lambda$ | Ridge penalty on scaled coefficients; implicit mGal⁻² in this weighted objective, not its square | Penalización Ridge de coeficientes escalados; mGal⁻² implícito en este objetivo ponderado, no su cuadrado |
| Residual | Prediction minus observation, mGal | Predicción menos observación, mGal |
| Support / soporte | Training hull AND prescribed horizontal neighbour radius | Envolvente convexa de entrenamiento Y radio horizontal prescrito |
| Conditional SD / DE condicional | Propagated input noise with geometry and selected parameters fixed | Ruido de entrada propagado con geometría y parámetros seleccionados fijos |

### Three different lanes

1. **Explanation:** the equations and hand exercises below. Four explanatory models concern surface Somigliana, a plate, two correlated errors and ideal Fourier attenuation. They are not browser jobs and are not implemented by these Markdown pages.
2. **Local science:** the existing pinned Python modules execute a declared eligible user input. A real result requires actual command execution, input/config/source/runtime identities and its actual receipt. Recipes in this wiki milestone were syntax-checked, not executed.
3. **Recorded teaching controls:** the three existing independent analytical-prism surveys can supply bounded local method evidence only with their actual request, result, source/runtime identity and receipt. No such recorded control or metric map is displayed by these schematic pages. Older M01 receipts retain their original history; they are not re-labelled as execution of these recipes.

### Before using Python

Use an **existing reviewed** CPython 3.12 environment matching the repository's [correction pins](../../../../data-pipeline/requirements-m01.txt) and [transform pins](../../../../data-pipeline/requirements-m01-transforms.txt). Do not create an environment or upgrade another agent's pins as part of these recipes. Run chapter Python blocks from `data-pipeline`. All blocks are complete snippets for actual user-selected files, not invented field fixtures. The existing `gravity_transforms.read_request` reader imports scientific dependencies; it is not a stdlib-only public upload service. See the [complete local workflows](../../../design/features/m01-scientific-course/workflows.md) for paired PowerShell/sh commands and export paths.

The core accepts `gravity-stations-1`, with five exact parent keys and explicit state/history. The ordinary adapter has a six-key request, four-key result and thirteen-key receipt; it preserves the full parent and checks its scientific identity. It is not HTTP/authentication/storage/job integration, and `host_approved`, `full_method_accepted`, `field_source_verified` remain false. A transform takes four keys: schema version, **full three-key correction result**, geometry and config. Do not pass the adapter wrapper or only the corrected dataset.

Boundaries differ by layer. The core allows up to 10,000 stations; the adapter allows 1..400; transforms require 20..400 total and at least twenty active stations. The adapter bounds already-native objects (depth 16, 200,000 nodes, 8,192 UTF-8 bytes per string, 128 per key, 16 MiB canonical request). It does not acquire raw bytes. The transform's local reader caps raw bytes at 32 MiB by a MAX+1 read, rejects depth over 16, duplicates and nonfinite numbers. The core CLI instead checks size before and after a whole read: it is **not** a streaming untrusted-upload allocation guarantee. The separate MAIN-owned [local physical JSON guide](https://github.com/fsantibanezleal/CAOS_Geophysics/blob/231ca4291b129251e0a80bec120f8a1fc6b02576/docs/guides/15_local_physical_json.md) distinguishes its 16-MiB raw and 8-MiB canonical structural boundaries; those do not replace the scientific contracts or establish host admission.

Keep complete original request bytes and parents, including integer versus float serialization, station order, `original_value`, processing and history. A valid integer-bearing core/adapter parent can fail the transform's bounded original-input reconstruction. Do not “fix” it by coercing integers to floats, replacing hashes or inventing a preceding parent. Resume is valid only where the immutable method can independently reconstruct its identity.

### Field and evidence boundary

Processed principal facts such as OG/FAA/SBA/TTC/CBA/ISO are not automatically raw observations. The actual Bartlett author compilation has unresolved vertical-datum, primitive-SD and original-lineage gaps for this physical chain. Selecting 400 rows does not cure them. Never invent sigma, replace missing elevations, reapply plate/terrain already present in CBA, or substitute synthetic controls for missing eligible field bytes. This course neither acquires nor republishes protected source files. Source reconciliation and host admission are separate requirements, not consequences of a lesson or successful fit.

The immutable [core](../../../../data-pipeline/gravity_processing.py), [adapter](../../../../data-pipeline/gravity_station_adapter.py) and [transform](../../../../data-pipeline/gravity_transforms.py) determine executable semantics. The [exact feature contract](../../../design/features/m01-scientific-course/contracts.md) records exact keys, limits and replay restrictions. Documentation QA is not independent numerical validation, frontend route QA, deployment or whole M01 acceptance.

## Español

Este curso plantea seis preguntas físicas sobre una estación medida, su campo de referencia y una representación transferible espacialmente. Enseña la cadena **local existente** de correcciones y transformaciones. No añade inversión de densidad, tratamiento de deriva/mareas instrumentales, consulta de DEM, autenticación de archivos ni cierre de la aceptación de datos reales. Las ecuaciones y diagramas son documentación explicativa, no trabajos científicos interactivos ni resultados numéricos registrados.

Lea los capítulos en orden. Cada uno incluye diagrama físico, derivación, ejercicio razonado, respuesta y tarea Python sobre un archivo elegido por el usuario. Los números de los ejercicios son hipótesis docentes explícitas o aritmética manual, **no resultados de un trabajo ejecutado del curso**. Los diagramas son esquemas, no estaciones medidas, mapas ajustados ni secciones de densidad. Ambas lenguas mantienen las mismas definiciones y restricciones. La tabla inicial enlaza las seis preguntas; el glosario bilingüe fija símbolos y unidades.

Se requieren derivadas vectoriales, atracción newtoniana, matrices de covarianza y mínimos cuadrados. Distinga siempre gravedad descendente medida $g$, gravedad normal $\gamma$, perturbación co-localizada $D=g-\gamma$ y componente local explícitamente declarada para la transformación. Una perturbación de magnitud escalar no es automáticamente una componente cartesiana armónica exacta. La cita de volumen libre de fuentes es una declaración física que debe justificarse, no prueba de ausencia de masa.

### Tres vías distintas

1. **Explicación:** ecuaciones y ejercicios manuales. Los cuatro modelos explicativos tratan Somigliana superficial, placa, dos errores correlacionados y atenuación ideal de Fourier. Estas páginas no implementan controles ni trabajos de navegador.
2. **Ciencia local:** los módulos Python fijados ejecutan una entrada del usuario declarada elegible. Un resultado real exige ejecución efectiva, identidades de entrada/configuración/código/runtime y su recibo real. En este hito wiki las recetas se comprobaron sintácticamente, no se ejecutaron.
3. **Controles docentes registrados:** los tres levantamientos existentes con prismas analíticos independientes pueden aportar evidencia local acotada solo con petición, resultado, identidad de código/runtime y recibo reales. Estas páginas esquemáticas no muestran tal control registrado ni mapa de métricas. Los recibos antiguos conservan su historia y no se renombran como ejecución de estas recetas.

### Antes de usar Python

Use un entorno CPython 3.12 **ya revisado** con las versiones exactas enlazadas arriba. No cree entornos ni actualice dependencias ajenas mediante estas recetas. Ejecute los bloques desde `data-pipeline`. Son fragmentos completos para archivos realmente seleccionados por el usuario, no datos de campo inventados. El lector local `gravity_transforms.read_request` importa dependencias científicas; no es un servicio público stdlib de carga. Los [flujos completos](../../../design/features/m01-scientific-course/workflows.md) contienen los comandos pareados PowerShell/sh y las rutas de exportación.

El núcleo recibe un padre `gravity-stations-1` de cinco claves exactas con estado e historia explícitos. El adaptador ordinario tiene petición de seis claves, resultado de cuatro y recibo de trece; conserva el padre completo y comprueba su identidad científica. No implementa HTTP, autenticación, almacenamiento ni trabajos. Sus tres indicadores `host_approved`, `full_method_accepted`, `field_source_verified` permanecen falsos. La transformación recibe cuatro claves: versión, **resultado completo de corrección de tres claves**, geometría y configuración. No entregue la envoltura del adaptador ni solo el dataset corregido.

Los límites cambian según la capa: núcleo hasta 10.000 estaciones; adaptador 1..400; transformación 20..400 y al menos veinte activas. El adaptador limita objetos nativos ya materializados (profundidad 16, 200.000 nodos, cadenas 8.192 bytes UTF-8, claves 128, petición canónica 16 MiB); no adquiere bytes originales. El lector de transformación limita bytes originales a 32 MiB mediante lectura MAX+1, rechaza profundidad mayor que 16, claves duplicadas y números no finitos. El CLI del núcleo comprueba tamaño antes y después de leer todo: **no garantiza** asignación acotada de una carga no confiable. La [guía JSON de MAIN](https://github.com/fsantibanezleal/CAOS_Geophysics/blob/231ca4291b129251e0a80bec120f8a1fc6b02576/docs/guides/15_local_physical_json.md) separa sus límites estructurales de 16 MiB originales y 8 MiB canónicos; no reemplazan los contratos físicos ni autorizan un host.

Conserve bytes originales y padres completos, tipos entero/flotante, orden, `original_value`, procesamiento e historia. Un padre con enteros válido para núcleo/adaptador puede no ser reconstruible por la transformación. No lo “repare” convirtiendo tipos, reemplazando hashes o inventando un padre previo. La reanudación solo es admisible cuando el método inmutable reconstruye independientemente la identidad.

### Límite de datos reales y evidencia

Los hechos principales procesados OG/FAA/SBA/TTC/CBA/ISO no son automáticamente observaciones sin corregir. La compilación real de Bartlett mantiene lagunas de datum vertical, DE primitivas y linaje original para esta cadena física. Seleccionar 400 filas no las resuelve. No invente sigma, sustituya elevaciones ausentes, vuelva a aplicar placa/terreno presentes en CBA ni use controles sintéticos como reemplazo del requisito de datos reales elegibles. El curso no adquiere ni redistribuye archivos protegidos. Reconciliar fuentes y admitir un host son requisitos separados, no consecuencias de una lección o buen ajuste.

Los enlaces al núcleo, adaptador, transformación y contrato anterior fijan las operaciones realmente disponibles. Revisar documentación no equivale a validación numérica independiente, QA de rutas frontend, despliegue ni aceptación completa de M01. Los capítulos siguientes explican por qué esos límites son físicos, no simples etiquetas administrativas.
