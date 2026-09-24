# Architecture

The canonical numerical path is `geology.py → {potential,electromagnetics,seismic,joint,learning}.py → rebuild.py → data/derived/v2`. Case constructors specify geometry, not a generic radial blob. Physics modules return full structured results. The orchestrator serializes finite arrays and hashes them in the catalogue. No training or bake runs in CI.

The browser path is `catalogue → selected artifact → family-specific renderer`. Potential fields use an instanced Three.js volume; MT uses true layer thicknesses and complex-response charts; seismic uses saved pressure and model updates; learned methods compare column-density or reconstruction-error maps. Canvas colour interpolation is a display operation; hover readouts remain cell values. Amplitude gain clips display colours at the shown limits and does not alter observations. Camera angles change the camera only.

`mt.ts` is a separate browser forward calculation using the same layered-earth equations. Unit tests compare it with all 24 offline MT truth responses. It does not approximate unrelated gravity or seismic methods.

Six shared-shell routes separate the instrument, introduction, methods, implementation, experiments and benchmark. EN/ES and light/dark states use shared-shell stores. Browser failures are visible. An aborted artifact request cannot overwrite a newer selection. No secret or service credential is in the frontend.

Both GitHub Pages and the ML VPS host a static build. Local CUDA and CPU compute are explicitly separated from public inspection. VPS releases use timestamped directories and an atomic current symlink. The prior release remains available for rollback. Pages produces direct route entrypoints and correct project-base artifact paths.
