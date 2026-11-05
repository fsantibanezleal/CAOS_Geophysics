# M02 3D volume component visual check — 2026-11-01

This is a browser rendering and interaction check of the isolated physical
volume component. The authored preview fixture is an eight-cell signed-density
block solely for rendering controls. It is not solver output, inversion
evidence, field data, or a science acceptance result.

## Rendering and interactions checked

- The Three.js renderer produced an orbitable cell volume from each supplied
  six-coordinate physical bound and signed density. A preceding blank-canvas
  capture exposed a renderer camera/clear-state defect; explicit scene clear
  color and camera target setup fixed it. `Stage` now supplies the canvas size,
  preventing the shared `PlotCard` body from clipping the volume.
- Desktop: 900 × 800, English, light; eight cells, mixed signed values, all
  cells visible. Screenshot:
  `E:\_Datos\CAOS_Geophysics\validation\gravity-density-volume-qa-20261101e.png`
  SHA-256 `560e3a6e06363f9ec490281d97ce74541cb4e00e2b19c0dd939149f78cf1ff68`.
- Phone: 390 × 844, Spanish, dark; elevation slice changed through the native
  select and exaggeration changed with keyboard End. No horizontal overflow;
  Spanish canvas accessible name present; no browser errors. Screenshot:
  `E:\_Datos\CAOS_Geophysics\validation\gravity-density-volume-mobile-es-dark-20261101-final.png`
  SHA-256 `f180d59aac6bc7a4dc2f6c18c02190f5ddd85702104edd6e67387cfc6699d5f4`.
- Keyboard: focused the canvas and pressed ArrowRight; rendered pixels changed,
  with no browser errors. The desktop capture is
  `E:\_Datos\CAOS_Geophysics\validation\gravity-density-volume-desktop-keyboard-20261101.png`
  SHA-256 `cc43af8ec887a937ace7c6a14b524ad8b4955da705f5f26bbce0fb7268e45cb0`.
- The WebGL canvas DOM identity remained stable while slice and exaggeration
  changed. The view updates existing scene objects, preserving the orbit camera.
  Production build passed. The `Workbench` chunk is 549.90 kB (down from 572.22 kB before lazy loading); `GravityDensityView` is a 9.05 kB async chunk, with OrbitControls at 19.10 kB and Three.js in a separate 493.25 kB chunk loaded for the 3D view. Vite still
  reports the pre-existing >500 kB Workbench chunk warning.
- Actual uploaded M02 result screenshots, full EN/ES × light/dark × viewport
  matrix, and integration/browser acceptance remain open.

Focused unit and production checks are listed in the product task ledger; these
screenshots do not close MV-08, MV-09, MV-12, or any release gate.

## Accepted-state replay follow-up

The M02 instrument now reads `final_solve.trace.models_kg_m3` and its paired `phi_engine` and `kkt_normalized` arrays from the hash-verified result. It requires exactly `iterations + 1` accepted states and exact equality between the terminal frame and `final_solve.model_kg_m3`. The renderer keeps one physical mesh and camera while updating cell colours for the selected state; play/pause and the iteration slider are display controls. The displayed objective and KKT values are recorded solver diagnostics, not a claim that the inverse is geologically resolved. A normalized contract test checks finite frames, the 201-state cap, and terminal-model binding. `npm run build` passes; Three.js remains in lazy chunks (`GravityDensityView` 9.05 kB, OrbitControls 19.10 kB, shared Three.js 493.25 kB before gzip). A disposable Playwright harness replayed two authored synthetic accepted states at desktop 1280 × 900 and phone 390 × 844: rendered pixels changed during play, slider endpoints responded, the same canvas node remained mounted, JavaScript errors were zero, and mobile horizontal overflow was false. The whole-page screenshots are retained outside the repository at D:\_Temp\gravity-playback-qa\desktop-full.png (SHA-256 8f42e03c0ae89dc01417ba0e3f143c80613ddd7feb367193d30395ae360f8aa5) and mobile.png (SHA-256 e565ae246190b9d14a4c68c84484bebd282c8f21f0582bba99ef3849f0860b38). This is UI interaction evidence with authored fixture data only. Actual uploaded M02 browser replay, chart parity, and full viewport/theme acceptance remain open.


