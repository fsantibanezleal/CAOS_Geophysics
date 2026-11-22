# Shell 0.19.8 adoption validation

Date: 2026-10-30

## Release identity

- Package: `@fasl-work/caos-app-shell@0.19.8`, exact product pin.
- Tag: [`v0.19.008`](https://github.com/fsantibanezleal/CAOS_APP_SHELL/releases/tag/v0.19.008).
- Tested `main` commit and npm `gitHead`: `7f89f5350e46d2a4ea396b3a72754802fdf82fa3`.
- npm integrity: `sha512-uHndhUiL+b9VlMWI8ndMbUzrHQY1XYKYA3j0xya9yQ0kiIT4QNOizAg9TQ6wVwXIH9PE6NDft50FM0hYZDa58w==`.
- Shell main workflow 41004044550 passed build and tests, guards, browser tests, and G15. Source G15 measured 249/249 cases with zero failures.

## Product checks

- `npm ci`: passed, 134 packages audited, zero vulnerabilities.
- `npm run build`: passed on the exact shell package.
- `npx vitest run src/test/foundation-routes.test.ts`: 6 passed after the exact shell pin assertions were updated.
- `npm run gate` with `GEOPHYSICS_GATE_OUTPUT` set to an absolute scratch path outside the checkout: passed, 1,442 measured states. The run captured 157 screenshots. The 768 by 1024 Spanish dark workbench capture was visually inspected; content and controls remain within the viewport.
- `scripts/check_notebooks.py`: passed, 60 bilingual notebooks are mirrored, ordered, annotated, and clean.
- A fresh-kernel replay executed all 60 notebooks. It found three stale figure outputs and no execution errors. The English and Spanish traveltime/FWI figures and the Spanish ERT inversion figure were refreshed using `scripts/run_notebooks.py`; three focused fresh-output checks then passed. The other 57 notebooks passed in the original full replay.

## External custody fixtures and frontend suite

The external data workspace contains the retained 24-case synthetic joint intake matrix, the 24-case solver output matrix, a native state-instrument export, the maximum-resource output, and a failed Python API custody export. All three producer-source hashes in the solver matrix match this product checkout. The solver matrix records 24 completed CLI workflows, but `scientific_precision_accepted=false`, `field_eligible=false`, and `public_activation=false`; these are artifact/import and adverse-control fixtures, not field evidence or accepted inversions. With `GEOPHYSICS_JOINT_MATRIX_FIXTURE` and `GEOPHYSICS_JOINT_CUSTODY_API_RECEIPT` pointing to the retained intake/API artifacts, `joint-input.test.ts` passed 31/31.

The retained selected instrument exposed an incorrect test assertion: a gravity-only candidate was compared with the final coupled result. The assertion now checks the coupled selected frame against the final gravity and magnetic response arrays. The large-hash admission harness now calculates the receipt byte count using the same exclusions as the importer. Against the retained native output and maximum-resource fixtures, the four joint importer/component/queue/profile suites passed 18 tests (5 optional skips), and the hash-admission suite passed 10/10. The complete frontend suite then reported **429 passed, 12 skipped, 0 failed tests**; two magnetic suites fail during setup because the exact retained M04 selected-final and browser-control files recorded in CAOS_MANAGE no longer exist at their recorded paths. No replacement fixture was fabricated. Those missing controls keep complete frontend acceptance open; the solver matrix's explicit scientific-precision refusal independently keeps scientific acceptance open.

## Release boundary

The product SDD, changelog, package manifest, lockfile, gate version assertion, and foundation test now name shell 0.19.8. The temporary PlotCard caption override was removed. The product shell gate passing is a shared-shell integration result only; it does not accept the scientific methods, field-data validity, manuscript/Zenodo records, API/worker admission, or full product UI.

No replacement was deployed. The sole application origin remains `https://geophysics.ml.fasl-work.com/`; its recorded active release is still `0.04.001`. Preserve it and two rollback releases until all approved product gates pass. GitHub Pages remains disabled for this product.
