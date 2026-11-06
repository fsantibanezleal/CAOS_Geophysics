# ML VPS state refresh: 2026-11-06

Read-only SSH and HTTPS observations at 2026-11-06 11:38-11:40 UTC. No host
files, services, users, firewall, DNS, deployment pointer, or application data
were changed.

## Active release and retention

The `current` pointer resolves to legacy static release
`20260926235216`. The release directory contains exactly three directories,
preserving the current release and two rollbacks:

| Role | Release ID | Logical bytes |
|---|---:|---:|
| Current | `20260926235216` | 816,111,047 |
| Rollback | `20260926233737` | 816,120,188 |
| Rollback | `20260926200023` | 686,433,273 |

The 28 previously identified extra release directories are absent. This
refresh did not prune anything.

## Host capacity and services

The root filesystem measured 80,290,492,416 bytes total, 48,955,027,456 used,
and 28,007,862,272 available (64% used). `MemAvailable` was 5,230,358,528
bytes. Nginx was active; `geophysics-api.socket`, `geophysics-api.service`,
and `geophysics-worker.service` were inactive. The product data root measured
262,144 logical bytes. `/var/lib/geophysics-deploy` measured 3,193,536,512
bytes; its largest entries were `runtime-release-8f192e8b` (1,523,105,792
bytes), `python-runtimes` (702,406,656 bytes), and three `runtime-*-upload`
directories totalling 876,593,152 bytes. These are candidate/runtime staging
artifacts, not public releases. This receipt only inventories them.

## Canonical HTTPS behavior

`GET https://geophysics.ml.fasl-work.com/` returned 200 `text/html`, 801
bytes. `GET /api/auth/config` also returned 200 `text/html`, 801 bytes, with
the same last-modified timestamp and ETag as the SPA shell. It did not return
the authentication JSON contract. Together with the inactive API and worker,
this confirms the public VPS still serves the legacy static application; the
replacement API/job service is not live.

## Deployment consequence

The current release and two rollback releases remain intact, and measured
free disk exceeds the prior 4 GiB staging precondition. This is capacity
evidence only; it does not qualify runtime installation, API/worker admission,
method execution, job limits, cancellation, browser/API integration, or a
replacement release. The active pointer remains on the legacy release.
