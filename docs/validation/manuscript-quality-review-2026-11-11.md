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
| Technical report 0.04.003 | 3,289 | 0 | 1 | 1 | 14 | 0 | Far below report floor |
| M12 null-space study 0.01 | 2,850 | 3 | 6 | 4 | 16 | 1 | Below manuscript floor; raw inputs/checkpoint unavailable for full replay |
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
and synchronized with its task branch. The Shell and Template checkouts are also
clean; their in-progress work is committed on task branches.

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

## 2026-11-11 follow-up: released base adoption

The preceding shared-base statements are historical snapshots and are
superseded by the verified state below. CAOS App Shell 0.26.0 is now released
and published; `main` is `d2b3351`, npm `latest` is 0.26.0, and its package
`gitHead` matches the release. CAOS Product Template 0.15.008 is released on
`main` at `7dce8c9`. Its exact-main CI and Pages build completed successfully.
The Geophysics candidate pins Shell 0.26.0 and records 0.15.008 as the reviewed
current template base while preserving `.template-version` as the original
0.13.001 instantiation record.

Candidate commit `37b4070` updates the SDD, exact package/gate assertions, and
this adoption evidence. The focused Shell-version test passes (6 tests), and
the production frontend build succeeds with 148 declared files copied. The
build still reports a Workbench chunk above Vite's 500 kB advisory threshold.
The PR remains draft. The notebook depth audit still fails with 181 findings;
the report and M12 manuscript remain below their required content depth; the
BS-1 draft remains unpublished; M04 and the complete product/science/host
acceptance gates remain open. These base-adoption results do not justify release
promotion or a VPS replacement. The ML VPS remains the single deployment
target, and GitHub Pages is not configured for this product.

## Release disposition

This review found and corrected scientific-description defects in the BS-1
draft. The independent scientific verdict passes at the paper's stated
synthetic scope, but the product release bar remains open: the unpublished
manuscript registry, full technical report, M12 paper, data and notebook gates,
current template compatibility, method matrix, and actual VPS acceptance remain
incomplete. Do not merge to `develop`/`main` or activate a VPS release until the
required gates pass. Publishing the reviewed manuscript would require a separate
Zenodo deposit action; that has not been performed.

## 2026-11-11 repository and manuscript recheck

The manuscript-depth checker was rerun from CAOS_MANAGE against the current
product checkout. It still reports five findings: the BS-1 draft title has no
published `product.json` record; `geophysics-identifiability` has no LaTeX
main file; the technical report and M12 manuscript lack `coverage.json`; and
no folder is declared as a technical report. Measured depth is unchanged:
BS-1 7,655 words / 16 equations / 7 figures / 6 tables / 32 references / 1
algorithm; the technical report 3,289 / 0 / 1 / 1 / 14 / 0; M12 2,850 / 3 / 6
/ 4 / 16 / 1. The technical report and M12 remain materially below the
published content bar. A coverage file or registry entry alone cannot correct
those content deficiencies; the draft remains unpublished and no DOI is
claimed.

Shared-repository state has changed since the earlier section above. Template
PR #124 is merged to `develop` at `265d3ece6fba3533229497acf69ea50adce32416`;
the checkout is synchronized and clean at that commit, but the version is not
tagged as a release. Its stage-input guard has no matching stage-input workflow
in this product, so copying that guard would not fix the product's open
pipeline or manuscript gates. Shell PR #218 remains draft on
`task/0-26-0-defects`; its branch is synchronized and clean, while the full
browser/gate acceptance remains unverified. The product's reviewed integration
pin remains Shell 0.25.0 pending a published and accepted successor. No shared
repository changes were copied into the product during this review.

The product's current-source M04 selective-likelihood change now materializes
only the sealed fit observations and selected noise block after recomputing the
geometry seal. Its focused six-test assembly suite and four-test calibration
suite pass with the solver's required single-thread BLAS environment. A
528-parameter synthetic fold also converged with the original-accuracy
certificate. This is one fold and does not change the five manuscript findings
or the product acceptance status: the SDD ledger remains one fail and 15
unresolved, the VPS still serves 0.04.001, and replacement activation remains
blocked by the required product, science, host, and release gates.

The current deployment index and R-C06/API lifecycle requirements have been
reconciled to the single ML-VPS origin and the approved internal-account
profile. Public research/architecture copy no longer discusses a second host;
the former 0.03/0.04 deployment receipts remain explicitly historical. The
VPS-only deployment verifier was run against the canonical hostname and failed
on the live-versus-local catalogue byte comparison, so no deployment occurred.
The frontend's production build succeeds; Vite still reports an existing
556-kB Workbench chunk above its 500-kB advisory threshold.

## 2026-11-11 follow-up: shared-base and scorer review

The shared-base state in the preceding paragraphs is superseded by the
released-base adoption record above. CAOS App Shell `v0.26.000` is on shared
`main` at `d2b3351`, and the product dependency and lockfile pin `0.26.0`.
CAOS Product Template `v0.15.008` is on shared `main` at `7dce8c9`; the product
SDD records this as its reviewed current base while `.template-version` retains
the original `0.13.001` instantiation. The 0.15.007 stage-input guard remains
inapplicable because the product does not run that template workflow. The
reviewed base pins and changes are verified; this does not mean every current
template requirement or product gate passes. In particular, the measured
notebook, manuscript, method, deployment and product acceptance gaps below
remain open.

The current M04 fold scorer had a physical sign inconsistency: it reconstructed
the inducing-field vertical component as `+F sin(I)` in ENU, while the
validated engine uses `-F sin(I)` for positive inclination in its positive-up
vertical coordinate. The scorer now consumes the
engine-returned background vector, checks its shape and finiteness, and keeps
the same selective post-seal read of validation-only likelihood values. A new
analytic linear-TMI regression isolates the vertical contribution and checks
the predicted score and weighted objective. The combined scorer and fit
assembly suite passes 10 tests; Ruff and `git diff --check` pass. This closes
that local scoring defect only; it is not a validation of the inversion
method's scientific acceptance.

The BS-1 geometry-normalized residual draft meets the measured manuscript depth
floors and passes the voice check, but the product-level manuscript gate still
rejects the unregistered title and the paper remains unpublished. Its frozen
negative comparison against a regularized straight-ray baseline does not
establish advantage over contemporary eikonal, Bayesian or learned tomography
methods. The null-space follow-up uses different cases and lacks the unprojected
predictions needed to isolate the projection's effect; it does not substantiate
a separate novel method. The technical report and M12 manuscript remain far
below their required content floors, `geophysics-identifiability` still has no
LaTeX main file, and the current depth checker retains five findings. These
manuscript facts and the earlier build/page review were rechecked against the
current checkout on 2026-11-11. No DOI or publication claim is assigned.

The current product checkout also contains the exact ray-screen optimizer
change and its 19-test rational-oracle suite. That focused code change does not
alter any manuscript result or clear the remaining product or VPS acceptance
gates.

## 2026-11-11 measured-field case and final gate recheck

The CAOS App Shell checkout is clean on `main` at `d2b3351` / tag `v0.26.000`;
the Product Template checkout is clean on `main` at `7dce8c9` / tag `v0.15.008`.
The product pins the released Shell `0.26.0` and records the released Template
base in its SDD while retaining `.template-version` as the original `0.13.001`
instantiation marker. Neither shared repository has an unpromoted patch needed
for this integration, so neither was changed.

The USGS Amargosa source and current product copy were rechecked against the
official OFR 00-188 archive. The new adapter verifies the pinned compressed
hash, source row and expansion counts, parses the three distinct magnetic
channels, projects NAD27 coordinates, selects representative whole tracks,
and runs M03 on the provider-levelled channel without repeating the provider's
corrections. The bilingual foundational notebook pair replays the archive and
exposes separate source-read, track-selection and M03 calls. The 78,030-byte
derived result is hash-pinned in the field-study index and is now shown in the
Research page with full-range nT colouring, measured flight/tie geometry,
support-mask inspection, held-line metrics, source links and explicit limits.
It remains interpolation evidence, not a subsurface inverse.

Focused checks pass: six browser-artifact contract tests, 75 Python source/M03
tests, Ruff, fresh execution of both Amargosa notebooks, production data copy,
TypeScript and Vite build. Playwright checked desktop and 390-pixel mobile
widths; the artifact returned 200 with the pinned 78,030 bytes, all 12 flight
and 4 tie tracks render, the two display modes switch, and no page error or
horizontal overflow was observed. The Vite build retains the existing
556-kB Workbench chunk advisory.

The full frontend suite is not green in a clean local environment: 433 pass,
36 fail, and 29 skip because several unrelated custody/runtime tests require
retained external M04/M11 matrix controls that are not configured here. Those
controls were not synthesized. The repository-wide notebook depth checker
still reports 153 findings, and the structural checker still reports other
lesson failures; both Amargosa lessons themselves are absent from those
findings. The manuscript checker still reports five admission findings. Its
measures remain BS-1 7,655 / 16 / 7 / 6 / 32 / 1, the technical report
3,289 / 0 / 1 / 1 / 14 / 0, and M12 2,850 / 3 / 6 / 4 / 16 / 1 (words /
equations / figures / tables / references / algorithms). BS-1 remains a
negative comparison against a regularized straight-ray baseline, not a
state-of-the-art or novelty demonstration. The M12 null-space study lacks the
matched unprojected predictions needed to attribute its effect.

The VPS-only verifier was run against `https://geophysics.ml.fasl-work.com/`
and failed on the first byte-level check: the live catalogue differs from the
local `0.04.003` candidate. The current VPS remains at `0.04.001`; no file was
uploaded, no GitHub Pages deployment exists, and no release was activated.
The existing draft PR #151 has no recorded status checks and was not merged.
The product, science, curriculum, manuscript, full-suite and host acceptance
gates therefore remain open.

## 2026-11-12 recheck: current-source M12 reproduction

The 2026-11-11 statements that the M12 source checkpoint and raw generated
inputs were unavailable are superseded. I reran both retained independent CPU
verifiers against the 2026-11-06 outputs: residual-v3.1 returned
`status=verified` for five cohorts, and nullspace-v1.1 returned
`status=verified` for four cohorts. The CUDA-trained checkpoint and exact
receipts now exist in the product checkout under
`data/derived/v2/models/m12-current-reproduction-20261106/`; the staged byte
hashes match the external run records. The reproducibility gap for those
frozen synthetic cohorts is closed. The learned residual comparator remains
failed (joint-shift velocity/oracle-time ratios 1.0437/1.3961), while the
separate null-space follow-up remains bounded synthetic evidence
(0.9701/0.9967) and does not isolate projection's incremental effect.
Neither result establishes field accuracy or product acceptance.

The working M12 paper was updated to v0.03 and its factual custody text now
matches that reproduction. Its depth is still only 3,223 words, 3 equations,
6 figures, 5 tables, 18 references and 1 algorithm; it is below the manuscript
bar and has no `coverage.json`. The technical report now records the verified
reproduction, but remains 3,481 words, 0 equations, 1 figure, 1 table, 14
references and 0 algorithms, with no coverage map. The independent BS-1 paper
remains the strongest manuscript (7,655 words, 16 equations, 7 figures, 6
tables, 32 references, 1 algorithm); its negative synthetic result and
single-seed, no-field limits remain explicit. The recorded independent review
found no remaining blocker at the paper's stated synthetic scope. Complete
comparison against the broader current method set and the publication gates
are still open.

The current depth checker reports three findings: report coverage missing,
M12 coverage missing, and no manuscript declared as the technical report.
It is not a pass: measured depth and the technical report's required content
are far below the binding floors. The November 11 shell/template audit remains
historical; the current checkouts are shell 0.26.000 and template 0.15.010,
with the product's shell pin already updated. No product release was promoted
or deployed by this recheck; the live ML-VPS and one-origin release gates remain
open.

The M12 manuscript PDF and technical report PDF were rebuilt with XeLaTeX. The
M12 cover/reproducibility pages and report cover/M12-results page were rendered
and inspected; no clipping or overlap was observed. Both logs have no
undefined citations/references or overfull boxes.

## 2026-11-12 follow-up: paired projection and manuscript scope

The Beyond Methods study `geometry-normalized-traveltime-refinement-v001` remains a separate negative-result manuscript. Its claim map covers the proposed geometry-normalized residual method; its measured depth remains 7,655 words, 16 display equations, 7 figures, 6 tables, 32 references and one algorithm. The literature comparison and scope language distinguish first-arrival tomography from eikonal/PINN forward solvers and waveform inversion. No superiority or novelty claim is added. The main paper's recorded independent review remains limited to its stated synthetic scope.

The M12 null-space paper was expanded and corrected after the current-source same-case counterfactual became reproducible. It now has 7,887 words, 14 display equations, 7 figures, 6 tables, 25 references, and one algorithm. Its content includes the linear projector assumptions, operator distinction between the straight-ray matrix and bilinear oracle, same-case ablation, paired-case bootstrap scope, literature boundary, and explicit synthetic/field limitations. Its coverage map binds the learned residual method to the method section and includes the new ablation table and figure as title-supporting evidence. The newly rendered PDF compiles with XeLaTeX; the generated table no longer overflows the text width. Underfull bibliography/paragraph boxes remain nonfatal; no undefined-reference/citation or overfull-box warning was reported in the final successful build.

The post-hoc paired analysis uses the frozen checkpoint, alpha and lambda and matches all 480 case IDs to the v1.1 manifests; projected predictions are checked against the original receipt. It exposes a trade-off: projected/raw independent travel-time ratios are below one in every cohort, while velocity RMSE nearly doubles in ID and acquisition-only cohorts and falls in family-only and joint-shift cohorts. The analysis remains exploratory, fixed-simulator evidence with `scientific_acceptance=false`; it does not alter the earlier failed residual comparator, the original projected-to-L2 receipt, or the product release verdict.

The full manuscript-depth gate now has two findings, both confined to the product technical report: its coverage map is absent, and no folder is declared as the full technical report. The current overview is 3,481 words, 0 equations, 1 figure, 1 table, 14 references and no algorithms; assigning it technical-report status would misrepresent its coverage and depth. Neither manuscript check passing qualifies the product, method ladder, host, or release for deployment.

## 2026-11-13 follow-up: current traveltime literature and independent review

The BS-1 paper's Related Work now includes the 2026 DNRtomo neural parameterization, unstructured triangular-mesh adjoint eikonal inversion, and NTK-adaptive PINN weighting. The descriptions distinguish supervised travel-time prediction, physics-informed tomography and nonlinear eikonal inversion; they do not imply a shared benchmark or comparative result. The DNRtomo Zenodo record lists data and outputs but no method code, and its license field is blank. Full-text details for the Zhang and Tang papers were not available to this review; their discussion is restricted to publisher abstract and indexed metadata. No new novelty, accuracy, or field-transfer claim is made.

The revised paper measures 7,827 prose words, 16 display equations, 7 figures, 6 tables, 36 cited works, and one algorithm. `build_analysis.py` verified its pinned receipts and regenerated the figures/tables; the XeLaTeX build produced a 25-page PDF; the manuscript-depth, scientific-voice, content-standard, and `git diff --check` gates pass. Three rendered pages were inspected after the update and showed no clipping or overlap. The result remains the frozen negative synthetic comparison, not a demonstrated improvement over current published systems.

An independent read-only scientific review found no P0/P1 issue and one P2 interpretation limit: synthetic observations and scoring use bilinear operator Q while the learned features, training data term, and reference inverse use straight-ray operator A. The manuscript discloses this mismatch and limits its conclusion; it does not include a matched-operator control, so the failure cannot isolate how the proposed feature behaves when the generating and inversion operators agree. This is retained as a limitation and a possible follow-up experiment, not evidence of an implementation defect.

The whole-product manuscript check currently reports exactly two findings: the technical report's coverage map is absent and no manuscript folder declares `kind: technical-report`. The report remains 3,481 words with no display equations or algorithms, one figure, one table, and 14 references, below the 12,000/25/10/8/30/3 floors and without complete method/contract coverage. The single BS-1 manuscript's passing depth gate does not close this product-level gap, publish its draft, or qualify the app for promotion or deployment.
