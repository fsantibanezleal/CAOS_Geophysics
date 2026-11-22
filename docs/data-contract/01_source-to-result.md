# From a source file to a geophysical result

![Source, raw asset, observation, computation and result are separate records](source-to-result.svg)

The diagram distinguishes five identities that are easy to collapse incorrectly. A provider page is not the bytes it advertises. An uploaded byte stream is not yet a usable gravity, MT or seismic observation. A dataset produced from those bytes is not a geological model. A successful worker process is not evidence of a unique inverse solution. Keeping these boundaries explicit is what lets a reader answer: *which observations, geometry, units, numerical assumptions and rights produced this result?*

The authenticated branch API accepts bounded, privately stored originals and creates owner-scoped typed datasets and jobs. Gravity flag QC and uploaded ordinary weighted-L2 (M02) are separate methods: the former preserves the observations; the latter requires additional source, correction-state, uncertainty and acquisition-group admission. Method adapters also exist for magnetic, EDI/MT, ERT/traveltime profiles and waveforms, but each has its own host/runtime switch and acceptance boundary. The M02 worker passed a scoped synthetic uploaded-survey test on the ML VPS; its production services and public online switch remain off, and full field/M02 acceptance is open. The live static experiment catalogue is a separate `inverse-earth/v2` known-truth lane. See the [API guide](../guides/06_api.md), [processing-job guide](../guides/07_processing_jobs.md), [M02 host receipt](../validation/actual-host-admission-m02-2026-11-06.md) and [case catalogue](../cases/README.md).

## 1. Identity and provenance graph

Let $B_0$ be original bytes, $P$ a parser and QC configuration, $D_1=P(B_0)$ a validated observation version, and $R_1=A(D_1,\theta)$ a result from algorithm $A$ with declared parameters $\theta$. The identifiers are not interchangeable:

$$
H_0=\operatorname{SHA256}(B_0),\qquad
H_D=\operatorname{SHA256}(\operatorname{canonicalJSON}(D_1)),\qquad
H_R=\operatorname{SHA256}(\operatorname{canonicalJSON}(R_1)).
$$

SHA-256 verifies byte identity, not data quality or scientific validity. A re-encoded but numerically equivalent CSV has different $H_0$; a parser upgrade may produce a new $D_2$ from the same $B_0$. A result must name the exact dataset version, method version, request/parameter hash and engine. The design follows the *entity–activity–agent* separation in [W3C PROV-O](https://www.w3.org/TR/prov-o/): original and derived files are entities; parsing and solving are activities that use inputs and generate outputs; providers and operators carry attribution. This application does not claim its JSON is itself an RDF PROV-O serialization.

| Record | Identity and minimum content | It does **not** establish |
| --- | --- | --- |
| `SourceRecord` | Provider or user, exact object URL/upload, citation, rights decision, expected bytes/hash where known, retrieval context. | That a URL is still reachable, that an unknown licence grants republication, or that the provider's interpretation is true. |
| `RawAsset` | Owner/project, original filename, measured bytes and SHA-256, immutable private storage key, detected format/envelope and receipt. | Units, CRS, tensor geometry, usable samples or solver eligibility. |
| `ObservationDataset` | Parser/version, parent raw hash, named dimensions and axis order, physical units/frame/datum, station or acquisition geometry, observed values, uncertainty meaning, mask and QC verdict. | Geological truth or an automatically corrected/denoised observation. |
| `ProcessingRun` / `SolverJob` | Input dataset versions, method and parameters, execution lane, admission/state, numerical and resource receipt, child-process identity. | A successful fit if the state is queued, failed, cancelled, nonconverged or ineligible. |
| `ResultArtifact` | Observed/predicted arrays, signed and weighted residuals, model/property units if an inverse ran, objective and stopping, coverage or reason unavailable, rights and export hashes. | A unique subsurface interpretation, calibrated posterior or independently validated geology. |

The [gravity dataset adapter](../../app/processing_contract.py) uses `geophysics.observation-dataset/v1` with a station axis, coordinates in metres, `observed_mgal`, `sigma_mgal`, explicit per-station uncertainty, a mask and missing-reason vector, parent raw SHA-256 and parser version. Its `parsed_for_flag_qc_only` verdict is structural; it is not a blanket modelling admission. The [flag-QC result](../../app/compute.py) contains robust scores and flags but deliberately no prediction, inverse model or geological residual. The separate M02 adapter in `app/gravity_l2_compute.py` may return a model, prediction, signed/standardized residuals, calibration and solver states only after source-qualified eligibility. The [canonical synthetic catalogue](data-contract.md#computed-experiment) carries known generated truth and is not the user-upload API. Unknown field geology must remain `truth=null`.

## 2. Acquisition, storage and rights

The local [source ledger](../../data/source-ledger.json) enumerates reviewed provider objects with acquisition mode and rights decision. The [acquisition script](../../data-pipeline/acquire.py) accepts a stable `source_id` or a manually obtained exact file, checks expected length and SHA-256, and refuses to overwrite an existing original. `provider-link-only` means a reader can reach the provider and a local analyst may retrieve it under the recorded workflow; it is **not** a raw-file redistribution grant. `derivative-only` describes a narrower reviewed publication permission. A source's software licence does not automatically license its field measurements. Unknown rights block a public raw mirror. The [acquisition guide](../guides/05_sources.md) lists exact objects, pins and local commands.

The API's private upload route is different from a provider mirror. It requires an owner, project, source statement and explicit `private_storage_permission: attested`. This is the uploader's assertion that the service may store the file privately, not proof that the service may publish it. The API rejects `forbidden` rights, arbitrary remote URLs and archives. Its raw tree is outside the web root, and raw downloads/exports require ownership. The [raw API guide](../guides/06_api.md) describes the cookie, CSRF, byte caps, quotas, export and deletion boundary. The public curated catalogue and account data must never share one implicit licence decision.

Byte integrity is checked at transitions, not inferred from a filename. For example, an EDI file cannot be reclassified as an earthquake waveform because both contain a station identifier; EDI is a *processed complex transfer function*. A `.sgt` first-arrival table is not an active-source shot gather. The [strict EDI](../../data-pipeline/edi.py), [ERT](../../data-pipeline/ert.py) and [traveltime](../../data-pipeline/traveltime.py) local adapters retain their own formats and errors. Their field-source publication verdicts remain separate from their numerical test results.

## 3. Physical meaning is a prerequisite for computation

Every quantity must carry the metadata needed to map numbers to physics. For a station observation $d_i$, the minimal usable pair is $(\mathbf{x}_i,d_i)$ plus its component convention and uncertainty $\sigma_i$, with coordinates and values expressed in named units. A weighted data objective can then be stated as

$$
\Phi_d(m)=\sum_{i\in\mathcal I_{\rm valid}}
\left[\frac{F_i(m)-d_i}{\sigma_i}\right]^2.
$$

Here $F_i(m)$ is the declared forward prediction at the **same acquisition location/component**, $\mathcal I_{\rm valid}$ excludes masked observations, and $\sigma_i$ is a supplied or explicitly assumed standard deviation in the observation's units. If errors are correlated, a diagonal $\sigma_i$ model is an assumption rather than a measured covariance. A smaller $\Phi_d$ alone does not prove recovered geology, because different models and regularizers can fit the same finite survey.

The raw API [metadata validator](../../app/formats.py) checks declared CRS/EPSG or named local frame, horizontal and vertical datum, positive vertical direction, axis order, units, component frame, epoch where applicable, and format-specific geometry. It then checks bounded file *envelopes*. For complex formats such as GeoTIFF, MiniSEED, SEG-Y and MTH5, an envelope pass is explicitly **not** a sample-level scientific parser or modelling verdict. The current typed processing parser checks a narrower gravity CSV: projected xy metres, vertical metres, mGal, exactly six declared station/x/y/z/value/sigma columns, 4–4096 stations, finite values, unique station IDs and XYZ, and strictly positive sigma. No CRS transformation or gravity correction is inferred.

Coordinate order is not just a storage detail. [pyproj warns](https://pyproj4.github.io/pyproj/stable/api/transformer.html) that an EPSG CRS may put northing or latitude first; a transform using traditional GIS x/y order must request and record `always_xy=True`. The [CF 1.13 convention](https://cfconventions.org/Data/cf-conventions/cf-conventions-1.13/cf-conventions.html) requires an explicit `positive="up"` or `positive="down"` for many vertical coordinates; metre units alone do not define depth sign. This project does not claim all its JSON artifacts are CF-compliant NetCDF. It applies the underlying discipline: named axes, unit, orientation and sign travel with the data.

| Modality | Observation, not inferred model | Non-negotiable geometry and unit boundary |
| --- | --- | --- |
| Gravity station | $g_z$ anomaly in mGal or declared SI equivalent. | XYZ, coordinate frame/datum, vertical and component sign, station identity, uncertainty and correction state. |
| Magnetic flight line | Total-field anomaly in nT, not susceptibility. | Flight/tie identity, sensor height, inducing field/frame, line geometry, uncertainty and preprocessing lineage. |
| MT EDI | Complex $2\times2$ impedance tensor versus frequency, with variance/rotation. | Tensor units/sign convention, frequencies, component errors and dimensionality screen; a failed 1D screen forbids a layered inversion claim. |
| ERT | Four-electrode configuration and transfer resistance in ohm. | A/B/M/N identities, electrode coordinates/topography, current/voltage meaning and error source; apparent resistivity is derived. |
| Refraction | Source–receiver first-arrival pick in seconds. | Source/receiver coordinates, time origin and pick uncertainty; it is not a waveform. |
| Earthquake trace | Samples in instrument counts or response-corrected physical units. | Channel orientation, sample rate/start time, response epoch and phase-reference provenance; a catalogue pick is not geological truth. |

## 4. Mask, outlier, uncertainty and negative-state rules

There are four different absences. **Invalid raw input** (nonfinite value, impossible geometry or missing required unit) is rejected before modelling. A **mask** records a present observation intentionally excluded by a documented rule, without replacing it with zero. A **QC flag** is a warning that preserves the observation and its original uncertainty until the user approves a transformation. **Ineligible** means the physical method does not apply, even if the file parsed. These states must not collapse into a successful empty plot.

The current gravity worker computes a median and median absolute deviation (MAD), then flags points whose robust score crosses the submitted threshold. It does not correct, discard, reweight or invert the data. The [processing guide](../guides/07_processing_jobs.md) gives the exact five-station example and parameter-effect test. In contrast, the ERT and traveltime local field examples lack measured error columns; their scripts label their error floors as *assumptions*. The MT tensor screen is a necessary check of 1D consistency, not proof of 1D geology; [Clear Lake cl061](../problem-types/mt-recovery.md#measured-clear-lake-station-screening-not-inversion) and [AusLAMP C15](../problem-types/mt-field-admission.md) retain ineligible verdicts rather than fabricate layered models.

For learned methods, the normalization fit and model-selection threshold belong to training/development partitions, never the held-out test. [The M12 validation](../problem-types/04_learned-velocity-validation.md) preserves its negative family-disjoint result. [The M13 phase-picking chapter](../problem-types/phase-picking.md) distinguishes analyst-pick agreement from geological truth and names the event/station leakage check. Neither learned score is a calibrated probability merely because a network outputs a softmax.

## 5. Reproduce the flag-QC path; distinguish an inverse

Use an isolated Python 3.12 API environment and migrations as in [the setup guide](../guides/06_api.md). Create a verified account and a project, then upload the five-station CSV in [the processing guide](../guides/07_processing_jobs.md) with its complete physical metadata, including `sigma_column`. The sequence is:

1. Save the original CSV and record its SHA-256 before upload. Confirm the owner's raw-asset receipt has the **same** SHA-256, an immutable asset ID and `raw_metadata_checked`, not `modelled`.
2. Create a gravity dataset from that asset. Confirm `parent_raw_sha256`, station count and order, projected coordinates, mGal/sigma units, and `parsed_for_flag_qc_only`. Download the original again and compare its hash; the dataset did not replace it.
3. Query dataset methods. The five-row fixture is eligible for `gravity.station-outlier-flags/v1`; it is deliberately not M02 eligible because it has no acquisition-group column or source declaration for processing state, error basis and background. A source-qualified M02 survey is a distinct input contract, and its online switch is closed in the current deployment.
4. Submit flag QC with threshold 6 and run the separate worker. Poll until a terminal state; a queued response is not a result. The worker should flag only S5 while retaining all five original observations.
5. Submit a new job on the **same dataset** with threshold 1. The flag set must change (S1 is additionally flagged), while the raw and dataset hashes stay fixed. This establishes that a scientific control changes an actual calculation, not an animation.
6. Export the successful processing bundle and run `app.bundle.verify_bundle` as documented in the processing guide. Verify its dataset/result hashes and rights. It intentionally omits raw bytes and private storage keys. This is robust flag QC, not a gravity inverse or a field interpretation.

### M02 uploaded ordinary weighted-L2 path

M02 is an independent adapter and solver path, not an extension of the median/MAD flag calculation. Its upload needs station identity, local east/north/up coordinates in metres, processed gravity anomaly in mGal, positive Gaussian standard deviations, a declared acquisition-group column, a provider-documented processing/correction state, an explicit fixed background and a source/rights/private-storage receipt. A successful CSV parse, a flag-QC result or the string `parsed_for_flag_qc_only` does not bypass these eligibility checks. The accepted M02 objective and parameter contract are documented in the [M02 method design](../design/features/m02-survey-inversion/design.md) and implemented by `app.gravity_l2_contract` / `app.gravity_l2_compute`.

The [actual-host admission receipt](../validation/actual-host-admission-m02-2026-11-06.md) records an authenticated authored 12-by-12 prism-survey upload, dataset creation, M02 eligibility, two isolated CPU solves, independent Choclo forward replay, held-out residual checks, export verification and exact raw-byte preservation. It establishes that bounded uploaded-user-data execution worked in the scoped ML VPS runtime. Its generator was synthetic; it does not establish field-geology accuracy, all survey regimes, full M02 method-ladder acceptance, production concurrency or public service availability. The report states the production API/worker and M02 switch were not enabled. The [browser receipt](../validation/m02-uploaded-prism-replay-2026-11-06.md) independently checks the returned trace and model rendering. Neither receipt promotes the method to the current live release.

For a failure exercise, remove `sigma_column` from the physical declaration or duplicate an XYZ row in a new CSV. Dataset creation must return a field-specific error and must not mutate the already accepted original. An EDI that fails its 1D consistency screen should remain available for QC but must not acquire a layered model. These are **different** gates: schema/byte identity, physical eligibility and numerical performance.

## 6. Evidence and limits

The [API contract tests](../../tests/api/) check ownership, immutability, format envelopes, private storage, job state, parameter effects, cancellation and processing export. The [local numerical tests](../../tests/numerics/) exercise method-specific physical or numerical oracles. These receipts are necessary but not sufficient for public availability: the full method/data acceptance, actual ML VPS resource and recovery gates, rendered browser acceptance and verified release cutover remain separate. The current public origin is a static scientific release, not evidence that this branch's authenticated workflow has been deployed.

The purpose of this contract is reproducible, qualified inference. It does **not** make field geology uniquely identifiable; provide measured observations for every promised method; turn a licence link into redistribution permission; or allow an API to report a successful solve after only inspecting a file header.

### Primary references

- [W3C PROV-O](https://www.w3.org/TR/prov-o/) for entities, activities, agents, use and generation.
- [CF 1.13](https://cfconventions.org/Data/cf-conventions/cf-conventions-1.13/cf-conventions.html) for named coordinate and vertical-direction conventions where applicable.
- [pyproj Transformer](https://pyproj4.github.io/pyproj/stable/api/transformer.html) for CRS axis-order behavior.
- [USGS Gravity and Magnetic Exploration](https://pubs.usgs.gov/tm/02/d04/tm2d4.pdf) for gravity measurement/correction context; product-specific corrections are not implied.
