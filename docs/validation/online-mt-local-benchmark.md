# Bounded EDI M05/M06 local resource receipt

Date: 2026-10-03. Receipt UTC: `2026-10-03T06:21:00.824554+00:00`. Host: Windows 11 build 26300, Python 3.12.10. Code milestone: `c187ebc`, based on develop `2202ebd`. These are **local** measurements through the authenticated API and actual singleton worker/child, not measurements on the ML VPS. No public listener opens.

The fresh `.venv-online-mt-oct3` has `include-system-site-packages = false`, passes `pip check`, and has no Torch. It was installed from `requirements-api.txt` and `requirements-dev.txt`. Actual scientific versions: NumPy 2.2.6, SciPy 1.15.2, MT Metadata 1.0.10, pandas 3.0.6, matplotlib 3.11.2, xarray 2026.9.0; psutil 7.2.2. The earlier `.venv-ingestion` is preserved, but has system-site access and is not an isolated runtime receipt. Reproduce in a fresh environment and a new, short private temporary directory; never reuse a directory whose outputs must be preserved:

```powershell
$env:GEOPHYSICS_RUN_LOCAL_MT_BENCHMARK = '1'
.\.venv-online-mt-oct3\Scripts\python.exe -m pytest -s -q -x -o addopts= --basetemp data/raw/b-next tests/api/test_online_mt_benchmark.py::test_local_nominal_upper_malformed_admission
```

The measured invocation used `--basetemp data/raw/b4` and passed in 43.20 s. Its private artifacts remain at `data/raw/b4/test_local_nominal_upper_malfo0/case-0/mt-receipts/`: canonical `benchmark.json` (SHA-256 `ab3e5ed26c0267fbb820e5767a28fa2633ec792f366add5b18b6510f766d478a`) and five successful-job ZIPs. Neither raw files nor private artifacts are committed. See the [contract and status matrix](../data-contract/02_online-edi-mt.md) for the host/frontend handoff.

The receipt schema is `geophysics.mt-admission-benchmark/v1`. It includes actual dependency/isolation/platform data, scientific code SHA-256 map, exactly measured original hashes/bytes, rejection statuses, and rows with request/preflight/job/dataset/result identity, state/error, worker/end-to-end wall, sampled child-tree RSS, scratch and bundle filename/hash/bytes. `host_activation_asserted=false`. Each ZIP contains exactly canonical `manifest.json`, `dataset.json`, `result.json`, with no private original. Result identities include actual scientific Python/package versions and their digest; UUID-bound result and bundle hashes change with each invocation.

| Source | Frequencies / bytes | Original SHA-256 |
| --- | --- | --- |
| Analytic 100 ohm m halfspace | 24 / 8,935 | `904f1e183f665ed642ff07d42ac3c1d7a4569b9590abe1d111401110db650039` |
| Independent two-layer reflection formula | 64 / 5,242,880 | `e603fadeb6871d9f0e101496a824295f009589b229e612e6bc62a676f363f70a` |
| M05 upper-dimensional reflection formula | 512 / 5,242,880 | `cb7017ac570b1e7a48c611bfeec74ac09830d5951af438bbc71f8f80a4a99d6d` |
| Missing required ZXY real block | 24 declared / 8,938 | `b39851f0b61a22ebe9fc101009818ac1444a9f8b6dd27ca5d7b8969bfb0e6a0c` |

The two upper sources use EDI comment padding to exercise the exact byte boundary without inventing additional observations. Their independent reflection formula is in `tests/api/test_online_mt_benchmark.py`; the inverse does not import that generator or receive the generating resistivities. The 64-frequency M06 recovers [120,12] ohm m within 0.5% at imposed 350 m thickness. The separate API gate checks the halfspace oracle, noisy layered parameter effects and conditional intervals.

| Case | State | Worker wall ms | End-to-end ms | Peak child tree RSS bytes | Peak scratch bytes | Result SHA-256 / failure |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Nominal M05 | succeeded | 8,891 | 8,974 | 248,025,088 | 252,473 | `f3f913a437308a924c2ff72ec17e67d2ed3b56335479209ad3c3a4686b156b96` |
| Nominal M06, 20 members | succeeded | 9,312 | 9,394 | 248,459,264 | 276,264 | `b9b63b788943d72e03667daf62c3b67ecebd0f856fe877d4fdd8625569bfc4e9` |
| Upper M05, 64 frequencies / 5 MiB | succeeded | 6,108 | 6,185 | 269,619,200 | 5,506,196 | `b831d1205c70bb1a275c97bcd25c42138ca4173779a49d1671cedc953c0d6f24` |
| Upper M06, 40 members / 5 MiB | succeeded | 6,514 | 6,566 | 270,438,400 | 5,556,793 | `9be82af01a83b5ac1e527379d267c4601c1743f4ee6cf3e5438101ec15961ef7` |
| Upper M05, 512 frequencies / 5 MiB | succeeded | 5,016 | 5,062 | 269,766,656 | 5,720,777 | `385b06db7c3f6fa923a4826e73e28607b28367a95ffc62dcb6ebb23faf3fe840` |
| Malformed M05 | failed, `processing_failed` | 4,717 | 4,792 | 250,929,152 | 236,889 | no result |

Boundary rejections were `422 method_ineligible` for M06 above 64 frequencies despite a passing M05, and `413 upload_too_large` at 5 MiB + 1 byte. The other API tests establish actual hash-pinned cl061 QC-only/M06 exclusion, wrong-principal 404, closed-admission 409 and durable revoked-worker admission, source tamper, cancel, timeout and memory failures.

RSS is the sampled sum of the child process tree, including the Windows Python launcher; parent API/worker resident memory is not included. Scratch includes the exact verified `source.edi` snapshot, bounded Matplotlib metadata cache, stderr and result. The owner original and immutable dataset live outside scratch. This is one run per case, not a nominal 95th percentile; process import and cache creation are included. The local ceilings are M05 768 MiB RSS, 8 MiB scratch, 90 s; M06 1 GiB RSS, 32 MiB scratch, 300 s, further limited by configured host ceilings. The Linux child also bounds address space, not only sampled RSS; imports, native-library mappings and parent overhead must be measured there. This receipt does not establish multi-user contention, other EDI dialects or VPS fit.

**Actual-host admission: pending.** Before setting `GEOPHYSICS_MT_ONLINE_ENABLED=1` on the ML VPS, rerun this matrix there under the intended restricted worker identity, collect a nominal distribution sufficient to evaluate the SDD's p95 below 70% of configured limits, verify at least 30% host memory/disk headroom, cancel/timeout/crash recovery and concurrent-read responsiveness, and retain the host receipt. No VPS activation, merge or deployment is asserted by this local record.

The user's read-only 2026-10-03 05:47 UTC snapshot reports 4 vCPU, 7,751 MiB total / 4,962 MiB available memory, 624 MiB swap used, 23 GiB root free, static nginx release `20260926235216`, and no runtime API. This is supplied capacity context, not an admission measurement. The user owns the isolated actual-host harness; no second public origin is proposed. The product convergence ledger and its separately failing release gate remain unchanged. The published static MT replay/source-fingerprint guard also remains unresolved, as documented in the [self-review](online-mt-self-review.md).
