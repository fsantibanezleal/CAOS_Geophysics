# Measuring bounded methods on the actual ML VPS

This is an operational guide for the approved single-VPS design, not a second deployment. The runner never edits public nginx, production accounts/data, DNS or Pages. Do not enable online methods from a Windows receipt or a green structural check.

## Isolated setup and invocation

A root operator installs the reviewed committed sources into a new immutable directory `/opt/fasl-admission/geophysics/<run-id>`, records the Git revision in `admission-source-revision.txt`, creates an isolated `.venv` there and installs `requirements-api.txt` plus `requirements-dev.txt`. Run `pip check`; capture installed versions and absence of Torch. Never share a production environment or download source data during measurement. The benchmark uses explicitly authored analytic EDI controls; actual field cl061 remains an independently pinned QC-only gate.

Invoke the server-only script from that immutable checkout:

```bash
bash scripts/server_mt_admission.sh mt-20261003-<revision>
```

The transient service uses `DynamicUser` and a `StateDirectory` with mode 0700. Source and venv are read-only under `ProtectSystem=strict`; only systemd private state and private temporary storage are writable. `PrivateNetwork` prevents external connections and no HTTP listener opens. Inspect actual unit properties and cgroup peak memory; intended directives alone are not evidence that the host applied them. The service has a 2 GiB memory ceiling, zero swap, two CPU cores maximum, 96 tasks and a 30-minute runtime ceiling. All library thread counts are one. Never broaden bounds to hide a failed admission.

## Measurements and failure controls

The distribution test runs twenty fresh nominal M05 attempts and twenty M06 attempts, retaining every job's exact preflight, inputs, request/result hashes and measured wall/RSS/scratch. Its nearest-rank p95 must be below 70% of each respective ceiling. A 50 ms monitor measures parent-plus-child RSS, host available memory and disk. Minimum host memory/disk headroom must be 30%. The process tree includes the TestClient API, worker and child, not other production services. Their load nevertheless affects actual host headroom. This sample is one nominal sounding, not a general scientific-data throughput claim.

While the real numerical child runs, authenticated reads are timed. These are **TestClient application** reads, not public nginx/TLS/network latency. A p95 below one second is the harness threshold; whole-site external responsiveness is a separate cutover gate. The nominal, exact-byte/dimension upper and malformed matrix is rerun on Linux through real child processes. Preserve all successful bundles and failed logs.

The real crash test sends `SIGKILL` to a separate worker parent after observing its actual `app.mt_compute` child. Closed-stdin protection must stop the orphan. Normal recovery records `worker_interrupted`, with no result. The existing conservative policy intentionally refuses unknown interrupted staging; an **operator** inspects and moves the exact harness stage into a retained quarantine before retry. This is not unattended crash recovery. Hashes before/after must match. Timeout, cancel, scratch and RSS fault-injection controls separately verify durable failure and no orphan. Never claim that those instrumented controls are independent scientific solves.

Linux `RLIMIT_AS` bounds mapped address space, whereas sampled RSS measures resident memory. `RLIMIT_FSIZE` bounds one file, whereas the worker counts total snapshot/cache/stderr/result scratch. Native dependency imports must fit both actual policies. A failure during imports is a failed admission, not permission to remove the limit.

## Evidence and activation boundary

Retain private raw JSON receipts, five benchmark ZIPs, server test output, applied service properties, immutable source revision, dependency report and host before/after capacity snapshots. Download into ignored `data/raw/host-admission/<run-id>/`; commit a sanitized measured summary and exact receipt hashes. Never commit private test-account databases, mail capture or authentication material.

Passing these bounded tests does not pass full R-017. Production SMTP/security, backup/restore, integrated numerical/data method gates, public HTTPS/SNI, hydrated EN/ES browser views and single-origin cutover are still required. Preserve the current origin and Pages state until those gates pass, then disable the old Pages app through the reviewed cutover workflow. A local application read test cannot stand in for that workflow.

Primary semantics: [Python resource](https://docs.python.org/3/library/resource.html), installed systemd 255 `systemd.exec` and `systemd.resource-control` manuals, [approved SDD](../design/SDD.md), [online MT contract](../data-contract/02_online-edi-mt.md). Upstream freedesktop manual access returned 403 during this review; installed host manuals were read directly instead.
