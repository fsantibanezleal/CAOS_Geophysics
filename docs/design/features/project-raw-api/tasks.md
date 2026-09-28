# Authenticated project and raw-asset API tasks

- [x] R-API-01, R-API-02: pin the documented FastAPI Users stack; migrate users/tokens; wire SMTP callbacks, cookie auth, CSRF and persistent rate limits.
- [x] R-API-03, R-API-10: migrate and implement owner-scoped project CRUD; reject schema drift at startup; keep jobs absent.
- [x] R-API-04 through R-API-07: implement staged immutable uploads, envelope/physical metadata checks and transactional quota. The original R-API-11 orphan sweep is superseded by the fail-closed review follow-up below.
- [x] R-API-08, R-API-09: implement verifiable export, permanent deletion, receipts and API-managed backup purge.
- [x] R-API-01 through R-API-11: run every exact named test gate in `requirements.md`; `python -m pytest tests/api --tb=short` passed 29 tests on 2026-09-27. This includes the negative ownership, CSRF/origin, rate, malformed metadata, MIME, size, quota, tamper, migration, interrupted-file and no-job checks.
- [x] Run repository guards: `ruff check data-pipeline tests app`, `check_artifacts.py`, `check_content_standards.py`, `check_template_residue.py`, `check_ci_budget.py` and `git diff --cached --check` all passed locally.

Convergence: the API unit's named gates pass locally. With `FWI_RECOVERY_ARTIFACTS=data/derived/v2`, the untouched scientific regression suite passes 134 tests. A separate fresh-CUDA run of the existing `FWI_FAULT` reference test fails its fixed expected status and produced opposite status mismatches on two runs. That numerical gate is outside this branch and remains unresolved; no solver, frontend or deployment acceptance is claimed. External encrypted-backup restoration against deletion receipts also remains a deployment blocker for its owner.

## Targeted review follow-up (2026-09-28)

- [x] R-API-11: replace startup sweeps with a read-only fail-closed audit; test orphan, abandoned transfer, interrupted deletion before/after receipt commit, uncertain upload commit and older-DB restoration without byte loss.
- [x] R-API-09: require exact owned-file preflight and durable deletion receipt with asset IDs/hashes/sizes before unlinking verified asset files.
- [x] R-API-12: implement the explicit owner-only source/asset view, redact storage paths from JSON and export, reject internal key drift, and test the response contract.
- [x] R-API-13: separate private-storage attestation from public mirroring rights, migrate without inventing historical attestations, and test rights-negative cases.
- [x] R-API-09, R-API-11 through R-API-13: rerun API/security/migration tests, repository guards and review staged scope before commit/push.
- [ ] INT-API-FE-01: frontend mirror/adapter parity remains blocked and is not part of this branch.

Review gate receipt: `python -m pytest tests/api --tb=short` passed 42 tests; the focused auth/ownership/rights/view/security subset passed 7 tests. Both runs emitted one Starlette TestClient deprecation warning, not a test failure. `ruff check data-pipeline tests app`, `check_artifacts.py`, `check_content_standards.py`, `check_template_residue.py`, `check_ci_budget.py`, `pip check` and staged-diff whitespace/scope review passed. No API job route, frontend change or deployment was added.
