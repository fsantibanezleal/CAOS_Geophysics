# Rights-aware original Ridgecrest case plan

Status: PLANNED / NOT_ACQUIRED / NOT_PROCESSED. This is a reproducible acquisition/calculation/evaluation plan, not a live fixture. Actual source byte counts, raw hashes, response eligibility, arrivals and measurements are all unset. Do not fill them with documentation hashes, expected sample counts or a synthetic waveform.

## 1. Provider identity, rights and immutable originals

Event candidate: SCSN `38457511`, corresponding to the USGS [ci38457511 event page](https://earthquake.usgs.gov/earthquakes/eventpage/ci38457511/executive). The public page is JavaScript-only in the research tool; it did not supply a parsed event origin. Future original phase/catalogue bytes, not a remembered rounded timestamp, determine the exact catalogue origin and revision. Planning window is2019-07-06T03:19:20Z..03:22:20Z (180 s). That window is a predeclared acquisition choice, not a measured origin or pick.

The [SCEDC cloud documentation](https://scedc.caltech.edu/data/cloud.html) explicitly identifies candidate originals:

- `s3://scedc-pds/event_waveforms/2019/2019_187/38457511.ms` (whole-event context, NOT a bounded input or authorized download here).
- `s3://scedc-pds/event_phases/2019/2019_187/38457511.phase` (original analyst/catalogue reference, separate from prediction input).
- `s3://scedc-pds/FDSNstationXML/CI/CI_GSC.xml` (all-epoch CI station metadata; exact body/epoch must be validated after retrieval).

These published paths are not proof of today's object availability, length, encoding, calibration or scientific eligibility. SCEDC's2020 Ridgecrest DAS hourly SEG-Y is a different dataset and excluded. No marine/FWI source or full-event station set is touched.

The [SCEDC-managed registry licence](https://registry.opendata.aws/southern-california-earthquakes/) specifies non-exclusive, royalty-free, non-transferable worldwide use/reproduction/public display of public SCSN data. Retain its exact retrieved document hash and attribution. The [citation policy](https://scedc.caltech.edu/about/citation.html) requires SCEDC DOI `10.7909/C3WD3xH1`, CI DOI `10.7914/SN/CI`, and other network-specific citations where applicable. This plan admits only an actual CI object within that scope, after Main's per-object rights review. Other networks, extra research datasets, third-party mirrors or private response files do not inherit those permissions. The code's licence is irrelevant to field-data rights.

Rights verdicts are separate: local processing permission, raw redistribution, derivative publication. Unknown/forbidden local permission yields `rights_ineligible`; unclear publication permits no public original/array commit. Retain URL/retrieval failure/rights refusal in the case inventory. Do not silently substitute a different station/event or invoke another dataset's licence to manufacture a positive case.

## 2. Exact proposed bounded acquisition

Initial candidate is **CI.GSC, empty location, HNZ**, one instrument-native channel. This is a predeclared candidate inspired by SCEDC's published channel example, not an assertion that its2019 data/response exists or passes. No switch to a visually better trace. A separately reviewed amendment can add more candidates, but the failed initial candidate remains in the denominator/inventory.

Before acquisition, seal this station/window and numerical profile without reading picks or scoring waveform quality. An operator, separately authorized by Main, makes one serial acquisition at a time to approved HTTPS SCEDC/AWS endpoints, with bounded streaming reads and fresh explicit private destination files. Calculation helper and scientific tests never fetch providers. No STP client installation, public origin, provider write or whole-day/event bulk download is needed.

Use [SCEDC station](https://service.scedc.caltech.edu/fdsnws/station/1/), [availability](https://service.scedc.caltech.edu/fdsnws/availability/1/) and [dataselect](https://service.scedc.caltech.edu/fdsnws/dataselect/1/) semantics:

1. Station response request:

   `https://service.scedc.caltech.edu/fdsnws/station/1/query?net=CI&sta=GSC&loc=--&cha=HNZ&starttime=2019-07-06T03:19:20&endtime=2019-07-06T03:22:20&level=response&format=xml&nodata=404`

2. Availability diagnostic with the same exact NSLC/time selection, `format=text&nodata=404` on `/fdsnws/availability/1/query`. This is not a substitute for decoded gap checks. If an exact provider parameter is unsupported, retain that status and do not guess that no gaps exist.

3. Windowed MiniSEED request:

   `https://service.scedc.caltech.edu/fdsnws/dataselect/1/query?net=CI&sta=GSC&loc=--&cha=HNZ&starttime=2019-07-06T03:19:20&endtime=2019-07-06T03:22:20&nodata=404`

4. Only after prediction/source selection is sealed, acquire the separate original phase object at `https://scedc-pds.s3.us-west-2.amazonaws.com/event_phases/2019/2019_187/38457511.phase`, capped at1 MiB. [Event service](https://service.scedc.caltech.edu/fdsnws/event/1/) `eventid=38457511&includearrivals=true&format=xml` is a documented alternate reference source, but not an automatic fallback: a changed source/adapter requires explicit review and separate receipt. This unit proposes only the STP phase conversion below.

`--` is SCEDC's request notation for empty location; record mapping to literal empty NSLC location in the scientific request. Do not strip arbitrary locations into a match. Response and waveform endpoints may have changed metadata revisions since2019; pin each actual body and epoch, not a URL alone.

Waveform cap16 MiB, metadata cap2 MiB, availability cap64 KiB, phase cap1 MiB. Stop while streaming at cap+1; Content-Length/ETag is metadata, not measured length/SHA. No transparent content decompression, implicit retry changing bytes, unreviewed redirects/hosts or oversized archive extraction. Record requested/final URL, query parameters, UTC request/finish, HTTP status/content type/encoding, Content-Length/ETag/Last-Modified if supplied, actual received bytes and SHA-256, source declaration and rights evidence. HTTP204/404 is retained `not_available`, not an accepted empty waveform; cap exceed is retained `source_over_limit`, not silently thinned data.

Dataselect may return entire records around the requested window. Preflight/decode all of them within fixed budgets, retain original bytes and every sample, and record the explicit conditioning slice. Require full coverage of the fixed requested interval; do not extend/shorten it after seeing a waveform or a pick. If actual NSLC/rate/epoch/encoding differs from the proposed lane, retain unsupported/QC-only; never re-encode the original as though the provider supplied eligible data.

## 3. Predeclared processing profile, conditional on actual rate/response

Conditioning interval is the180 s window above; analysis interval03:19:40Z..03:21:40Z (120 s). The following settings are authored experimental settings, not claimed Ridgecrest-optimal parameters or measured instrument constants:

```json
{"output":"native","prefilter_hz":[0.5,1.0,12.0,15.0],"water_level_db":60.0,"taper_fraction":0.05,"bandpass_hz":[1.0,10.0],"filter_order":4,"filter_mode":"offline-zero-phase","edge_guard_s":10.0,"sta_s":0.2,"lta_s":2.0,"threshold_on":3.5,"threshold_off":1.5,"refractory_s":1.0,"welch_segment_samples":1024}
```

Measured rate must lie in the approved lane and satisfy all profile/Nyquist/sample-count/epoch conditions; do not assume100 Hz, acceleration or unmodified int32 counts from the candidate name. ADC rails stay null unless actual converter-range evidence is obtained; do not use MiniSEED sample dtype limits as hardware rails. Field truth, measured calibration uncertainty and timing sigma remain null. Freeze the complete request and identities before evaluation; no reference-based parameter search. One separately named filter-effect control may change bandpass [1,10] to [2,8] on the identical admitted original; it is not permission to tune until the catalogue matches.

## 4. Original phase conversion and residual protocol

[STP manual1.01](https://scedc.caltech.edu/data/stp/STP_Manual_v1.01.pdf), section4.5 and6.9, describes an event header and13-field rows with NSLC, geographic metadata, phase, first motion, onset/pick quality, distance and seconds after origin. The appendix's abbreviated list differs from its explicit location-bearing example. The proposed converter supports the location-bearing13-field dialect only; another actual dialect remains `reference_unsupported`, not a guessed column offset.

Proposed new function, within owned `waveform_evaluation.py`: `references_from_stp(raw: bytes, event_id: str, selected_nslc: tuple) -> dict`. Exact bytes <=1 MiB, ASCII/no BOM/NUL, <=4096 lines, each<=2048 bytes; no path/network. LF or CRLF delimiters, terminal newline optional, blank lines ignored but retained offsets/line numbers count. There is exactly one header followed by rows, no multi-event stream or arbitrary comments. Header may have a single leading `#`, then exactly9 whitespace-separated fields `(event_id,event_type,origin_utc_date_time,latitude,longitude,depth,magnitude,magnitude_type,quality)`. Origin is one `YYYY/MM/DD,hh:mm:ss[.ffffff]` token, real Gregorian1970..2100 UTC with no leap second. Event id is1..20 decimal digits matching the requested id; event_type `le` or `ts`; magnitude_type is one ASCII letter preserved, not a unit conversion. Latitude[-90,90], longitude[-180,180], finite depth/magnitude and quality[0,1] are required; they do not enter waveform physics.

Each later row has exactly13 fields: network, station, channel, location, latitude, longitude, elevation, phase, first_motion, onset, quality, distance, origin_offset_s. NSLC obeys contracts; only `--` maps to empty location. Phase is P/S; first_motion is exactly two characters with first in `c,d,.` and second in `u,r,.`; onset is `i,e,w`; quality finite[0,1], distance finite>=0 in declared km, elevation finite in declared metres. Unknown codes/dialects are `reference_unsupported`, never shifted columns. Numeric tokens<=128 bytes with ordinary signed decimal/exponent syntax, no nonfinite/bool/coercion; time-offset specifically uses signed decimal seconds without exponent and at most6 fractional digits, abs(offset)<=86400 s. Add integer microseconds to the original exact origin, preserving a signed pre-origin pick if actually supplied. Fully validate all rows before selecting channel; at most128 selected rows. Store original zero-based line index, byte offset/length and SHA of row bytes excluding line terminator as source_record_id lineage. Multiple same NSLC+phase picks are all ambiguous, including equal-time duplicates; none is averaged or selected for best agreement.

The manual maps quality scores to ordinal sample-error categories; those are not documented Gaussian standard deviations. Preserve the code and category but keep `uncertainty_s=null` and `analyst_status=catalogue-unspecified` unless independent provenance actually identifies a manual pick. No rewriting a category into a sigma, no claim analyst times are field truth. Converted reference `source.raw_sha256` is the original phase-file SHA; evaluator independently measures the converted JSON byte/hash identity. A source-valid replay must regenerate every selected reference from that original source, not merely trust a self-supplied digest.

The conversion function returns `{event_id,origin_utc,raw_bytes,raw_sha256,rows,unsupported_or_ambiguous_rows}` with bounded original metadata/row lineage, not an assertion of rights or completed sealing. After the prediction manifest exists, the authorized caller constructs the exact reference JSON using these selected rows, original phase hash and separately reviewed rights/citation. `selection_sealed_before_scoring=true` records that procedure but is not proof by itself; source-valid gate checks actual ordered receipts and regenerates from original bytes. CLI `--evaluate-with` is converted JSON only, never an STP/QuakeML format guess or a download. Original-field and reference-conversion receipts remain separate.

Run the separately sealed evaluator exactly as [algorithms](algorithms.md) section7. Report all available/unavailable/ambiguous references, unlabelled candidate matches/residuals and unmatched predictions. If no usable GSC HNZ reference exists, retain `not_evaluable`; do not move to another channel or copy a nearby station's P/S time. Frozen M13 scores/results are historical comparisons only, not a fresh Ridgecrest run.

## 5. Expected statuses and source-valid gates

No positive status is promised for this real candidate. Actual alternatives: `not_available`, `rights_ineligible`, `source_over_limit`, `reference_unsupported`, parser `rejected`, retained `qc_only`, or conditional `computed` with possibly zero onsets and `not_evaluable` reference status. Record the observed outcome with original hashes. A successful synthetic control does not close the original field case gate.

Real case gate: `tests/data/test_waveform_ridgecrest.py::test_original_bytes_response_epoch_and_retained_outcome`. Independent original-byte replay must match source identities, exact NSLC/time/response stage selection, raw decoded samples and QC verdict; numerical parity tolerances are predeclared separately. Missing private actual files yields explicit unresolved/skip and blocks real-case acceptance, not permission to create fake live fixtures. Resource gates are authored controls, not field observations.

Negative case controls use new derived copies labelled `authored_negative_from_original`: remove an epoch, alter a gain, change NSLC, insert a gap or clip values. Each carries original parent hash and exact modification; none retains the original raw hash or is called an observed provider failure. The original outcome remains immutable. No actual field bytes, negative derivatives or private QA outputs are committed without explicit rights/scope approval.

## 6. Current receipt state

| Field | Current value |
| --- | --- |
| Acquisition/execution | NOT_RUN |
| Event/station/channel | Planned38457511 / CI.GSC / empty location / HNZ |
| MiniSEED/StationXML/phase measured bytes and SHA | null |
| Actual rate/response native quantity/epoch | null |
| Actual local/runtime/resource receipts | null |
| Raw publication rights approval | pending per-object Main review |
| Field truth/calibration sigma | null |

The only measured provider-related bodies currently retained as hashes are research documents in [primary retrieval metadata](evidence/primary-retrieval.json). They cannot fill any scientific source field above.
