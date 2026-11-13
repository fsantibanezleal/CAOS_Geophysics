# Current shell, template, and manuscript review

Review date: 2026-11-11. This records the current checkout and supersedes the
version references in the 2026-11-10 reconciliation. That earlier file remains
the historical baseline for its original commit.

## Shared foundation versions and adoption

The product is on `task/geophysics-client-first-completion`, based at
`68de7761432d9cb0f2be58f2d65216e7a7e81016` before this working change. The
product checkout is synchronized with its same-named `origin` branch. The
shared shell main is `d2b3351b672bfa43e6aceb5893afb672b1fc58d7`, release
`0.26.000`; the template main is `7dce8c9db460fb094d26b3a024872dd6f036e215`,
release `0.15.008`. Their local `main` branches matched their fetched remote
main branches at review time.

`frontend/package.json` and `frontend/package-lock.json` resolve
`@fasl-work/caos-app-shell` 0.26.0. `frontend/scripts/gate.mjs` refuses any
other shell version and runs the shared product gate with Focus and Showcase
required. The SDD now identifies shell 0.26.0 and template 0.15.008. The
`.template-version` value `0.13.001` remains the original instantiation
provenance; it is not a claim of current-template equivalence.

The latest template's shared `frontend/scripts/declared.mjs`,
`frontend/scripts/copy-data.mjs`, `frontend/src/lib/declared.test.ts`, and
`frontend/src/lib/copy-data.test.ts` are byte-identical to the product copies.
The product's own `copy-data.product.mjs` remains the scoped extension point
for its domain artifacts. Template 0.15.007's stage-input rule applies only to
`scripts/local/workflow.py` inputs; neither that runner nor its workflow JSON
exists in this product, so no unrelated runner or migration is being added.
Template 0.15.008's shell update is already reflected in the exact product pin.

Shell 0.26.000 addresses chart header sizing, moving chart marks, settled
callout geometry, fitting card decks, responsive callout values, Focus HUD
clipping, UTC time labels, serialized browser tests, formatter cost, and the
G21 frame interval floor. The product does not replace the shell's global CSS
or fonts. Its stylesheet holds geophysics widget and story-layout rules that
consume shell tokens. A successful build or dependency resolution alone does
not pass the shell's visual gate; the current candidate must pass the product
gate and its screenshot review before release.

## Manuscript status and scientific review

The independent CAOS_MANAGE depth checker currently reports:

| Manuscript folder | Words | Equations | Figures | Tables | References | Algorithms | Result |
|---|---:|---:|---:|---:|---:|---:|---|
| `geometry-normalized-traveltime-refinement-v001` | 7,655 | 16 | 7 | 6 | 32 | 1 | Meets the measured manuscript floors; declared as a draft with no DOI or peer-review claim. |
| `inverse-earth-studio-report-0.04.003` | 3,289 | 0 | 1 | 1 | 14 | 0 | Fails the technical-report content floor and has no `coverage.json`. |
| `m12-nullspace-refinement-v0.01` | 2,850 | 3 | 6 | 4 | 16 | 1 | Fails the manuscript floor and has no `coverage.json`; it is not mapped to a declared SDD claim. |
| `geophysics-identifiability` | n/a | n/a | n/a | n/a | n/a | n/a | Markdown only; it is not a LaTeX manuscript. |

The three LaTeX titles and kinds are now registered in `product.json`; no DOI
has been assigned to any of them. This removes the unmatched geometry-paper
title finding but does not supply report or nullspace coverage. The refreshed
checker reports four remaining findings: the Markdown-only folder, missing
coverage for the report and nullspace paper, and no manuscript folder
classified as a technical report.

The geometry-normalized paper is the local manuscript mapped to BS-1 in its
`coverage.json`. It describes the path-length-normalized residual backprojection,
coverage conditioning, bounded residual CNN, training and baseline selection,
and a synthetic-only held-out comparison. Its result is explicitly negative:
on the joint family-and-acquisition shift, the learned-to-reference velocity
and observed-pick travel-time error ratios are 2.194 and 5.585, with reported
case-bootstrap 95% intervals 2.133–2.264 and 5.509–5.662; all 160 cases exceed
the validation-derived 6.091 ms screen. The predeclared criterion requiring
both ratios below one is not met. The paper also labels its post-outcome
channel ablation exploratory. This is an honest falsification study; it does
not establish improved inversion, field transfer, geological truth, or a
state-of-the-art advantage.

That paper's title, equations, figures, result-support labels and BS-1 mapping
agree with the local evidence. It is an unassigned preprint: the header says no
DOI, the new `product.json` entry records its manuscript kind, and no Zenodo
record or publication claim is made. No identifier is invented to satisfy a
metadata gate.

The existing technical report and nullspace study are not publication-ready.
All 49 manuscript PDF pages were rendered and inspected in contact sheets. The
25-page geometry-normalized paper has legible single-column layout, embedded
figures and tables, and no visible blank, clipped or displaced page; extracted
PDF text has no unresolved `??` references or replacement characters. The
visual inspection does not verify every numerical claim or citation against
its source. The report and nullspace PDFs also render without obvious page-flow
defects, but the nullspace paper is only 2,850 words, 3 equations and 16
references. The report's source and rebuilt PDF now state that no DOI is
assigned; the old placeholder DOI macros were removed. Its methods table was
reflowed, then rebuilt to 12 pages with no LaTeX overfull boxes or unresolved
cross-reference markers. Both remain below their required content/coverage
bars.

The geometry paper's figures and tables are visually intact, and its title,
equations, figure labels, result-support labels and BS-1 mapping agree with the
local evidence. It still requires a final cross-check against the current
frozen receipts before a future version can be considered for publication. The
technical report must cover every implemented method, data contract, pipeline
and result; the current source does not do so.

## Current release boundary

This review establishes the shared foundation versions and identifies current
content gaps; it does not establish product acceptance. The M04 solver
candidate-path failure, complete method matrix, method-specific local data
workflows, frontend visual acceptance, actual-host resource admission, account
and project flows, release rehearsal, and the canonical ML-VPS cutover remain
separate open gates. No GitHub Pages deployment or second application origin
is part of this release. The single intended public origin remains the ML-VPS
hostname in `product.json`.

## Follow-up verification: 2026-11-12

The same-named remote branch and local task branch were synchronized at
`68de7761432d9cb0f2be58f2d65216e7a7e81016`; `origin/develop` is its recorded
base, so no rebase is required. The open PR #151 remains a draft. The local
checkout has one worktree. Product changes are still pending in that branch;
this review does not equate a committed draft with merge or release approval.

The product build succeeds after the data-copy, shell-layout, title, linked
evidence and manuscript metadata changes. Focused EDI/FWI tests report six
passed and two skipped; focused magnetic tests pass (9 tests) with the
required single-thread BLAS environment, and Ruff passes.
A focused browser matrix for the changed routes and the 1280x800 layout
passes. The all-route browser gate measured 1,683 states and retained seven
findings: one executive-to-proposal navigation timeout, five Spanish intro
transition/coverage findings, and one lazy story route that had not settled at
the gate's wait boundary. A later focused G21 replay still timed out while
reading the matching linked-panel state after a synthetic click; manual
browser inspection showed matching scene/panel IDs and bidirectional
selection on the regularization story. This discrepancy is unresolved, so
the all-route visual gate is not accepted. No shell package source was edited.

The M04 sparse candidate remains an actual solver failure, not a harness
success: the approved same-beta run reaches its 120 s wall cap at epsilon
0.0125 and selects no candidate. The independent L2 solve converges, but does
not substitute for sparse success or the missing candidate matrix, nested
selection/refit, and sealed evaluation. Its current receipt is recorded
outside the repository under the configured research-run root; the bounded
solver result is not product acceptance.

The BS-1 manuscript is the only substantive beyond-methods manuscript and
meets the measured structural floor. Its predeclared hypothesis is falsified
on the frozen synthetic joint-shift cohort; it makes no field-transfer,
geological-truth, or superiority claim. It remains an unpublished draft, and
its quantitative claims still require a final cross-check against the frozen
receipts. The other manuscript findings remain: the technical report and
nullspace study are below their content bars and lack coverage maps, the
identifiability folder is Markdown-only, and no declared technical report has
complete method/pipeline coverage. Those gaps are not closed by registering
titles or rebuilding a PDF.

No current full-product acceptance exists. Promotion to `develop`/`main` and
the sole ML-VPS deployment remain blocked by the solver, complete scientific
matrix, manuscript depth/coverage, all-route UI, and host-admission gates.
GitHub Pages remains retired; there is no second application deployment.

## 2026-11-12 evidence correction and M04 lesson review

The BS-1 numerical cross-check is now reproducible from the recorded run roots.
The manuscript folder had contained reserialized primary and ablation receipt
JSON files that no longer matched the recorded SHA-256 values or the ablation's
primary-receipt binding. The byte-exact files were recovered from
`E:/_Datos/CAOS_Geophysics/m12-physics-v2-20261111-run1/receipt.json` and
`E:/_Datos/CAOS_Geophysics/m12-physics-ablation-v1-20261111-run3/receipt.json`.
Their hashes now match the manuscript's pinned identities. The committed
checkpoints and ablation variants also match their receipt hashes.

`build_analysis.py` then verified the source and artifacts and regenerated all
seven figures and five result tables. The current joint-shift result is 2.1942
(95% paired case-bootstrap interval 2.1328–2.2641) for velocity RMSE and 5.5854
(5.5093–5.6623) for independent travel-time RMSE across 160 cases; all 160
exceed the validation-derived 6.091015 ms threshold. These remain negative
synthetic results and do not support novelty, field transfer or superiority.
The compiled 25-page PDF extracts to the same text as the prior PDF; the
LaTeX build has no unresolved references or overfull boxes. The depth check
passes at 7,655 words, 16 equations, 7 figures, 6 tables, 32 references and one
algorithm, and the scientific-voice check is clean. The paper is still an
unpublished draft, and this review does not establish peer review or DOI
publication.

The bilingual M04 fit-objective lesson now explicitly compares a diagonal
approximation with the production full-covariance whitener on the same three
residual rows and marginal uncertainties. Fresh-kernel replay produces an
identical 6.06% objective decrease in both languages, with an authored
sensitivity covariance clearly distinguished from measured field covariance.
The new method entrypoint, notebook title, sources and scope are synchronized
across the product registry and source-to-content review. The structural docs
matrix passes for all 13 methods and 66 notebooks. The course-wide notebook
depth checker still has 142 findings; the four product-wide manuscript
findings and remaining scientific/release gates are unchanged.

## Follow-up: 2026-11-12 current template adoption

The prior follow-up contains two stale statements corrected here. The current
checkout includes `scripts/local/workflow.py` and `scripts/local/workflow.json`;
the workflow declares `scripts/local/geophysics_readiness.py` and the product
readiness checker guards that provider. `.template-version` now records the
adopted CAOS_PRODUCT_TEMPLATE 0.15.010 release. The product-local staged
workflow already contains the custom-provider admission behavior introduced
by 0.15.010 and the explicitly scoped engine-version checks introduced by
0.15.009; its other product-specific differences were reviewed rather than
replaced wholesale from the template. The exact Shell 0.26.0 pin remains in
the manifest, lockfile, and product gate. No shell CSS, font, or package source
was changed.

Fresh verification on this checkout passed the custom-readiness and bootstrap
admission tests (47 passed, 7 skipped), and `python scripts/check_readiness.py`
reported the declared product provider current. The convergence ledger is
hash-bound to the corrected SDD. Manuscript-depth measurement reports 7,655
words for the geometry-normalized synthetic comparison and 7,887 words for
the M12 null-space study; both meet the measured manuscript floor. The geometry
paper reports its failed predeclared comparison and explicitly disclaims an
algorithmic novelty or field-transfer result. The product technical report
remains 3,481 words, with no equations or algorithms, one figure, one table,
14 references, and no `coverage.json`; it still fails the 12,000-word, method-
and-contract-coverage report bar. Current manuscript-depth checking reports
those two technical-report coverage/classification findings. This update does
not turn either manuscript's structural measure into peer review, scientific
acceptance, or release acceptance.

The current notebook-depth checker reports 121 course findings, down from the
stale 142 count in the preceding note. The structural EN/ES method and source
matrix passes, and `product.json` now inventories 13 real pipeline entrypoints
with bilingual chapter mappings; the M13 notebook is also mapped to the actual
browser-model-assets contract it exercises. Three contracts remain unmapped:
API payloads, data readiness, and the private API. The depth result is not
accepted. The product's sole
deployment verifier still rejects the live ML-VPS catalogue because its bytes
do not match this candidate; no deployment or origin change was attempted.

The final remote sync for this review found Shell `main` and `develop` equal at
`d2b3351` / v0.26.000, and Template `main` at `0da2ba6` / v0.15.010 with the
current `develop` release promoted by PR #134. Both shared checkouts are clean
and have one worktree. The product task branch remains synced to its remote;
PR #151 is open and draft with no reported checks. No rebase was needed.
Product promotion and the single ML-VPS
cutover remain blocked by the scientific, content, browser, and host gates.

The literature recheck supports the manuscript's restrained claim boundary.
The M12 paper already cites the 2025 NeurIPS Non-Linear Projections of the
Null-Space paper, the 2023 data-proximal null-space network work, and Bacca's
2025 projection-correction preprint as related prior art; it explicitly says
those methods were not reproduced or benchmarked. Its separate comparison of
traveltime methods identifies differences in forward physics, data, objective,
and uncertainty rather than ranking published metrics. No new novelty or
superiority assertion is supported by the current evidence.
