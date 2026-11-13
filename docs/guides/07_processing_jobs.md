# Private uploaded-data processing jobs

The authenticated API in this branch has owner-scoped project, original-asset, typed-dataset, method-eligibility, job, result, cancellation and export routes under `/api/projects/{project_id}`. It includes reversible gravity flag QC and an ordinary weighted-L2 uploaded-survey method, plus modality-specific adapters whose eligibility is controlled separately. The job routes are not guest endpoints. This branch is not the currently deployed public release: the production API/worker services and online M02 switch remain off, so this source-tree capability must not be presented as an online method available at the live site.

`gravity.station-outlier-flags/v1` returns robust scores and flags while preserving observations, uncertainty and station order. `gravity.survey-l2-ordinary/v1` runs a bounded CPU inverse for source-qualified gravity surveys. The latter passed an isolated ML VPS runtime test on 2026-11-06 using an authored synthetic 12-by-12 prism survey, with two parameter variants, Choclo replay, held-out residual checks and upload-byte preservation. This is scoped runtime evidence, not full M02 acceptance: field eligibility, broader survey families, production capacity and deployment remain open. See the [host receipt](../validation/actual-host-admission-m02-2026-11-06.md) and [M02 requirements](../design/features/m02-survey-inversion/requirements.md).

## Local process separation

Install `requirements-api.txt` and run `alembic -c app/alembic.ini upgrade head` before starting the API. Start the API as in [the API guide](06_api.md). In a separate terminal using the same private data root and database path, start one worker:

```powershell
$env:GEOPHYSICS_DATA_DIR = 'D:\private\geophysics-api'
$env:GEOPHYSICS_DB_PATH = 'D:\private\geophysics-api\api.sqlite3'
.\.venv-api\Scripts\python.exe -m app.worker
```

The worker needs only the private root and SQLite path, not SMTP or authentication secrets. Run it under a restricted OS identity with read/write access to that root and read-only application code. A process lock permits one worker. The API never runs the processing engine in its request/background-task process. The worker launches only the fixed `app.compute` child with an argument vector, a sanitized environment, private scratch working directory and no shell. [psutil 7.2.2](https://pypi.org/project/psutil/7.2.2/) supplies process-tree RSS/termination; its [process API](https://psutil.readthedocs.io/stable/) is the reviewed monitoring dependency. This is local engineering evidence, not an actual-ML-VPS resource benchmark.

## From a raw upload to a typed dataset

In the single-origin frontend, open App -> Projects & raw data, sign in, select/create a project and upload an original with the six explicit gravity columns, including **Sigma column (required for flag QC)**. The optional sigma field leaves raw-only uploads supported; it does not infer uncertainty. Choose **Open processing workbench** to give that project the primary App instrument. This uses the existing App route with `?project=<UUID>`; a bookmark still requires the owner's actual cookie session.

The workbench's Data validation section submits the original to the dataset API. It reads method eligibility from the server; controls appear only for methods the server admits. Job history shows the immutable request, queue/worker outcome, cancellation and measured resource usage. Flag-QC success shows robust scores and flags beside unchanged observations and sigma. M02 success shows its returned model, predictions, residuals and solver trace. A queued response is not a result, and a failed/cancelled job has no result/export. The M02 browser replay is documented in [its independent result-view receipt](../validation/m02-uploaded-prism-replay-2026-11-06.md).

**Verify & export processing ZIP** downloads the actual owner-only bundle and verifies bounded members, hashes and dataset/result/request identity before saving. M02 bundle verification also checks its source and solver receipts and numerical result closure; it does not establish field-geology accuracy. Other modality adapters have independent contracts and admission switches; a gravity view cannot treat an MT QC success as an inverse or send a fabricated parameter shape.

For the isolated local real API/worker browser gate, from `frontend/` run `npm run build:single-origin`, then `npx playwright test --config playwright.processing.config.ts --reporter=line`. It reads the existing API interpreter, creates a migrated temporary private database under ignored `frontend/node_modules/.processing-qa/`, captures verification mail locally, and runs the actual separate worker. Screenshots and the independently Python-verified downloaded bundle stay in `.processing-qa/evidence/`; no canonical artifact or private user dataset is modified. These engineering controls do not activate public online processing. See [the feature requirements](../design/features/processing-workbench/requirements.md) for exact gates.

Upload an owner-only gravity CSV using [the raw-asset API](06_api.md). In addition to its mandatory physical metadata, set `physical.geometry.sigma_column` to a distinct CSV column. The baseline gravity parser accepts six declared station/x/y/z/value/sigma columns, 4–4096 stations and at most 2 MiB. M02 may add one explicitly named acquisition-group column. Coordinates must be explicitly declared in metres, gravity in mGal and sigma as a positive per-station standard deviation; the source can declare an EPSG frame or an explicit local CRS. Nonfinite values, duplicate station IDs or XYZ triples, missing/extra columns and missing uncertainty are rejected. No projection, unit conversion, correction, missing-value replacement or outlier exclusion is inferred. This typed dataset can be used for flag QC; passing M02 source admission is a separate check.

This five-station example is a flag-QC fixture, not an M02-eligible survey: it omits acquisition groups and the provider's processing, uncertainty and background declarations. With geometry columns `station,x,y,z,g,sigma`:

```csv
station,x,y,z,g,sigma
S1,0,0,100,1,0.1
S2,10,0,100,2,0.1
S3,20,0,100,3,0.1
S4,30,0,100,4,0.1
S5,40,0,100,100,0.1
```

After the verified upload, send `POST /api/projects/{project_id}/datasets` with `{ "asset_id": "<uploaded asset UUID>" }`. The response supplies a dataset ID, raw hash, dataset hash and `parsed_for_flag_qc_only` verdict. `GET /datasets/{dataset_id}` returns the typed, immutable observations, sigma, station axis, physical metadata, rights and empty correction history. Its original raw file remains unchanged. One raw asset can create one dataset at this parser version; a second request returns `409 dataset_exists`.

The local `data-pipeline/ingest.py` five-column `east_m,north_m,up_m,value,sigma` workflow is not a substitute for the authenticated dataset adapter. Do not treat a raw receipt or successful CSV parse as physical QC or inversion eligibility.

## Eligibility, admission and result

`GET /api/projects/{project_id}/datasets/{dataset_id}/methods` returns separate `methods` and `unavailable` arrays. M02 requires a provider-declared processed gravity anomaly in the local east/north/up frame, mGal, explicit Gaussian sigma semantics, an acquisition-group column, a declared background reference and a passing source/rights/storage check. It does not run missing M01 corrections. If these checks pass but the method switch is closed, the API reports `pending_host_admission`; clients must show that unavailable state instead of submitting. The active public service does not currently expose this branch's M02 route.

For the flag-only method, submit:

```json
{
  "dataset_id": "<dataset UUID>",
  "method_id": "gravity.station-outlier-flags/v1",
  "parameters": { "threshold": 6 }
}
```

to `POST /api/projects/{project_id}/jobs`. The threshold is 1-10. The 202 response is a queued, immutable request with dataset/request hashes and preflight limits; it is not a computed result. One queued/running job per account and 32 queued jobs globally are admitted by a SQLite write transaction; dataset creation is limited to 20 and job submission to 30 attempts per client address per hour. The private account quota covers raw and derived bytes plus an 8 MiB active-result reservation. The flag-QC method is capped at 256 MiB child RSS, 8 MiB scratch and 30 seconds wall. M02 has separate declared limits of 2 GiB RSS, 256 MiB scratch and 600 seconds, reduced by the worker's configured ceiling. These are admission caps, not a claim that every accepted survey will finish within them.

Poll `GET /api/projects/{project_id}/jobs/{job_id}`. States are `queued`, `running`, `succeeded`, `failed` or `cancelled`; non-success states carry an error code and no result URL. `POST .../cancel` immediately cancels queued work or requests termination of a running child. `GET .../result` is available only after success. It contains the original mGal and sigma arrays, station geometry, median, MAD, scaled MAD, robust scores, boolean flags, parameter/code/input hashes, rights and a flag-only lineage step. Threshold 6 flags only S5 in the table above; threshold 1 also flags S1. These are statistical controls, not claims that either station is geologically wrong.

`GET .../export` yields a processing ZIP with exactly `manifest.json`, `dataset.json` and `result.json`. It excludes raw CSV and private storage keys. The verifier checks member hashes, identity, shape, axes, units, rights, parameters and method-specific numerical invariants. For M02 it also checks the source and solver receipts and result closure; it does not establish field-geology accuracy. A recipient can verify a downloaded bundle locally:

```python
from pathlib import Path
from app.bundle import verify_bundle

manifest, dataset, result = verify_bundle(Path("processing.zip").read_bytes())
```

The ZIP is private project output; it does not publish or redistribute the original. A verified bundle establishes serialization and calculation consistency only within its declared method contract. It is not independent evidence that an inversion is geologically unique or field-validated.

## Failure, deletion and release boundary

Malformed dataset requests return field-specific 422 or 413. Ineligible methods, closed host admission, account/queue/quota limits, missing/changed private bytes, cancellation, child error, timeout, RSS and scratch breaches have typed non-success responses/statuses. The worker terminates the child/process tree on cancellation or resource breach; each fixed child watches a parent pipe so a worker crash stops it. On restart the worker marks abandoned `running` jobs `worker_interrupted`. Unknown staged or orphaned derivative bytes stop startup for restricted operator recovery; no automatic sweep occurs.

Project DELETE refuses active jobs, unverified derived files and any existing project backup entry. It records raw and derived hashes before removing only exact owned files. It makes no backup-erasure claim; backup inventory, purge and tombstone-aware restore remain a separate operator release gate.

Public online release requires the remaining M01-M13 numerical and data-method gates, shared schema review, frontend eligibility parity, full export/import acceptance, and nominal/upper/malformed plus cancellation/crash measurements on the actual ML VPS. The recorded M02 host run covers an authored synthetic survey only; its online switch and production services remain disabled. Local or host validation receipts do not imply deployment or public job availability.
