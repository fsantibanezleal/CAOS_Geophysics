# Lossless bounded IRLS stage representation

This unit implements serialization of actual fixed-stage records, not a new
solver, IRLS acceptance rule, archive verifier or accepted full M02 workflow.
The original nonnull fixed-point failure remains a genuine failing numerical
test. No epsilon, beta, bounds, stopping tolerance or resource cap changes.

## Requirements and named verification

- SB01 WHEN a book is supplied, THE codec SHALL admit the complete supplied
  native envelope before hashing, numeric traversal or copies, reject hooks,
  and preserve the existing caps. Gate:
  `tests/numerics/test_gravity_irls.py::test_SB01_complete_metadata_admission_before_hash_or_copy`
  and `test_SB01_foreign_hook_rejected_without_comparison`.
- SB02 THE codec SHALL preserve all 256 digest bits through four signed64 words,
  without floating conversion. Gate: `test_SB02_signed_words_exact_bits_no_float_roundtrip`.
- SB03 THE codec SHALL preserve every original fifteen-key stage digest, literal
  unavailable metric, actual weight/model/span and trace binding. Gate:
  `test_SB03_lossless_fifteen_key_digest_null_and_trace_binding`,
  `test_SB03_actual_native_null21_book_preserves_every_stage`,
  `test_SB03_actual_nonnull_cap_outcome_lossless_not_promoted` and
  `test_SB03_no_stage_or_initial_threshold_after_failed_initialization`.
- SB04 IF a schema, code, digest, metric ordinal, span, threshold, unit or trace
  is inconsistent, THEN THE codec SHALL refuse before returning decoded rows,
  including empty books and deliberately rehashed inconsistent records. Gate:
  `test_SB04_rehashed_inconsistent_book_never_decodes`,
  `test_SB04_trace_changes_and_unaccounted_rows_rejected` and
  `test_SB04_empty_book_still_rejects_foreign_semantics`.
- SB05 THE complete consumer SHALL preserve the literal 256 KiB metadata,
  256 MiB result arrays, 32768 scalars and depth8 limits, charging every logical
  occurrence. Gate: `test_SB05_actual25_books_fit_whole_guard_without_list_digest_waiver`
  and `test_SB05_unchanged_array_limit_counts_duplicate_logical_occurrences`.
- SB06 BEFORE any scientific output is called verified, THE future complete
  result/archive consumer SHALL replay actual source/operator/weights, request,
  policy and complete directory/member/EOF bindings. Gate: future complete
  IRLS result/export replay controls; **NOT RUN / not implemented by this codec**.

All current named tests above live in `tests/numerics/test_gravity_irls.py`.
SB05's 25-position fixture uses actual native null stage records, not 25 actual
fits. Its acceptance is a representation test, not a full calibration gate.

## Exact native schema and digest domains

`gravity-survey-irls-stage-book-1` has exactly nineteen keys:
schema, count, index, accepted_span, model_span, beta_engine, epsilon,
epsilon_units, norms, hash_encoding, weight_sha256_words, operator_sha256_words,
smallness_weights, status, reason, metrics, logical_stage_sha256, book_sha256,
trace_binding_sha256. Count is an exact int0..21. Active count a is1..4096.
Array types are exact native float64/int64, never subclasses or coercions.

| Array | Shape | Meaning |
| --- | --- | --- |
| index | int64[s] | Contiguous actual stage0..s-1 |
| accepted_span, model_span | int64[s,2] each | Chained actual accepted/model row indexes0..200 |
| beta_engine | float64[s] | Exact fixed candidate beta times fit count |
| epsilon | float64[s,4] | Actual pinned log17 thresholds, exact floors from17 |
| weight_sha256_words, operator_sha256_words | int64[4s,4] each | Stage-major component digests, exact big-endian signed64 mapping |
| smallness_weights | float64[s,a] | Actual positive finite p1 weights |
| status, reason | int64[s] each | Closed positive outcome dispatch |

Units are exactly `(g/cc,g/cc/m,g/cc/m,g/cc/m)`; norms are four exact floats
`(1,2,2,2)`. `hash_encoding` is `sha256-big-endian-signed64x4-1`.
Digest words decode each eight-byte segment with big-endian signed conversion;
all-zero words are real bits, not missing-value sentinels.

Status0/1/2 means converged/nonconverged/failed. Reason0..9 means respectively
absolute_stationary, kkt_stable, iteration_cap, cg_cap, line_search_failed,
wall_cap, zero_free_direction, nonfinite, engine_error, state_mismatch.
Status0 requires reason0/1; status1 requires2..6; status2 requires7..9.
An unsupported pre-stage terminal is not encoded as a successful stage.

Metrics has exactly columns,index,values. Columns are the literal eight names
phi_d_initial, phi_m_initial, phi_engine_initial, kkt_initial, phi_d_final,
phi_m_final, phi_engine_final, kkt_final. Index is int64[s,8]; -1 means literal
None, and all present row-major entries use each contiguous ordinal0..v-1 once.
Values is float64[v], v<=8s, finite nonnegative. Zero is preserved as measured
zero, not used for unavailable values.

`logical_stage_sha256` preserves the existing native digest of the original
fifteen-key tuple, including native arrays and None. `book_sha256` hashes every
other book key. `trace_binding_sha256` hashes the actual two-key shared model/
stage-index trace. Initial model rows have label-1; each accepted stage span
binds actual subsequent rows and its stage label. No hidden/gap/extra rows or
stage transition counted as an optimizer step. Initial epsilon can be None
only when there are no stages and no thresholds were computed.

## Full-wrapper layout correction and remaining implementation

The old nested stage-book proposal reaches depth9 at
`candidates[i].folds[j].solve.stages.metrics.columns[k]`. A real test-first
failure demonstrates this; the existing depth8 guard remains unchanged.
Prospective result3 instead has a top-level stage_books tuple containing
exactly24 fold books plus a25th iff the selected development refit ran.
Each fold solve references index3*candidate+fold; final solve references24.
There must be no missing/unused/duplicate reference or omitted failed fit.
Each fit has one distinct logical book; repeated aliases are still charged
at every occurrence by the unchanged guard. This preserves all per-fit data
while keeping complete result/evaluation wrappers within the depth envelope.

The codec itself does not implement/register complete calibration-result3,
evaluation-result3 or archive EOF/source verification. Legacy L2 validators
remain unchanged and reject IRLS discriminators. Full result publication needs
typed pool/request/source/policy/trace/operator replay and actual complete
selection/refit/evaluation/export/import tests. No universal maximum combined
trace layout is claimed: exceeding an unchanged complete-wrapper cap refuses.

## Actual local unit receipts

Test-first absence:20 failures, preserved. First implementation:20PASS.
Expanded controls:23PASS/4FAIL, preserving two empty-book semantic defects,
missing pre-stage threshold support and the depth9 design failure. Corrected
unit:27PASS/0FAIL/0SKIP,9.08s. The real null21 case is
CONVERGED/IRLS_STATIONARY_NULL; the real nonnull case is
NONCONVERGED/IRLS_ITERATION_CAP, preserved without promotion. These receipts
do not establish complete scientific/native/host/field acceptance.
