# From a source file to a geophysical result

![Source, raw asset, observation, computation and result are separate records](source-to-result.svg)

The diagram distinguishes five identities that are easy to collapse incorrectly. A provider page is not the bytes it advertises. An uploaded byte stream is not yet a usable gravity, MT or seismic observation. A dataset produced from those bytes is not a geological model. A successful worker process is not evidence of a unique inverse solution. Keeping these boundaries explicit is what lets a reader answer: *which observations, geometry, units, numerical assumptions and rights produced this result?*

This is the platform's intended end-to-end contract, with a narrower implemented state. The current authenticated API accepts bounded, privately stored raw files in several declared formats; it produces a typed observation dataset and a flag-only processing result for **gravity station CSV only**. Its result is not a physical correction or inverse solve. Separate local scripts implement strict EDI screening, topographic ERT and first-arrival tomography, but those are not automatically available as online user jobs. A published synthetic `inverse-earth/v2` experiment is a different, known-truth contract. [The API guide](../guides/06_api.md), [processing-job guide](../guides/07_processing_jobs.md) and [case catalogue](../cases/README.md) keep those lanes distinct.

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

The current API's [typed gravity dataset](../../app/processing_contract.py) uses `geophysics.observation-dataset/v1` with a station axis, projected XYZ coordinates in metres, `observed_mgal`, `sigma_mgal`, explicit `per_station_standard_deviation`, a mask and missing-reason vector, parent raw SHA-256 and parser version. Its [flag-only result](../../app/compute.py) deliberately contains no predicted field, inverse model or geological residual. The [canonical synthetic catalogue](data-contract.md#computed-experiment) instead includes known synthetic truth and separately simulated observations. Truth must be absent for unknown field geology.

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

## 5. Reproduce a complete **currently implemented** API calculation

Use an isolated Python 3.12 API environment and migrations as in [the setup guide](../guides/06_api.md). Create a verified account and a project, then upload the five-station CSV in [the processing guide](../guides/07_processing_jobs.md) with its complete physical metadata, including `sigma_column`. The sequence is:

1. Save the original CSV and record its SHA-256 before upload. Confirm the owner's raw-asset receipt has the **same** SHA-256, an immutable asset ID and `raw_metadata_checked`, not `modelled`.
2. Create a gravity dataset from that asset. Confirm `parent_raw_sha256`, station count and order, projected coordinates, mGal/sigma units, and `parsed_for_flag_qc_only`. Download the original again and compare its hash; the dataset did not replace it.
3. Query dataset methods. Only `gravity.station-outlier-flags/v1` is active. Submit threshold 6 and run the separate worker. Poll until a terminal state; a queued response is not a result. The worker should flag only S5 while retaining all five original observations.
4. Submit a new job on the **same dataset** with threshold 1. The flag set must change (S1 is additionally flagged), while the raw and dataset hashes stay fixed. This establishes that a scientific control changes an actual calculation, not an animation.
5. Export the successful processing bundle and run `app.bundle.verify_bundle` as documented in the processing guide. Verify its dataset/result hashes and rights. It intentionally omits raw bytes and private storage keys. Do not call it a gravity inverse or a full field interpretation.

For a failure exercise, remove `sigma_column` from the physical declaration or duplicate an XYZ row in a new CSV. Dataset creation must return a field-specific error and must not mutate the already accepted original. An EDI that fails its 1D consistency screen should remain available for QC but must not acquire a layered model. These are **different** gates: schema/byte identity, physical eligibility and numerical performance.

## 6. Evidence and limits

The [API contract tests](../../tests/api/) check ownership, immutability, format envelopes, private storage, job state, parameter effects, cancellation and processing export. The [local numerical tests](../../tests/numerics/) exercise method-specific physical or numerical oracles. Those are necessary but not sufficient for a public online method: actual ML VPS wall, peak memory, scratch, cancellation/crash recovery, backup/restore and rendered browser behavior remain separate release gates. The current public 0.04.001 origin is still a static scientific replay, not evidence that the new authenticated workflow has been deployed.

The purpose of this contract is reproducible, qualified inference. It does **not** make field geology uniquely identifiable; provide measured observations for every promised method; turn a licence link into redistribution permission; or allow an API to report a successful solve after only inspecting a file header.

### Primary references

- [W3C PROV-O](https://www.w3.org/TR/prov-o/) for entities, activities, agents, use and generation.
- [CF 1.13](https://cfconventions.org/Data/cf-conventions/cf-conventions-1.13/cf-conventions.html) for named coordinate and vertical-direction conventions where applicable.
- [pyproj Transformer](https://pyproj4.github.io/pyproj/stable/api/transformer.html) for CRS axis-order behavior.
- [USGS Gravity and Magnetic Exploration](https://pubs.usgs.gov/tm/02/d04/tm2d4.pdf) for gravity measurement/correction context; product-specific corrections are not implied.
