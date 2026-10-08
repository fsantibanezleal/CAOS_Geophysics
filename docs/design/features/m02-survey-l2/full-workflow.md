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
the separate outer observation/noise and (for IRLS) the calibration request.
CLI success confirms transport/replay, not scientific convergence; calibration
returns exit 2 for an unsuccessful selection after publishing its failure
record. `verify` replays every fit without optimization. No archive can choose
an engine, install code, waive native epoch matching or activate a service.

FW07 THE L2 replay SHALL independently reconstruct each native objective,
trace/KKT, physical prediction, marginal score, fixed selection and diagnostics
against the complete original calibration request, including retained failures.
Gate: tests/numerics/test_gravity_workflow_io.py::test_l2_replay_rehashed_tamper
