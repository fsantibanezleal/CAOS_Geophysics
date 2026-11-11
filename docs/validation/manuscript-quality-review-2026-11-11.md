# Manuscript quality review

Date: 2026-11-11. This review applies the binding CAOS manuscript content bar in
`_CAOS_MANAGE/conventions/manuscript-content-bar.md` to the current geophysics
checkout. It is a release finding, not manuscript approval.

## Gate result

The product does not pass the manuscript gate. The authoritative command
`python tools/zenodo/check_manuscript_depth.py <product> --report`, run from
CAOS_MANAGE, returned five findings:

1. `manuscripts/geophysics-identifiability` has no LaTeX `main.tex`.
2. `manuscripts/inverse-earth-studio-report-0.04.003/coverage.json` is missing.
3. `manuscripts/m12-nullspace-refinement-v0.01/coverage.json` is missing.
4. No manuscript is declared as the required technical report.
5. The SDD's proposed BS-1 method has no manuscript mapped to it.

Measured content against the binding floors:

| Manuscript | Prose words | Display equations | Figures | Tables | Cited works | Algorithms | Required floor |
|---|---:|---:|---:|---:|---:|---:|---|
| Technical report 0.04.003 | 3,357 | 0 | 1 | 1 | 14 | 0 | 12,000 / 25 / 10 / 8 / 30 / 3 |
| M12 null-space study 0.01 | 2,837 | 3 | 6 | 4 | 16 | 1 | 7,000 / 12 / 6 / 4 / 25 / 1 |

The existing technical report and null-space manuscript are both LaTeX, but neither
meets its content floor. The technical report misses every measured floor. The
null-space paper meets only the figure, table and algorithm counts; it is short by
4,163 prose words, nine display equations and nine cited works, before section,
uncertainty, ablation, caption, label and figure-generation review.

## Proposed method and evidence boundary

The SDD's BS-1 is geometry-normalized, physics-conditioned residual input for a
bounded travel-time velocity CNN. Its current frozen `physics-v2` run trained on
the RTX 4070 Laptop GPU for 40 epochs and selected epoch 40. Its held-out result is
negative: on the 160 joint family/acquisition-shift surveys, learned-to-classical
RMSE ratios are 2.1942 for velocity and 5.5854 for independently computed travel
time; all 160 cases exceed the predeclared forward-residual threshold. The locked
advantage predicate therefore fails. The experiment supports no improvement,
novelty, field accuracy or geological-generalization claim.

The bilingual Level 4 notebooks replay this result and the hash-bound receipt is
recorded in `bs1-learning-lesson-replay-2026-11-11.md`. That is valuable negative
experimental evidence, but it is not a manuscript and does not close the BS-1
paper requirement. The earlier M12 null-space manuscript studies a different
projection follow-up and cannot be relabelled as the BS-1 paper. The two studies
use different checkpoints/cohorts and the older follow-up explicitly lacks the
raw arrays required for full replay.

## Required work before publication

- Create the technical report as a substantive LaTeX account of every implemented
  method, every data contract, each pipeline stage and the results actually shown.
- Create a separate LaTeX manuscript for BS-1 that reports the negative result,
  clearly limits it to the frozen synthetic generator, and does not make a
  superiority or novelty claim. The exploratory two-channel ablation is now
  recorded in `bs1-ablation-2026-11-11.md`; describe its post-hoc status and
  limitations without using it to tune or rescue the primary held-out result.
- Generate figures and result tables from committed scripts and hash-verified
  artifacts; do not hand-enter values or treat the external training directory as
  a repository deliverable.
- Add `coverage.json` for each qualifying manuscript, exact titles in coverage
  and `product.json`, the required sections and section-level depth, notation,
  uncertainty, caption/label references and checked citations.
- Re-run the full content gate and obtain a separate scientific review of claims,
  methods, figures and title support. Do not reserve a DOI or publish before both
  checks pass.

## Related shell/template reconciliation

CAOS_APP_SHELL 0.26.0 is merged to both `develop` and `main` (PRs #215 and #216).
The main-branch release CI, including its long browser/G15 gate, is still running.
The public npm version remains 0.25.0 and CAOS_Geophysics still pins 0.25.0, so
the product has not yet adopted the 0.26.0 package. The local product template is
clean and synced to `develop` 0.15.006. This review does not claim a new app build,
host acceptance or deployment.
