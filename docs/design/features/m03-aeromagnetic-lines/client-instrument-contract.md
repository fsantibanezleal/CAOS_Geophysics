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

An explicit saved-job UUID form opens an actual already registered job through
the same authenticated project-scoped GET. It requires a canonical UUID and
does not depend on a source selector, invoke start, fabricate a dataset choice,
write admission or silently restore a job from local storage. It is disabled
while an observed job remains queued/running or an action is pending. Opening
retained evidence is read-only and does not rerun an outer evaluation. Source
intake, dispatch, export/download and parent navigation remain distinct gates.

The owner API uses existing same-origin cookie, CSRF, no-store and redirect-error
transport. Start/job/result/cancel projections are closed, checked and bound to
project/job/dataset identities. Polling observes an actually queued/running job;
cancel requests drain and does not declare it drained. `succeeded` means execution
completed, not scientific PASS. Full Result/2 dispatch preserves fixed-basis-v1
and resolution-v2 epochs. All109 pinned server schema descriptors are checked by
the exact client schema-parity gate; finite, safe integer, UTC and closed-field
checks are representation validation, not scientific or host certification.

The default `api.reader(project,job)` consumes the actual paged durable registry
schema m03-owner-members/1, binding every page to the job/result SHA, exact
offset/total/next-offset and sorted unique names/UUIDs. One512-entry page is
cached, not an unbounded survey-sized member map. The parent may supply the
same reviewed reader explicitly. The member adapter never guesses UUIDs from filenames or accepts URLs
and paths. Registry lookup must check owner/project/job/member scope and exact
named identity. Responses use `application/octet-stream` even for finite JSON
manifest bytes, because the shared downloadable-byte transport refuses JSON
success responses. Each fragment is counted and SHA256-verified before decoding.
Server validation still checks the entire finite closure before publishing it.
Result loading also resolves the actual result.json member UUID, verifies its
exact job SHA/byte receipt and original bytes (maximum2MiB), then parses Result/2
and binds run_id to the job. Parsing a reserialized HTTP object is not custody.

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
Profile pointer coordinates are transformed through the inverse SVG screen matrix
before mapping to the bounded source-order ordinal. CSS aspect-ratio letterboxing
must not select a different row from the visible point. The focused profile also
supports Left/Right/Home/End with the same linked readouts; these controls only
select retained observations and never trigger a fit or modify source/QC bytes.
Displayed row/grid windows are additionally bound to the actual Result SHA,
view, ordinal window and channel/plane selection. A render before the next
asynchronous load must hide the old incompatible window, not interpret line
data as an outer residual or another plane/job's values. No placeholder or
default-zero window is introduced while the correctly bound bytes load.

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

Opening a saved UUID clears the previous evidence before lookup, including when
the new UUID is invalid, foreign or missing; failed lookup never keeps the old
result under the newly entered identity. Loaded display windows bind the actual
job UUID, result SHA, view, channel/plane and first ordinal before rendering.
The original-row/evaluation window caption is HTML outside the SVG, so it is
readable and wraps at phone width rather than being clipped/scaled in the plot.
The linked metric SVG is a labelled group, not an image with hidden focusable
descendants; its actual sealed crossover controls remain keyboard-addressable.

Abrir un UUID guardado borra la evidencia anterior antes de buscarlo, incluso
si es inválido, ajeno o ausente. Una búsqueda fallida nunca conserva el resultado
anterior bajo la identidad nueva. Las ventanas vinculan UUID real, SHA, vista,
canal/plano y ordinal inicial; el rótulo HTML externo al SVG se adapta al teléfono.
El SVG métrico es un grupo rotulado, no una imagen que oculta controles
enfocables; los cruces sellados reales conservan selección por teclado.

The actual browser gate must mount the real owner adapter and durable registry,
choose a registered original source/request, start the full cold worker, await
its terminal receipt, inspect linked channel/plan/crossover/outer/grid selections,
export/download from the persisted DTO, cancel native work and verify drain,
restart/recover, and delete the project with stale member404. Test EN/ES, both
themes, desktop/phone, cross-owner failures and keyboard selection. Unit tests,
strict TypeScript and parsing an actual retained Result are not that browser gate.
No synthetic HTTP service or mocked lifecycle may substitute for it.

## Additive QR and intake/dataset representations

Result/3 is read as the separate augmented_direct_qr_v3 epoch. Its additive
schema_qr.json is a mechanical transcription of the frozen Python descriptors,
not a modification of Result/2, metadata/request/2 or the97-fit qualification
sources. The client validates exact original-coordinate diagnostic equations,
unmodified1e-9 relative-gradient and strict1e8 augmented-B condition boundaries,
the dense integer capacity equation and engine DLL identities. These checks are
representation integrity, not a replacement for scientific recomputation.
The instrument labels QR distinctly from LSMR and reports the B domain explicitly.

The owned intake/dataset leaf uses the existing same-origin ApiClient upload
transport. Only an actual selected File/Blob is transmitted, preserving all
original bytes; no URL, local device path or embedded example is accepted. The
user supplies provider, attribution, actual SHA256 and the exact rights statement,
decision and private-storage attestation. Size is taken from File.size. It is not
inferred that a provider, rights assertion or filename has been verified. No
whole4GiB browser buffer is allocated to compute a hash; the server independently
streams and verifies the declared digest. JSON sidecars remain immutable files.

Asset receipt has8 exact keys; dataset request has9 and the dataset receipt has8.
Actual UUID/SHA receipts must agree with the submitted role/hash/size. Exactly one
original, metadata and request reference and all actual chosen auxiliary receipt
pairs form the request; no nonexistent Dataset UUID is fabricated before creation.
Only a201 published dataset receipt supplies the Dataset UUID/SHA/row count for
the existing11-key start DTO. Dataset birth does not start science automatically.
Every receipt says provider not_verified and field not_established. A project
change discards stale local references. Clearing a reference never claims deletion
of durable bytes. Shared upload has no AbortSignal; the leaf waits for the actual
receipt and rejects stale generations, never claims upload cancellation/drain.
Mount/navigation, trusted fixed preparation installation, all-writer quota,
canonical schema union and actual current-shell browser workflow remain parent
integration gates. There is no mock API, no CLOSED completion or default enable.

### Sibling action custody

The composed intake and instrument share one synchronous in-view action lease.
It is claimed before sending an HTTP operation, so a sibling or repeated
submission cannot enter before React activity effects update. Source selection,
start and exports are disabled during the pending operation. A stale finalizer
cannot release another lease. Project changes do not clear an outstanding lease;
dataset publication is awaited and stale receipts are discarded for display.
Client abort is not used as evidence of dataset rollback or native drain.

This lease is only UI request coordination. HTTP settlement can still leave
uncertain server custody after network failure; server reconciliation, quota,
actual native drain and fixed installation remain mandatory. It is not device
scheduling or permission to delete retained bytes. Four deterministic lease
controls supplement the original29 contracts (18 source/registry,6 intake,
5 QR), giving33 actual required cases,
with no skipped cases. Current-shell pointer/keyboard/browser gates are separate.

ES: Ambos componentes comparten una reserva síncrona de acción de interfaz.
Cambiar de proyecto no libera una solicitud pendiente; un finalizador antiguo
no libera otra acción. La respuesta HTTP no prueba rollback, drenaje nativo ni
ausencia de deuda. Los controles del servidor y la recuperación siguen vigentes.

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
