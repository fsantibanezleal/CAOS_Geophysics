# Shared protected-method integration, 2026-10-08

This is an integration record, not whole-product or VPS release acceptance.
The project shell now selects gravity station QC, MT, supplied ERT/first-arrival
profiles and waveform processing without changing the selected owned project.
Navigation lives inside the original instrument sidebar and uses existing
shell controls, typography and themes; no CSS, font or palette is introduced.
Methods still obtain execution eligibility from their actual API/platform.

## Source and numerical boundaries

The M08 merge preserves the existing profile and MT request, parser, source,
result, configuration and worker branches. Its explicit migration head is
`0004_waveform_artifacts`. Saved 0003 databases are not accepted as 0004 by
bypassing startup checks. Browser qualification uses newly completed native
0004 jobs and exports their exact receipts through the authenticated API.
The test harness provisions no account and executes no replacement solver.

The original FWI generation, original local profile results and newly persisted
native profile results are supplied to all optional frontend gates. Native cells
are not resampled into decorative images. Hashes, units, selected row/cell,
prediction/residual values and complete saved exports retain their original
contracts. A display refresh does not recompute physics.

## Fresh checks

- TypeScript passes. All 224 frontend tests pass with zero skips, including
  eight shared-mount EN/ES controls and original full-budget FWI/profile bytes.
- Waveform publication/service/storage/migration: 41 pass, zero skips or errors;
  actual original processing/export is included. Windows publication preflights
  exact UTF-16 destinations before mkdir/copy and rejects the observed long-path
  failure, without registry changes or device-prefix bypass.
- Existing supplied-profile contract/uploads/jobs: 26 pass, zero skips; actual
  original ERT and traveltime engines, cancellation and lowered runtime ceilings
  are included. This is Windows execution, not a Linux queue activation receipt.
- Authenticated shared-app rendering: one complete original-result roundtrip
  passes across 16 case/language/theme/viewport contexts. It checks every native
  cell count, exact inspection JSON, verified ZIP/re-import, project identity,
  waveform method navigation, usable plot width and mobile control access.
  Screenshots were inspected, not merely generated.
- Content, template-residue and single-origin source/build guards pass.

## Retained failures and remaining work

The first sibling navigation implementation passed document-overflow checks but
visually squeezed plots into a narrow column. It was rejected after screenshot
inspection; usable instrument-width assertions now detect that regression.
An older browser fixture failed the unchanged migration-head check. Its database
was preserved rather than migrated in place. An initially hidden mobile control
required the real expansion action, not a weakened visibility assertion.

Initial waveform tests also retained a missing interpreter, native subprocess
timeout and Windows generated-path failure. Fresh explicit-runtime/short-root
runs and the publication preflight are distinct from those failures. Scientific
tolerances and native resource ceilings were not changed to obtain a pass.

The root Linux profile guardian, waveform Linux runtime, remaining potential-
field/joint pipelines, full native host tests and complete single-VPS release
remain separate work. This record does not enable a method, replace failed
scientific assertions, promote a branch or change the public release pointer.
