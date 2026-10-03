# Online EDI M05/M06 contract and admission handoff

This is the bounded authenticated backend contract for the [EDI guide](../guides/08_online_edi_mt.md) and [feature SDD](../design/features/online-edi-m05-m06/requirements.md). The actual ML VPS gate is unresolved; no public API origin or browser activation is established by this contract.

## Owned input and method identity

Use the existing `/api/projects/{project_id}` asset, dataset and job endpoints. Dataset creation accepts one owned raw `edi` asset and returns an immutable envelope. M05 runs the strict full-tensor parser. M06 requires the exact dataset's successful M05 job and a passing all-frequency tensor screen.

| Contract | Fields and semantics |
| --- | --- |
| Dataset identity | `schema=geophysics.observation-dataset/v1`, UUID `dataset_id`, `version=1`, `owner_id`, `project_id`, `raw_asset_id`, `parser_version=edi-strict-envelope/v1`, `modality=edi_transfer_function`, `qc_verdict=awaiting_full_tensor_qc`. |
| Original receipt | `parent_raw_sha256`, exactly measured `parent_raw_bytes`; the original stays unchanged. Every scientific read uses its verified exact-byte `source.edi` snapshot in private staging. |
| Axes | `axis_order=["frequency"]`, `dimensions.frequency=N`; the envelope count is declared, then reconciled with original blocks by M05. |
| Physics | `physical_metadata` retains CRS/datum/epoch, impedance unit `ohm` or `mV/km/nT`, component frame, station ID, full tensor/optional tipper, common rotation, explicit time sign and variance meaning. |
| Rights | `source` retains provider, exact URL where present, DOI/citation, rights decision/statement and attribution. Attested private storage is required; export grants no new raw redistribution rights. |
| M05 | `method_id=mt.edi-full-tensor-qc/v1`, `parameters={}`; 2..512 frequencies and original at most 5 MiB. |
| M06 | `method_id=mt.edi-fixed-thickness-trf/v1`; `qc_job_id`, `thickness_m=[]` or one thickness in [2,4000], one/two `initial_ohm_m` strictly inside (1,6000), finite `beta` in [0,1], integer `bootstrap_samples` 20..40 and integer `seed`. Requires 12..64 original frequencies. |

The envelope is not a parsed or eligible sounding. No component/period mask can rescue a failed screen. Instrument-frame angles can be preserved; geographic rerotation only supports an exact 90-degree signed permutation with an explicit north reference. No missing covariance is filled in.

## Job and result shape

The existing job view carries `request`, `dataset_sha256`, `request_sha256`, `preflight`, state/timestamps, `wall_ms`, `peak_rss_bytes`, `scratch_bytes`, `error` and a success-only `result_url`. Preflight includes memory/scratch estimates and memory/scratch/wall ceilings. A `202` response is queued admission. Cancellation or failed eligibility supplies no inverse result.

Both successful methods return `schema=geophysics.processing-result/v1`, job/dataset/method/request identity, original `raw_asset_id/raw_sha256/raw_bytes`, `engine_sha256/parser_sha256/forward_sha256`, Python/scientific-package `environment` plus `environment_sha256`, source/physical metadata, frequency axis and `truth=null`.

| Result path | Shape / interpretation |
| --- | --- |
| `frequency_hz` | `[N]`, distinct positive Hz in increasing order; original ordering/permutation remains in provenance. |
| `screen` | `inverse-earth/edi-screen/v1`; `methods={}`, `inversion_performed=false`, necessary `one_d_inversion_eligible` verdict. |
| `screen.tensor.real/imag/sigma` | `[N][2][2]`, frequency/electric/magnetic axes; E/H ohm and SD of each real/imaginary part. |
| `screen.tensor.rotation_deg` | `[N]`, resulting frame; provenance records original rotations and action/reference. |
| `screen.observed.xy/yx` | `[N]` real/imaginary ohm, apparent resistivity ohm m, phase degrees and `sigma_real_imag_ohm`. Curves compare Zxy and -Zyx; the full tensor retains the actual signed Zyx. |
| `screen.metadata.tipper` | Optional ancillary tipper, rotation and missing frequencies; unused in the inverse. |
| `inverse` for M05 | `null`; Clear Lake cl061 stays here because its screen fails. |
| `inverse` for M06 | `inverse-earth/edi-1d/v1`; imposed `thickness`, sorted frequencies, observed complex curves, marginal `sigma`, frozen `active` training mask, full source/tensor receipt and `truth=clean=null`. |
| `inverse.methods.mt-lm` | Legacy key for bounded SciPy TRF: layer `model` in ohm m, predicted curves, signed observed-minus-predicted residuals, states/history, objective terms, train/holdout/component WRMS, solver budget/stop and local identifiability. |
| `inverse.evaluation_protocol` | Every fifth sorted frequency held out before fitting; three starts selected by training objective; same-input halfspace, alternative beta and thickness perturbations. No holdout tuning. |
| `inverse.methods.mt-lm.uncertainty` | 20..40 `[draw][layer]` conditional samples, seeds, bounds, fixed thickness, conditioning model/errors/beta/mask, failures and pointwise percentile lower/upper/mean/SD. No geological posterior or field coverage assertion. |

The [MT chapter](../problem-types/mt-recovery.md) gives the plane-wave recurrence, complete objective, sigma normalization and independent halfspace/reflection-formula oracles. Held-out periods from one sounding do not establish independent-station generalization or 1D geology.

## Re-import and host-harness artifact

`GET /jobs/{job_id}/export` returns exactly canonical `manifest.json`, `dataset.json`, `result.json` in a ZIP. Manifest members include byte counts/SHA-256, axes, units, parameters, rights and parser/engine/forward/original receipts; `raw_bytes_included=false`. `app.bundle.verify_bundle` recomputes the tensor screen and observed curves, fitted predictions/residuals and interval summaries, and reconciles conventions with parser provenance. This establishes serialization consistency; retain the original for independent reprocessing.

The opt-in `tests/api/test_online_mt_benchmark.py` produces `geophysics.mt-admission-benchmark/v1` JSON plus successful-job ZIPs in its private `case-0/mt-receipts/` directory. It prints JSON after `MT_LOCAL_BENCHMARK=`. Fields include UTC timestamp, system/Python, actual environment-isolation verdict, dependency versions, scientific code SHA-256 map, exact source hashes/bytes, admission rejections, and job rows with immutable request/preflight/result identity, state/error, worker/end-to-end wall, sampled child-tree RSS, scratch and bundle path/hash/bytes. No public listener opens; `host_activation_asserted=false`. Nominal distributions and host recovery/headroom need separate evidence.

| Matrix input | Expected M05 / M06 status |
| --- | --- |
| Nominal analytic halfspace: 24 frequencies, 8,935 bytes | M05 succeeds; M06 succeeds with 20 members and independent 100 ohm m oracle. |
| Independent two-layer reflection formula: 64 frequencies, exactly 5 MiB (comment padding) | M05 succeeds; M06 succeeds with 40 members and [120,12] ohm m oracle within 0.5% at imposed 350 m thickness. No generator truth is passed to the inverse. |
| 512 frequencies, exactly 5 MiB | M05 succeeds; M06 is `422 method_ineligible` despite passing QC. |
| Original at 5 MiB + 1 byte | Upload is `413`; no dataset/job is created. |
| Missing required tensor block | M05 is durable `failed/processing_failed`; no inverse/export. |
| Actual hash-pinned Clear Lake cl061 | M05 succeeds QC-only with failed 1D screen; M06 is `422 method_ineligible`. |
| Closed host flag | Submission is `409 host_admission_pending`; a queued MT job also fails before child spawn if the worker flag is closed. |
| Foreign owner / wrong dataset's QC | Foreign actions return `404`; another dataset's QC cannot admit M06. |

M05 ceilings: 768 MiB child RSS, 8 MiB scratch, 90 s. M06: 1 GiB, 32 MiB, 300 s, reduced by configured host ceilings. Snapshot/cache/stderr/result count as scratch. Measure the restricted Linux worker, parent/API overhead, p95 nominal load, host headroom and cancel/crash/concurrent-read recovery before setting `GEOPHYSICS_MT_ONLINE_ENABLED=1` in both services. [The local receipt](../validation/online-mt-local-benchmark.md) remains separate from that unresolved gate.
