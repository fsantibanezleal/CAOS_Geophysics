# Read-only validation digest requirements

| ID | EARS requirement | Named failing gate |
|---|---|---|
| VDG-001 | THE digest SHALL verify completed command receipts and seals without executing commands, capturing current runtime inventories, or modifying evidence. | `tests/ops/test_validation_digest.py::test_adversarial_read_only_digest` |
| VDG-002 | WHERE a digest output is requested, THE reader SHALL create a new external JSON file exclusively and refuse to overwrite existing output. | `tests/ops/test_validation_digest.py::test_adversarial_output_is_exclusive` |
| VDG-003 | IF report, fingerprint, predecessor, receipt or sealed evidence disagrees, THEN THE digest SHALL refuse instead of reporting acceptance. | `tests/ops/test_validation_digest.py::test_adversarial_tampered_evidence_refused` and `tests/ops/test_validation_digest.py::test_adversarial_predecessor_binding_refused` |
| VDG-004 | THE digest SHALL return bounded structured counts and the first failed or refused node, with no raw logs by default. | `tests/ops/test_validation_digest.py::test_adversarial_failure_and_blocked_digest` and `tests/ops/test_validation_digest.py::test_adversarial_unfinished_report_refused` |
| VDG-005 | WHERE explicit failure-tail inspection is requested, THE digest SHALL expose at most 4096 bytes per stream from only the first failed command. | `tests/ops/test_validation_digest.py::test_adversarial_explicit_bounded_tail` |
| VDG-006 | THE digest SHALL distinguish retained command evidence from current-source, scientific, generated-output and deployment acceptance. | `tests/ops/test_validation_digest.py::test_adversarial_read_only_digest` |
