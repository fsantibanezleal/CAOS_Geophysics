# Actual ML-host MT admission observations

This is measured backend admission evidence, not a product release. The public site, nginx configuration, DNS, GitHub Pages and production private state are unchanged. Online MT activation remains closed.

## Immutable execution and restrictions

The first uploaded scientific runtime is committed revision `65132e960cd9a305d4241ad2a5b26c05e62a7ddf`, based on reviewed MT `7b69404`. Its selected Git source TAR was 1,433,600 bytes, SHA-256 `f5f0ee2cb9b6fed28d63cfbedf74597168461b55e796e4cfc8e9d1042d519ac9`, verified after SSH transfer. The server installed the pinned API/dev requirements in an isolated `.venv`; `pip check` passed. Runtime: Ubuntu Linux kernel 6.8.0-117, Python 3.12.3, NumPy 2.2.6, SciPy 1.15.2, MT Metadata 1.0.10, pandas 3.0.6, matplotlib 3.11.2, xarray 2026.9.0. Runtime venv size: 566 MiB. No Torch or server GPU is used.

Scientific work runs under a transient non-root DynamicUser with a private mode-0700 StateDirectory, strict read-only system filesystem, private network/devices/tmp, no capabilities, no new privileges, a 2 GiB cgroup ceiling and zero cgroup swap. Applied properties were read while the initial service was running: DynamicUser=yes, ProtectSystem=strict, PrivateNetwork=yes, MemoryMax=2,147,483,648, MemorySwapMax=0, CPUQuota=2 cores. The separate controls service uses the same policies with a one-core quota, not weaker memory/time/scratch limits. No listener is opened. The final `systemd-run` exit report's implausible 604 KiB memory peak for the controls service is NOT used as scientific memory evidence; application child-tree sampled RSS and the live unit observation are separate measurements.

## Actual controls, 06:48 UTC

The restricted controls invocation passed **6 tests** in **114.75 s**. These are the real parent-crash test, nominal/upper/malformed matrix, MT preflight/cancel/timeout/memory test and three generic worker failure/resource tests. The measured worker matrix receipt is retained privately under ignored `data/raw/host-admission/mt-controls-65132e9/benchmark.json`, SHA-256 `794ae956df662dc840a5726a9ae10ddfed5294958fdd9566a5bda778125aea3e`.

| Case | Result | Worker wall | Child-tree peak RSS | Peak scratch |
| --- | --- | ---: | ---: | ---: |
| Nominal 24-frequency M05 | success | 10,271 ms | 245,121,024 bytes | 53,880 bytes |
| Nominal M06, 20 bootstrap members | success | 10,929 ms | 246,939,648 bytes | 77,250 bytes |
| 64-frequency, exactly 5 MiB M05 | success | 10,497 ms | 264,994,816 bytes | 5,307,619 bytes |
| Same M06, 40 members | success | 13,214 ms | 272,162,816 bytes | 5,358,177 bytes |
| 512-frequency, exactly 5 MiB M05 | success | 10,426 ms | 269,565,952 bytes | 5,522,187 bytes |
| Missing required tensor block | failed/processing_failed, no export | 10,505 ms | 243,945,472 bytes | 38,296 bytes |

M06 rejects the passing 512-frequency QC input with 422/method_ineligible. Upload at 5 MiB + 1 byte rejects 413/upload_too_large. The imposed 350 m two-layer control independently recovers [120,12] ohm m within 0.5%; its generating model is never supplied to the solver. These are original synthetic oracle controls, not new field demonstrations. Upper-source exact hashes differ from the Windows generator's bytes; the actual Linux receipt binds its own measured bytes instead of assuming cross-platform byte identity. A numerical comparison is not an original-source hash substitute.

The real separate `app.worker` parent was killed with SIGKILL while its real `app.mt_compute` child existed. The child exited, normal recovery persisted failed/worker_interrupted with no result, then refused disputed staging as intended. Only that new harness stage was moved into retained operator quarantine with matching before/after hashes. A new M05 attempt succeeded. The actual crash receipt SHA-256 is `e1dc3d8b8a65da30107f0d337dd9ac10809efb8b5c53c6f518c42244fa689d04`. This establishes operator-assisted fail-closed recovery, not unattended restart.

## Distribution failure and corrected actual measurements

The first distribution invocation failed after 268.80 s because one isolated API store made more than the existing 30-jobs/IP/hour admission limit. Successful earlier job outputs and the failed store remain preserved; that run is not a passing forty-sample measurement. Production rate limits were not changed. Harness correction `f65e85a08a46a4106351249b420c2696e661c138` uses separate private stores per method: twenty M05 submissions, one prerequisite QC plus twenty M06 submissions. Incomplete invocations now retain a partial measurement receipt.

The new immutable selected source TAR SHA-256 is `4a1437c5487b9a305a28debbfcf80361423d7e00f6f58c9c1e6e68748cf36abd`. To avoid duplicate dependency disk consumption, its `.venv` is a read-only hardlink clone of the pinned admission environment, never updated in place; application/test source is the new revision. No other product environment is reused or modified.

The corrected restricted invocation completed all forty successful nominal jobs and retained the full receipt before failing the disk inequality. Runtime 350.32 s. Exact private `nominal-host-receipt.json` SHA-256: `63549f518d80a9146102a4cfe73276d561fa479ae9b4ed67138bf698d0c2b2cb`.

| Method | Attempts | Nearest-rank p95 wall | p95 child RSS | p95 scratch |
| --- | ---: | ---: | ---: | ---: |
| M05 | 20 | 8,651 ms | 245,182,464 bytes | 53,880 bytes |
| M06 | 20 | 8,511 ms | 247,214,080 bytes | 77,250 bytes |

These wall/RSS/scratch inequalities passed unchanged 70% ceilings. Observed parent-plus-child peak RSS was 428,449,792 bytes; host available RAM minimum was 4,806,569,984 of 8,127,717,376 bytes. The sampler observed 4,660 authenticated application reads: p95 34.386 ms, maximum 289.049 ms, not public HTTP/TLS latency. The test stopped at disk, so subsequent parent-tree/read assertions were not executed, although the retained values are independently below their stated thresholds. Full admission verdict is **FAIL**, not a filtered pass of the preceding checks.

## Unclosed host/release gates

Independent Windows re-import of the five actual Linux control ZIPs found a cross-platform near-zero residual defect in the original M06 verifier: a one-ULP re-evaluated prediction changes the subtraction while the exported prediction/residual pair remains internally consistent. Main preserved the originals and isolated the fix on `task/geophysics-mt-bundle-parity`, without altering this immutable executed runtime or its measurements. The corrected verifier checks prediction against independent physics with the unchanged tolerance, then checks the residual against the exact already-validated exported prediction, also with unchanged tolerance. The regression reproduces the failure before the fix and rejects re-hashed corruptions afterwards. All five original Linux bundles pass re-import with that correction; the correction is not yet a deployed runtime or full host acceptance.

| Private Linux export | Bytes | SHA-256 |
| --- | ---: | --- |
| nominal-m05.zip | 19035 | `45d5992a2ac721cfd3579843568ba814c0a913f31879ec8a48d14cc9455ccc35` |
| nominal-m06-20.zip | 42549 | `fcd47647a864f1e498064fe51dbb266c1a5004df9cde02d48929e6916e84471e` |
| upper-m05.zip | 38823 | `313159afca37d720c6ed8985035f3b2bd77f550377df20a2a8438e232a3c035d` |
| upper-m06-40.zip | 89537 | `40d590a9e36b924e1f8343c4a330ca3990fa87fcea0dbb34a8b8813df0a00615` |
| upper-m05-512-5mib.zip | 253396 | `68970962a66a3a24246b6898c41ee21de6ee73723b57dc1ede9e6d558a82ef77` |

After runtime installation root free space was 23,650,004,992 of 80,290,492,416 bytes, **29.45%**; the actual corrected distribution minimum was 23,622,492,160 bytes (**29.42%**). Both are below the approved 30% disk threshold. No threshold was lowered and no old release directory was deleted/compressed. Owner direction about lossless compression of obsolete geophysics releases is pending. Keep the current active and two newest rollback releases intact. Existing server age is 1.1.1, below the separately reviewed recovery tooling's maintained 1.3.1 minimum; a provenance-verified isolated binary is needed for the restore drill, not a global blind upgrade.

Nominal p95 and minimum host memory/disk headroom are now measured, with the disk gate failing. These TestClient reads do not establish nginx/public HTTPS responsiveness. Backup/restore, durable external deletion authority, approved SMTP delivery, full field/method/data/UI/wiki convergence, external HTTPS/browser and single-origin cutover remain separate gates. No valid cutover receipt or full-product acceptance is asserted here.
