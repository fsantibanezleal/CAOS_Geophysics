# Selected-result reactivity and scientific controls · 2026-11-06

## Scope

This is a local browser result for the static scientific workbench at source
revision `6061ea28088b480516f7d484d21123b557860b05`. The production frontend
build completed with `npm run build`. The browser suite ran against that build
with Vite preview; it did not call an API, upload a file, modify project data,
or use the VPS.

Command:

```powershell
$env:CAOS_SCIENTIFIC_CONTROLS_OUTPUT='E:\_Datos\CAOS_Geophysics\validation\scientific-controls-20261106-final-rerun'
npx playwright test -c playwright.scientific-controls.config.ts
```

Result: **5 passed, 0 failed, 0 skipped, 0 flaky** in 19.0 s. The retained
Playwright JSON report is at
`E:\_Datos\CAOS_Geophysics\validation\scientific-controls-20261106-final-rerun\playwright-report.json`,
SHA-256 `288b1c2964991f898df5d13ed7bba5974a79c6901bca52808efbec711ebd8883`.

## Observed behavior

- Switching from the gravity stock to the magnetic dyke changes the rendered
  observation plot, its shell state key and the selected case label. The
  selected noise variant changes the rendered plot again. Linked data cards
  report `data-stale="0"`; the inversion view is available.
- In the baked `FWI_LAYERED` case, selecting source position S1 changes the
  observed, predicted and signed-residual chart state keys and the rendered
  residual raster. Axes identify receiver position in metres and time in
  seconds. The residual legend is symmetric around zero and reports relative
  amplitude.
- The 3D gravity scene's 30° angle step changes the rendered scene. The angle
  step control is absent from the FWI section view, which exposes distance and
  depth in metres.
- The FWI wavefield slider selects saved frames. Frame 16 renders differently
  from frame 0 and displays `0.384 s`; the inversion replay selects saved model
  updates with an update index. Play advances the selected sequence and Pause
  freezes it. Predictions remain bound to the final model.

The animation check compares frame 0 with frame 16. The later low-amplitude
tail is close to the zero colour under the fixed global scale; identical
pixels at the final frame would not prove that the frame selector failed.
The test checks a physically varying saved frame without changing the scale.

## Acceptance boundary

These checks cover baked synthetic cases and the currently declared browser
controls only. They do not establish field-data accuracy, user-uploaded
results across all modalities, product-wide R-013/R-014 closure, notebook or
method acceptance, actual-host behavior, deployment readiness, or release
acceptance. The convergence ledger remains `R-013=unresolved` and
`R-014=unresolved` until the full modality and supplied-result matrices pass.

## Source hashes

| File | SHA-256 |
|---|---|
| `frontend/e2e/selected-case-reactivity.spec.ts` | `a75eddc15f5f7c3da82552cd8537cff9167c86470df60fbf7328bb6b9cae2dd7` |
| `frontend/e2e/scientific-views.spec.ts` | `bb880a37f4f0a7efc54f125561dbe585c439784adff6356db858f837d384c382` |
| `frontend/e2e/animation-controls.spec.ts` | `407c8ecc8e30f5c176c5e85ef67d899f679c54cf37c2a054e2d92331bb887169` |
| `frontend/playwright.scientific-controls.config.ts` | `d7bd0f961a586b7e50f8b5cf94f4cc7c29d4aa890bc02bfd364164f91a8563e1` |
