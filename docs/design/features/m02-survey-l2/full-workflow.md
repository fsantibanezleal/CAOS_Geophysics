# Submitted gravity workflow and complete IRLS result

This extends the lossless stage-book contract into the authorized ordinary
submitted-data workflow. The fixed native objectives, log17/floor3 policy,
eight betas, three folds, shared 200 accepted steps, 120 s per fit and 1800 s
per calibration remain literal. Non-null fixed-point failures remain failures.

## Contracts and replay

`calibrate_gravity_irls` accepts the seven-key calibration envelope, schema
`gravity-survey-irls-calibration-request-1`, epoch `m02-survey-irls-cpu-1`.
Policy has name, beta_candidates, optimizer, training, irls. Name is
`ordinary-irls-fixed-beta-log17-stage-1`; optimizer is the current CPU5 L2
initialization policy. The fixed stages retain the independently bound generic
linear optimizer and its diagonal metric. No metric or scientific policy switch
is introduced by this orchestration.

Result schema `gravity-survey-irls-calibration-result-3` retains the L2
top-level fields and adds `irls_policy_sha256`, `stage_books` and `fits`. There are
exactly 24 books plus one iff a selected refit ran. A solve references its book
by integer `stages`, never a nested book or truncated stage list. Each solve
adds the complete `l2_initialization`, five-key `irls_terminal` and actual
`initial_epsilon` (four floats or None). Its trace has the existing eight arrays
plus `stage_indices` and `models_q`. Exact native q is retained alongside
physical density because multiplication and subsequent division by 1000 need
not recover the same binary64 operand. Source/weight/operator replay uses the
actual native q, and checks its exact physical conversion for accepted stages.
Native accepted metrics concatenate initialization and
accepted stage states; each stage's true initial metrics live in its book.
Relative changes are within each fixed stage, never across a weight change.
Fit-level terminal metrics are the last stage's actual final metrics (or L2
initialization if no stage ran), not necessarily the last accepted trace row:
a genuine zero-step stage can change the objective/normalization at the same q.
No stage observation is inserted as an accepted step to make these equal.
Complete fits live in the top-level `fits` tuple; each fold's `solve` and
`final_solve` are integer references (3*candidate+fold and 24). A real first
complete null workflow exposed depth9 in nested terminal.stage_changes records;
this fit pool keeps the combined request/result/evaluation envelope within the
literal depth8 guard, without dropping any terminal or initialization. Books
and fits have equal counts and exact ordered references; no unused or duplicate
reference is accepted. Legacy L2 never dispatches these references.
Stage spans bind those actual accepted rows; transition observations consume
no optimization steps. Literal unsupported stages are not successful fits.

`validate_gravity_irls(result, calibration_request)` first admits the entire
combined envelope under unchanged 256 MiB/256 KiB/32768/depth8 bounds. It checks
closed keys/types, every request/result/policy/plan/source digest, book reference,
terminal/trace/failure, all stage weights/operators and native metrics by
rebuilding the frozen objective at each preceding actual model. It independently
recomputes physical predictions, residuals and available validation scores.
It does not rerun an optimizer. A content hash alone is not scientific replay.
Failed selection/results can be validated and exported without being scored as
accepted frozen models.

Separate evaluation schema `gravity-survey-irls-evaluation-request-3` carries
frozen_calibration, calibration_request, observations, noise and schema. The
outer values enter only after calibration; unsuccessful selection refuses.
Evaluation uses the outer marginal covariance and never refits. Field truth and
model accuracy are None, and all field/API/host/full-method claims stay false.

## Verification

FW01 THE workflow SHALL run all 24 fits and at most one selected refit.
Gate: tests/numerics/test_gravity_irls_workflow.py::test_full_native_null_selection_refit_and_replay

FW02 IF a fold or refit fails, THE workflow SHALL retain the failure and exclude
incomplete candidates without substitution.
Gate: tests/numerics/test_gravity_irls_workflow.py::test_failed_fold_and_selected_refit_retained

FW03 WHEN outer values arrive, THE evaluation SHALL replay the frozen result
without optimization and reject unsuccessful or tampered results.
Gate: tests/numerics/test_gravity_irls_workflow.py::test_outer_evaluation_no_refit_and_rehashed_tamper

FW04 THE workflow SHALL enforce closed types, complete-wrapper caps and one
distinct referenced book per fit before traversal or publication.
Gate: tests/numerics/test_gravity_irls_workflow.py::test_complete_guard_and_book_reference_negatives

The supplied-data archive/CLI uses separately documented explicit external
data/temp roots. It cannot supply prepared engines, callbacks or field approval.
Source/native runtime acceptance and actual online admission remain separate
from this local mathematical workflow.

## Native transport and external local execution

FW05 THE local adapter SHALL use a closed `gravity-native-archive-1` manifest,
tagged dictionaries/tuples and raw native float64/int64/bool arrays. Every
member has a SHA256 and exact byte/shape/type binding. ZIP is stored-only,
flat-named, bounded, without duplicate members, encryption, comments, trailing
bytes, callbacks, pickle or extraction. Re-import verifies the complete archive
before returning a native object, then the unchanged native caps and method
replay apply. An archive hash is transport integrity, not field acceptance.
Gate: tests/numerics/test_gravity_workflow_io.py::test_archive_negatives

FW06 THE CLI SHALL require an absolute external data root (argument or
GEOPHYSICS_LOCAL_DATA_ROOT) and temp root (argument or
GEOPHYSICS_LOCAL_TEMP_ROOT), reject repository roots and symlink/reparse
ancestors, and publish new immutable archives without replacing existing
files. No implicit repository data/temp fallback is permitted. Normalized
native inputs are declarations, not proof of rights, original-byte verification
or M01 correction. Source ROOT, acquisition, ERT and traveltime are untouched.
Gate: tests/numerics/test_gravity_workflow_io.py::test_external_roots_and_no_overwrite

Commands are `calibrate`, `verify`, and `evaluate`; `--input`/`--output` are
flat archive names below the explicit data root. Calibration archives retain
the complete original native calibration request and every actual fit/result,
including failures. Evaluation inputs carry a complete frozen calibration,
the separate outer observation/noise and the complete calibration request.
The local L2 adapter's evaluation-request-2 adds that original request, replays
every fit and only then constructs the unchanged native L2 evaluation-request-1.
Evaluation output losslessly flattens the original request into top-level
frozen_calibration/calibration_request/observations/noise/evaluation_schema plus
result/schema; another request wrapper would exceed the unchanged depth8 cap
for legacy L2 traces. `verify` independently recomputes the marginal score as
well as replaying every fit, without invoking an optimizer.
CLI success confirms transport/replay, not scientific convergence; calibration
returns exit 2 for an unsuccessful selection after publishing its failure
record. `verify` replays every fit without optimization. No archive can choose
an engine, install code, waive native epoch matching or activate a service.

FW07 THE L2 replay SHALL independently reconstruct each native objective,
trace/KKT, physical prediction, marginal score, fixed selection and diagnostics
against the complete original calibration request, including retained failures.
Gate: tests/numerics/test_gravity_workflow_io.py::test_l2_replay_rehashed_tamper

## Optional conditional data-noise refits

FW08 AFTER a fully converged selected calibration is frozen, THE worker SHALL
run exactly32 actual development-only refits at the selected fixed beta, original
start/reference/bounds/mesh/noise and (IRLS) the same log17 policy. Generator is
NumPy2.2.6 PCG64 with seed20261008, fixed here before execution; draws are
standard normals multiplied by the declared SD or original full covariance's
Cholesky factor. Observed development values plus draws are the refit targets.
There is no reselection, outer input, reuse of fitted model as start or fabricated
refit. All failed/unstarted fits and all32 targets are retained. A shared1800s
refit-job deadline and original120s/200-step fit limits remain literal.
Gate: tests/numerics/test_gravity_noise_refits.py::test_actual_frozen_refits

Refit result is a separate `gravity-noise-refits-result-1` native object with
original calibration/request hashes, fixed seed/beta/rows,32xdevelopment data,
fits and distinct stage books (IRLS only), explicit successful mask and elapsed
time. It is a conditional noise-refit distribution only: no percentiles,
posterior, geological interval, calibrated coverage or field truth is emitted.
Frozen calibration stays in its own immutable archive; the refit archive uses
hash references so it does not duplicate an already-maximal frozen wrapper.
Verification requires both original objects and regenerates every draw, then
replays every actual fit without invoking an optimizer. An unsuccessful frozen
calibration refuses before any draw or fit. Missing covariance credibility and
geometry/background/prior uncertainty remain separate scientific gates.

The first actual32 IRLS refits exceeded256KiB metadata when combined with the
original frozen calibration. Refit-only fit records losslessly encode terminal
stage_changes as two-column float64 `values` and same-shaped bool `available`,
columns=model_relative,weights_relative. Unavailable slots are literal0 with
false mask, never fabricated observations. At most20rows, no change removed.
Replay checks exact shapes/masks/nonnegative values and restores one actual fit
at a time after the full compact wrapper guard. Calibration-result-3 is unchanged.
Whole combined wrapper256MiB/256KiB/32768/depth8 limits are not raised or bypassed.
Transition columns alone were insufficient: the frozen result consumes187684
descriptor bytes and original request11090, leaving about63KiB for32 refits.
The refit-only `records` book therefore stores a closed typed node/edge table,
an interned exact string table and non-deduplicated float64/int64/bool pools.
Every array/scalar numeric operand has its own sequential pool span, preserving
all bits and logical duplicate storage. Node codes0..8 are None, bool, int,
float, str, float-array, int-array, bool-array, dict; code9 is tuple. Nodes are
five int64 columns (code,start,count,dimension1,dimension2), -1 dimension2
means1D. Dict edges are ordered key/value pairs; tuple edges are child nodes.
Edges/nodes are padded zero-filled4096-row blocks with exact lengths; numeric
pools are zero-padded4096-column matrices with exact lengths. Decoder enforces
single parent/no cycles, complete node/edge/string use, sequential numeric spans,
canonical padding, exact type/shape and original decoded scalar/depth bounds.
It restores containers and immutable numeric pool views only after the complete
compact wrapper and full record structure have been verified. Replay then
checks each actual fit/book pair; numeric operand buffers are not duplicated.
No raw inputs, foreign
callbacks or engine objects can use this refit-only closed record schema.

FW09 THE IRLS science matrix SHALL use the literal original24 L2 source-disjoint
controls, seeds700001+100*family+condition, priors/covariances and partitions.
Only the method schema/epoch/name and frozen IRLS policy are substituted. Actual
calibration, every-fit replay and complete failure-preserving archive are checked.
Nominal off-axis/bipolar independent/correlated controls still REQUIRE selected
convergence, outer WRMS<=2 and model/reference error ratio<1. A failure remains
a positive scientific gate failure, never skip/xfail or a negative-control pass.
Gate: tests/numerics/test_gravity_irls_matrix.py::test_original24_irls_science
This ordinary24 matrix does not close parent48/96 topography/padding protocols.
