# Frontend foundation design

Status: implementation design under the approved product SDD. This document authorizes only the frontend foundation; it does not activate the new service or supersede live 0.04.001 evidence.

## Route and build boundary

`frontend/src/lib/routes.json` is the one ordered six-route declaration. A typed `routes.ts` exports it to `AppShell` and maps IDs to existing page components. The static entrypoint generator reads the same JSON. A wildcard redirects to App and is not a seventh public destination. The existing pages and scientific views remain intact.

Default Vite mode is `legacy`. It retains the current relative static asset base, existing Pages-subpath detection and copied route entrypoints for both live static origins. Explicit `single-origin` mode selects a root asset base and router basename `/` and skips duplicated entrypoints. The single-origin build is an integration input for later API/host work; this branch does not serve it. Artifact loading uses the same deployment mode so the legacy JSON release continues to hydrate. No automatic hostname inference decides the future mode.

## Typed evidence and transport seam

The new contract module mirrors the product SDD's snake-case wire vocabulary. It includes discriminated rights decisions and job states; source/raw/dataset/processing/job/result records; physical axes, coordinate reference or explicit local coordinates, uncertainty and lineage; and observed/predicted/residual/model arrays. Processing runs link each output dataset version to immutable mask and uncertainty hashes; the versioned dataset carries the arrays. Data-array axis order is checked against declared dimensions; physical coordinate axis order is declared separately. Core runtime parsers reject missing identity or SHA-256, invalid timestamps, non-finite values, missing units, ambiguous geometry, mismatched shapes, inverted residual sign, cyclic provenance and field truth. The parsers are intentionally strict at the boundary while the existing v2 release format stays separate. Python schema and API response parity remain integration dependencies.

The transport module accepts only same-origin `/api/` paths and encodes search parameters through `URLSearchParams`. It forwards cookies on the same origin, JSON request/response headers and abort signals, rejects non-JSON success and structured HTTP failures, and takes a CSRF token explicitly for unsafe calls. It has no mock dataset or fallback result. Endpoint-specific methods and UI calls wait for the backend contract review; the generic transport and typed records can be independently tested now. Upload streams and auth flows are outside this unit.

## Shell and architecture evidence

The installed `@fasl-work/caos-app-shell` remains the sole owner of chrome, tokens, fonts, language, theme, architecture dialog and content primitives. Product CSS remains restricted to geophysical instruments; the fixed browser-chrome colour override is removed. The architecture modal continues to inline five themed bilingual SVGs. Each diagram labels the approved system as a target and keeps a conspicuous live-release boundary. It describes source rights, immutable raw/dataset versions, API admission, a separate CPU worker, offline GPU methods, replay and evidence gates without implying they already operate online. Clear Lake cl061 is QC-only; M13 browser inference is conditional on real held-out parity. Existing science figures and EDI code are retained.

## Verification and convergence

Unit tests cover route parity, both build modes, contract failures and same-origin transport behavior. The local Playwright gate drives pointer navigation at desktop and phone sizes, inspects the actual six routes, checks EN/ES and theme state, captures screenshots, and records document fit and runtime errors. The architecture gate checks SVG language switching and text bounds in both themes. Legacy and target builds are both compiled. A final requirement-to-gate verdict is recorded in `tasks.md`; unimplemented API endpoints and host cutover remain explicitly unresolved, not passed by frontend tests.
