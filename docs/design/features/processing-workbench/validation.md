# Selected-project processing workbench local validation

Date: 2026-10-03. Local engineering evidence only; no merge, deployment, release or M01-completion assertion.

## Measured gates

- `cd frontend; npm test -- --reporter=dot`: 82 tests across 16 files pass, including gravity receipt/result/bundle negatives, identity binding, CSRF/abort/failures, optional explicit sigma, and three PR100 handoff controls for EDI receipt and immutable M05/M06 job/eligibility shapes. MT controls are schema fixtures, not scientific output or browser MT execution evidence.
- `npm run build:single-origin`: TypeScript and Vite pass. The existing large-chunk advisory remains; no scientific computation runs in build.
- `npm run build`: static frontend build and five generated route entrypoints pass after syncing reviewed develop 59437a6.
- Ruff on `tests/ui/processing_devserver.py`, `scripts/check_content_standards.py`, `check_template_residue.py`, `check_ci_budget.py`, `check_artifacts.py` and `check_phase_assets.py` pass. `check_sdd_convergence.py` accepts ledger structure while retaining one failed and 18 unresolved product requirements; it is not final scientific acceptance. Owner convergence/plan files were not edited by this feature.
- `npx playwright test --config playwright.processing.config.ts --reporter=line`: all five real API/worker tests pass. No successful job/result/eligibility response is mocked. A network abort only tests poll failure/recovery. Actual owner upload, API row validation, immutable admission, worker child, polled result and authenticated export run locally against a migrated isolated SQLite/private root.
- The independent five-station control `[1,2,3,4,100]` mGal with sigma `[0.1,0.1,0.1,0.1,0.1]` retains exact arrays; submitted threshold 1 returns S1/S5 flagged, median 3 and MAD 1. Queued cancellation has no result/export. Sigma 0 is rejected by dataset creation. Constant observations fail in the actual worker with `degenerate_mad_scale`; they are not displayed as success.
- The actual downloaded processing ZIP passes browser original-member SHA-256/shape/identity/semantics checks and the independent `app.bundle.verify_bundle` Python re-import verifier. Original raw CSV is not exported.
- Local screenshots cover EN/ES, light/dark, 1280x800, 1600x900, 2560x1440 and 390x844, plus returned-score and phone observed-chart views (21 PNGs). Inspected desktop and phone renders after correcting absolute-coordinate padding and mobile flex overflow. Tests check six navigation links, desktop document fit, width fit, instrument area, phone chart reachability/no overlap, keyboard station selection, pointer/brush/pan/reset, paged station table and real touchscreen selection.
- Direct selected-project hydration and actual navigation/back work. Guest ownership does not reveal private observations; logout/authorization loss clears them. Ordinary transport errors retain actionable controls and expose retry.

Generated evidence and downloaded owner-only test ZIP remain under ignored `frontend/node_modules/.processing-qa/evidence/`, not a release/public asset. The API interpreter is read-only. QA creates no canonical artifacts and edits no backend application code.

## Self-review and scope

Reviewed scientific non-claims, owner/dataset/job/request/hash bindings, terminal-state consistency, unsafe-request CSRF, stale-read abort/discard, stopped polling on terminal outcome, absence of result for failed/cancelled work, and bounded ZIP members before download. Observation/sigma readout/table preserve JavaScript number precision; chart ticks are presentation-only. Project selection uses the existing router's query state, not a new route. Shared shell tokens/fonts and six routes remain; the global footer now accommodates actual owner observations instead of labelling every view synthetic.

MT record compatibility follows PR100's stable contract: EDI envelopes are awaiting full-tensor QC, not parsed observations; M05 parameters are empty and success is QC-only; M06 requires immutable same-dataset QC identity, imposed layer bounds, 20..40 members and seed. Scratch estimates remain distinct from measured usage. Existing MT jobs participate in active-job polling/cancellation without a gravity result/export adapter. Unknown/future versions fail closed. PR100 backend code is not copied/merged here. M05/M06 scientific submit, result views and MT bundle verification need separate integration validation following owner review; default host admission stays closed.

This is the scoped frontend contribution to #74/#75, not closure of full correction/inversion/evaluation/export acceptance. No predicted/residual/model arrays are invented for flags; no station is excluded; no data normalization or correction occurs in the browser. Actual-host resource/headroom/cancel/crash benchmarks and integration remain owner/scientific backend gates.

Persistence: implementation commit `6656c82`; reviewed-develop sync `7586c22`; draft [PR #103](https://github.com/fsantibanezleal/CAOS_Geophysics/pull/103) targets develop. PR100 code was not merged; no develop/main merge or deploy was performed. The manually requested trunk-style CI run is a repository guard, not scientific/host admission evidence.
