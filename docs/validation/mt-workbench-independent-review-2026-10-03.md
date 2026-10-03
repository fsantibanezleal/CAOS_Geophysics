# Independent local MT workbench review

Date: 2026-10-03. Main independently reviewed the MT frontend contracts, client, real-worker harness and selected scientific captures, then checked out a separate detached review tree at `3bd0e8757cd0a228c06fcb1afd20e011ebd179bf`. No concurrent frontend tree, existing evidence, private original, production service or environment was overwritten. PR #111's later documentation-only handoff does not change the tested frontend code.

The explicit read-only backend was `59f46c5a945531e573ae6db611a1f860237e3ba5`, with the existing isolated online-MT interpreter. The reviewer installed only this detached frontend's ignored lockfile dependencies. `npm ci` reported 133 audited packages and zero advisories at execution. This is an installation-time report, not a complete security audit.

## Executed independent gates

- `npm test -- --reporter=dot`: 94 tests in 17 files pass, 3.68 s.
- `npm run build:single-origin`: TypeScript and single-origin build pass; Vite 12.65 s. Existing large-chunk warning remains; no computation occurs in the build.
- With `GEOPHYSICS_MT_QA_ENABLE=isolated-test-only`, `npx playwright test --config playwright.mt.config.ts --reporter=line`: five tests pass, 2.4 min. Actual authenticated originals, migrated database and separate worker are used, not intercepted scientific responses.
- With that opt-in unset, the same command: one closed-admission test passes, four enabled-only scientific cases intentionally skip, 6.8 s. The actual API refuses submission with `host_admission_pending`; the UI is disabled.

The enabled run covers original halfspace and noisy layered data, actual changes with beta/thickness/seed, immutable request identity, six downloaded scientific bundles independently re-imported by the backend, pointer/keyboard/zoom/linked selection, EN/ES light/dark desktop/phone scientific views, actual measured cl061 QC-only, malformed-job failure and queued cancellation. The response verifier checks forward curves, exported-prediction residual identity, objective/WRMS normalization, model/seed/interval identities and bounded stored ZIP members. Passing these checks is not calibrated uncertainty, model uniqueness or field recovery.

## Pinned private receipts

The detached review tree retains ignored `frontend/node_modules/.mt-qa/evidence/` outputs, separate from the author's evidence. They contain only this isolated test's data; no private user dataset is published here.

| Receipt | SHA-256 |
| --- | --- |
| Enabled run | `3430fa95447da2081ddf1a3b287d0df7e1d7e0bb47bed6402c64a0a4b114c34d` |
| Default-closed run | `bf0bb65ac1cecb568d4763ea0eae758497b31848c8b841c6b668342317cae853` |

The enabled receipt reports five passed tests and zero browser errors, and records exact backend code, output and screenshot hashes. Independent visual inspection covered cl061 full-tensor scores in English/dark at 1600 pixels, signed complex residuals with a common symmetric scale at 1600 pixels, and Spanish/light 390-pixel imposed-layer geometry and exact values. The shared CAOS shell supplies fonts/themes/navigation; science-specific plot controls do not establish user aesthetic acceptance.

## Limits and integration

M05 is full-tensor QC, not inversion. M06 fits XY in an imposed one-/two-layer model, retains frozen frequency holdout and unfitted -YX validation, and reports conditional bootstrap rather than a geological posterior. cl061 fails its necessary tensor screen and has no inverse result. Scientific result state is removed on failure, cancellation or session/identity changes.

This is pinned Chromium/Windows loopback evidence, not Linux resource admission, public HTTPS/browser evidence, complete M01-M13 acceptance, a main release or deployment. Actual ML-VPS disk admission remains failed at 29.42% versus the unchanged 30% requirement. Online flags remain closed by default. Backend/corrected canonical integration and broader release gates are independent; no public origin or deployment changed during this review.
