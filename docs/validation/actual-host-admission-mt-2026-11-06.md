# Actual ML VPS admission: online MT methods

## Scope

This report records the approved, isolated Linux admission run for the current-source M05 and M06 online methods. It is a bounded runtime and resource measurement on the canonical ML VPS, not scientific field validation or acceptance of the replacement application. The inputs are authored analytic half-space EDI controls. M05 performs tensor quality control; M06 performs the fixed-thickness 1D inverse after the required QC screen. No field geology or known field truth is involved.

The immutable source is commit `5a72fc336258f07bc84718b77791dcb83ea0fdfb`. Its streamed Git archive measured 876,482,560 bytes and SHA-256 `3e6487838bc5061696920a1734caea5e68d796b79a57a3bf5089f7033023eb5f`; the hash was checked on the VPS before extraction. The installed dependency inventory is SHA-256 `2df59416a5f25bb8697b61dc16eb52d295d6e64c93c3707ebc582f9f3100f4cf`. All six method/worker source hashes written by the benchmark matched the committed local source. The environment used Python 3.12.3 on Ubuntu 24.04, systemd 255, passed `pip check`, and did not install Torch.

## Applied service envelope

The test ran in transient unit `geophysics-admission-mt-20261106-5a72fc3`, invocation `fd2e7a0a82ec4835931d8b351d0e577e`. While active, systemd reported `DynamicUser=yes`, `StateDirectoryMode=0700`, `ProtectSystem=strict`, `ProtectHome=yes`, `PrivateTmp=yes`, `PrivateDevices=yes`, `PrivateNetwork=yes`, `NoNewPrivileges=yes`, `RestrictSUIDSGID=yes`, `ProtectKernelTunables=yes`, `ProtectKernelModules=yes`, `ProtectControlGroups=yes`, `RestrictRealtime=yes`, and an empty capability bounding set. The unit had `MemoryHigh=1610612736`, `MemoryMax=2147483648`, `MemorySwapMax=0`, `CPUQuotaPerSecUSec=2s`, `TasksMax=96`, and `RuntimeMaxUSec=30min`.

The runner finished with status 0. Runtime was 8 minutes 17.729 seconds, CPU time was 13 minutes 42.231 seconds, cgroup peak memory was 485.5 MB and swap peak was 0 bytes. No listener or external network was available to the unit.

## Nominal distribution

The harness completed 20 scored jobs for each method, plus the prerequisite M05 QC job used by the M06 cases. The source bytes were identical across the 40 scored method jobs. Each scored row retained its input, preflight, request and result identities in the private raw archive.

| Method | Jobs | p95 wall | Wall ceiling | p95 process RSS | RSS ceiling | p95 scratch | Scratch ceiling |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| M05 EDI tensor QC | 20 | 9,876 ms | 90 s | 244,056,064 B | 805,306,368 B | 53,880 B | 8,388,608 B |
| M06 fixed-thickness TRF | 20 | 10,099 ms | 300 s | 245,755,904 B | 1,073,741,824 B | 77,250 B | 33,554,432 B |

There were 5,028 authenticated application reads while jobs ran. Their p95 was 41.02 ms and maximum was 231.66 ms. These are same-process `TestClient` timings, not public HTTPS latency. The sampled minimum host `MemAvailable` was 4,915,912,704 bytes and minimum free disk was 25,645,625,344 bytes. The largest configured worker, API and bootstrap-controller reservations sum to 2,684,354,560 bytes; the maximum one-job scratch reservation was 33,554,432 bytes. Both were covered by the measured minimum headroom. The sampled parent-plus-child RSS peak was 428,810,240 bytes.

## Upper, malformed and interruption controls

The current-host benchmark recorded six controls: nominal M05 and M06 succeeded; upper-size M05 and upper-frequency M06 succeeded; a 5 MiB M05 upload succeeded; and the malformed M05 source ended in the expected durable `processing_failed` state without a result bundle. Requests above 64 M06 frequencies were rejected with HTTP 422 `method_ineligible`; uploads above 5 MiB were rejected with HTTP 413 `upload_too_large`.

The real parent-crash test killed a worker parent after observing its child. The child was no longer alive, the interrupted job persisted as `worker_interrupted`, operator review remained required for the disputed staging, and a subsequent job succeeded with a recorded result hash. This is supervised recovery, not automatic approval of interrupted staging.

The cancellation, timeout, memory/scratch and job-limit controls also ran in the same bounded unit. The exact host command completed **9 passed, 0 failed, 0 skipped** in 491.37 seconds, with one Starlette `TestClient` deprecation warning.

## Raw evidence and release boundary

The private archive `host-evidence.tar.gz` is retained under the device data root at `CAOS_Geophysics/host-admission/mt-20261106-5a72fc3/`. Its SHA-256 is `1737e6c4ae0dcec08f72ebda5ad60d2ac2a4f8517c42c36d095ab5f3ba699d43`. It contains the raw host receipts, five benchmark ZIPs, generated test state, applied unit-property record, dependency inventory and complete runner output. Raw records contain test-only identifiers and remain outside the public repository. The immutable source revision and dependency report remain recorded with the private host run.

In the post-test snapshot before staging cleanup, nginx remained active; the Geophysics API socket, API service and worker remained inactive. The public `current` symlink still resolved to `20260926235216`; the release tree still contained only current `20260926235216` and rollback releases `20260926233737` and `20260926200023`. The temporary source and virtual environment used 2,357,694,464 bytes and were removed after the evidence archive was verified. The subsequent disk snapshot showed 27,981,316,096 bytes available and `MemAvailable` of 5,121,268 kB. No public release, service activation, DNS, Nginx, account or project state was changed.

This closes the named actual-host M05/M06 nominal, upper/malformed and crash/resource measurements for this exact source and one VPS. It does not qualify gravity, ERT, seismic, joint or learned online workloads; candidate-release capacity; public HTTPS/browser behavior; all-method ownership/security; or the complete R-007/R-017 and product acceptance gates. The release ledger therefore remains unresolved.
