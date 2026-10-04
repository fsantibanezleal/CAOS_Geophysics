# Service release preparation and qualified cutover

The platform has one application origin. Nginx serves the shared-shell frontend
and proxies its account/project API through a restricted Unix socket. The API
and the scientific worker are separate unprivileged services. A static-file
upload cannot deploy those services.

## 1. Reproducible preparation is not publication

Run the full local numerical, source, API, trained-model and rendered browser
gates against the selected source. Commit their approved product artifacts and
keep actual operating receipts in the private management repository. Build the
frontend locally, once. CI/CD never computes or trains.

An already-reviewed build can live on a separate local scratch drive. Supply
`-BuildDirectory` to the PowerShell preparer, or `--build` to the Python
preparer and the `check_single_origin.py --built` guard. These explicit absolute
paths receive the same entry/asset and no-link inventory checks as
`frontend/dist`. This does not establish that an old build belongs to new source;
retain the exact source/build and rendered review receipts.

From the repository root, provide an existing trusted interpreter and an
explicit absolute new output directory whose parent exists:

```powershell
./deploy/prepare-service.ps1 -Python $ValidationPython -OutputDirectory $NewQualificationDirectory
```

The source must be clean and committed. The preparer checks the actual
convergence ledger and single-origin build configuration, copies exact bytes
and writes `release.json`. It refuses an existing output, symlinks/reparse
entries, unsafe or case-colliding names, uncommitted evidence, mutation during
copying and byte/file limits. It performs no dependency installation, SSH,
account creation, scientific calculation or activation. An interrupted or
failed new directory is retained, not overwritten by a retry.

The bundle contains `web/` and `source/`. Only `web/` becomes the Nginx document
root. The manifest records every runtime and web member's SHA-256 and byte
length. `qualification_only=true` and `full_release_accepted=false` are fixed
statements, not switches a caller can change to authorize release.

## 2. Runtime and private state

The Linux operator stages the immutable bundle under the application's
releases root, installs an API-only `.venv` in that release from the exact
`requirements-api.txt`, records the resolved dependency inventory and runs
`pip check`. GPU/training requirements are not installed on the VPS. Source
and environment are owned by the operator, readable but not writable by the
service account. Staging and source verification precede activation.

The bounded installer is executable from the staged candidate's source:

```bash
/usr/bin/python3 -I -B source/scripts/stage_service_runtime.py \
  --release /var/www/geophysics.ml.fasl-work.com/releases/REVIEWED_ID \
  --evidence /var/lib/geophysics-deploy/REVIEWED_RUNTIME_ID \
  --bundle-sha256 REVIEWED_MANIFEST_SHA256
```

Use the explicit measured IDs and digest, not these placeholders. This operator
step refuses the active release, existing environments, wrong bundle bytes,
unsafe requirements and insufficient available bytes. Wheel-only installation
uses isolated pip without global changes or cache. The complete installed
file/interpreter and resolved dependency inventories are retained in private
evidence; failed candidates are retained and never reused by overwriting them.
Runtime installation is not method admission, activation or complete delivery.

Private state lives in `/var/lib/geophysics`, owned by the dedicated service
account with mode0700, outside all release and document roots. Alembic creates
the exact reviewed schema before first activation. Existing databases are
never replaced with a local candidate or downgraded. An incompatible revision
requires a separately reviewed migration/compatibility contract. The internal
account CLI creates or explicitly rotates accounts from private files; no
password is embedded in product source or in a frontend bundle.

Root-owned mode0600 `/etc/geophysics/api.env` selects the canonical origin,
local account mode, state path and stable auth secret. The separate
`worker.env` has only state/database paths and admitted-method flags. Literal
ASCII `GEOPHYSICS_NAME=value` entries are used, not executable shell text.
Neither file is committed, printed or served. No SMTP, public signup, email
verification/reset or off-host backup is required for this operating profile.
These choices do not restrict the database to one user or one project.

## 3. Measured host qualification

Use an isolated candidate with the exact bundle/runtime bytes to execute
nominal, upper-bound, malformed, cancellation, crash/recovery, ownership and
concurrent-public-read controls. Record actual outcomes, source revision,
command, elapsed time, resource counters and output hashes. The operating
admission record is `geophysics.service-host-admission/v1`, with
`source_revision`, `bundle_sha256`, seven named checks (`nominal`, `upper`,
`malformed`, `cancel`, `crash`, `ownership`, `public_read`) and a fresh measured
capacity record. Each check names its private absolute evidence path and
SHA-256. A typed record alone is not proof the controls ran; those outputs are
independently reviewed.

The read-only `collect_capacity` function measures Linux `statvfs` available
bytes, `/proc/meminfo` MemAvailable and explicit current/two-rollback release
directories. Existing projects and releases already consume the measured
filesystem; do not subtract them twice. Reserve the actual incoming/extracted
release, measured API environment installation, job scratch and API/worker/
controller memory. A percentage of the whole host is not the admission rule.
Measurement does not delete releases or claim their scientific qualification.

Systemd limits apply to the whole API or worker service, not to a scientifically
unqualified method or an imaginary per-job disk sandbox. The Unix socket is
mode0660 and accessible to Nginx's group; no public backend TCP listener is
needed. Nginx overwrites forwarded headers. Actual socket permissions, cgroup
limits, descendant shutdown and selected method admission must be measured on
the deployed operating system, not inferred from these local file tests.

## 4. Qualified activation and rollback

Only after all non-deployment SDD requirements pass and actual-host admission
is reviewed, invoke the committed `deploy/activate-service.sh` with the exact
release ID and private admission record. It takes an app-specific deploy lock,
rehashes the bundle and receipts, verifies capacity and compatible SQLite
schema, saves the previous application site/units, freezes writes and refuses
a busy queue. It does not kill a live calculation to make room for deployment.

The worker is stopped before the source switch. The `current` symlink changes
atomically, only this application's units/site are installed, systemd/Nginx
configuration is verified, and the new API must pass actual Unix-socket local
account configuration and anonymous project401 checks before the worker starts.
Nginx then reloads. An activation failure attempts restoration of the previous
release/site/services and retains its state for inspection. A failed rollback
is reported as an attempt, never as a proven restoration. No schema downgrade,
project deletion, certificate bootstrap, DNS edit or unrelated service change
is part of activation.

Final external HTTPS exact-file/six-route verification, secure account sessions,
real user-data workflows, full browser use and exercised rollback must still
pass. The old release remains available throughout. Preparation/activation
and full release acceptance are separate facts. This avoids requiring a
post-deployment observation before there is a candidate to observe without
waiving the observation.

After all final gates pass, retain current and two explicitly qualified
rollback releases. Inspect and approve each additional ordinary directory
directly under this application's releases root before removal. Never follow
a link or remove the current target, private projects, another application's
files or a broad host directory. Release rollback is not a project backup.

See [service design](../design/features/single-vps-service/design.md),
[single-site verification](17_single_site_verification.md) and the
[approved product requirements](../design/SDD.md).
