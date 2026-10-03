# M13 real-waveform implementation design

Status: executable data boundary under the approved product SDD. It is not a trained or released M13 method.

## Source and format

The metadata source is the SeisBench STEAD mirror's 402,560,190-byte `metadata.csv`, already hash-verified in the metadata profile. The companion `waveforms.hdf5` is a separate 91,127,786,704-byte source and is not trusted until its download completes and a full SHA-256 receipt is recorded. SeisBench's documented waveform format maps `trace_name` to `data/[block]` and an explicit slice; the STEAD mirror uses bucketed `NCW` storage. The reader accepts only the observed bounded bucket-slice grammar, verifies the HDF5 format declaration (`CW`/`ZNE`/100 Hz/counts), decodes one 3-by-6000 trace and converts it to explicit `[sample,E,N,Z]` order. Unsupported layouts fail rather than guessing. The data are instrument counts without response restitution, not velocity in m/s.

## Partitions and selection

Use the fixed event-hash/station-hash intersection specified in `profile_stead_metadata.py`; the published trace-level train/dev/test column is ignored. A quake trace enters a partition only when its event and station hashes agree and both analyst P/S samples are finite integers in order. Noise traces have no event and follow the station hash. No event or station may appear in two partitions. A deterministic hash rank caps each partition's quake and noise inventory without inspecting waveform values, SNR or labels beyond eligibility. Manifest records candidate/quarantine counts, IDs, hashes and exact selection parameters. The final test waveform is not read for model or threshold selection.

## Model and evaluation boundary

The model input is 6000 samples at 100 Hz with E/N/Z channels. Normalize each trace from its own finite waveform (demean and per-component peak) without analyst picks or cross-split fitted statistics; preserve original counts, scales, orientation, and mask in local provenance. Training data include quake and station-disjoint noise windows. The P/S/noise target is a declared Gaussian arrival kernel; decision thresholds and minimum peak separation are fitted on dev only. The learned and M08 classical picker consume identical held-out traces, including misses and noise false positives. Report per-phase hit/false/miss rates and timing residuals, not just attractive probability examples. A separate untouched test run and browser-export parity are release gates.

No raw STEAD bytes are committed or web-served from this stage. Small rights-cleared held-out excerpts, model weights and derived probabilities need a separately recorded release decision, full source receipt and browser parity before public activation.
