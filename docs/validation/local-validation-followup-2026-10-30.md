# Local validation follow-up : 2026-10-30

This follow-up records checks run after the earlier local-science receipt. They ran in the direct CAOS_Geophysics checkout at base `0cf38910ff69a90bf895ea1fde417bf62c049068` with an uncommitted working tree. The earlier receipt remains tied to its recorded revision; this file does not retroactively change its evidence.

## Completed checks

- Fresh-kernel execution passed for all 10 newly added method-comparison notebooks: MT, ERT, seismic, joint inversion, and learning, in English and Spanish. The runner exited 0 and retained execution outputs under `${CAOS_TEMP_ROOT}\caos-notebooks-current-2026-10-30`; repository notebook sources were not rewritten by check mode.
- `\.venv-api\Scripts\python.exe -m pytest tests/api/test_metadata.py -q` passed all 14 tests, including the StationXML companion-metadata rejection path.

## Expanded local validation : 2026-10-30

The expanded checks below ran in the same direct checkout and dirty working tree. They are local evidence only.

- Notebook replay: the full fresh-kernel run executed all 62 English/Spanish notebooks. It initially reported four stale outputs and no execution errors. Three saved outputs were refreshed (held-out learning and the English/Spanish M12 null-space figures); the null-space legends were moved to lower-right whitespace and the English reference label now names the straight-ray L2 baseline. A fresh recheck of all four affected notebooks, including the FWI control, passed. Combined with the other 58 passing notebooks from the full run, all 62 currently pass execution/output checks.
- Focused Python regressions passed: 30 tests across the new internal-name gate, convergence-ledger parser, and notebook runner.
- Product CI source gates passed: artifact inventory (20 truths, 120 experiments, 348 method results), M13 asset integrity, bilingual docs matrix (13 methods/62 notebooks), structural M01-M13 method matrix (13/13), deploy-place policy (VPS only), contract catalog, reproducible OpenAPI, API schema checks (31 operations/53 schemas), internal-name gate, README area index, template-residue, single-origin, and content standards. The deterministic readiness record was regenerated and then verified against 20 cases, 120 variants, and 120 present artifacts.
- `npm run build` passed. Vite warned that two chunks exceed 500 kB after minification; the output was still produced successfully.
- `npm test` did not pass: 380 passed, 36 failed, and 23 skipped. The failed M04 and M11 custody suites require the exact retained external controls; the historical CAOS_MANAGE paths for those controls are absent on this machine. No substitute fixture was generated. Full frontend acceptance remains open.
- The convergence ledger now passes its structural/hash check and remains at 1 pass, 1 failed, 17 unresolved requirements. The 13-method structural inventory is not scientific acceptance.

## Still open

- These focused checks do not change scientific acceptance. The current convergence ledger remains structurally valid at 1 pass, 1 failure, and 17 unresolved requirements; the 13-method matrix still does not assert scientific acceptance.
- The fixture-dependent frontend suite, complete release matrix, VPS host qualification, deployment, and post-deployment verification remain open. No host state or release was changed.

The machine-readable command and result record is `local-validation-followup-2026-10-30.json`.
