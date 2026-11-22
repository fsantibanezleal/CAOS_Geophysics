# Validation digest adversarial checks

The digest is a read-only presentation of retained command receipts. These tests plant incomplete or tampered evidence and assert that the result stays bounded and refuses false acceptance.

| requirement | adversarial check | gate |
|---|---|---|
| VDG-001 | Plant completed receipts and monitor command execution and evidence writes; require a read-only digest. | `tests/ops/test_validation_digest.py::test_adversarial_read_only_digest` |
| VDG-002 | Pre-create the requested output file; require exclusive creation to refuse overwriting it. | `tests/ops/test_validation_digest.py::test_adversarial_output_is_exclusive` |
| VDG-003 | Alter sealed evidence or predecessor identity; require refusal rather than an acceptance summary. | `tests/ops/test_validation_digest.py::test_adversarial_tampered_evidence_refused` and `tests/ops/test_validation_digest.py::test_adversarial_predecessor_binding_refused` |
| VDG-004 | Plant a failed or unfinished command; require bounded counts, first-failure identity and no raw-log dump. | `tests/ops/test_validation_digest.py::test_adversarial_failure_and_blocked_digest` and `tests/ops/test_validation_digest.py::test_adversarial_unfinished_report_refused` |
| VDG-005 | Plant oversized and multiple failure tails; require at most 4096 bytes from only the first failure. | `tests/ops/test_validation_digest.py::test_adversarial_explicit_bounded_tail` |
| VDG-006 | Supply retained receipts without current-source or deployment evidence; require the digest not to imply release acceptance. | `tests/ops/test_validation_digest.py::test_adversarial_read_only_digest` |
