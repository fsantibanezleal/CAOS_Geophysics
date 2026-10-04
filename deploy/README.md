# Deployment

The sole public application origin is `https://geophysics.ml.fasl-work.com/`, hosted on the ML VPS. GitHub stores source and runs inexpensive integrity/build checks; it is not an application host. No secondary project-site publication, relative asset base, alternate public build, or mirrored application is supported.

The VPS release uses an immutable directory under `/var/www/geophysics.ml.fasl-work.com/releases/` and an atomic `current` symlink. Nginx serves the SPA with a deep-link fallback and caches hashed assets while keeping `index.html` and replay data revalidatable.

The current public release is still the legacy 0.04.001 static frontend. Removing the old secondary publication does not deploy or accept the replacement. Historical validation receipts remain historical, even where they document the former duplicate publication.

## Approved replacement

The reviewed product SDD requires one HTTPS origin for the shared-shell frontend, same-origin API, authenticated account/project writes, immutable private raw/derived data, and a separate unprivileged bounded CPU worker. Complete local CPU/GPU pipelines, FWI optimization and model training stay offline; the browser and CPU worker execute only their individually validated online operations. Private storage, service secrets and backups are not placed in the Nginx document root.

Both `npm run build` and its compatibility alias `npm run build:single-origin` build root-relative assets. Nginx must resolve the six frontend routes through the SPA fallback, and proxy `/api/` to the API; route-specific copies of the asset tree are not generated. A filesystem release is not automatically an API/worker release.

Cutover requires all product scientific/UI/API/ownership/job gates, actual-host measured capacity and security admission, same-origin HTTPS/browser checks, release hash verification and tested rollback. Internal SQLite accounts require no SMTP or external verification/reset. Off-host backup/deletion-journal integration and production-scale administration are deferred for this owner-tested stage. Retain current plus two rollback releases; capacity must cover actual release/project/job bytes and memory, not an arbitrary whole-host percentage. No green source guard, HTTP response or isolated solver test substitutes for full acceptance. Other hosted products remain untouched.

`python scripts/check_single_origin.py` prevents the retired deployment path from returning to active source/build configuration. It does not assert live deployment or whole-product acceptance. See [withdrawal evidence](../docs/validation/pages-withdrawal-2026-10-03.md) and [product SDD](../docs/design/SDD.md).
