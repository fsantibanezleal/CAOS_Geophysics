# Private gravity-station processing jobs

This unreleased API branch adds one authenticated, bounded processing operation: `gravity.station-outlier-flags/v1`. It flags statistical outliers without changing observations, uncertainty or station order. It is not a gravity datum/correction chain, physical inversion, M01 completion, validated geological model or public online-method release. No `/api/jobs` solver endpoint is present.

## Local process separation

Install `requirements-api.txt` and run `alembic -c app/alembic.ini upgrade head` before starting the API. Start the API as in [the API guide](06_api.md). In a separate terminal using the same private data root and database path, start one worker:

```powershell
$env:GEOPHYSICS_DATA_DIR = 'D:\private\geophysics-api'
$env:GEOPHYSICS_DB_PATH = 'D:\private\geophysics-api\api.sqlite3'
.\.venv-api\Scripts\python.exe -m app.worker
```

The worker needs only the private root and SQLite path, not SMTP or authentication secrets. Run it under a restricted OS identity with read/write access to that root and read-only application code. A process lock permits one worker. The API never runs the processing engine in its request/background-task process. The worker launches only the fixed `app.compute` child with an argument vector, a sanitized environment, private scratch working directory and no shell. [psutil 7.2.2](https://pypi.org/project/psutil/7.2.2/) supplies process-tree RSS/termination; its [process API](https://psutil.readthedocs.io/stable/) is the reviewed monitoring dependency. This is local engineering evidence, not an actual-ML-VPS resource benchmark.

## From a raw upload to a typed dataset

Upload an owner-only gravity CSV using [the raw-asset API](06_api.md). In addition to its mandatory physical metadata, set `physical.geometry.sigma_column` to a sixth, distinct CSV column. The API dataset parser accepts exactly the six declared station/x/y/z/value/sigma columns, 4-4096 stations and at most 2 MiB. EPSG projected xy metres, vertical metres, mGal observations and strictly positive per-station sigma in mGal are required. Nonfinite values, duplicate station IDs or XYZ triples, missing/extra columns and missing uncertainty are rejected. No projection, unit, correction, missing-value replacement or outlier exclusion is inferred.

For example, with geometry columns `station,x,y,z,g,sigma`:

```csv
station,x,y,z,g,sigma
S1,0,0,100,1,0.1
S2,10,0,100,2,0.1
S3,20,0,100,3,0.1
S4,30,0,100,4,0.1
S5,40,0,100,100,0.1
```

After the verified upload, send `POST /api/projects/{project_id}/datasets` with `{ "asset_id": "<uploaded asset UUID>" }`. The response supplies a dataset ID, raw hash, dataset hash and `parsed_for_flag_qc_only` verdict. `GET /datasets/{dataset_id}` returns the typed, immutable observations, sigma, station axis, physical metadata, rights and empty correction history. Its original raw file remains unchanged. One raw asset can create one dataset at this parser version; a second request returns `409 dataset_exists`.

The local `data-pipeline/ingest.py` five-column `east_m,north_m,up_m,value,sigma` inversion CLI is a different workflow, and its curated tar/EDI dispatcher does not emit this API dataset schema. Do not treat the presence of a raw upload receipt as a modelling QC pass or claim parser parity without INT-PJ-INGEST-01.

## Eligibility, admission and result

`GET /api/projects/{project_id}/datasets/{dataset_id}/methods` lists the flag-only processing method as eligible and M01-M13 complete methods as `not_activated` with a reason. Submit only:

```json
{
  "dataset_id": "<dataset UUID>",
  "method_id": "gravity.station-outlier-flags/v1",
  "parameters": { "threshold": 6 }
}
```

to `POST /api/projects/{project_id}/jobs`. The threshold is 1-10. The 202 response is a queued, immutable request with dataset/request hashes and preflight limits; it is not a computed result. One queued/running job per account and 32 queued jobs globally are admitted by a SQLite write transaction; dataset creation is limited to 20 and job submission to 30 attempts per client address per hour. The private account quota covers raw and derived bytes plus an 8 MiB active-result reservation. The flag-only method is capped at 256 MiB child RSS, 8 MiB scratch and 30 seconds wall; host-level ceilings are 2 GiB/1 GiB/10 minutes, not permission to run larger methods.

Poll `GET /api/projects/{project_id}/jobs/{job_id}`. States are `queued`, `running`, `succeeded`, `failed` or `cancelled`; non-success states carry an error code and no result URL. `POST .../cancel` immediately cancels queued work or requests termination of a running child. `GET .../result` is available only after success. It contains the original mGal and sigma arrays, station geometry, median, MAD, scaled MAD, robust scores, boolean flags, parameter/code/input hashes, rights and a flag-only lineage step. Threshold 6 flags only S5 in the table above; threshold 1 also flags S1. These are statistical controls, not claims that either station is geologically wrong.

`GET .../export` yields a ZIP with exactly `manifest.json`, `dataset.json` and `result.json`. No raw CSV or private storage key is included. A recipient can re-import and verify the processing-only bundle locally:

```python
from pathlib import Path
from app.bundle import verify_bundle

manifest, dataset, result = verify_bundle(Path("processing.zip").read_bytes())
```

The verifier rejects member hash, identity, shape, axis, unit, rights, parameter and numerical-flag drift. This is not the parent SDD's full solver-result export contract (R-011).

## Failure, deletion and release boundary

Malformed dataset requests return field-specific 422 or 413. Ineligible methods, account/queue/quota limits, missing/changed private bytes, cancellation, child error, timeout, RSS and scratch breaches have typed non-success responses/statuses. The worker terminates the child/process tree on cancellation or resource breach; the fixed child watches a parent pipe so a worker crash stops it. On restart the worker marks abandoned `running` jobs `worker_interrupted`. Unknown staged or orphaned derivative bytes stop startup for restricted operator recovery; no automatic sweep occurs.

Project DELETE refuses active jobs, unverified derived files and any existing project backup entry. It records raw and derived hashes before removing only exact owned files. It makes no backup-erasure claim; backup inventory, purge and tombstone-aware restore remain a separate operator release gate.

Online scientific release remains blocked on independent M01 correction/holdout and other M01-M13 numerical gates, shared ingestion-schema review, frontend eligibility parity, full R-011 export, and nominal/upper/malformed plus cancellation/crash benchmarks on the actual ML VPS with 30% host headroom. No deployment or public job availability is implied by these local tests.
