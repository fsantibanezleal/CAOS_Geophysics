# Authenticated projects and original-byte uploads

This guide covers the unreleased API foundation only. The current public static site does not call it. A successfully uploaded original has `validation_status: raw_metadata_checked`; it is not yet a scientifically validated dataset and cannot be submitted to a solver. The integration and worker branches own those later transitions.

## Local setup

Use Python 3.12 or newer. On PowerShell, create a separate ignored runtime environment and install only the API lane:

```powershell
py -3.12 -m venv .venv-api
.\.venv-api\Scripts\python.exe -m pip install -r requirements-api.txt
.\.venv-api\Scripts\alembic.exe -c app\alembic.ini upgrade head
.\.venv-api\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000
```

Set these process environment variables before migration and startup. Keep their values in the operator's secret store, never in the public repository or browser bundle:

| Variable | Meaning |
| --- | --- |
| `GEOPHYSICS_AUTH_SECRET` | At least 32 random characters for FastAPI Users verification/reset tokens and request admission keys. |
| `GEOPHYSICS_PUBLIC_ORIGIN` | Exact browser origin, such as the final HTTPS site; no path or trailing slash. |
| `GEOPHYSICS_SMTP_HOST`, `GEOPHYSICS_SMTP_PORT`, `GEOPHYSICS_SMTP_USERNAME`, `GEOPHYSICS_SMTP_PASSWORD`, `GEOPHYSICS_SMTP_FROM` | TLS mail delivery for verification and password reset. Missing credentials fail startup. |
| `GEOPHYSICS_DATA_DIR` | Optional absolute private root, default `data/raw/api/`. |
| `GEOPHYSICS_DB_PATH` | Optional absolute SQLite path, default `<data_dir>/api.sqlite3`. Set before running Alembic too. |

The default private path is already covered by `data/raw/` in `.gitignore`. The web server must never serve it as static content. The ASGI deployment must preserve a trustworthy client address for rate limits. Production cookies require HTTPS and are HTTP-only, host-only and SameSite Strict. Before any new migration, back up the SQLite file and private byte tree as a consistent restricted snapshot. The second migration adds private-storage attestations without retroactively asserting consent for older rows. Release requires encrypted/restricted backups, a restore drill and verified deletion-tombstone handling; this API branch has no external backup integration.

The test-only `cookie_secure=False` setting is available through `create_app(Settings(...))` for loopback HTTP tests, not through production environment configuration.

## Account and project flow

All unsafe `/api/` requests require a same-origin `Origin` or `Referer`, a CSRF token from `GET /api/auth/csrf`, the `X-CSRF-Token` header, and the cookie set by that response. Obtain a new token when the browser session starts. Registration is `POST /api/auth/register`; the verification token is mailed and submitted to `POST /api/auth/verify/verify`. The library login is `POST /api/auth/cookie/login` with form fields `username` (the email address) and `password`. `GET /api/auth/me` confirms the verified session. `POST /api/auth/reset-password/forgot-password` emails a reset token; `POST /api/auth/reset-password/reset-password` accepts `{ "token": "...", "password": "..." }` and revokes all existing sessions. `POST /api/auth/cookie/logout` revokes the current token.

Verified accounts can use `GET/POST /api/projects`, `GET/PATCH/DELETE /api/projects/{project_id}`, and `GET/POST /api/projects/{project_id}/assets`. A project body is `{ "name": "Survey name", "description": "..." }`; PATCH accepts either field. Project, asset, download and export URLs return 404 for both missing and another owner's ID. Guests have no project or raw-byte access.

The service accepts original bytes as the body of `POST /api/projects/{project_id}/assets`. Send `Content-Type` matching the declared MIME and one UTF-8 JSON `X-Asset-Metadata` header no larger than 16 KiB. A minimal gravity station example is:

```json
{
  "filename": "stations.csv",
  "mime": "text/csv",
  "format": "gravity_csv",
  "source": {
    "provider": "User upload",
    "rights_statement": "I may store this original privately but cannot publish its raw bytes.",
    "rights_decision": "provider-link-only",
    "private_storage_permission": "attested",
    "attribution": "Survey team"
  },
  "physical": {
    "coordinate_reference": "epsg",
    "epsg": 32719,
    "axis_order": "xy",
    "horizontal_datum": "WGS84",
    "vertical_datum": "survey benchmark",
    "vertical_positive": "up",
    "horizontal_unit": "m",
    "vertical_unit": "m",
    "measurement_unit": "mGal",
    "epoch_utc": "2026-09-27T12:00:00Z",
    "component_frame": "local vertical down",
    "geometry": {
      "station_id_column": "station",
      "x_column": "x",
      "y_column": "y",
      "z_column": "z",
      "value_column": "g"
    }
  }
}
```

`expected_bytes` and `expected_sha256` are optional advance declarations; if supplied, the upload must match. The response always records the measured byte count and SHA-256. Reuploading the same original filename within a project creates a new immutable asset and increments that source's version; it never overwrites bytes. `private_storage_permission: "attested"` is a required statement that the uploader is authorized to store these bytes in this private account; it is not proof of public redistribution rights. `rights_decision` separately describes public use: `provider-link-only` and `derivative-only` can still be private originals for this owner, `forbidden` is rejected, and `mirror` never automatically publishes bytes. There is no arbitrary URL fetch or guest raw route. Provider-linked records and catalogue publication require a separate rights-reviewed source unit.

The API accepts these raw envelopes and per-format caps: gravity, magnetic, traveltime and ERT CSV (50 MiB each); EDI (5 MiB); StationXML (20 MiB); and GeoTIFF, MiniSEED, SEG-Y and MTH5 (200 MiB each). The per-request maximum is also 200 MiB and the account raw-byte quota is 1 GiB. Archives, including ZIP and gzip, are refused rather than extracted. The API checks explicit CRS with `pyproj`, units, EPSG datum consistency (official datum name or WGS84/NAD83 shorthand), epoch, component frame and format-specific geometry. Complex binary checks validate only a bounded envelope. The future scientific ingestion/QC gate must parse and independently validate contents before modelling.

`GET /api/projects/{project_id}/assets/{asset_id}` returns the versioned `geophysics.raw-asset-view/v1` receipt. The owner-only projection includes `owner_id`, `project_id`, `source_id`, `original_filename`, `mime_type`, byte count, SHA-256, physical metadata, `raw_metadata_checked`, nested `source.location: {kind: "upload", filename}`, and a receipt/download URL. Citation is null when none was provided; it is never invented. The private filesystem `storage_key` is intentionally absent from JSON, OpenAPI responses and export manifests. Append `/download` to retrieve exact bytes with `X-Content-SHA256`. `GET /api/projects/{project_id}/export` returns a ZIP with `manifest.json` and `raw/{asset_id}/{original_filename}` members; check each member against its manifest hash. If bytes have changed on disk, download/export returns `409 raw_integrity_failed`.

`DELETE /api/projects/{project_id}` first rejects unexpected or changed project files. It also returns `409 backup_reconciliation_required` if any `.backups/<owner>/<project>` entry exists, including an empty directory: the API has no backup manifest proving that it owns the entry or knows its contents. This refusal leaves the project, raw bytes, backup entry, quota and receipts unchanged. With no project backup entry, DELETE commits a deletion receipt with exact asset IDs, hashes and sizes before unlinking only those verified owned raw files. The response includes a receipt ID, `backup_erasure_status: not_attempted` and `external_backup_status: pending_reconciliation`; the receipt records `backup_purge_status: not_attempted`. Neither is evidence that backup copies were erased. Backup inventory, retention or purge and tombstone-aware restore require a separate explicit operator procedure. Preserve and inspect any project backup in restricted storage before an operator clears its path and retries DELETE; do not treat moving it as erasure. External encrypted backups may still retain an older copy until their published retention period ends; a restore must honor the tombstone before returning any deleted project. That operational contract is a release blocker until the backup owner demonstrates it.

Startup is a read-only private-state audit. It never age-sweeps staged files, exports, orphaned project bytes, interrupted `.deleting` directories or backups. Any such bytes, a missing referenced asset or inconsistent quota counter stops startup with `private_recovery_required`. An operator must preserve and inspect the exact SQLite snapshot, receipt and bytes in a restricted recovery area, then decide how to reconcile them; do not delete a directory simply because an older DB lacks its rows. This is intentionally an operational stop, not a successful upload or automatic repair.

The merged frontend `api/contracts.ts` is not yet parity-compatible: it requires a storage key, non-null citation and `valid` status. Those fields would leak an internal location, fabricate provenance or overstate QC. Integration gate INT-API-FE-01 requires a reviewed frontend mirror/adapter and live contract test before connecting this API to the public browser; this branch does not change the frontend.

The project API returns `{ "code", "message", "fields"? }` errors: 401 for absent verified account, 403 for origin/CSRF, 404 for missing/foreign IDs, 413 for a size cap, 415 for bytes/MIME/format, 422 for declared metadata, 429 for a rate window and 507 for account quota. FastAPI Users account routes retain their library error shape, including rejection of login before verification. The name and final hostname of the single public origin remain owner decisions; no deployment or cutover is part of this branch.
