# Full-survey owner wire review / Revisión de interfaz propietaria

## English

This is a producer-reviewed, executable CLOSED mount proposal, not independent
approval, activation or completion of M03. The isolated `app/magnetic_survey_port.py`
uses existing host authentication, real DB project ownership and host CSRF/origin
middleware. It neither imports scientific engines nor reads submitted bodies,
paths or recipes, allocates survey storage, schedules work, changes migrations or
touches the shared workbench. The accompanying patch is checked against its owned
server source; an integrator must adapt it to their current assembly. Installing
the port cannot be switched OPEN by an environment flag.

GET `/api/projects/{project_id}/magnetic-line-surveys/capability` returns the closed
ten-key `m03-owner-capability/1` response model. All statuses are literal, extra
keys refuse. `online=closed`, `field_acceptance=unresolved`, original S1 and both
opened source-refinement predictive verdicts remain `fail`; real full-field
execution is `not_verified`, owner lifecycle `not_integrated`, host admission
`not_established`. The advertised future result schema is
`magnetic-line-survey-result/1`, not the completed diagnostic envelope. There is no
claim that a Result exists. POST the same prefix `/jobs` returns 409
`method_closed` after ownership. Unauthenticated requests return 401, nonexistent
or foreign projects 404, unsafe mutations 403 through existing middleware.
No raw provider rights or private device paths are exposed.

### Required replacement, before OPEN

1. Resolve uploaded original asset UUIDs through the existing owner-scoped DB,
   immutable byte/hash receipts and verified external storage. Clients never
   send device paths or Python module names. Metadata, request and each auxiliary
   original need their own hash-bound owner references. No inferred line IDs,
   UTC, elevations, errors or synthetic substitute for a field source.
2. Strictly parse the existing full SurveyInput/SurveyRequest schemas. Build the
   value-free original or correctly aligned GeometrySeal before channel access.
   Keep every original row/ID, all sources in one global operator and the frozen
   candidate matrix, leakage-safe partitions and original scientific thresholds.
3. Complete the fold-local correction DAG, references, global incidence, grid,
   support/masks, transform limitations, typed SurveyResult cross-member closure,
   immutable export and verified replay. The existing bounded CLI is not a
   full-survey job recipe. Empty actual calibration and original S1 FAIL remain.
4. Add durable owner job/result/member lifecycle to the existing method inventory:
   queue, cancellation, timeout, restart recovery, terminal accounting, quotas,
   deletion and private export authorization. Never reuse another method's
   result discriminator or leave a magnetic member accessible after deletion.
5. Implement measured Linux process-tree CPU/RSS/commit/scratch limits and cold
   whole-request/p95 admission on the chosen single ML VPS. Windows component Job
   receipts are not Linux host acceptance. No new mail/backup/Pages dependency.
6. Add isolated frontend typed API/result readers and original source-bound
   linked survey/grid/crossover/validation views. Compose existing shell and
   project navigation; do not replace the shared Workbench. Verify real click
   navigation, ownership failures, replay/live labels, EN/ES, light/dark, phone
   fit, cancellation and actual browser evidence before activation.

Tests use real migrated SQLite, existing fastapi-users account/verification and
CSRF/origin middleware with a captured in-memory mail sender, not a new SMTP
service. Malformed submitted recipes are refused without parsing. Cross-owner
and logged-out access are tested on the same actual project. The mount itself
is unapplied; no deployment or server assembly change is part of this proposal.

## Español

Es una propuesta ejecutable CLOSED revisada por su productor, no aprobación
independiente, activación ni M03 completo. Reutiliza autenticación, propiedad
real de proyectos en la base y protección CSRF/origen. No importa motores, lee
cuerpos/rutas/recetas, crea almacenamiento, agenda trabajos ni modifica
migraciones o Workbench. El parche se comprueba contra el servidor propietario;
la integración debe adaptarlo al ensamblado actual. No existe bandera OPEN.

GET capability entrega el modelo cerrado de diez claves indicado arriba:
online cerrado, campo sin resolver, S1 y ambos refinamientos FAIL, ejecución de
campo no verificada, ciclo propietario no integrado y admisión de host no
establecida. El esquema de resultado anunciado es futuro, no un resultado
existente. POST jobs rechaza con 409 method_closed tras comprobar propietario;
401 sin sesión, 404 proyecto ajeno/ausente y 403 mutación insegura. No expone
derechos privados ni rutas del dispositivo.

Antes de OPEN se requieren originales por UUID propietario y hash, metadatos y
auxiliares con custodia, parser cerrado, sellado geométrico sin valores, todas
las filas originales, operador global, particiones/candidatos/tolerancias
congelados; DAG completo de correcciones por partición, referencias físicas,
incidencia global, grilla, máscaras, transformaciones, SurveyResult, exportación
inmutable y replay verificado. La CLI acotada no es una receta de encuesta
completa. Se conservan calibración realmente vacía y S1 FAIL.

También faltan ciclo durable de trabajos/resultados/miembros con cuotas,
cancelación, recuperación y eliminación; límites Linux medidos y admisión de
solicitud completa/p95 en el único VPS ML; lectores frontend tipados y vistas
vinculadas de originales/grilla/cruces/validación integradas al shell existente,
con pruebas reales de navegación, propiedad, EN/ES, temas y teléfono. No se
agrega requisito SMTP, respaldo ni Pages. Las pruebas usan SQLite migrada,
cuentas reales y correo capturado en memoria. El parche permanece sin aplicar;
no se despliega ni modifica el ensamblado del servidor.
