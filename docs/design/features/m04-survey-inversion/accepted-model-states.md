# Saved selected-final solver model states

## Requirements

R-488 AFTER a complete selected final refit and closed optimizer audit, THE
exporter SHALL extract only the initial model and actual accepted model arrays
from that selected candidate's final-refit native traces. Training folds,
failed solves, rejected trials and repeated stage-entry models SHALL NOT become
animation states. No interpolated or newly solved model is produced.
Gate: `tests/data/test_magnetic_model_states.py::test_retained_actual_selected_final_null_state`
and `tests/data/test_magnetic_model_states.py::test_selected_trace_continuity_and_history_binding`.

R-489 BEFORE reading/materializing audit/state arrays, THE extractor SHALL
check existing regular-file, line16MiB, complete64MiB, history4096 and physical
parameter2048 limits. The state sequence SHALL contain at most201 original
models, preserving accepted200. The state's numeric payload SHALL remain
within8MiB and the existing complete128MiB bundle/64numeric-member capacities.
Failure SHALL refuse without publishing, truncating or changing old bytes.
Gate: `tests/data/test_magnetic_model_states.py::test_audit_and_state_capacity_refusals`.

R-490 WHEN states are replayed, THE reader SHALL bind selected candidate,
final-refit fold, native source/epoch, complete inventory/audit hashes, exact
history indices and q-model hashes, physical SI arrays and the final model.
Missing/drifted arrays, wrong mappings or non-contiguous traces SHALL refuse.
Legacy v1 remains closed and has no model-state claim. New v2 adds one explicit
closed model-state member, with no unknown ZIP sibling/member exception.
Gate: `tests/data/test_magnetic_model_states.py::test_selected_trace_continuity_and_history_binding`
and complete numeric bundle/result/API roundtrip controls.

R-491 WHERE the v2 states exist, THE protected viewer SHALL replay saved physical
cells at discrete state indices, with exact selected-final phase/record readouts
and explicit no-interpolation wording. Objective-only v1 history SHALL remain
labelled as records, never accepted-model animation. Shared Stage, camera,
physical units/range and linked cell/row gates remain mandatory.
Gate: focused exact-state consumer negatives and rendered pointer/keyboard
replay in EN/ES, both themes and desktop/phone contexts.

## Design

Current v1 generations publish objective records and model hashes, not model
arrays. Existing bounded native OptimizerAudit does retain actual returned
trace.models_q. The retained original CSV/null generation's selected final
b07-l2 audit contains exactly one seven-cell model and zero accepted moves;
this proves one saved initial/final state exists, not nonzero animation.
Failed nonzero fits and prior source epochs are not upgraded.

Reuse that existing audit AFTER it is closed and AFTER calibration returned
complete, before immutable bundle publication. No additional callback, objective,
fit clock, native memory allowance or scientific solver is introduced. Audit
bytes are streamed with the original capacities and source identity. Final
selected records must match complete result history in order. Initial states
of subsequent fixed-surrogate solves must exactly equal the last retained
model and are not duplicated. Only trace entries after index0 count accepted
moves. Zero-step traces are lawful but do not invent motion. Convert recorded
q once with the original chi scale0.01, keeping q hashes for exact history
binding and comparing the final SI model byte-for-byte.

The optional capability is versioned explicitly as magnetic-survey-result-2;
it is not an extra field tolerated in the closed v1 grammar. The manifest
remains the existing exact registered numeric inventory: state arrays are
ordinary declared/hash-checked NPY members inside its unchanged64-member/
128MiB ceiling. Legacy export/import and strict owner bindings remain unchanged.
Protected v2 view dispatch is explicit; absent states show objective records
and no playback. No new shared controller, migration, all-writer lifecycle,
privileged API, native admission, field truth or release flag is added.

## Tasks

1. Freeze this precode and reread the genuine final native audit (R-488).
2. Implement bounded read-only selected-state extraction and exact negatives
   without any new scientific run (R-488/R-489/R-490).
3. Wire post-fit publication and closed v1/v2 numeric readback/ZIP validation,
   with declared members only and no off-ledger API scratch (R-489/R-490).
4. Supply the typed v2 owner view and exact protected client grammar, discrete
   actual-array replay and original-generation refusal controls (R-490/R-491).
5. Qualify retained genuine bytes and rendered interaction gates. Changed
   full648 nonzero fitting, independent precision, native resource/cancel/crash,
   full frozen adverse matrix and integration remain separate prerequisites.
