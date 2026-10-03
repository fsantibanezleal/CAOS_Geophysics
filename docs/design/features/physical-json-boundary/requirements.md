# Local physical JSON boundary requirements

Status: exact requirements frozen after MAIN's full b124 review and explicit local-only implementation approval, recorded before code. The new module/tests now exist; actual per-gate execution and remaining review holds are in [tasks](tasks.md) and the [review packet](review-packet.md). Read [research](research.md), [design](design.md), [contracts](contracts.md) and [validation](validation-plan.md) together. This does not activate any caller or waive vertical gates.

R-PJB01 THE local helper SHALL accept only exact built-in bytes and return only the newly decoded native gravity-stations-1 dict, without wrappers, defaults, copies, normalization or input mutation.
Gate: tests/data/test_gravity_station_json.py::test_exact_bytes_and_native_return

R-PJB02 IF actual raw bytes exceed 16777216, THEN THE helper SHALL reject before decoding, token conversion or final object construction; empty input SHALL reject as invalid JSON.
Gate: tests/data/test_gravity_station_json.py::test_actual_raw_byte_boundary

R-PJB03 WHEN scanning untrusted bytes, THE helper SHALL enforce root container depth 16, 200000 counted containers/keys/scalars, decoded key/value UTF-8 limits 128/8192 and numeric lexeme length 128 BEFORE final object construction or copying.
Gate: tests/data/test_gravity_station_json.py::test_scanner_bounds_before_materialization

R-PJB04 IF JSON is malformed, trailing, BOM-prefixed, invalid UTF-8, duplicate after escape decoding, surrogate-invalid or nonfinite including float overflow, THEN THE helper SHALL reject without exposing private input or a partial dict.
Gate: tests/data/test_gravity_station_json.py::test_strict_grammar_encoding_duplicates_and_nonfinite

R-PJB05 THE helper SHALL preserve native int/float types, finite signed floating zero and decoded Unicode without global JSON settings, hooks, numeric rewriting or Unicode normalization, and SHALL limit integer tokens to inclusive magnitude 9007199254740991.
Gate: tests/data/test_gravity_station_json.py::test_numeric_unicode_semantics_and_integer_bounds

R-PJB06 THE helper SHALL enforce 8388608 scientific ASCII-canonical bytes before final object construction and independently cross-check the same bound with streamed standard encoding, without joining a full canonical copy or changing the existing scientific hash dialect.
Gate: tests/data/test_gravity_station_json.py::test_canonical_precount_and_scientific_vectors

R-PJB07 WHEN a bounded native root is constructed, THE helper SHALL enforce exact gravity-stations-1 root/metadata/instrument/station keys, literals, declared scalar ranges, 1..400 stations and exact nonblank unique station IDs without inventing datum, geoid, rights or units.
Gate: tests/data/test_gravity_station_json.py::test_exact_root_metadata_and_station_contract

R-PJB08 WHERE an uploaded root declares history, THE helper SHALL validate the exact ordered 0/2/3/4 record shapes, parameter literals and station-aligned arrays/hashes specified in contracts.md without replaying values or certifying supplied hashes.
Gate: tests/data/test_gravity_station_json.py::test_exact_history_shapes_without_numerical_replay

R-PJB09 THE helper SHALL raise only the proposed safe typed contract errors for expected input failures, with fixed codes/messages and bounded known field paths, never supplied names/values, raw text, decoder document, file paths or source citations.
Gate: tests/data/test_gravity_station_json.py::test_safe_typed_errors_and_no_decoder_context

R-PJB10 THE helper SHALL import only stdlib and perform no file/network/path/environment lookup, core import, scientific call, external hook, process execution or global parser/recursion/integer-limit change.
Gate: tests/data/test_gravity_station_json.py::test_stdlib_only_no_io_hooks_or_global_changes

R-PJB11 WHILE a root is structurally accepted, THE helper SHALL leave numerical history/coordinate/error geometry decisions to the unchanged ordinary core, and SHALL never claim scientific, provider, field, host or method eligibility.
Gate: tests/data/test_gravity_station_json.py::test_structural_acceptance_is_not_scientific_admission

R-PJB12 WHEN later local callers retain provenance, THE helper SHALL leave original bytes and supplied source identity unchanged; raw and scientific hashes SHALL remain separate and SHALL NOT be manufactured by reserializing the source.
Gate: tests/data/test_gravity_station_json.py::test_raw_and_supplied_source_hash_domains

R-PJB13 THE prospective implementation SHALL have measured local nominal/upper/malformed time and memory evidence, prove rejected scanner inputs never reach materialization, and preserve existing gravity/MT parsers and immutable scientific sources.
Gate: tests/data/test_gravity_station_json.py::test_local_resource_and_legacy_regression_evidence

R-PJB14 THE unit SHALL remain local-only with no API/route/wire/storage/migration/jobs/bundle/frontend/admission activation or waiver to the held physical-vertical SDD, and no helper/test source SHALL be written before full main review and explicit approval.
Gate: docs/design/features/physical-json-boundary/review-packet.md; tests/data/test_gravity_station_json.py::test_local_only_scope_and_nonclaims
