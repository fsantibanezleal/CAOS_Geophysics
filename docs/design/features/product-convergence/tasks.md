# Convergence ledger tasks

- [x] PC-01 through PC-05: write the feature contract before checker implementation.
- [x] PC-01, PC-02, PC-04: implement strict ledger/evidence validation and adversarial local tests.
- [x] PC-03: implement a separately failing release mode, without changing production.
- [x] PC-05: persist current scoped plan/branch/CI/remaining-work review and distinguish historical tasks.
- [ ] Validate locally, review, commit/push and promote the scoped unit to develop. Product release acceptance stays open.

Local gate record, 2026-10-03: ten stdlib/unittest and pytest convergence tests pass, including evidence/source/output tampering, missing gate, requirement drift, incomplete method table, artifact substitution, self-reference and duplicate-origin controls. The unchanged API regression suite passes 68 tests with one upstream TestClient deprecation warning. Ruff, artifact/phase/template/content guards, CI budget and staged whitespace checks pass. Structural ledger validation passes and the separate release command fails as required, with 18 unresolved requirements and one failed complete-method requirement. No receipt is invented to promote these product verdicts.
