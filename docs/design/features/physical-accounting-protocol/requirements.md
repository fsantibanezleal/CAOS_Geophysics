# Pure accounting protocol requirements

Date: 2026-10-03. Pure unit implemented under MAIN exact approval of 2c94da4;
see [approval](approval.md) and [actual local evidence](implementation-evidence.md).
Parent directional acceptance is not native implementation or OS/context authorization.
Read [research](research.md), [design](design.md), [contracts](contracts.md),
[validation](validation.md), [tasks](tasks.md) and [review packet](review-packet.md).
All twelve pure gates exist and pass locally; independent MAIN review/rerun is
still required before develop promotion. All fifteen actual-platform gates remain
CLOSED/NOT_RUN.

| ID | Requirement | Gate |
| --- | --- | --- |
| PAP-001 | THE pure unit SHALL expose deterministic in-memory protocol, conversion and state operations only; it SHALL NOT launch processes, inspect sources, read clocks, perform file/network/OS I/O, or activate runtime admission. | `tests/worker_accounting/test_protocol.py::test_pure_boundary_and_no_authority` |
| PAP-002 | WHEN supplied a record, THE decoder SHALL validate exact byte type and type-specific length before copying or decoding, then enforce lexical depth/node/member/string/number bounds before allocating the JSON tree; it SHALL NOT use decode-first or stringify-first fallback. | `tests/worker_accounting/test_protocol.py::test_bounds_precede_decode_and_conversion_serialization` |
| PAP-003 | THE decoder SHALL reject duplicate/unknown keys, wrong schemas/types, floats/nonfinite numbers, numeric booleans, noncanonical encodings and unsupported record/platform variants without accepting arbitrary objects or callbacks. | `tests/worker_accounting/test_protocol.py::test_strict_shapes_and_canonical_records` |
| PAP-004 | WHEN converting Windows or Linux supplied native counters, THE unit SHALL enforce native widths, checked sum/multiplication and int64 nanosecond bounds, with Windows 100-ns and Linux 1000-ns units and Linux max(usage,user+system). | `tests/worker_accounting/test_protocol.py::test_golden_units_and_native_maxima` |
| PAP-005 | IF a supplied counter, component or sequence regresses, overflows or underflows, THEN THE unit SHALL reject it without wrapping, saturation, coercion, zero replacement or changing the accounting variant. | `tests/worker_accounting/test_protocol.py::test_regression_overflow_underflow_and_bool` |
| PAP-006 | THE unit SHALL use immutable exact correction/transform limits: B=60/240 s, S=57/237 s, M=3 s, and separate parent/byte bounds. | `tests/worker_accounting/test_protocol.py::test_exact_lane_limits_and_no_override` |
| PAP-007 | WHEN consuming a protocol transition, THE unit SHALL check phase, immutable attempt/job/object/platform/binding and separate sample/control sequences before updating state; invalid evidence SHALL latch FAILED_HELD. | `tests/worker_accounting/test_protocol.py::test_transition_identity_and_replay_entire_phase_table` |
| PAP-008 | WHILE consuming supplied records, THE unit SHALL derive bounded sample count/bytes/digest and timing consistency, require three matching spaced final records after supplied drain, and never call an asserted timestamp an OS reading. | `tests/worker_accounting/test_protocol.py::test_bounded_trace_and_final_consistency_exact_trace_caps` |
| PAP-009 | IF final evidence is unavailable, THEN THE unit SHALL preserve its exact null/false unavailable variant, deny protocol eligibility and prevent later records from repairing uncertainty or manufacturing a zero-valued final. | `tests/worker_accounting/test_protocol.py::test_unavailable_is_not_final_zero_held_diagnostic` |
| PAP-010 | WHEN a receipt/release acknowledgment is checked, THE unit SHALL bind canonical receipt bytes, exact identities, counters/limits/digest/flags and checked parent totals before protocol eligibility; final CPU>B SHALL always fail. | `tests/worker_accounting/test_protocol.py::test_receipt_release_and_eligibility_b_plus_one` |
| PAP-011 | THE unit SHALL return only fixed bounded safe errors and a protocol-only eligibility verdict with runtime_authorized=false; supplied assertions or well-formed digests SHALL NOT confer containment, durability or publication authority. | `tests/worker_accounting/test_protocol.py::test_safe_errors_and_forged_authority_constructor_variants` |
| PAP-012 | THE pure unit SHALL expose only the approved public protocol surface and SHALL NOT add a CLI, native compile probe, package, profile, OS, controller or runtime-admission interface. | `tests/worker_accounting/test_protocol.py::test_public_surface_and_exports` |
