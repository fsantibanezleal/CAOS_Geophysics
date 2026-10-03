# Combined candidate independent review handoff

Date: 2026-10-03. The pre-implementation [combined plan](combined-plan.md)
extends the prior [assembly plan](assembly-plan.md), not the scientific gates.
Actual combined execution source is `11a5587e8a14ef787c74df194b428dbf2718f940`:
corrected FWI plus develop `afac8ab7b0be2df474406d1b17f0a165be9e0599` and
PR100 `0970a09fa7640d3ac6148a9ccdc0335d2a75782b`. Imported MT scientific code
is unchanged from `7b69404`. No canonical import, release, merge or deployment.

## Assembly and full-source audit

Fresh ignored candidate: `data/experiments/fwi-mt-full-candidate-20261003-run1`.
Receipts: `data/experiments/fwi-mt-full-receipts-20261003-run1`.
The original FWI-only full candidate and its 179-test historical receipt remain
intact. They are not relabeled as combined-source acceptance.

The MT producer receipt matches the independently supplied SHA
`76ef56e96c4d287906bfeade956e04099c26bd3fa19c4a06b048438180744fd2`.
All seven MT-relevant producer/checker source files match this combined tree.
Its unrelated seismic producer hash differs by design and is explicitly recorded,
not substituted. Producer Torch 2.12.0+cpu remains separate from independent
replay Torch 2.14.0+cu126. The machine receipt binds all 120 condition selections,
original hashes, byte counts, family proofs, tool hashes and replay outputs.

- **72 reused conditions:** gravity, magnetics, joint and learned modules match
  pinned baseline `dce92a1d8693afd60a33ff429dfff59cad4de64d` byte-for-byte.
  Each run retains its actual original version, fingerprint and complete bytes.
  All 12 corresponding case catalog entries equal the original catalog.
- **24 FWI conditions:** frozen precision-10 CUDA ledger, actual unchanged
  corrected solver/geology/writer hashes, 28 calls per stage, 112 total calls,
  explicit LBFGS max_eval=25. No seed, mask, wavelet or objective change.
- **24 fresh MT conditions:** exact fresh producer hashes and sizes, actual
  current generator fingerprint and immutable original reference hash per run.
  All 72 method dictionaries reproduce the original numerical values, histories,
  metrics, bootstrap and verdicts; this does not reuse old provenance bytes.
- **13 auxiliary files:** unchanged learned models/training and synthetic EDI
  fixture/calibration bytes; refreshed measured cl061 screen and manifest.
  The manifest outside `field_screens` is exactly equal to baseline. Fresh cl061
  screen bytes happen to equal its prior screen, but independent real parsing
  and current parser bindings were executed. Historical calibration is reuse,
  not newly measured empirical coverage. No phase/learned retraining.

The frozen plan is rechecked before copying, including tool hashes and all
selected input hashes. Copies and every original input are checked afterward.
No partial MT catalog/release overwrites the full catalog. Missing fresh MT,
stale scientific source, duplicate/missing ledger paths, reduced settings,
changed inherited EDI evidence and forged field eligibility are fail-closed.
`catalog.py`, `check_artifacts.py`, all scientific tolerances and the MT partial
checker remain unchanged during this extension.

## Independent numerical gates

The unchanged artifact gate passes **20 cases / 120 conditions / 348 methods**.
Full catalog SHA is
`a31c7560ded59060a2a62deecf9a8734fcc5a51c304bd1cdf49206e9dec3fc70`.
All **48 CUDA FWI replays** pass the original forward rtol/atol 2e-5/2e-5 and
residual rtol/atol 2e-4/2e-5. Observations, final predictions, residuals, metrics,
history and verdicts are independently recomputed. Its receipt hash
`79721c8b1f167559a96dc481e631b1869c6bdd66dbe2dc5b945dbae5464a0c2a`
equals the prior corrected precision-10 replay, not the failed seven-digit run.

The full-candidate MT orchestrator calls the unchanged numerical/field functions,
without weakening the existing partial-catalog CLI gate. It passes **4,038
objective states and 3,072 actual conditional bootstrap refits**, plus seeded
inputs, bounds, solver settings, final forward curves, residuals, metrics,
identifiability and verdicts. The MT receipt SHA is
`167314def5584af2bbe4c1d14e7d5931b6bdf4316e5cc986a58991b27f588006`.
The 24 conditions retain 61 recovered and 11 unresolved results. Tolerances are
still prediction rtol=3e-5/atol=1e-10, metrics rtol=2e-4/atol=2e-5 and the
original seven-digit residual cancellation allowance.

Actual cl061 original is 16,411 bytes, SHA
`90c5c96cd69d6d29c866a768097cb3b38bc20e8b9c143e24bf10b2d253261e83`.
It was hash-verified and copied into ignored local storage for independent replay
and the rehashed-eligibility adversarial test, not redistributed or committed.
Fresh parse retains 42 frequencies, null truth, no methods, no inversion and
ineligible status. Diagonal WRMS 320.2332602646 and 109.5078797787 and
antisymmetry WRMS 267.6000387519 exceed the unchanged threshold 3.

## Retained scientific negatives

| Family | Recovered | Unresolved | Failed | Negative control |
| --- | ---: | ---: | ---: | ---: |
| Gravity | 19 | 29 | 0 | 0 |
| Magnetics | 0 | 60 | 0 | 12 |
| MT | 61 | 11 | 0 | 0 |
| FWI | 24 | 6 | 6 | 12 |
| Joint | 18 | 30 | 0 | 12 |
| Learned | 0 | 48 | 0 | 0 |
| Total | 122 | 184 | 6 | 36 |

Layered multiscale active/held-out WRMS remains 1.2077864408/1.2330355644
(old fresh regression 2.607551/2.656599); model RMSE ratio is 0.5269253074.
Salt negatives, gas-channel unresolved cases, strong-regularization failures,
joint conflicts and failed learned claims remain. Synthetic recovery is not
geological truth. See [original findings](findings.md) and
[comparative receipt](../../../validation/fwi-lbfgs-regression-2026-09-28.json)
for the actual forward/adjoint audit and unsuccessful alternatives.

## Commands and release boundary

Expanded pipeline tests passed **300 with 15 explicit skips**, no errors or
failures, in 63.13 s. All original solver/data files, new FWI/assembly tests,
all nine MT adversarial tests including actual cl061 eligibility forgery,
M01 controls and source/contract checks execute. API/host and phase/learning
tests are separate scopes; no phase retraining occurs here. Skips cover opt-in
attributed source acquisitions, unavailable PyGIMLi/field originals, absent
C15 EDI and Windows symlink privilege. None covers FWI or pinned cl061.

The initial expanded collection failed because this runtime lacked `boule`;
`pipeline-tests.xml` preserves that failure. An ignored local dependency target
provides repository-pinned boule 0.5.0, harmonica 0.7.0, verde 1.9.0 and their
missing dependencies. No shared environment changed. A first dependency staging
attempt used verde 1.8.1 and lacked attrs; it is preserved separately and was
not used for successful tests. Core replay remains NumPy 2.2.6, SciPy 1.15.2,
Torch 2.14.0+cu126 and MT Metadata 1.0.10. This is not a claim that every
transitive M01 environment pin equals the existing FWI runtime.

`python` below denotes the existing FWI pipeline runtime. `$mtContribution` is
the owner-supplied read-only MT candidate directory. Use fresh output/receipt
names to reproduce; frozen plans and existing candidate/report paths must not
be overwritten. Pin CPU thread counts to one for MT replay; FWI uses four.

```powershell
python data-pipeline/assemble_fwi_candidate.py plan --output data/experiments/fwi-mt-full-candidate-20261003-run1 --receipts data/experiments/fwi-mt-full-receipts-20261003-run1 --mt $mtContribution --mt-receipt-sha256 76ef56e96c4d287906bfeade956e04099c26bd3fa19c4a06b048438180744fd2
python data-pipeline/assemble_fwi_candidate.py assemble --output data/experiments/fwi-mt-full-candidate-20261003-run1 --receipts data/experiments/fwi-mt-full-receipts-20261003-run1
python scripts/validate_fwi_mt_candidate.py --data data/experiments/fwi-mt-full-candidate-20261003-run1 --source data/downloads/clear-lake/USGS-GMEG.2022.cl061.edi --expected-canonical-sha256 7dfc0fc18a0a45988f501a7aaedbda12abca3628cfa403b19696bda618aba266 --report data/experiments/fwi-mt-full-receipts-20261003-run1/mt-independent-replay.json
python scripts/validate_fwi_exports.py --data data/experiments/fwi-mt-full-candidate-20261003-run1 --report data/experiments/fwi-mt-full-receipts-20261003-run1/cuda-replay.json
$env:INVERSE_EARTH_DATA = (Resolve-Path data/experiments/fwi-mt-full-candidate-20261003-run1).Path
$env:FWI_RECOVERY_ARTIFACTS = $env:INVERSE_EARTH_DATA
$env:PYTHONPATH = (Resolve-Path data/experiments/fwi-test-dependencies-pinned).Path
python -m pytest tests --ignore=tests/api --ignore=tests/learning -q -o addopts='' -ra --junitxml=data/experiments/fwi-mt-full-receipts-20261003-run1/pipeline-tests-complete.xml
python -m ruff check data-pipeline tests scripts/validate_fwi_mt_candidate.py
python scripts/check_content_standards.py
python scripts/check_template_residue.py
python scripts/check_ci_budget.py
python scripts/check_sdd_convergence.py
```

Canonical 137-file tree digest before/after numerical replay remains
`7dfc0fc18a0a45988f501a7aaedbda12abca3628cfa403b19696bda618aba266`.
It is intentionally source-stale for FWI/MT until owner-controlled import.
Candidate compatibility version 0.04.001 is unpublished and unassigned; the
scientific correction needs the next actual release version (owner-controlled,
expected patch 0.04.002), not an overwrite of old main's claim.

Product convergence remains R008 fail and 18 unresolved, byte-identical to
develop. Actual-host acceptance is separate: main reported disk 29.42% below
the unchanged 30% gate and a Linux/Windows M06 residual seam, subsequently
reported fixed in its verifier-only tree. This worker neither measures nor
asserts host readiness. Main owns independent review, canonical import,
versioned release evidence and PR readiness. No merge, cutover or deployment.
