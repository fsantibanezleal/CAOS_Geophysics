# Private EDI tensor QC and bounded layered MT jobs

This guide covers the authenticated M05/M06 API vertical on an owner-supplied EDI transfer-function file. It is implemented in the existing private dataset/job/result/export workflow and executed by the separate singleton worker. **Production admission is closed by default**: the actual ML VPS benchmark and recovery drill have not been run. The current public browser still displays curated artifacts; this branch does not deploy an online MT control there. The companion [local benchmark receipt](../validation/online-mt-local-benchmark.md) is engineering evidence from Windows, not host activation.

The [backend contract and host-harness handoff](../data-contract/02_online-edi-mt.md) defines exact input/result shapes, method IDs, boundary statuses and generated benchmark artifacts. The [MT method chapter](../problem-types/mt-recovery.md) supplies the forward recurrence and complete normalized objective.

## Source and physical contract

Authenticate and create a project as in the [API guide](06_api.md). Upload a single original `.edi` of at most 5 MiB with `POST /api/projects/{project_id}/assets`. The raw upload's `X-Asset-Metadata` must include an attested private-storage permission, source rights/attribution, exact expected byte count and SHA-256, and the usual coordinate/datum fields. For a source that declares native `(mV/km)/nT`, positive-time sign, complex variance and an instrument frame, the EDI-specific part is:

```json
{
  "filename": "station.edi", "mime": "text/plain", "format": "edi",
  "source": {
    "provider": "User upload", "rights_statement": "I have permission to store this original privately.",
    "rights_decision": "provider-link-only", "private_storage_permission": "attested",
    "attribution": "Survey and operator", "expected_bytes": 8935,
    "expected_sha256": "<64-hexadecimal-character hash>"
  },
  "physical": {
    "coordinate_reference": "local", "local_crs": "documented source station frame",
    "axis_order": "xy", "horizontal_datum": "documented survey datum",
    "vertical_datum": "documented elevation datum", "vertical_positive": "up",
    "horizontal_unit": "m", "vertical_unit": "m", "measurement_unit": "mV/km/nT",
    "epoch_utc": "2026-09-28T00:00:00Z", "component_frame": "instrument axes",
    "geometry": {
      "station_id": "HALFSPACE_100_NATIVE", "frequency_count": 24,
      "tensor_components": ["Zxx", "Zxy", "Zyx", "Zyy"],
      "rotation_degrees": 0, "rotation_reference": "unspecified",
      "sign_convention": "+", "variance_convention": "complex"
    }
  }
}
```

The byte count and hash above describe the repository's original synthetic halfspace fixture and are examples of fields to fill from *your* file; the placeholder SHA is not a usable receipt. For a field file, provide its actual CRS, axis order, datums and epoch. The API rejects missing physics metadata; the M05 child rejects any declared station ID, count, units, sign, variance, component/tipper presence or common rotation that disagrees with the original EDI blocks. The current online subset accepts one constant declared Z rotation for the entire sounding, a full four-component impedance tensor and optional complete tipper. Instrument axes are preserved. Geographic rotation requires an explicit north reference and the parser permits only an exact 90-degree signed permutation because EDI marginal variances lack the cross-component covariance needed for arbitrary rerotation. The EDI is a processed transfer-function product, not raw E/H time series.

Upload writes the original once under the owner's private project; `POST /api/projects/{project_id}/datasets` with `{"asset_id":"<asset UUID>"}` creates a versioned, hashed *envelope dataset*. Its `awaiting_full_tensor_qc` verdict is deliberate: it does not claim scientific eligibility from the filename or upload header. Every subsequent job verifies the original byte count/hash again. Other users cannot read or act on the project.

## M05: full tensor screen

After actual host admission, `GET /api/projects/{project_id}/datasets/{dataset_id}/methods` offers `mt.edi-full-tensor-qc/v1`. Queue it with `POST /api/projects/{project_id}/jobs`:

```json
{"dataset_id":"<dataset UUID>","method_id":"mt.edi-full-tensor-qc/v1","parameters":{}}
```

The worker calls the existing strict [`edi.py`](../../data-pipeline/edi.py) parser and compares the original frequency, complex impedance and variance blocks with [MT Metadata's EDI reader](https://mt-metadata.readthedocs.io/en/latest/source/api/mt_metadata/transfer_functions/io/index.html). Missing/sentinel/nonfinite numbers, absent components, inconsistent frames or ambiguous interpretation fail the job. The result contains the full complex 2×2 impedance and per-real/imaginary standard deviations in E/H ohm, frequency in Hz, any ancillary tipper with its missing mask, parser/code/source hashes, supplied physical metadata and source rights. Native MT units are converted by `μ₀×1000`; a negative-time convention is conjugated to `exp(+iωt)`. Complex variance is divided by two before taking marginal standard deviations; per-real-component variance is not. No error floor or covariance is invented.

The necessary isotropic 1D condition is `Zxx≈0`, `Zyy≈0`, `Zxy+Zyx≈0` across *all* supplied frequencies. Each diagonal and the conservative antisymmetry statistic is a two-real-component WRMS; all three must be at most 3. The off-diagonal sum uses `σxy+σyx`, an upper uncertainty scale that needs no invented cross-component covariance. This is a declared diagnostic threshold, not a confidence level or proof of 1D geology. The [phase-tensor literature](https://doi.org/10.1111/j.1365-246X.2004.02281.x) explains why phase information is a separate structural diagnostic; a favorable phase label cannot override a failed full complex tensor. The original USGS Clear Lake `cl061` file has a passing parser/QC receipt but fails this necessary screen, so it remains M05 only. Its field geology has no known resistivity truth in this product.

## M06: fixed-thickness conditional inverse

Only a successful M05 job for the *same* dataset and source bytes with a passing full-tensor screen can authorize `mt.edi-fixed-thickness-trf/v1`. A halfspace request is:

```json
{
  "dataset_id": "<dataset UUID>", "method_id": "mt.edi-fixed-thickness-trf/v1",
  "parameters": {
    "qc_job_id": "<passing M05 job UUID>", "thickness_m": [],
    "initial_ohm_m": [100], "beta": 0.001,
    "bootstrap_samples": 20, "seed": 61001
  }
}
```

For two layers, supply exactly one finite-layer thickness between 2 and 4000 m and two initial resistivities strictly inside `(1,6000)` ohm m. The thickness is **imposed by the operator**; it is not observed or estimated. The inversion fits complex `Zxy` in log resistivity through the existing `invert_edi` / bounded SciPy TRF path. `Zyx` is retained as an unfitted component check; both diagonals participated in the all-frequency M05 admission. Sorted frequencies with indices 4, 9, 14, … are frozen as holdout *before* any fit. Three starting models are fitted; the lowest training objective among successful starts is selected without looking at holdout. A one-layer model fits the same training periods as the baseline. One alternative beta and two ±20% thickness cases (for two layers) report sensitivity, with no tuning on holdout. The selected model, observed/predicted/signed residual impedance, apparent resistivity, phase, WRMS, objective terms, identifiability and stopping reason are all exported. [SciPy's TRF documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html) defines the bounded least-squares engine called by this path.

The 20–40-member pointwise parametric bootstrap uses the selected TRF model and supplied marginal errors. Its interval is conditional on the fixed layer count/thickness, independent Gaussian real/imaginary errors, beta, bounds and frame. It is neither a calibrated posterior nor a field geological confidence region. Weak directions, static shift, 2D/3D structure, systematic error and correlated periods remain limitations. No field truth, geological recovery score or unmeasured target is filled in.

Poll `GET /api/projects/{project_id}/jobs/{job_id}` and read `/result` only after success. `POST .../cancel` stops queued or running work. A source/parameter preflight, one-active-job account limit, singleton process lock, wall/RSS/scratch enforcement and crash recovery use the same worker as M01. The export ZIP contains canonical `manifest.json`, `dataset.json`, `result.json`; it omits original private EDI bytes. Re-import with `app.bundle.verify_bundle(Path("processing.zip").read_bytes())` to check hashes, axes, physical units, source/rights identity, observed tensor and fitted predictions/residuals. Keep the original EDI if future scientific reprocessing or independent parser comparison is needed.

Every parser and inverse call reads the child's verified exact-byte `source.edi` snapshot. Snapshot bytes, cache, stderr and result all count as scratch; the owner original is unchanged. Native numerical-library threads are limited to one. The storage-only worker independently refuses MT work when its admission flag is closed, including a previously queued job. Re-import also checks physical conventions against parser provenance and interval summaries against the exported ensemble.

## Online activation boundary

The development setting `mt_online_enabled=True` is used only by local tests. The service environment flag `GEOPHYSICS_MT_ONLINE_ENABLED=1` must remain unset on the ML VPS until its own nominal/upper/malformed matrix, actual measured capacity for release/project/job disk and memory, cancellation/crash recovery, deployment security and browser gates have receipts. The former arbitrary30% whole-host condition is superseded, not the method's memory/scratch/deadline limits. A local pass or a successful synthetic job is not admission. The source remains runnable offline with `data-pipeline/edi.py` under its documented limits if the online gate stays closed.
