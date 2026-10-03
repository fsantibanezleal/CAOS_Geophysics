# M08 local waveform sub-SDD: full pre-code review packet

Date: 2026-10-03. Status: DOCS_ONLY / FULL_MAIN_READ_REQUIRED / NOT_APPROVED.
Research checkpoint851bc581ee46bb7f0576c739525c9a5e6f338215; complete science
milestone242dec06bcee12a7110d271c5955aa10b2d0e5d7. Final pushed head is recorded in
the draft PR self-review/handoff, not inferred from these historical milestones.
Base develop4db6a1613373d139e4496b6392e605c36adfa978. Related issues
[#42](https://github.com/fsantibanezleal/CAOS_Geophysics/issues/42) and
[#50](https://github.com/fsantibanezleal/CAOS_Geophysics/issues/50) stay open;
neither whole-method acceptance nor implementation authority follows from this SDD.
Draft [PR142](https://github.com/fsantibanezleal/CAOS_Geophysics/pull/142) targets
develop. Do not mark ready/merge before Main's full pinned pre-code review.

## 1. Full reading inventory and exact decision

Seven core files, all required for the Main pre-code review:

1. [Research and existing scientific/source inspection](research.md).
2. [Twenty EARS requirements with prospective named gates](requirements.md).
3. [Local method, owned paths, engine/resource/authority design](design.md).
4. [Exact input/time/response/QC/output/error contracts](contracts.md).
5. [Independent numerical, negative, case and resource validation](validation-plan.md).
6. [Dependency tasks and hard authorization holds](tasks.md).
7. This review packet and exact scope/nonclaims.

Required scientific annexes, not a substitute for those core files:
[literal equations and estimator semantics](algorithms.md),
[rights-aware original Ridgecrest plan](ridgecrest-case.md), and exact actual
documentation retrieval records in [original receipt](evidence/primary-retrieval.json)
and [supplement](evidence/primary-retrieval-supplement.json). Bodies/hashes are
research documents, never MiniSEED/response/pick fixtures. The original eight
records remain unchanged; nineteen supplemental attempts include one bounded
failure and its separately measured full-document retry. No field asset exists.

Main must accept/amend this exact packet before any proposed module/test/fixture:

- Local question/identifier: `seismic.waveform-qc-classical/v1`; original measured
  integer counts, complete published response, conditional native motion,
  offline filter/PSD and unlabelled onset intervals. Not an earthquake/earth-model
  inverse, a new calibration, phase classifier or frozen M08/M13 replacement.
- Fixed proposed limits:16 MiB MiniSEED2,2 MiB StationXML,64 KiB request/raw and
  scientific ASCII identity, one station/1..3 actual channels,4096 records,
  60000 samples/channel and180000 total,300 s conditioning, XML and response
  descriptor caps, FFT<=131072, W<=20000000, derived directory<=32 MiB.
  Parser limits and work estimates are NOT a measured memory/CPU admission lane.
- Time/frame/unit policy: exact microsecond corrected record grids, no gap fill,
  interpolation or guessed ENZ; full nested epoch coverage; complete linear
  stages and native SI units only. Clock/ADC/calibration uncertainty remains
  unknown; `absolute_timing_verified=false`, phase/sigma/field_truth null.
- Numerical semantics: explicit detrend/taper, full complex response/native
  inverse/prefilter and null-water-level safety, SOS/acausal edges, periodic-Hann
  Welch density/Parseval, exactly `classic_sta_lta_py`, strict hysteresis and
  greedy sealed-reference matching. Oracle scales/tolerances are predeclared;
  near-threshold disagreement is unresolved, not a threshold/tolerance repair.
- Actual engine candidate: ObsPy1.4.2/libmseed/evalresp plus NumPy2.2.6,
  SciPy1.15.2. Compatibility is UNVERIFIED; no install/env change or silent
  fallback authorized. Confirm available approved runtime before a numerical lane.
- Rights/case decision: initial CI.GSC empty-location HNZ, event38457511,
  fixed2019 window/profile, separately authorized bounded source acquisition
  and per-object rights review. No substitute successful station/response/label
  if the original is unavailable/unsupported/QC-only. Source-valid replay
  regenerates from original bytes, never a self-declared digest or edited epoch.
- Future exact new paths: those in design section2 only. Main separately decides
  local child containment/telemetry authority. Memory threshold is UNSET/CLOSED;
  proposed60 s child deadline is not a passed local/VPS/browser/phone profile.

## 2. Current documentation checks versus future acceptance

The [docs audit](evidence/docs-review.json) records local scope/link/mapping/source
checks only. Source invariance is also explicitly pinned in research.md.
Twenty future gates are absent/NOT_RUN, including
`tests/numerics/test_waveform_picks.py::test_response_epoch_and_classical_picks`.
No mocked decoder/response, numerical suite, cold RSS/CPU/scratch measurement,
local waveform acquisition, catalogue comparison, API test/build/browser grid
or actual host admission was executed by this design task.

Measured cheap checks use the existing CPython3.12.10 interpreter read-only:

```text
python -B scripts/check_content_standards.py
python -B scripts/check_template_residue.py
python -B scripts/check_ci_budget.py
git diff --cached --check
```

Disabled bytecode only for each command, no environment setting/install or
shared output adoption. The additional read-only docs audit verifies all local
Markdown links, unique twenty requirement/gate mappings, absence of prospective
source/test paths, original retrieval-receipt identity, all eleven actual source/
artifact hashes and Git blob invariance against the original base. It checks
the task diff contains only this feature directory; it does not waive the
existing product convergence ledger. Unrelated runtime gates remain unchanged.

Independent Main review must resolve any proposed cap/engine/parser/scientific
policy revision explicitly; these prose choices are not prior implementation
approval. After approval, test-first genuine engines/oracles/source cases and
actual resources require new exact receipts and independent replay, not reusing
the design guard verdict.

## 3. Scope, exclusions and retained uncertainty

This branch adds only the seven core docs, two scientific annexes and three
documentation evidence files in `docs/design/features/m08-waveform-user-data/`.
No product SDD/shared ledger/wiki/source/test/canonical/dependency/lock/environment/
frontend/API/worker/storage/job/migration/bundle or host/provider configuration
is an edit target. The local CLI takes explicitly user-declared file paths,
never provider URLs; its proposed directory format is not the app export format.

All eleven protected diagnostic directories remain untracked/excluded and
untouched. Prior physical-JSON branch76f7443550d988fbf6cd44ead732d0dfe063ecfa and
course refbe4ec1cea4a02c25829ec902fbc86e53d313fe30 are preserved. Private originals,
QA/receipts and environments are not inspected/adopted as new producer evidence.

Still unresolved: real engine/runtime compatibility, all twenty scientific/
negative/resource gates, actual raw source/response/reference rights and hashes,
full-window eligibility, optional analyst evaluation, memory/containment/cancel/
crash telemetry, independent implementation replay and full M08/product vertical
instruments. All acceptance flags remain false in the proposed local result.
No online activation, generic MiniSEED3/SEG-Y/DAS/FWI adapter, learned-model training,
M13 inference/parity/checkpoint/cohort change, scientific source-policy waiver,
merge/deployment or host execution is authorized by this handoff.
