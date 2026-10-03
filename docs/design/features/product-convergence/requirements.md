# Product convergence ledger requirements

Date: 2026-10-03. Parent: the approved replacement product SDD, R-018.

PC-01 THE ledger SHALL enumerate every current product EARS requirement exactly once and retain its exact declared verification text. Gate: `tests/test_sdd_convergence.py::TestConvergence::test_requirement_coverage_and_gate_drift`.

PC-02 IF a requirement lacks a passed, source-bound gate receipt, THEN the ledger SHALL retain an unresolved or failed verdict rather than infer success from file presence, historical checkboxes or CI. Gate: `tests/test_sdd_convergence.py::TestConvergence::test_pass_requires_checked_evidence`.

PC-03 WHEN release verification is requested, THE checker SHALL fail unless every product requirement passes and the deployment is the single approved VPS service. Gate: `tests/test_sdd_convergence.py::TestConvergence::test_release_rejects_partial_and_duplicate_deployment`.

PC-04 IF evidence escapes the repository, changes bytes, or names a missing executable gate, THEN the checker SHALL reject the ledger. Gate: `tests/test_sdd_convergence.py::TestConvergence::test_evidence_integrity_and_gate_existence`.

PC-05 THE status review SHALL separate the legacy main release, merged replacement development and interrupted protected work, with current revision/PR/CI evidence and explicit remaining work. Gate: `scripts/check_sdd_convergence.py::main` and `docs/design/plan-status-2026-10-03.md`.
