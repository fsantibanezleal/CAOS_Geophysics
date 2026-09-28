# M13 earthquake phase picking: feature requirements

Date: 2026-09-27
Status: implementation design, subordinate to the approved product SDD
Issues: BL-018 / #50 (classical M08 comparator), BL-050 / #83 (M13)

## Scientific question and scope

Given an oriented, sample-rate-declared three-component event waveform, estimate P and S onset times and compare them with independently supplied analyst picks and a classical STA/LTA-based picker on **identical** held-out traces. A probability curve is not a catalogue pick until threshold, peak separation and timing reference are declared. A low timing residual on a few curated examples is not generalization.

The official PhaseNet [paper](https://doi.org/10.1093/gji/ggy423) and [MIT source](https://github.com/AI4EPS/PhaseNet) are algorithm references. The official release's test-data archive is a **small, 100-trace engineering fixture**, not a scientifically sufficient training benchmark or evidence of its raw redistribution rights. Its downloaded source URL is https://github.com/AI4EPS/PhaseNet/releases/download/test_data/test_data.zip; local receipt is 24,935,083 bytes, SHA-256 `60476821a71697ded05884c225c75ae7e0099bd9a7b79c4e2bdc9e7b3a5706b3`. It contains 100 event-labelled NPZ traces, 100 distinct event indices and 82 station names. All claims from this source must be marked *fixture/pilot*; no raw bytes are committed or mirrored.

The original [STEAD repository](https://github.com/smousavi05/STEAD) declares CC BY 4.0 for its waveform dataset. The SeisBench mirror's metadata.csv has been acquired locally (402,560,190 bytes; SHA-256 `9b9007406ebfef8c182060c8bb4266d29bbc433985f91f7e2dc476c8aca08efe`) and [profiled](../../../../data/derived/phase/stead-metadata-profile.json). Its 1,265,657 rows include 745,012 earthquake traces with valid P-before-S indices. The mirror's published trace-level split repeats 59,820 event IDs and 1,942 stations across partitions on that eligible subset, so that split is rejected for M13 validation. A deterministic event-hash/station-hash intersection would retain 397,686 train, 11,777 dev and 14,754 test traces, quarantining 320,795 cross-partition traces. This is a **metadata-only candidate**; waveform-byte verification, source-specific QC and an untouched final evaluation remain required.

## Input and provenance contract

- Preserve the source ZIP unchanged and hash before parsing. Reject excess entries, absolute/parent paths, oversized uncompressed total, duplicate names and unexpectedly shaped entries. Read NPZ members without extracting to a web-served directory; `allow_pickle=False`.
- Require explicit sampling interval and units, numeric finite waveform, bounded dimensions, phase indices in range with P before S, trace ID, event ID, station ID and channel description. Never impute an absent component as a measured zero; mark it absent. Do not infer response-corrected velocity from a unit string alone.
- The fixture metadata declares `dt=0.01 s`, P near sample 6000, S from samples 6052–7327, and mixed `m/s` and `m/s**2` units. These cannot be pooled as one physical-amplitude feature without an explicit transform. Per-trace scale-normalized picking is allowed with units still recorded, and unit-stratified metrics required. **Do not train M13 on this 100-trace archive:** nearly fixed P index would permit a clock-position shortcut unrelated to waveform physics.
- Canonical model input is a declared 4096-sample window at 100 Hz that includes both labelled phases in the fixture; the indexing transform and any truncation are recorded. For user data, no silent resampling, component rotation or response removal. Explicit preprocessing and QC precede inference.

## Leakage-safe evaluation and classical comparator

- Partition **events and stations** before fitting any normalization or threshold; assert neither spans train/dev/test. A small fixture can use graph-connected groups. For full STEAD, hash events and stations independently and retain only traces where assignments agree; quarantine all mismatches and report resulting strata. An external test source must also be screened for any pretraining overlap. The 100-trace fixture can validate the split procedure but cannot support a broad performance claim.
- Fit learned weights and decision thresholds on train/dev only. Test is read once for final metrics. Record training seed, source hash, split-member hashes, library/CUDA versions, model architecture, epochs, loss, checkpoint hash and early-stopping choice. Fine-tuned borrowed checkpoints need their own documented training-source overlap; otherwise train from scratch and state sample-size limitations.
- Run a classical M08 picker on exactly the same trace IDs, sample windows and picks. Report per-phase coverage/recall, missed picks, false picks per window, absolute timing residual distribution and signed bias, stratified by station/network and physical unit; retain failed and low-SNR examples. A matched noise and channel-drop degradation test must be repeatable.
- Phase labels are uncertain analyst observations. Do not call the model output geological truth or a validated event catalogue. Unseen network/site performance and family shift remain unverified until measured.

## Browser inference and release gate

- Export the **same** evaluated checkpoint with a versioned input/output shape and preprocessing specification. On real held-out traces, compare browser probability arrays with the local reference within a predeclared numerical tolerance (initial float32 maximum absolute error ≤ 0.001), and verify peak times within one 0.01 s sample at a fixed threshold. This is a parity check, not a model-accuracy metric.
- The browser must execute inference locally on supplied/curated eligible waveforms, show P/S/noise curves and M08 picks on identical axes, and expose source, normalization, threshold, uncertainty and failure status. Reduced-motion and touch/pointer access follow the product SDD; no precomputed animation may masquerade as inference.
- Do not publish the fixture's raw traces, model weights derived from uncertain-rights data, or a public M13 case until a source/derivative rights decision is recorded. Until an adequately sized benchmark and browser parity both pass, M13 stays **incomplete**, even if local pilot tests are green.

## EARS requirements and executable gates

R-PH-001 WHEN a source archive is imported, THE pipeline SHALL verify exact bytes and safe entries before decoding. Gate: `tests/learning/test_phase_source.py::test_archive_receipt_and_rejections`.

R-PH-002 WHEN a trace has invalid geometry, unit, sample rate, pick order or nonfinite data, THE pipeline SHALL reject it or return a typed QC failure without fabricated samples. Gate: `tests/learning/test_phase_source.py::test_trace_contract_rejects_ambiguity`.

R-PH-003 BEFORE training, THE pipeline SHALL create a deterministic event-and-station-disjoint partition and fit any learned transform on training members only. Gate: `tests/learning/test_phase_split.py::test_disjoint_station_event_and_reproducible_hash`.

R-PH-004 WHEN M13 is evaluated, THE pipeline SHALL compute classical M08 and learned outputs on the identical held-out traces and report misses, false alarms and phase timing residuals with failures retained. Gate: `tests/learning/test_phase_evaluation.py::test_matched_inputs_and_failed_picks`.

R-PH-005 WHEN an exported model is loaded in the browser, THE app SHALL match the canonical checkpoint's probabilities and picks on held-out real traces within the declared tolerance. Gates: `tests/learning/test_live_export.py::test_onnx_offline_parity` and `frontend/e2e/phase-picker-live.spec.ts::real_trace_parity_and_matched_baseline`.

R-PH-006 IF source or model redistribution rights remain unresolved, THE release SHALL keep raw/derived bytes private and mark M13 ineligible for a public curated case. Gate: source-rights ledger review and release asset scan.

R-PH-007 WHEN the STEAD mirror's bucketed waveform file is read, THE adapter SHALL require the complete pinned byte/hash receipt, declared 100 Hz sample rate, counts without response restitution, Z/N/E orientation and a bounded trace slice; IF any contract fails, THEN no waveform SHALL enter training or evaluation. Gate: `tests/learning/test_stead_waveforms.py::test_bucket_reader_and_rejections` followed by an independent SeisBench read on the verified source.

R-PH-008 BEFORE reading waveforms for model fitting, THE metadata selector SHALL partition events and stations jointly, assign noise by station, retain no cross-partition trace, and apply a fixed hash rank independent of amplitude or SNR. Gate: `tests/learning/test_stead_waveforms.py::test_joint_metadata_selection` and full-source manifest counts.

## Acceptance sequence

Source/rights receipt → parser and negative fixtures → deterministic split → classical baseline → GPU training with genuine checkpoint → held-out benchmark/degradation → export and local parity → browser parity and rendered QA → rights approval and public release. Each transition records failure as failure. No green unit test alone closes #83.
