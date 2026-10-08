# Process an owned MiniSEED and StationXML pair

This instrument runs `seismic.waveform-qc-classical/v1`, the genuine bounded
counts/response/SOS/Welch/classic pipeline. It does not infer a subsurface model,
assign P/S phases, calibrate clock uncertainty or establish provider authenticity.
See the [literal algorithms](../design/features/m08-waveform-user-data/algorithms.md)
and [protected contract](../design/features/m08-protected-waveform/design.md).

## Originals and source binding

Sign in and use Projects to upload unchanged integer-count MiniSEED plus its exact
StationXML companion. The upload's declared geometry identifies the companion
asset; both originals stay private, immutable and independently hashed. Select
the original MiniSEED in the waveform instrument and inspect **Exact owned source
pair**: names, measured bytes/hashes, original source declarations, rights and
geometry. A filename is not evidence of response epoch, NSLC, source rights or
timing quality. Missing companion/rights/format/identity prevents indexing.

Storage must be explicitly configured outside checkouts, including temporary,
cache, staging and derived outputs. The Windows publication preflight checks the
exact result metadata, directory and every member destination before installation;
an unsupported UTF-16 length of260 or more rejects `waveform_storage_unavailable`.
Select a supported external root; do not change global registry or use an
unchecked extended-path prefix.

## An explicit scientific request, not a preset

Start with blank grouped controls or import your own exact request using Advanced
JSON. No scientific values are seeded. Every numerical choice and NSLC row must
be entered/imported explicitly. Backend validation remains authoritative.

- **UTC and NSLC:** exact conditioning/analysis UTC with up to six fractional
  digits and a terminal Z. Conditioning is10–300s, analysis at least5s and inside
  conditioning. Select one to three measured channels from the same station.
  A blank location is explicitly confirmed, never inferred from a channel suffix.
- **Source and rights:** declare user/provider provenance, source citation,
  previous-processing statement and processing rights. Provider URL, source hash
  and evidenced ADC rails remain explicit advanced fields. Unknown rails stay
  unknown; no clipping clearance is inferred from missing evidence.
- **Response and prefilter:** native output is fixed by this method; the actual
  StationXML channel determines displacement/velocity/acceleration. Enter four
  increasing prefilter corners, with first at least0.05Hz and inner corners
  enclosing the bandpass. Water level is explicitly disabled (null) or20–120dB.
  It stabilizes inverse amplitude, not a noise covariance or uncertainty estimate.
- **Acausal filter:** enter prototype order2–6, taper fraction0.01–0.10 and
  edge guard0–150s. Offline zero-phase SOS filtering is fixed, not an online
  arrival warning. The worker calculates the effective valid-edge interval.
- **STA/LTA:** explicit STA0.05–2s < LTA0.5–20s and1 < off < on ≤100;
  refractory0–10s. These ratios are not probabilities or calibrated phase picks.
- **Welch PSD:** power-of-two segment64–8192 samples. Actual sample rate and
  analysis length must support the estimator; no silently shortened segment.

Advanced JSON and structured controls edit the same draft. Invalid values are
shown rather than coerced or repaired; unknown imported evidence is not discarded.
Save/load request JSON for reproducibility. Review the exact draft against the
selected pair, then index. A source or draft edit clears that review. Indexing is
structural, not physical QC. Earlier immutable datasets/jobs remain unchanged;
**Edit indexed request as a new draft** never rewrites their source identities.

## Execute, inspect and reopen

Submit the eligible method, inspect submitted parameters/limits and poll job
history or cancel. Missing reviewed native context fails closed, not an
uncontained fallback. Windows uses committed-memory accounting; Linux uses
retained cgroup memory charge, neither peak RSS. A succeeded API job may still
be scientific `qc_only`: inspect exact QC reasons and do not fabricate missing
response/PSD/triggers. CPU B60/S57,1GiB, scratch52690944 and timing caps are fixed.

**Verify, plot and export all arrays** downloads and hash-verifies the complete
bundle before decoding. **Reopen saved ZIP against this successful job** uses
that exact job/result inventory, rejects changed/extra/compressed/missing members
and clears earlier arrays on failure. It is not an unbound arbitrary ZIP viewer.

Counts, native physical/filter signals and characteristic share the exact
conditioning-relative time cursor, with exclusive analysis-end boundary lines.
The actual `edge_valid` and `time_taper` arrays show eligibility/taper, not a
universal boundary-error guarantee. Arrow keys/Home/End move the time cursor.
PSD retains squared counts/native units per Hz and its actual frequency array.
Response amplitude is hypot(real, imaginary), principal phase atan2(imaginary,
real) in rad without unwrapping; response frequency and descriptor units are
the exported measured arrays. These are display transforms only: original
complex arrays and scientific seals never change. Spectra do not share a time
cursor. Unlabelled triggers show exact UTC, sample [on, off) interval, peak ratio
and edge truncation; phase and timing sigma remain null.

The same existing instrument works in EN/ES, light/dark and phone/desktop. Expand
Processing controls on a phone. Method navigation belongs inside the single
instrument aside, not a second page column. No new fonts/colors/CSS are needed.
Actual platform adversarial/cold gates and configured single-VPS qualification
remain separate from a successful calculation or rendered plot. No host, field
or method acceptance follows from this user workflow alone.

## Local validation storage

For owned frontend tests select an absolute external `GEOPHYSICS_QA_CACHE`, then
run `vitest run --config vitest.waveform-qa.config.ts --configLoader runner`.
This merges the existing test configuration without repository-local results
cache. The runner loader avoids the bundler's repository-local `.vite-temp`.
Use the same `--configLoader runner` with `vite.waveform-qa.config.ts` for the
isolated build, whose cache and dist roots must both be explicit and external.
Keep browser evidence in explicit external `GEOPHYSICS_QA_EVIDENCE`. These are
validation commands, not a production mount or an execution admission receipt.
