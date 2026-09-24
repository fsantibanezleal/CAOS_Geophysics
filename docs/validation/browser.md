# Rendered browser acceptance · v2 rebuild

Executed against local development and the production build on 2026-09-23/24 (UTC). Browser-driven UI interactions were used, not a build-only assertion.

- All 20 geological case views loaded with their expected family-specific renderer.
- All 54 case/method combinations opened Measurements and Recovery & residual without JavaScript errors or nonfinite text.
- All 120 case/condition selections loaded the context view and exposed 120 distinct artifact SHA-256 values. Numerical hashes were independently checked on disk.
- Desktop rendering was inspected at 1280×800, 1600×900 and 2560×1440; mobile at 390×844. No document horizontal overflow was observed. Mobile exposes a compact case/playback surface with expandable experiment/method controls.
- Light/dark and EN/ES switches were exercised. Layer columns, gravity/magnetic 3D geometry, acoustic pressure/receiver gathers and learned maps were visually inspected.
- Wave play/pause, keyboard scrubbing and switching between acoustic-time playback and recorded velocity updates were exercised. Wave display uses labelled linear interpolation between computed snapshots; inverse states remain discrete.
- Production-build direct routes loaded Introduction, Methodology, Implementation, Experiments and Benchmark headings and real content. Benchmark metrics hydrated from the v2 catalogue.
- The live MT resistivity slider recomputed the layer column and response curves. Its numerical parity across all offline truth soundings is tested separately.
- An architecture deep-route check exposed a shared-shell relative-asset issue. Diagrams were changed to raw SVG imports so every route uses the same inlined diagram, without a relative fetch.
- A layout review found that MT initially opened on identical 100 Ω m starting columns. Cases now open on their computed final column; replay still includes the common initial state.
- Old ignored `frontend/public/data` and `pyodide` build leftovers are excluded by an allowlisted `public-release` build source. They are not canonical evidence and are not shipped. No broad local directory cleanup was needed.

These checks establish rendered functionality and engineering acceptance, not the user's aesthetic approval or field-science validity. Numerical, remote CI and deployed checks are separate records.

Final production inspection on 2026-09-24: both HTTPS endpoints loaded actual data. VPS 3D angle-step/cut, acoustic playback and live MT were exercised; Pages benchmark counts, route navigation, inlined architecture, Spanish/light MT and mobile layout were inspected. A shared-shell brand-link escape was fixed with the router basename; final recovery error is now the benchmark fallback metric. See `deployment.md` for the released commit and exact-byte receipts.
