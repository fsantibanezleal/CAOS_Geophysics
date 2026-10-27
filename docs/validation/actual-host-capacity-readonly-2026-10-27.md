# ML VPS capacity snapshot (read-only)

Observed at **2026-10-27 17:25:29 UTC** over the approved SSH identity, with the host key checked against the workstation's existing `known_hosts` entry. Target: `ml-fasl-work` (`89.167.4.175`). No files, services, accounts, firewall rules, DNS, or release pointers were changed.

## Host and shared capacity

| Measurement | Observed value |
| --- | ---: |
| Root filesystem size | 80,290,492,416 bytes |
| Root filesystem used | 44,565,065,728 bytes |
| Root filesystem available to root | 32,397,824,000 bytes |
| Available CPU count | 4 |
| `MemTotal` | 8,127,717,376 bytes |
| `MemAvailable` | 5,270,228,992 bytes |
| Swap total / used | 4,294,963,200 / 686,817,280 bytes |
| Uptime / load average | 108 days 16:08 / 0.27, 0.15, 0.14 |

The host is shared. A read-only top-level logical disk scan measured `/var` at 23,932,809,216 bytes, `/opt` at 10,475,483,136 bytes, `/usr` at 2,742,304,768 bytes and `/root` at 951,283,712 bytes. Within `/var`, `/var/www` used 14,767,030,272 bytes and `/var/lib` 8,488,636,416 bytes. Within `/opt`, `fasl-apps` used 4,792,221,696 bytes, `fasl-admission` 4,025,081,856 bytes, and `neuraxis-operations` 1,658,163,200 bytes. These are logical directory totals and can include shared filesystem allocation effects; they do not identify data eligible for deletion.

## Existing geophysics state

The canonical origin still resolves to the static `current` release:

`/var/www/geophysics.ml.fasl-work.com/releases/20260926235216`

The active release contains 816,111,047 logical bytes. The two immediately preceding dated static releases contain 816,120,188 bytes (`20260926233737`) and 686,433,273 bytes (`20260926200023`). Three later qualification directories contain 1,352,061,332 bytes (`20261004-qual-35c30dc`), 1,352,043,163 bytes (`20261004-qual-72d303b`) and 1,352,079,275 bytes (`20261004-qual-837c154`); they are qualification artifacts, not current releases or approved rollback targets. The release tree also contains older dated artifacts. Nothing was pruned.

The private state at `/var/lib/geophysics` contains a 192,512-byte SQLite database; `/var/lib/geophysics/projects` and `/var/lib/geophysics/derived` contain no regular-file bytes. The state directory is mode `0700`, owned by `geophysics`; the database is mode `0600`, owned by `geophysics`.

No persistent geophysics API or worker service appeared in the active system-service listing during this snapshot. The existence of the database and prior isolated qualification units does not prove that replacement API/worker workflows are live.

## Admission boundary

This snapshot does **not** establish capacity for the proposed immutable release plus two rollback releases, API/runtime installation, configured job scratch, retained user projects, or worker/API/controller memory ceilings. Those candidate byte and memory bounds have not yet been measured together, and the actual-host job, cancellation, ownership, HTTPS/API hydration and browser acceptance gates remain open. The host has capacity headroom, but R-007 remains unresolved and no release is admitted or deployed by this evidence.

Commands were limited to read-only `df`, `free`, `readlink`, bounded directory-size scans, metadata/stat checks, service listings and process summaries. The raw values above are the relevant measured facts; this note does not authorize or propose deletion of unrelated application data.
