# ML VPS read-only capacity check — 2026-10-31

Refreshed at `2026-10-31T08:01:00Z` from the direct product checkout at `9f022aae8d178211b4c77730b722723fc3345a3b`; the working tree had 73 changed paths. This was a read-only check. No release, service, account, project data, or host configuration was changed.

## Live origin

`https://geophysics.ml.fasl-work.com/` returned HTTP 200 over HTTPS with `nginx/1.24.0`. The page title was `Inverse Earth Studio | Geophysics`; `/data/v2/catalog.json` returned HTTP 200 and declares `0.04.001`.

`/api/health` also returned HTTP 200, but its content type was `text/html` and its body was the SPA `index.html`. This is the static fallback, not an API health response; it confirms the public API route is not live.

## Host resources and release retention

| Measurement | Result |
|---|---:|
| Root filesystem | 80,290,492,416 bytes total; 45,213,458,432 used; 31,749,431,296 available (59%) |
| `/proc/meminfo` `MemAvailable` | 5,228,388,352 bytes |
| Active release | `20260926235216` |
| Retained release directories | `20260926200023`, `20260926233737`, `20260926235216` |
| Geophysics release tree | 2,322,522,112 bytes logical |
| `/var/lib/geophysics-deploy` | 3,193,536,512 bytes logical |
| `/var/lib/geophysics` | 262,144 bytes logical |
| API service | inactive |
| Worker service | inactive |

The active release and exactly two rollback release directories are present; there were no extra release directories to prune, so no deletion was performed. Free root space exceeds the current 4 GiB runtime-stager precondition. The static application is still the legacy `0.04.001` release; the replacement has not been staged or activated.

## Commands

Read-only commands used (the SSH identity path is supplied locally and is not recorded):

```powershell
ssh -i $key root@89.167.4.175 "date -u +%Y-%m-%dT%H:%M:%SZ; df -B1 /; grep MemAvailable /proc/meminfo; readlink -f /var/www/geophysics.ml.fasl-work.com/current; find /var/www/geophysics.ml.fasl-work.com/releases -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort; systemctl is-active geophysics-api.service geophysics-worker.service; du -s -B1 /var/www/geophysics.ml.fasl-work.com /var/lib/geophysics-deploy /var/lib/geophysics"
```

HTTPS reads used `Invoke-WebRequest` against the canonical origin and `/data/v2/catalog.json`.

## Acceptance boundary

This establishes current disk/memory availability, the active static release, and the three retained release directories. It does not accept the replacement's API/worker isolation, account/project workflows, scientific methods, or browser behavior. Both online services remain inactive and `/api/health` resolves to the SPA fallback, so hosted project creation and server-side jobs are not available in this release.
