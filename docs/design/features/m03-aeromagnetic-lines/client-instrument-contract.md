# Source-bound magnetic survey instrument

The additive leaf `frontend/src/features/magneticLineSurvey/SurveyInstrument.tsx`
composes the installed shell0.8 `Knob`, `Readout`, language and number-format APIs.
The parent composes this leaf inside its existing CaseWorkbench and navigation;
the leaf is not another shell, replacement Workbench or standalone demo. Parent
mounting and real owner lifecycle/browser acceptance are required separately.

## Inputs, identity and transport

`projectId` is the authenticated selected project. `sources` contains immutable
owner-bound original asset/request UUID and SHA descriptors, bilingual title and
review, actual original-row count and the factual authored/user/provider kind.
There is no default data, provider fetch, embedded survey, route fallback or
scientific parameter rewrite. A new scientific recipe requires a newly admitted
immutable request attachment, not client editing of a successful Result.

The owner API uses existing same-origin cookie, CSRF, no-store and redirect-error
transport. Start/job/result/cancel projections are closed, checked and bound to
project/job/dataset identities. Polling observes an actually queued/running job;
cancel requests drain and does not declare it drained. `succeeded` means execution
completed, not scientific PASS. Full Result/2 dispatch preserves fixed-basis-v1
and resolution-v2 epochs. All109 pinned server schema descriptors are checked by
the exact client schema-parity gate; finite, safe integer, UTC and closed-field
checks are representation validation, not scientific or host certification.

`readMember(job)` must be supplied by the actual durable owner/job/member UUID
registry. The member adapter never guesses UUIDs from filenames or accepts URLs
and paths. Registry lookup must check owner/project/job/member scope and exact
named identity. Responses use `application/octet-stream` even for finite JSON
manifest bytes, because the shared downloadable-byte transport refuses JSON
success responses. Each fragment is counted and SHA256-verified before decoding.
Server validation still checks the entire finite closure before publishing it.

Public/private export requests use the reviewed closed scope DTO. The currently
unresolved persisted artifact UUID/download projection must be reviewed and
implemented; the leaf deliberately says only that an export response arrived.
It does not fabricate download URLs, replay availability or a replay-success flag.

## Scientific views and exact display limits

The original-row profile reads at most4096 original rows and65536 scalar cells
per verified window. This is display paging, not survey thinning: the retained
backend fit and Result refer to the complete original acquisition. The selected
channel resolves its actual declared QC-mask target; rejected values are omitted,
never replaced by zeros. Pointer selection links the profile, metric plan, row
ordinal, actual original ID and aligned E/N/Z coordinates. Coordinates retain the
admitted upward/datum convention; no web projection or inferred terrain is added.

The plan uses an equal metric scale in E/N, shows only the current declared row
and crossover windows and labels its actual display extents. It does not draw
unloaded points, interpolate tracks or infer geological boundaries. Crossover
windows contain at most128 actual retained rows, including rejected rows, nullable
geometry, actual segment IDs, height/time differences and reason enums. Exact
manifest/page/chunk layout, byte/hash and closed crossover row schema are verified.
Geometry acceptance is not a solved line-offset correction. Null crossings are
not fabricated and rejected crossings do not become calibration evidence.

The outer view reads actual retained observed/predicted/residual members. Its
ordinal is explicitly an evaluation ordinal, NOT an original acquisition ID.
No absent original-ID or QC-mask member is invented. It displays the retained
scientific verdict, not a new outer evaluation or reopened untouched holdout.

Grid display selects an actual fitted physical plane, datum and height, loading
at most16 grid rows subject to65536 scalar cells per window. Pointer/keyboard
selection reports physical E/N, prediction nT and actual support mask. Unsupported
cells remain transparent/no-data; the informational higher-plane bit4096 is not
an exclusion. No browser kernel, geological-depth inference, cell aggregation or
mock raster is used. Color scale and display magnification affect visualization
only: no solve, correction, QC, training selection or scientific threshold changes.

## Cancellation, adverse evidence and browser acceptance

Project/source changes abort active display/action requests and discard stale
state. Row/member loads are separately abortable. Request failure shows a fixed
bilingual message without paths, raw values or tracebacks. Scientific gates,
actual fit count and selected training parameters remain visible independently of
execution state. Source review distinguishes authored control and genuine field
acquisition; numerical/local byte success is not field or host acceptance.

The actual browser gate must mount the real owner adapter and durable registry,
choose a registered original source/request, start the full cold worker, await
its terminal receipt, inspect linked channel/plan/crossover/outer/grid selections,
export/download from the persisted DTO, cancel native work and verify drain,
restart/recover, and delete the project with stale member404. Test EN/ES, both
themes, desktop/phone, cross-owner failures and keyboard selection. Unit tests,
strict TypeScript and parsing an actual retained Result are not that browser gate.
No synthetic HTTP service or mocked lifecycle may substitute for it.

## Español: instrumento y límites verificables

El componente aislado usa el shell0.8 y se compone en el CaseWorkbench existente.
Las fuentes y solicitudes son referencias inmutables UUID/SHA del mismo proyecto.
No hay datos de ejemplo predeterminados, descarga externa, rutas locales ni
reinterpretación de un resultado como receta nueva. Estado exitoso significa
ejecución terminada: no convierte FAIL científico en PASS de campo o del host.

Las ventanas verificadas conservan filas originales, máscaras y coordenadas
alineadas; el ajuste del servidor usa el levantamiento completo. El plano métrico
y los cruces se vinculan a evidencia retenida, incluyendo rechazos y geometría
nula, sin inventar intersecciones ni correcciones de nivelación. El ordinal externo
es de evaluación, no un ID original ni una máscara QC inventada. Mallas y planos
usan altura/datum físicos, nT y máscaras reales, sin rellenar celdas no soportadas.

La custodia SHA de fragmentos no recalcula el hash del arreglo completo. Exportar,
disponer originales y ejecutar replay son hechos distintos. El registro durable,
DTO de descarga, recuperación, cancelación medida, eliminación y pruebas reales
del navegador EN/ES/claro/oscuro siguen siendo gates de integración obligatorios;
no se sustituyen por compilación, mocks ni pruebas unitarias.
