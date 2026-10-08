# Pure accounting protocol requirements

Date: 2026-10-03. Pure unit implemented under MAIN exact approval of2c94da4;
see [approval](approval.md) and [actual local evidence](implementation-evidence.md).
Parent directional acceptance is not native implementation or OS/context authorization.
Read [research](research.md), [design](design.md), [contracts](contracts.md),
[validation](validation-plan.md), [tasks](tasks.md) and [review packet](review-packet.md).
All twelve named pure gates now exist/pass locally; independent MAIN review/rerun
before develop promotion. All fifteen actual-platform gates still CLOSED/NOT_RUN.

PAP-001 THE pure unit SHALL expose only deterministic in-memory protocol,
conversion and state operations, without launch, source/profile measurements,
clock reads, file/network I/O, OS calls or runtime admission activation.
Gate: tests/worker_accounting/test_protocol.py::test_pure_boundary_and_no_authority.

PAP-002 WHEN supplied a record, THE decoder SHALL check exact byte type and
type-specific length before copying/decoding, then lexical depth/node/member/
string/number bounds before allocating the JSON tree, with no full-buffer
decode-first or stringify-first fallback.
Gate: tests/worker_accounting/test_protocol.py::test_bounds_precede_decode_and_conversion.

PAP-003 THE decoder SHALL reject duplicate/unknown keys, wrong schemas/types,
floats/nonfinite numbers, numeric bools, noncanonical encodings and unsupported
record/platform variants without accepting an arbitrary object or callback.
Gate: tests/worker_accounting/test_protocol.py::test_strict_shapes_and_canonical_records.

PAP-004 WHEN converting Windows or Linux supplied native counters, THE unit
SHALL enforce native widths, checked sum/multiplication and int64 ns bounds,
with Windows 100-ns and Linux 1000-ns units and Linux max(usage,user+system).
Gate: tests/worker_accounting/test_protocol.py::test_golden_units_and_native_maxima.

PAP-005 IF a supplied counter/component/sequence regresses, overflows or
underflows, THEN THE unit SHALL reject it without wrapping, saturation, coercion,
zero replacement or a changed accounting variant.
Gate: tests/worker_accounting/test_protocol.py::test_regression_overflow_underflow_and_bool.

PAP-006 THE unit SHALL use immutable exact correction/transform limits,
unchanged B=60/240 s, S=57/237 s, M=3 s and separate parent/byte bounds.
Gate: tests/worker_accounting/test_protocol.py::test_exact_lane_limits_and_no_override.

PAP-007 WHEN consuming a protocol transition, THE unit SHALL check the phase,
immutable attempt/job/object/platform/binding and separate sample/control
sequences before updating state; invalid evidence SHALL latch FAILED_HELD.
Gate: tests/worker_accounting/test_protocol.py::test_transition_identity_and_replay.

PAP-008 WHILE consuming supplied records, THE unit SHALL derive bounded sample
count/bytes/digest and timing consistency, require three matching spaced final
records after supplied drain, and never call an asserted timestamp an OS reading.
Gate: tests/worker_accounting/test_protocol.py::test_bounded_trace_and_final_consistency.

PAP-009 IF final evidence is unavailable, THEN THE unit SHALL preserve its exact
null/false unavailable variant, deny protocol eligibility and prevent later
records from repairing uncertainty or manufacturing a zero-valued final.
Gate: tests/worker_accounting/test_protocol.py::test_unavailable_is_not_final_zero.

PAP-010 WHEN a receipt/release acknowledgment is checked, THE unit SHALL bind
canonical receipt bytes, exact identities, counters/limits/digest/flags and
checked parent totals before protocol eligibility; final CPU>B SHALL always FAIL.
Gate: tests/worker_accounting/test_protocol.py::test_receipt_release_and_eligibility.

PAP-011 THE unit SHALL return only fixed bounded safe errors and a protocol-only
eligibility verdict with runtime_authorized=false; no supplied assertion or
well-formed digest SHALL confer containment, durability or publication authority.
Gate: tests/worker_accounting/test_protocol.py::test_safe_errors_and_forged_authority.

PAP-012 THE later implementation SHALL add exactly the two assigned new paths
and leave all worker/API/database/migrations/ops/module/admission/source-policy
and environment paths unchanged, with no CLI/native compile probe or package.
Gate: tests/worker_accounting/test_protocol.py::test_public_surface_and_exports.
