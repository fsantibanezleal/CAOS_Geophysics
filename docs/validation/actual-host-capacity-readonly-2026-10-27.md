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

At the time of this initial snapshot, capacity for the proposed immutable release plus two rollback releases, API/runtime installation, configured job scratch, retained user projects, and worker/API/controller memory ceilings had not been measured together. The follow-up below compares the then-current host snapshot with a locally prepared candidate bundle and configured reserves. API/runtime installation size, retained user data after onboarding, actual-host job/resource behavior, cancellation, ownership, HTTPS/API hydration and browser acceptance remain unqualified. R-007 remains unresolved and no release is admitted or deployed by this evidence.

Commands were limited to read-only `df`, `free`, `readlink`, bounded directory-size scans, metadata/stat checks, service listings and process summaries. The raw values above are the relevant measured facts; this note does not authorize or propose deletion of unrelated application data.

## Follow-up: candidate bundle and live capacity: 2026-10-27 20:39 UTC

A second read-only SSH observation at 20:39:02 UTC confirmed the active symlink still resolves to `releases/20260926235216`; the two retained prior releases remain `20260926233737` and `20260926200023`. Their measured regular-file totals were 816,111,047, 816,120,188 and 686,433,273 bytes. Root filesystem free bytes were 32,396,886,016; `MemAvailable` was 5,284,040,704 bytes and free swap was 3,525,372 KiB. `systemctl is-active` returned inactive for the geophysics API socket/service and worker; `/run/geophysics-api.sock` was absent. No remote files, service state or active release were changed.

The clean local qualification bundle for source revision `f80dd9145231c48bfc497a3566e13b36c391c448` was prepared and hash-verified by `scripts/prepare_service_release.py`. Its manifest SHA-256 is `5e13acd70058f6e640dbeb70723734f4fe6acac405474377ae73168566c0be93`. The bundle contains 385 source files (8,915,430 bytes), 283 web files (847,093,983 bytes), and an 87,506-byte manifest: 856,096,919 total logical bytes. It explicitly records `qualification_only=true` and `full_release_accepted=false`; it was not uploaded. The `.venv` and `.venv-gravity` runtime environments are absent from the bundle and their actual installation sizes remain unmeasured.

Simple capacity arithmetic leaves 30,467,047,273 bytes after the current observed free space is reduced by the candidate bundle and the configured 1 GiB job-scratch reserve. The 5,284,040,704 observed available-memory bytes exceed the configured API (512 MiB), worker (2 GiB) and bootstrap-controller (1 GiB) ceilings by 1,525,944,320 bytes. The exact inputs are in [service-capacity-preflight-2026-10-27.json](service-capacity-preflight-2026-10-27.json); `verify_single_vps_release.validate_capacity` reports the supplied inventory is internally consistent and three releases are named, while explicitly returning `host_measurement_verified=false`. These comparisons do not measure installed runtime bytes, concurrent service load, actual per-job RSS/scratch, job timeout/cancellation/recovery, or owner workflows. They are a bounded preflight only; R-007 and release admission remain unresolved.

## Follow-up: current branch qualification snapshot, 2026-10-27 21:15 UTC

A fresh read-only SSH observation at 21:15:04 UTC confirms that the active origin remains `/var/www/geophysics.ml.fasl-work.com/releases/20260926235216`; the two required rollback releases remain `20260926233737` and `20260926200023`. Their logical byte totals are unchanged at 816,111,047, 816,120,188 and 686,433,273. Root filesystem available bytes are 32,396,664,832; `MemAvailable` is 5,253,464,064 bytes and free swap is 3,525,372 KiB. `/var/lib/geophysics/projects` and `/var/lib/geophysics/derived` each contain zero regular-file bytes. The API socket/service and worker are inactive; this remains a static legacy release.

The current clean source revision `fa2da6a5a05f0bad755b9c832b5ec71cced3f11b` was built locally and packaged as a qualification-only bundle at `E:\_Temp\geophysics-qa\release-fa2da6a`. Its 386 source files total 8,921,851 bytes; 283 web files total 847,093,983 bytes; its 87,657-byte manifest has SHA-256 `a677b2cc8e7d36c35794b3f001a1862f1c8e0a0c5162cf3c29885d1b2abe9496`. The complete bundle totals 856,103,491 bytes and explicitly sets `qualification_only=true` and `full_release_accepted=false`.

Using the measured free space, the candidate bundle and the configured 1 GiB job-scratch reserve leave 30,466,819,517 bytes before runtime installation. The available memory exceeds the explicit API (512 MiB), worker (2 GiB) and bootstrap-controller (1 GiB) ceilings by 1,495,367,680 bytes. The updated [capacity preflight](service-capacity-preflight-2026-10-27.json) records the exact inputs. Existing releases and project files already consume the observed filesystem and are not subtracted a second time. The candidate was not uploaded; Linux runtime installation size, future retained project bytes, execution-time memory under other hosted services, per-job resource behavior, cancellation/recovery and owner/browser workflows remain unmeasured. No host files, services, accounts or release pointers changed. R-007 and release admission remain unresolved.
