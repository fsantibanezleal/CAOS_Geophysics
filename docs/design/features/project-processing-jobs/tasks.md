# Bounded project processing and CPU worker tasks

- [x] R-PJ-01, R-PJ-02: migrate dataset metadata; add strict bounded gravity parser, immutable derived file, hash verification and negative tests.
- [x] R-PJ-03, R-PJ-09: expose typed method verdicts, owner isolation and explicit no-solver/non-scientific-QC boundary.
- [x] R-PJ-04: migrate processing jobs, canonical request hash and transactional admission with queue/account bounds.
- [x] R-PJ-05, R-PJ-06 local gate: add isolated worker/compute entry points, real flag-only numerical control, cancellation, resource/time/failure handling and interrupted-worker recovery. Actual-host benchmark remains open below.
- [x] R-PJ-07: add owner-only result/export and strict bundle round-trip, semantic-parity and tamper tests.
- [x] R-PJ-08: integrate exact derived-file project deletion and read-only startup audit.
- [x] Run local API/security/migration tests, focused method/limit tests, Ruff and repository guards; review scoped paths for the new task branch.
- [ ] INT-PJ-INGEST-01: independently review parser parity with the offline ingestion contract before claiming a shared scientific dataset schema.
- [ ] Product R-006, M01-M13, full R-011 and host release gates remain open; no solver, frontend or deployment acceptance is claimed by this unit.

Local convergence evidence (2026-09-28): all 67 `tests/api` cases pass, including every exact R-PJ-01 through R-PJ-09 named gate. `ruff check data-pipeline tests app`, `pip check`, `check_artifacts.py`, `check_content_standards.py`, `check_template_residue.py`, `check_ci_budget.py` and staged diff whitespace checks pass. The repository has no `scripts/check_sdd.py`, so the requirement-to-test mapping above was reviewed against collected test names rather than claiming that unavailable guard ran. These checks do not replace the open scientific, integration, frontend and actual-host gates.
