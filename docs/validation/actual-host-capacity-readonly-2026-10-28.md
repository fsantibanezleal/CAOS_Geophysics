# ML VPS capacity and publication snapshot (read-only)

Observed 2026-10-28 at 12:18 UTC over the approved SSH identity with strict host-key checking. Target `ml-fasl-work` (`89.167.4.175`). The host, release tree, services, DNS, account state and active symlink were not changed.

## Current public state

- `https://geophysics.ml.fasl-work.com/` returned HTTP 200. Its 801-byte HTML response was last modified 2026-09-26.
- `current` resolves to `/var/www/geophysics.ml.fasl-work.com/releases/20260926235216`, the legacy 0.04.001 static release.
- The API socket, API service and worker service were inactive. There was no active geophysics service deployment.
- The GitHub Pages API returned 404 and the former `fsantibanezleal.github.io/CAOS_Geophysics/` URL returned HTTP 404. No duplicate GitHub Pages application was active in this observation.
- A listener on 127.0.0.1:8174 belongs to Neuraxis Operations. It is unrelated and was not inspected beyond process name and working directory or changed.

## Shared host capacity

| Measurement | Observed |
|---|---:|
| Root filesystem total | 80,290,492,416 bytes |
| Root filesystem used | 73,310,773,248 bytes |
| Root filesystem available | 3,652,116,480 bytes |
| Root filesystem reported use | 96% |
| `MemAvailable` | 5,300,334,592 bytes |
| Swap used | 752,877,568 bytes |

Read-only logical directory totals were `/var` 52,720,844,800 bytes, `/var/www` 41,230,503,936 bytes, `/opt` 10,475,483,136 bytes, `/usr` 2,742,304,768 bytes, `/srv` 1,709,158,400 bytes, and `/root` 952,541,184 bytes. These totals are not all unique physical allocations and do not authorize removing any other product's data.

## Geophysics release tree

The release directory contains 33,736,204,288 logical bytes across 31 direct release directories. The active release and two prior dated releases total 2,322,509,824 bytes:

| Retained role | Directory | Bytes |
|---|---|---:|
| Current | `20260926235216` | 817,393,664 |
| Rollback 1 | `20260926233737` | 817,401,856 |
| Rollback 2 | `20260926200023` | 687,714,304 |

The remaining 28 direct release directories total 31,413,694,464 logical bytes. They include older dated releases, three `20261004-qual-*` builds, interrupted transfer `release-0b2ea33`, and failed runtime or bootstrap qualification candidates. The directories were individually inventoried; none is the `current` symlink target. Their measured sizes are recorded below.

| Directory | Bytes | Directory | Bytes |
|---|---:|---|---:|
| `20260913081418` | 4,059,136 | `20260913081833` | 4,059,136 |
| `20260913082247` | 4,059,136 | `20260913082518` | 4,059,136 |
| `20260913082806` | 4,059,136 | `20260913083406` | 13,213,696 |
| `20260913083607` | 13,213,696 | `20260924031106` | 136,183,808 |
| `20260924032105` | 136,183,808 | `20260924044648` | 463,208,448 |
| `20261004-qual-35c30dc` | 1,389,305,856 | `20261004-qual-72d303b` | 1,389,285,376 |
| `20261004-qual-837c154` | 1,389,326,336 | `release-0b2ea33` | 2,703,360 |
| `release-0b2ea33b` | 857,853,952 | `release-5355478` | 857,882,624 |
| `release-42268c9` | 1,349,541,888 | `release-94ad4f4` | 1,411,309,568 |
| `release-033a5e7` | 2,197,209,088 | `release-0517c13` | 2,197,221,376 |
| `release-37f1883` | 2,197,209,088 | `release-8f192e8` | 2,197,336,064 |
| `release-8f192e8b` | 2,197,237,760 | `release-9d203f1` | 2,197,336,064 |
| `release-92e53bd` | 2,203,107,328 | `release-b544af1` | 2,197,204,992 |
| `release-ca9e2c1` | 2,197,204,992 | `release-d576a9d` | 2,203,115,520 |

`/var/lib/geophysics` contained 225,280 logical bytes. The project and derived directories contained only directory entries in the bounded inspection; no regular project or derived files were reported in the prior 2026-10-27 snapshot. No database or project state was read or modified.

## Readiness consequence

The current host has only 3.65 GB free, while the prior local qualification bundle was 856,103,491 bytes before service-runtime installation and scratch reservation. This is not a fresh capacity admission for the current branch. No capacity, job, ownership, cancellation, whole-product or replacement-release gate is claimed. The active public service remains the legacy static application.

`docs/guides/18_service_release.md` requires final product gates before activation and directs operators to retain the current release plus two explicitly qualified rollbacks. It also requires inspecting and approving each extra ordinary release directory before removal. This snapshot makes the required review concrete; no release directory was removed or compressed.
