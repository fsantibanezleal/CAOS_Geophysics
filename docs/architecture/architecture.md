# Architecture

The canonical numerical path is `geology.py → {potential,electromagnetics,seismic,joint,learning}.py → rebuild.py → data/derived/v2`. Case constructors specify geometry, not a generic radial blob. Physics modules return full structured results. The orchestrator serializes finite arrays and hashes them in the catalogue. No training or bake runs in CI.

The browser path is `catalogue → selected artifact → family-specific renderer`. Potential fields use an instanced Three.js volume; MT uses true layer thicknesses and complex-response charts; seismic uses saved pressure and model updates; learned methods compare column-density or reconstruction-error maps. Canvas colour interpolation is a display operation; hover readouts remain cell values. Amplitude gain clips display colours at the shown limits and does not alter observations. Camera angles change the camera only.

`mt.ts` is a separate browser forward calculation using the same layered-earth equations. Unit tests compare it with all 24 offline MT truth responses. It does not approximate unrelated gravity or seismic methods.

Six shared-shell routes separate the instrument, introduction, methods, implementation, experiments and benchmark. EN/ES and light/dark states use shared-shell stores. Browser failures are visible. An aborted artifact request cannot overwrite a newer selection. No secret or service credential is in the frontend.

Both GitHub Pages and the ML VPS host a static build. Local CUDA and CPU compute are explicitly separated from public inspection. VPS releases use timestamped directories and an atomic current symlink. The prior release remains available for rollback. Pages produces direct route entrypoints and correct project-base artifact paths.

## Authenticated project and raw-source API foundation (unreleased)

The approved replacement design activates `app/` as a FastAPI service on the future single ML VPS origin. This branch contains account, project and private original-byte operations only. It is not connected to the currently released static frontend and it runs no solver or background calculation. No `/jobs` route exists. The current Pages and VPS static release described above remains the public application until the integrated release gates pass.

FastAPI Users owns password hashing, registration, verification, reset and database-backed cookie tokens. Reset revokes all existing account tokens. The service adds origin and CSRF checks plus SQLite-backed rate windows before unsafe requests reach library or project routes. SQLite metadata is changed only through committed Alembic migrations. All project and asset queries include the authenticated owner ID, with foreign IDs returning the same 404 as missing IDs.

A raw upload moves through a bounded stream, a private staging file, format and physical metadata envelope checks, an account quota transaction, and a SHA-256 receipt. The final file path uses only generated owner/project/asset IDs under ignored `data/raw/api/projects/`. It is never served by a static file mount. A `raw_metadata_checked` receipt establishes original-byte integrity and explicit declared units, CRS, datum, epoch, component frame and geometry. It does not establish scientific QC, compatible methods or a validated dataset. The separate ingestion adapter must create that versioned dataset.

Export is an owner-only ZIP of exact raw bytes and a JSON manifest containing source rights, metadata and hashes. Download and export hash the current stored bytes and fail if they differ from the receipt. Deletion hard-removes DB rows and API-owned bytes, retains an owner-linked tombstone with hashes, and purges any API-managed backup directory. External encrypted backup operators must apply tombstones during restore and demonstrate a restore drill before public cutover. Startup reconciles interrupted deletion directories, abandoned staging/exports and unreferenced final files while holding a SQLite writer lock; a DB row with missing raw bytes blocks startup.

The security and storage contract, exact endpoints and local commands are in [`../guides/06_api.md`](../guides/06_api.md). Feature acceptance gates are in [`../design/features/project-raw-api/requirements.md`](../design/features/project-raw-api/requirements.md). The reviewed product design remains [`../design/SDD.md`](../design/SDD.md).
