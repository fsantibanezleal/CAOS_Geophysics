# Manuscript, shell and template review

Date: 2026-11-11. This is a local release review against the binding CAOS
manuscript bar and template 0.15.006. It is not scientific acceptance or a
release approval.

## Manuscript gate

The full local `check_manuscript_depth.py <product> --report` run finds five
remaining product-level findings:

1. The BS-1 draft title is absent from `product.json`, which records published
   DOI-backed documents only. The draft must not be added before the complete
   report and publication workflow; no DOI is invented.
2. `manuscripts/geophysics-identifiability` has no LaTeX `main.tex`.
3. `manuscripts/inverse-earth-studio-report-0.04.003/coverage.json` is missing.
4. `manuscripts/m12-nullspace-refinement-v0.01/coverage.json` is missing.
5. No manuscript folder is declared as the required technical report.

The remote branch baseline at `1e208f8` has a fifth finding: BS-1 has no
manuscript. This working tree now contains a draft BS-1 paper and a `coverage.json`
claim map. Its measured depth and scientific-content review pass, but the
product-level checker has no published-record title match. The full gate also
fails because the technical report and older manuscript are incomplete.

| Document | Prose words | Equations | Figures | Tables | Cited works | Algorithms | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| Technical report 0.04.003 | 3,357 | 0 | 1 | 1 | 14 | 0 | Far below report floor |
| M12 null-space study 0.01 | 2,837 | 3 | 6 | 4 | 16 | 1 | Below manuscript floor; raw inputs/checkpoint unavailable for full replay |
| BS-1 geometry-normalized residual study v0.01 draft | 7,655 | 16 | 7 | 6 | 32 | 1 | Measured depth, voice and independent scientific review pass at stated scope; unpublished-record gate remains open |

The binding floors are 12,000/25/10/8/30/3 for a technical report and
7,000/12/6/4/25/1 for a method manuscript (words/equations/figures/tables/
references/algorithms). The BS-1 draft adds an artifact-generated resolution-
kernel spectrum, numerical rank, supported-cell and angular-gap diagnostics. It
makes no untested lower-variance claim and does not claim that its negative
benchmark demonstrates novelty or advantage.

### BS-1 evidence and scientific limits

The SDD defines BS-1 as geometry-normalized, physics-conditioned residual input
for travel-time velocity refinement. The frozen GPU run selected epoch 40 of 40.
On 160 joint family/acquisition-shift synthetic surveys, learned-to-classical
RMSE ratios are 2.1942 for velocity (95% paired bootstrap interval 2.1328–2.2641)
and 5.5854 for observed-pick travel time (5.5093–5.6623); all 160 cases exceed
the validation-derived 6.091015 ms screen. The locked advantage rule fails. The
paper describes the comparison with a regularized straight-ray baseline and a
separately discretized bilinear scorer that also generates the synthetic picks,
but does not claim exhaustive comparison with current eikonal, Bayesian or
learned tomography implementations. Results remain
specific to the frozen synthetic generator and its acquisition shifts.

The paper corrects the implementation description: the reference solves an
unconstrained regularized normal system and clips physical slowness after the
solve. It does not label this as a bounded least-squares optimizer. Later channel
ablations use new test-cohort seed bases but reuse the primary training seed;
they are exploratory and do not alter the locked primary result. The paper was
rebuilt to a 25-page PDF. Layouts A/B/C have 252/254/251 supported cells and
numerical kernel ranks 126/128/127 at a relative eigenvalue cutoff of $10^{-10}$;
their largest axial-angle gaps are 11.30/10.96/11.64 degrees. These describe the
discretized acquisition operators, not geological uncertainty. Visual review of
pages 1, 12, 15, 16, 19 and 25 found a readable title/header, legible equations,
the complete diagnostics table and no clipping on those inspected pages.

Local verification performed:

- `build_analysis.py`: receipt and source hashes verified; seven figures and five
  generated result tables produced.
- `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex`: success,
  25-page PDF. No undefined reference/citation or overfull-box failure appeared.
- `check_manuscript_depth.py --only geometry-normalized-traveltime-refinement-v001 --report`:
  measured 7,655 words, 16 equations, 7 figures, 6 tables, 32 references and one
  algorithm; the content gate reports the missing published-record title match.
- `check_manuscript_voice.py` and the product `check_internal_names.py`: pass.
- `git diff --check`: pass.
- A separate scientific reviewer found the paper passes the content bar at its
  stated synthetic scope, verified formulas, hash-bound results and all seven
  figures, and found no P1 issue. Its three P2 language/citation findings were
  corrected. The reviewer then verified the revised wording, removed citations,
  rebuilt PDF and affected rendered pages; no remaining blocker was found.

The paper remains a draft. It has no DOI and is not published, so it is kept in
the manuscript workspace and is not added to the Zenodo-backed `product.json`
manifest. No DOI is invented to make the checker green. The technical report and
M12 paper also have no assigned DOI in their LaTeX headers.

## Technical report and earlier null-space manuscript

The report remains a short overview rather than the required thesis-depth account
of all implemented methods, data contracts, pipeline stages, results and limits.
Its current source is LaTeX, but it lacks measured depth and generated evidence
coverage. It cannot be repaired by adding a coverage file alone.

The M12 null-space study is a distinct follow-up, not a substitute for the BS-1
paper. It compares a projected candidate against a straight-ray baseline on
four synthetic cohorts and explicitly says it does not reproduce or outperform
the cited contemporary methods. Its receipt is present, but the exact source
checkpoint and raw generated inputs required for full solver replay are absent.
The paper is below the content floor and must not be presented as fully
reproducible or as a state-of-the-art comparison.

## Shell and product-template compatibility

All three repositories were fetched from origin. The product checkout is clean
at `f50dc67`, synchronized with its task branch. The Shell and Template
checkouts are also clean; their in-progress work is committed on task branches.

- The product records template instantiation origin `0.13.001`; this is not a
  claim that it conforms to the current template. Latest released template tag
  is `v0.15.006`. Template `0.15.007` is in open PR #124 and is not yet
  merged or tagged. Its new stage-input guard is not used by this product's
  pipeline workflow, so it has not been copied into the product.
- Product frontend and lockfile still pin Shell `0.25.0`. `npm view` reports
  `0.25.0` as the published version. Shell main contains merged `0.26.0` work,
  but there is no published `v0.26.000` package to adopt. The local Shell task
  branch adds two commits for known defects 43, 50, and 68 plus G21 tolerance.
  Its 335 unit tests, build, and 434-requirement SDD gate pass. The full gate
  matrix and browser suite remain unverified: this checkout already had three
  other full gate runs active, so this run was stopped rather than adding load
  or interfering with their shared fixture directory. The branch remains
  unpushed and unpromoted; the product stays on published Shell 0.25.0.
- Template `0.15.007` PR #124 contains the stamped-input guard plus a
  case-insensitive `.JSON` regression. Eleven focused tests, Ruff, the
  232-requirement SDD gate, and version coherence pass. The full pytest suite
  was interrupted early and remains unverified. The Template CI workflow runs
  on pushes to `main` and `develop`, not pull-request events; no workflow run
  is recorded for this PR. It has not been promoted.
- A fresh template-base scan of remote product commit `1e208f8` was started. It
  completed its early gates, then stalled in `check_content_standards.py`; the
  process was stopped after collecting its logs. The scan is not a full template
  pass. Exact temporary scan and visual-QA directories remain because the local
  command runner blocked recursive removal; only the LaTeX build intermediates
  were cleaned.
- Fresh scan findings include manuscript/schema and manuscript-depth failures,
  a document-check import crash (`contract_schemas`), readiness import failure
  (`pipeline`), base-integrity failures (shell modes, unadmitted model assets and
  repository-local machine paths), and conflicting pins in the technology
  matrix. `check_doc_paths.py` also reports unresolved paths. The content
  standards guard did not complete.
- The draft BS-1 entry is absent from `product.json` because that manifest
  accepts DOI-backed records; the paper's draft state remains explicit here and
  in this review. As a result, the manuscript title-to-registry content gate
  remains open until a compliant Zenodo record exists; no DOI or publication is
  fabricated.
- The repository contains the ML-VPS nginx configuration and systemd socket,
  API, and worker units. The product's only configured origin is
  `https://geophysics.ml.fasl-work.com/`; the product repository has no
  GitHub Pages workflow. A read-only remote comparison found the VPS serves
  catalog version `0.04.001`, while the local checkout is `0.04.003`.
  `scripts/verify_deployment.py` fails at the exact catalog comparison, so the
  candidate has not been deployed or accepted. No VPS files were changed.

The single-origin rule remains decisive: the ML VPS is the sole app target.
The VPS still serves the older release, and the product's content, notebook,
manuscript, and scientific acceptance gates remain open, so no replacement was
activated.

## Release disposition

## M12 bilingual method lesson update

The earlier M12 checkpoint lesson was a train-and-verify run with stale stored
metrics and did not meet the notebook bar. It has been replaced by a frozen,
hash-checked inference lesson in English and Spanish. Each mirror now measures
1,620 explanatory words after the depth tool's excluded sections, three
computed figures, two display equations, and six referenced sources. Both
notebooks execute in fresh kernels and pass the isolated-run byte-freshness
check. The runner now stages only this lesson's receipt and compact checkpoint
alongside its pipeline source; a focused regression test covers that behavior.

The recomputed M12 checkpoint remains a negative result: learned/classical
velocity RMSE ratios are 27.597, 5.617, 27.217, and 5.616 across the ID,
family-only, acquisition-only, and joint-shift groups; independent travel-time
ratios are 26.804, 12.279, 25.596, and 12.231. The notebook calls the real
local user-data processor with an explicitly synthetic control and preserves
the no-field-validation/no-online-admission claims. This repairs the M12
lesson pair only. The repository-wide notebook content and product gates still
fail on other lessons, so this work does not close R-016 or release acceptance.

Shell and template review found unreleased task-branch changes in both shared
repositories. The product must stay on published Shell 0.25.0 until Shell
0.26.0 is published; Template 0.15.007 remains in PR #124. Product template
compatibility is still incomplete. The CAOS notebook depth gate passes this
M12 pair, but course-wide notebook debt remains.

## Release disposition

This review found and corrected scientific-description defects in the BS-1
draft. The independent scientific verdict passes at the paper's stated
synthetic scope, but the product release bar remains open: the unpublished
manuscript registry, full technical report, M12 paper, data and notebook gates,
current template compatibility, method matrix, and actual VPS acceptance remain
incomplete. Do not merge to `develop`/`main` or activate a VPS release until the
required gates pass. Publishing the reviewed manuscript would require a separate
Zenodo deposit action; that has not been performed.
