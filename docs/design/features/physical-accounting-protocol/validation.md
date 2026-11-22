# Pure accounting protocol adversarial validation

The checks below execute the implementation's focused protocol tests through
named adversarial entry points. They validate the bounded, synthetic protocol
unit only. They do not establish that an OS process was contained or measured,
that resource limits were enforced by a host, or that runtime admission is safe.

| requirement | adversarial check | gate |
| --- | --- | --- |
| PAP-001 | Plant hostile platform and method inputs; verify caller assertions never grant runtime authority or invoke OS-facing behavior. | `tests/adversarial/test_physical_accounting_protocol_adversarial.py::test_adversarial_pap_001_authority_boundary` |
| PAP-002 | Plant oversized and hostile byte-like inputs; verify type, size, lexical and serialization limits reject before decode, conversion or digest work. | `tests/adversarial/test_physical_accounting_protocol_adversarial.py::test_adversarial_pap_002_preallocation_bounds` |
| PAP-003 | Plant duplicate, unknown, malformed, noncanonical, wrong-type and unsupported record fields; verify strict decoding rejects each variant. | `tests/adversarial/test_physical_accounting_protocol_adversarial.py::test_adversarial_pap_003_strict_records` |
| PAP-004 | Plant maximum-width Windows/Linux counters and boundary values; verify independently fixed unit conversion and overflow behavior. | `tests/adversarial/test_physical_accounting_protocol_adversarial.py::test_adversarial_pap_004_counter_arithmetic` |
| PAP-005 | Plant regressing components, exhausted sequences, booleans and overflow/underflow values; verify rejection without repair or wrapping. | `tests/adversarial/test_physical_accounting_protocol_adversarial.py::test_adversarial_pap_005_invalid_counters` |
| PAP-006 | Plant modified and out-of-range lane limits; verify exact frozen limits cannot be overridden. | `tests/adversarial/test_physical_accounting_protocol_adversarial.py::test_adversarial_pap_006_frozen_limits` |
| PAP-007 | Plant illegal phase transitions, changed identities and repeated/exhausted sequence numbers; verify FAILED_HELD remains sticky. | `tests/adversarial/test_physical_accounting_protocol_adversarial.py::test_adversarial_pap_007_transition_replay` |
| PAP-008 | Plant oversized traces, bad digest/count/timing and inconsistent final records; verify bounded accumulation and final consistency checks. | `tests/adversarial/test_physical_accounting_protocol_adversarial.py::test_adversarial_pap_008_trace_and_final` |
| PAP-009 | Remove or mutate final evidence, then submit a later plausible record; verify unavailable state cannot be repaired into success or zero. | `tests/adversarial/test_physical_accounting_protocol_adversarial.py::test_adversarial_pap_009_unavailable_is_sticky` |
| PAP-010 | Plant altered receipts/releases and CPU at B+1; verify identity/digest binding and the strict budget boundary. | `tests/adversarial/test_physical_accounting_protocol_adversarial.py::test_adversarial_pap_010_receipt_and_budget` |
| PAP-011 | Plant forged eligibility, unsafe error codes and hostile object variants; verify safe bounded errors and no authority escalation. | `tests/adversarial/test_physical_accounting_protocol_adversarial.py::test_adversarial_pap_011_no_forged_authority` |
| PAP-012 | Inspect public exports and constructors while attempting to expose CLI/native/runtime controls; verify the approved pure interface only. | `tests/adversarial/test_physical_accounting_protocol_adversarial.py::test_adversarial_pap_012_public_surface` |
