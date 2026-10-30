# Shell 0.19.9 adoption validation

Date: 2026-10-30

## Release identity

- Package: `@fasl-work/caos-app-shell@0.19.9`, exact product pin.
- Tag: `v0.19.009`; merged shell main commit `6adf19725182f0471fe36d419366f263ed19b424`.
- npm integrity: `sha512-U+Dkp5oNh1RNCkBXs2UU4tIf6ldFD6rgLFwQreKCXj7QqEjPws9jSnqw4X7/moxeu/ilXurQ03f6AXU0Ae80pQ==`; shasum `2b13a8c3dd8887ed528bf30184cfbb7e058eba02`.
- Shell main workflow 41009479929 passed build/tests, guards, and browser/G15 jobs. A clean clone of the tag passed `npm ci`, `npm test` (297 passed), and `npm pack --dry-run`; the packed output matched the registry integrity.

## Product checks

- Exact shell pin is present in `frontend/package.json` and lockfile; the measured gate and focused route assertions expect 0.19.9.
- `npm run build`: passed (1,939 modules transformed; Vite emitted its existing large-chunk advisory).
- `npx vitest run src/test/foundation-routes.test.ts`: 6 passed.
- `npm run gate` with output under `D:\_Temp\geophysics-shell0199-gate-20261030`: passed, 1,442 measured states, 157 captures, no waivers or failures. The 768 × 1024 Spanish dark workbench capture was visually inspected; the workbench and controls fit the viewport. This is integration evidence, not owner design acceptance.
- The 0.19.9 release fixes the ordinary `CaseWorkbench` G6 instrument marker (shell defect 48).

## Frontend evidence and limits

The fixture-backed Vitest run completed with 429 passed, 12 skipped, and two suites failing during setup. The missing inputs are the retained selected-final magnetic extraction control and the owned-custody magnetic browser-control file. Those exact M04 controls are unavailable at their recorded paths; no replacement fixture was fabricated. The earlier joint-result timeout no longer reproduces after raising that single test's timeout from 30 to 120 seconds; the fixture-backed full run completed in 29.22 seconds.

Independent of these frontend setup failures, the retained 24-case solver output explicitly records `scientific_precision_accepted=false`, `field_eligible=false`, and `public_activation=false`. `scripts/check_sdd.py` reports 538 live requirements and 27 planned requirements/gates not built, including physical worker accounting and the single-VPS service. The method matrix is structural only (`scientific_acceptance=false`). `scripts/check_manuscripts.py` fails because `product.json` has no technical-report declaration; the existing identifiability study explicitly says it is not a peer-reviewed manuscript. No DOI or publication is claimed.

## Release boundary

Template pin is `CAOS_PRODUCT_TEMPLATE 0.13.001`. The 0.19.9 adoption and shell gate do not accept scientific methods, field-data claims, API/worker admission, manuscript/Zenodo completion, actual-host capacity, or the product as a whole. The only app origin remains `https://geophysics.ml.fasl-work.com/`; the active release remains `0.04.001`. No replacement was deployed. Preserve the active release and two rollback releases until every approved acceptance gate passes. GitHub Pages is disabled for this product.
