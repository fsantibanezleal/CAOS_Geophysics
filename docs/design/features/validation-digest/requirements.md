# Read-only validation digest requirements

VD-001 THE digest SHALL verify completed command receipts and seals without executing commands, capturing current runtime inventories, or modifying evidence.
Gate: tests/ops/test_validation_digest.py::test_read_only_digest.

VD-006 WHERE a digest output is requested, THE reader SHALL create a new external JSON file exclusively and refuse to overwrite existing output.
Gate: tests/ops/test_validation_digest.py::test_output_is_exclusive.

VD-002 IF report, fingerprint, predecessor, receipt or sealed evidence disagrees, THEN THE digest SHALL refuse instead of reporting acceptance.
Gate: tests/ops/test_validation_digest.py::test_tampered_evidence_refused.

VD-003 THE digest SHALL return bounded structured counts and the first failed or refused node, with no raw logs by default.
Gate: tests/ops/test_validation_digest.py::test_failure_and_blocked_digest.

VD-004 WHERE explicit failure-tail inspection is requested, THE digest SHALL expose at most 4096 bytes per stream from only the first failed command.
Gate: tests/ops/test_validation_digest.py::test_explicit_bounded_tail.

VD-005 THE digest SHALL distinguish retained command evidence from current-source, scientific, generated-output and deployment acceptance.
Gate: tests/ops/test_validation_digest.py::test_read_only_digest.
