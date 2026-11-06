# ML VPS read-only capacity check: 2026-11-06

Observed at `2026-11-06T08:03:08Z` over the configured SSH identity. The
follow-up per-release byte scan completed at the same session. These commands
were read-only. No release, service, account, project data, or host
configuration was changed.

## Current VPS state

| Measurement | Observed |
| --- | ---: |
| Root filesystem total | 80,290,492,416 bytes |
| Root filesystem used | 48,954,134,528 bytes |
| Root filesystem available | 28,008,755,200 bytes (64% used) |
| `/proc/meminfo` `MemAvailable` | 5,244,616,704 bytes |
| Active release | `20260926235216` |
| Current release logical bytes | 817,393,664 |
| First rollback `20260926233737` logical bytes | 817,401,856 |
| Second rollback `20260926200023` logical bytes | 687,714,304 |
| Current plus two rollback logical bytes | 2,322,509,824 |
| Geophysics release-tree logical bytes | 2,322,522,112 |
| `/var/lib/geophysics-deploy` logical bytes | 3,193,536,512 |
| `/var/lib/geophysics` logical bytes | 262,144 |
| Nginx | active |
| API socket, API service, worker | inactive |

The release tree contains exactly the current release and those two rollback
directories. All three are intact. The canonical `current` symlink resolves to
`20260926235216`.

## External HTTPS observations

- `https://geophysics.ml.fasl-work.com/`: HTTP 200, `text/html`, 801 bytes.
- `/data/v2/catalog.json`: HTTP 200, 348,353 bytes, release `0.04.001`.
- `/api/health`: HTTP 200 but `text/html`, 801 bytes. This is the SPA fallback,
  not an API health response.

The VPS still serves the legacy static release. Authenticated projects and
server-side compute are not live on this release.

## Commands

The root-only snapshot used the approved SSH key without recording its path:

```sh
date -u +%Y-%m-%dT%H:%M:%SZ
df -B1 /
grep MemAvailable /proc/meminfo
readlink -f /var/www/geophysics.ml.fasl-work.com/current
find /var/www/geophysics.ml.fasl-work.com/releases -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort
du -s -B1 /var/www/geophysics.ml.fasl-work.com /var/lib/geophysics-deploy /var/lib/geophysics
systemctl is-active nginx geophysics-api.socket geophysics-api.service geophysics-worker.service
du -s -B1 /var/www/geophysics.ml.fasl-work.com/releases/20260926235216 /var/www/geophysics.ml.fasl-work.com/releases/20260926233737 /var/www/geophysics.ml.fasl-work.com/releases/20260926200023
```

## Admission boundary

This is a fresh host inventory, not replacement-release admission. It does not
measure the current candidate bundle or its extracted runtime, active project
growth, concurrent job memory/scratch, timeout/cancellation/recovery, or
authenticated owner workflows. It does not change service activation. A
qualified bundle and the full numerical, account, ownership, browser, and
actual-worker gates remain prerequisites before cutover.
