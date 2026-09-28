# Earthquake phase picking (M08 classical comparator; M13 learned)

Status: **partial, local processing only**. The public 0.04.001 application does not execute this workflow. The attached [fixture audit](../../data/derived/phase/fixture-audit.json) is an exploratory failure-preserving ingestion and classical-baseline receipt, not a trained M13 result or release acceptance.

## Physical observation and inference target

A seismometer records ground motion as a time series for each available component. The compressional P onset normally precedes the shear S onset for a local event, but the waveform also contains site response, noise, scattering, other events and instrument effects. Picking estimates two onset times, not a subsurface image or an earthquake location. Instrument counts cannot be labelled velocity or acceleration without response information. In the upstream engineering fixture, individual trace metadata label either m/s or m/s²; the two are not pooled as an amplitude scale.

For sample index `i` and sampling interval `Δt`, `t_i = t_start + i Δt`. A phase residual is `r_phase = t_predicted - t_analyst`; positive means a late automated pick. The tolerance event is `|r_phase| ≤ τ`, here an exploratory `τ = 0.5 s`. Analyst picks have their own uncertainty, so even `r ≈ 0` is agreement with a reference, not geological truth.

## Source, format and window

The official [PhaseNet repository](https://github.com/AI4EPS/PhaseNet) offers a 100-trace test-data archive with labelled P/S indices and mixed network/station/channel metadata. We downloaded that release asset into ignored local raw storage and verified exact SHA-256 `60476821a71697ded05884c225c75ae7e0099bd9a7b79c4e2bdc9e7b3a5706b3` (24,935,083 bytes). The source is [provider-linked](https://github.com/AI4EPS/PhaseNet/releases/download/test_data/test_data.zip), not copied into this public repository. The MIT notice applies to the PhaseNet code; it is **not** treated as permission to republish third-party waveform bytes.

The loader bounds archive entry count and expansion, refuses path traversal and duplicate names, prohibits pickle-bearing NPZ, and compares catalogue versus embedded station, event, unit, interval, channel and pick fields. It quarantines 7/100 traces with ambiguous 1/2/3 channel orientation; 93 retain an unambiguous E/N/Z component mask, including single-component recordings. Missing components remain masked. A component filled with zeros by the provider is not relabelled as a measured quiet channel.

This particular archive places P near sample 6000 and S from 6052 to 7327 at 100 Hz. A fixed 4096-sample window from source index 4096 contains both phases for its engineering audit. The window is fixed for all traces and does not use each analyst pick to choose a centre. **The archive is unsuitable for training:** a network could learn the almost fixed P clock position instead of an onset feature. User-supplied event windows need their own independent event-time/survey metadata and cannot inherit this archive-specific index. Each measured component has a trace-local mean removal and peak scale recorded for inverse visualization; this operation is not a substitute for response correction. Learned training will need to freeze exactly the same operation for browser inference.

## Leakage-safe split

The split algorithm forms connected components in a bipartite graph whose vertices are events and stations and whose edges are traces. An event or station appearing in several recordings therefore remains in one component. A salted SHA-256 assignment of components to train/dev/test makes both event and station disjoint. For the 93 eligible fixture traces, the fixed salt `phasenet-fixture-v1` gives 61/17/15. This is a procedural check, **not** a sufficiently powered generalization test; all partitions were inspected during the exploratory baseline run. A later final benchmark requires a larger independently sourced, rights-cleared cohort with an untouched test set.

## Classical M08 comparator

The current local comparator operates on the identical normalized window used for a future learned picker. For energy `e_i = Σ_c x_{i,c}²`, it computes

`C_i = mean(e_{i-STA+1:i}) / max(mean(e_{i-LTA+1:i}), ε)`,

with STA = 0.12 s, LTA = 1.2 s and threshold 2.5. Its first upward crossing is provisionally P; the next at least 0.4 s later is provisionally S. It never reads the analyst pick when selecting a crossing. This is deliberately a simple classical detector, not a seismic phase classifier. A noise burst can become P and a coda onset can become S. No second crossing is recorded as missing, not silently replaced by a labelled time.

The observed failure is substantial. With the declared 0.5 s tolerance, development P/S recall is 5/17 and 4/17; exploratory test P/S recall is 1/15 and 1/15. Median absolute errors on the exploratory test are 16.81 s (P) and 15.01 s (S), dominated by premature triggers. These figures argue against calling the baseline adequate and against presenting it as a polished online method. They remain in the committed receipt, including miss/outside-tolerance denominators. A serious M08 comparator needs response-epoch QC, event-time/velocity-informed gates or more robust waveform features, with those priors sourced independently of analyst pick labels.

## Learned M13 design and non-claims

[Zhu and Beroza's PhaseNet](https://doi.org/10.1093/gji/ggy423) estimates per-sample P/S/noise probabilities from three-component waveforms. A valid implementation must train or fine-tune a versioned model, preserve event/station split and normalization, calibrate thresholds on development only, and compare against M08 on the **same** held-out trace IDs. Record false picks per window, misses, timing residuals, network/station and unit strata, noise/channel-drop sensitivity, and negative results. A checkpoint that might have seen the test waveforms during pretraining cannot be called independent without upstream training provenance.

The planned browser export must execute that same checkpoint on real, held-out waveforms. Offline and browser probability arrays must agree to max absolute float32 error ≤ 0.001 and peak times within one 0.01 s sample at fixed thresholds. Curves alone are not accuracy evidence; source, model hash, normalization, threshold and label uncertainty must remain visible. There is currently **no** trained M13 checkpoint, browser export or web inference. The 100-trace fixture is inadequate to close [BL-050](https://github.com/fsantibanezleal/CAOS_Geophysics/issues/83).

For a larger training/held-out source, the [STEAD origin](https://github.com/smousavi05/STEAD) labels its dataset CC BY 4.0. The [SeisBench metadata mirror](https://seisbench.gfz-potsdam.de/mirror/datasets/stead/) was downloaded locally and SHA-256-verified (402,560,190 bytes; `9b9007406ebfef8c182060c8bb4266d29bbc433985f91f7e2dc476c8aca08efe`). Its [aggregate profile](../../data/derived/phase/stead-metadata-profile.json) has 1,265,657 rows, including 745,012 valid P-before-S earthquake traces. The mirror's provided trace-level split repeats 59,820 events and 1,942 stations across train/dev/test among eligible records: it is **not** the required independent split. Hashing events and stations separately and retaining only agreeing assignments is a candidate, with 397,686/11,777/14,754 train/dev/test traces and 320,795 quarantined mismatches. The 91,127,786,704-byte waveform HDF5 is being acquired separately and has **not yet** passed a complete-byte hash and waveform-QC gate, so these metadata counts are not trained-model evidence. STEAD's README warns of misplaced back-azimuths and some duplicated-component noise traces. SCEDC's [deep-learning collections](https://local.scedc.caltech.edu/data/deeplearning.html) are another official route, but the 9 GB P-picking file alone does not solve the P/S benchmark.

## Reproduce this bounded audit

```powershell
gh release download test_data -R AI4EPS/PhaseNet -p test_data.zip -D data/raw/phasenet
.venv-pipeline/Scripts/python scripts/phase_fixture_audit.py --archive data/raw/phasenet/test_data.zip --output data/derived/phase/fixture-audit.json
.venv-pipeline/Scripts/python -m pytest tests/learning -q
```

The loader refuses a changed archive hash. Raw source storage and Python environments are ignored by Git; the committed JSON contains aggregate metrics and checksums, not waveform samples. The Phasenet archive and full STEAD/SCEDC downloads are intentional local data acquisition, never a CI, build or deployment side effect.
