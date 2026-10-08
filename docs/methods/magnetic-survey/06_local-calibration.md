# Actual local calibration / Calibración local real

## English: executed scope and remaining boundaries

The ordinary source modules now compose real supplied-data secondary ENU and
linear TMI likelihoods with the public M02 **candidate** optimizer. They execute
all eight fixed betas, L2 and sparse-smallness candidates, three sealed inner
folds, selected-candidate development refit and one-time outer evaluation.
This is not a stored-example replay. The source closure and reviewed native
acceptance registry remain separate gates. Exact total anomaly now composes the
reviewed public nonlinear candidate export with a physical Jacobian, refreshed
PSD GN and independently audited native-norm chords; see
[exact nonlinear composition](07_nonlinear-composition.md). Candidate execution
is not an accepted nonlinear source registry or independent magnetic convergence.
A linear fit is never substituted for an exact-magnitude observation.

The complete feature also still needs the frozen nontrivial S2 comparisons,
complete provider field acquisitions, owned API integration, linked interactive
views and measured native/host admission. A local null workflow is not their
acceptance. No public deployment or worker activation occurs here. The four
result claims are always false, including verified field source and geological
truth. Hashing supplied original bytes verifies their identity, not their
physical correctness, ownership licence, inducing field or processing history.

Source-linked composition:

| Module | Actual responsibility |
| --- | --- |
| `magnetic_likelihood.py` | Seal geometry before decoding selected observations; read principal covariance, freeze model, guard fitting/outer roles |
| `magnetic_optimizer_adapter.py` | Actual SimPEG fixed regularizer, whitened physical objective/GN and magnetic certificate; no copied M02 solver |
| `magnetic_calibration.py` | All candidates/folds, true-p1 continuation, literal metrics, failure ledger, final selection/refit/evaluation |
| `magnetic_diagnostics.py` | Local free-face resolution and explicit horizontal signed residual spectrum helper |
| `magnetic_result_bundle.py` | Closed fitted NPY generation, bounded import, physical units/hashes and metric replay |
| `magnetic_local_paths.py` | Explicit external device data/scratch; repository/worktree outputs reject |
| `run_magnetic_survey.py` | Read-only original verification, reviewed local-candidate receipt, actual commands and non-success exits |

## English: fixed likelihood, regularization and stopping

Physical susceptibility is `chi=.01*q`, bounded by the supplied SI prior, never
q relabelled SI. Phi is unhalved whitened data misfit plus fixed beta times the
actual vendor regularizer. Re-factor each selected principal covariance: no
subset of a full whitening matrix, diagonal approximation, jitter or anomaly-
derived SD. Validate the complete declared SD/SPD model after the seal and before
fitting. Unresolved rights or non-original unresolved processing lineage rejects.
Unselected observation lexemes are advanced without number conversion in the
row reader, after complete transport/hash validation. A literal
`cross_partition_dependence=declared_absent` requires actual zero covariance
across outer/development and inner fit/validation blocks. Nonzero entries reject
that contradictory declaration; use the truthful `possible_not_removed` label
and keep the full principal likelihood. Buffering never removes this dependence
or creates statistical independence. No covariance entry is repaired or zeroed.

Each sparse fit starts from that fold/beta's converged L2 model. Each of the eight
positive thresholds constructs a fresh actual unscaled SimPEG Sparse object.
Shared accepted-step budget is 200 across L2 plus all its surrogate solves; each
epsilon has at most 20 reweighting steps. There is no beta cooling or retry with
an alternative optimizer. At each fixed epsilon the *true* smooth-p1 objective
must not increase beyond `64*eps*max(1,abs(before),abs(after))`. The independent
true projected gradient, not fixed-weight surrogate gradient, must satisfy
`1e-7*max(1,||g_initial||inf)` and relative model change must be at most `1e-5`.
The core's own stops, line search and CG caps remain unchanged. Any cap, stall,
certificate failure or stationarity failure remains failed.

One failed fold makes the candidate score null. Complete scores are pooled
`sum(phi_d)/sum(n_components)`, not averages of an incomplete subset. Ties within
the frozen 64-machine-epsilon rule choose L2, then larger beta, then fixed ID.
Selected refit failure does not pick the next-best model. A selected sparse
candidate also fits its same-beta L2 development baseline. Baseline IDs are
not invented alternate volumes. The present closed result records the selected
volume; comparison-volume/UI integration remains required.

All physical fitting/validation/refit reads close at final-model freeze. The
ordinary CLI flushes, fsyncs and reads back a separate `OUTPUT.frozen.json`
before outer likelihood becomes available. It contains the actual model and
candidate/configuration hashes, false claims and an explicit frozen-before-
evaluation state, **not** a successful result. In-process numerical controls may
use an in-memory freeze; those do not prove crash durability. No fit callback
occurs after the outer read. Original acquisition row/component order is retained;
residual is observed minus predicted. Outer evaluation is once per invocation,
not a claim that this acquisition has never been seen in a previous study.

## English: explicit storage and real tools

Use caller-configured external device roots. A configured temporary root does
not implicitly supply a data or model root. Supply an absolute
`--data-root` or `GEOPHYSICS_LOCAL_DATA_ROOT`, plus the explicit external
`--temp-root` (or `GEOPHYSICS_TEMP_ROOT` in trusted composition). Do not put raw,
models, cache, pytest receipts or result generations in any checkout. The product
Python environment can execute E-worktree sources with the separately reviewed
M02 source directory on PYTHONPATH; no install/internal package is required.

Replace the uppercase placeholders below with caller-owned absolute paths.
Create their external parent directories explicitly. Do not use a provider URL,
relative output or repository `data/` default:

```text
APPROVED_PYTHON -B data-pipeline/run_magnetic_survey.py validate --request ABS_REQUEST_JSON --original ABS_RETAINED_ORIGINAL --output EXTERNAL_NEW_GEOMETRY_JSON --data-root EXTERNAL_DATA_ROOT --temp-root EXTERNAL_TEMP_ROOT
APPROVED_PYTHON -B data-pipeline/run_magnetic_survey.py calibrate --request ABS_REQUEST_JSON --original ABS_RETAINED_ORIGINAL --output EXTERNAL_NEW_GENERATION --data-root EXTERNAL_DATA_ROOT --temp-root EXTERNAL_TEMP_ROOT --binding-receipt ABS_OPERATOR_REVIEWED_RECEIPT --allow-candidate-core --wall-seconds 7200
APPROVED_PYTHON -B data-pipeline/run_magnetic_survey.py import --bundle EXTERNAL_GENERATION --temp-root EXTERNAL_TEMP_ROOT
APPROVED_PYTHON -B data-pipeline/run_magnetic_survey.py evaluate --bundle EXTERNAL_GENERATION --temp-root EXTERNAL_TEMP_ROOT
```

Request bytes are capped at 8MiB. Retained original is streamed in 1MiB blocks,
maximum 128MiB, with exact declared size/SHA256; it is never copied to a bundle.
Original verification requires the complete declared file, not a sample masquerading
as a complete acquisition. Correction parameters/physical lineage are not
certified by its hash. Validate remains geometry-only even when raw identity clears.

The binding receipt is an explicit trusted **local operator** capability, not an
upload, source-acceptance registry or automatic self-generated approval. Its
schema `magnetic-local-binding-1` has exactly `schema`, `scope` (literal
`local_candidate_only`), `review_reference`, `sources`, `source_inventory_sha256`,
`runtime_epoch`, `policy`. `sources` is the complete loaded module-name/SHA256
table in `run_magnetic_survey.SOURCES`, including the M02 transitive
`gravity_l2_precision` certificate validator. The inventory hash covers canonical
JSON of that table. Review the actual code first; a matching self-hash alone is
not acceptance. The receipt does not choose alternate sources or Python callbacks.
The request binding must match the exact public export/source/epoch. The explicit
candidate flag only permits this local candidate experiment. There is no flag
to bypass native norm proofs, claim field truth or admit an online job. The
quantity remains an explicit physical declaration in the admitted request.

Stdout is one bounded JSON summary; vendor diagnostics go to stderr and complete
actual iteration history stays in the result. Exit 0 means that named local
operation completed, not full scientific acceptance; 2 is invalid source/input,
3 dependency/resource/numerical/convergence failure, 5 local IO/durability failure.
Argparse rejects unknown flags/commands. `evaluate` is explicitly
`reused_sealed_evaluation`: it imports and recomputes outer physical noise metrics,
not a new fit or independent unseen holdout. Import does not refit or download.

## English: fitted generations and diagnostics

The fitted generation is separate from the older geometry-only JSON export.
It contains manifest plus at most 64 uncompressed non-object NPY members, total
128MiB; manifest 1MiB; NPY headers 64KiB. Original bytes remain with their owner.
All descriptor and member hashes, physical units, row/active ordering, frozen
candidate inventory, complete history and result false claims are checked.
The lossless three-table history codec stores all 32 model-hash bytes, not a
truncated digest. Import rejects object/pickle, traversal, extra/missing/partial
members, duplicate references, shape/header bombs, corrupted hashes, bad units
and rehashed forged claims/metrics. Import also validates complete uncertainty,
literal residual sign and independently replays development/outer metrics.

Writer uses only a fresh external generation, exclusive member creation,
flush/fsync, same-directory manifest replacement and complete readback. Existing
successful generations never overwrite. A numerical failure produces a separate
`failure.json` ledger with typed reason, actual candidate/fold outcomes and
unexecuted folds marked `not_run`; selection/model/prediction/metrics are null.
Started interrupted fits retain their actual failure reason, not `not_run`.
The separate `write_failure` operation validates the same closed identities,
candidate metrics and literal history, fsyncs and verifies a bounded readback.
There is **no success manifest** in that generation. A frozen receipt may remain
after later failure, intentionally preserving evidence without claiming success.
Injected disk-full/publication failures protect the previous generation and clean
only known newly written members. This is not measured Windows process-kill,
power-loss, directory-fsync or cross-volume durable-pointer acceptance; no active
generation pointer is switched by these tools.

Resolution uses the final fixed-objective Hessian on the sign-qualified free
face. Dense matrix/diagonal/stacked singular values exist only for A<=64. Larger
models solve at most eight deterministic point-spread columns and expose no dense
rank/spectrum. Zero rows identify bound-locked variables; all-bound has no invented
inverse. Sparse diagnostics are final-frozen-weight local resolution, not true-p1
posterior covariance. Measured resources remain unavailable (`null`) until actual
CPU/peak memory/scratch instrumentation supplies the complete resource record.
The separate spectrum helper accepts only a contiguous uniformly spaced original
line projected horizontally: view-only demeaning, Hann, rfft, one-sided PSD in
nT^2*m versus cycles/m. Gaps/irregular spacing are unavailable, never resampled.

Executable evidence paths: `tests/data/test_magnetic_likelihood.py`,
`test_magnetic_local_paths.py`, `test_magnetic_local_cli.py`,
`tests/numerics/test_magnetic_calibration.py`, `test_magnetic_full_calibration.py`,
`test_magnetic_diagnostics.py`. Full nested null/counterfactual tests use the
frozen S2 acquisition geometry with a **separate seven-cell control mesh**, not
the S2 528-cell inverse or its off-grid truth. Nonzero IRLS tests retain the
independent nonuniform seven-cell Choclo/physical-face control, including all eight
thresholds and independent true gradient. These are not substitutes for S2-A..F,
quantity/remanence/wrong-field negatives, full-cap execution or field acceptance.

The separate `local_nonzero_control.py` supplies clean Choclo observations from
one off-grid prism with no remanence, declared .012 SI and fixed .5 nT conditional
SD (no added noise realization). Its original includes all 288 rows; evaluator
bounds/chi remain separate from the modelling request. Actual nested fitting,
frozen-model receipt and fitted generation readback are exercised, with failed
sparse candidates retained rather than partially averaged. This tests real
nonzero supplied-data mechanics; neither its small mesh nor its outer score
closes the frozen S2 528-cell predictive/negative-control or field gates.

## Español: alcance, separación y uso

La calibración local usa observaciones entregadas, no resultados guardados. Las
ramas vector ENU y TMI lineal ejecutan ocho betas, L2 y Sparse, tres particiones
internas, selección fija, reajuste en desarrollo y evaluación externa única.
El núcleo público M02 sigue siendo **candidato**, no registro de aceptación.
La anomalía exacta del módulo total compone ahora la exportación pública no lineal
candidata, GN semidefinido actualizado y auditoría independiente de cada paso
con el certificado de norma. No equivale a registro de aceptación ni convergencia
magnética independiente; no se reemplaza por TMI lineal. Persisten controles S2 no triviales, datos de campo completos,
integración API/vistas y admisión nativa/host. No se despliega ni activa servicio.

Susceptibilidad física `chi=.01*q`; Phi sin factor medio; covarianza principal
completa con nuevo Cholesky en cada partición. Sin jitter, aproximación diagonal,
SD estimada por amplitud ni cambio de beta. Cada Sparse parte de L2 convergente
del mismo fold/beta. Se comprueban ocho umbrales, descenso del objetivo p1 real,
gradiente proyectado independiente y cambio de modelo. Ninguna tolerancia, stop,
certificación, búsqueda lineal o límite CG se debilita para aprobar. Fold fallido
implica score nulo; no promedio parcial ni selección alternativa si falla reajuste.

Se sellan geometría/IDs antes de valores. Al congelar modelo se cierran lecturas
de ajuste/selección; la CLI conserva modelo y hashes en `OUTPUT.frozen.json`
con flush/fsync/lectura antes de abrir evaluación externa. Ese recibo no es
resultado exitoso. Orden original conservado; residual observado menos predicho.
Cambiar valores externos en la prueba deja selección/modelo/historia iguales y
cambia sólo evaluación e identidades que corresponden. No demuestra que la
adquisición nunca se haya evaluado en otro estudio.

Use raíces externas configuradas por el usuario. Si sólo existe temp declarada,
no infiera una raíz data/models. Configure raíz externa absoluta
mediante `GEOPHYSICS_LOCAL_DATA_ROOT` o `--data-root`, y scratch externo explícito.
Datos crudos, modelos, caché y salidas dentro de repositorios/worktrees se rechazan.
Use los cuatro comandos anteriores con rutas absolutas reales y entorno aprobado.
El original retenido se lee y hashea, no se descarga ni copia al bundle.

El recibo de operador revisado tiene alcance literal `local_candidate_only`,
inventario completo del código cargado (incluido validador transitivo M02),
hash de inventario, epoch, policy y referencia de revisión. Hash propio correcto
no equivale a aceptación científica. `--allow-candidate-core` habilita únicamente
experimento local candidato: no omite certificado normativo, verdad geológica, campo verificado,
ejecución en línea ni despliegue. Los cuatro claims siempre son falsos.

Importar valida hashes/tipos/unidades/orden, incertidumbre completa, residual y
métricas recalculadas. Evaluar significa `reused_sealed_evaluation`, no nuevo
holdout. Bundle nuevo NPY acotado, sin pickle; no sobrescribe original ni resultado
anterior. Fallos numéricos guardan ledger `failure.json`, selección/modelo nulos
y folds no ejecutados `not_run`, sin manifiesto exitoso. Fallos inyectados de disco
o publicación conservan generación anterior; no se afirma recuperación Windows
ante caída/proceso muerto/energía ni puntero activo durable entre volúmenes.

Resolución local del objetivo fijo y cara libre, calificada por límites/GN/pesos
finales. No es covarianza posterior ni certeza. Matriz densa sólo A<=64; arriba
ocho columnas deterministas. Recursos no medidos siguen nulos, no cero inventado.
Espectro de vista únicamente en línea contigua regularmente espaciada en distancia
horizontal, Hann/rfft/PSD firmada; huecos rechazan sin remuestreo. Las pruebas
numéricas pequeñas/null no sustituyen adquisición S2 con 528 celdas, remanencia,
campo incorrecto, datos físicos externos, contención ni aceptación completa.

Native unrepresentable likelihood metrics and failed resolution solves/spectra
remain numerical failures, without an SD floor, rank cutoff or nugget fallback.
Métricas no representables y fallos nativos de resolución/espectro se conservan
como fallos numéricos, sin piso SD, corte de rango ni nugget.
