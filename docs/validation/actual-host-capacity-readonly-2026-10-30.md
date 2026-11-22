# ML VPS capacity and deployment-state receipt (read-only)

Observed: 2026-10-30 12:43:12 UTC over the repository's recorded SSH identity with strict host-key checking. Commands were read-only. No release, service, account, project data, DNS, or Nginx configuration was changed.

## Live deployment state

- Canonical origin: `https://geophysics.ml.fasl-work.com/`.
- The `current` symlink resolves to the legacy `0.04.001` release directory `20260926235216`.
- Nginx is active; `geophysics-api.socket`, `geophysics-api.service`, and `geophysics-worker.service` are inactive.
- The release root contains 31 direct release directories. Current plus the two recorded rollback releases total 2,322,509,824 logical bytes.

## Shared capacity

| Measurement | Observed |
|---|---:|
| Root filesystem total | 80,290,492,416 bytes |
| Root filesystem used | 76,061,892,608 bytes |
| Root filesystem available to non-root | 900,997,120 bytes |
| Reported root use | 99% |
| `/proc/meminfo` `MemAvailable` | 5,173,907,456 bytes |
| `/var/www` logical usage | 43,293,372,416 bytes |
| Geophysics web/release tree logical usage | 33,736,204,288 bytes |
| `/var/lib/geophysics` logical usage | 262,144 bytes |
| `/var/lib/geophysics-deploy` logical usage | 3,193,536,512 bytes |

Logical directory sizes can include data not uniquely allocated to those paths. The root filesystem's non-root available-byte count, rather than total-minus-used, is the relevant staging measure.

## Admission consequence

The repository's API-runtime stager requires at least 4 GiB available before installation. The observed 900,997,120 bytes do not meet that precondition. The current host therefore cannot pass the existing runtime-staging capacity check at this observation. This is a measured host-state failure, not a whole-host percentage policy. The current release and its two rollback releases remain intact. Other release directories and `/var/lib/geophysics-deploy` were measured but not deleted or modified. No replacement candidate was uploaded or activated.

This receipt does not establish CPU-worker containment, actual per-method job capacity, service health, scientific acceptance, or complete release acceptance. Re-measure after any separately reviewed host-storage change and before candidate admission.
