# Manuscript and shared-base review: 2026-11-21

## Scope

Reviewed the current shared-shell and product-template bases, the product's exact pins, the 0.04.003 technical report, and the BS-1 geometry-normalized residual-learning manuscript. This is a repository and claim review, not independent peer review or product scientific acceptance.

## Shell and template

The product pins `@fasl-work/caos-app-shell` 0.26.2 in its frontend manifest, lockfile and exact-version gate. It records CAOS_PRODUCT_TEMPLATE 0.15.014 in `.template-version`. The current local `develop` and `main` refs in the shell and template have identical trees (`git diff develop..main` is empty); their `main` histories are respectively two and seven merge commits ahead. The product's recorded adoption identifies the relevant shell and template contracts and their local adaptation. No newer tree delta was available to port, so no shared repository was modified.

## BS-1 manuscript

The manuscript is an explicitly unreviewed, DOI-unassigned preprint and a negative synthetic comparison. It reports 8,734 prose words, 16 equations, 8 figures, 7 tables, 43 references and one algorithm; the content-bar checker passes. The refreshed source compiles successfully to a 29-page PDF. The rendered literature page was inspected after separating the newly added reference into its own paragraph.

The core claim is appropriately bounded: for this authored 16 by 16 experiment, the residual CNN loses to the regularized straight-ray reference on the frozen cohorts. The primary joint-shift ratios are 2.194 for velocity RMSE and 5.585 for Q-scored travel-time RMSE; all 160 cases exceed the fixed validation-derived threshold. A second CUDA execution reuses the same training seed and therefore is execution sensitivity, not independent initialization uncertainty. The ablations are post-hoc and exploratory. Data are synthetic, and the generator families were known by design.

The principal interpretive limitation is operator mismatch: Q creates and scores the observations, while A constructs CNN features and the reference inverse. The paper states that this design cannot isolate mismatch as a cause. This review corrected the SDD's contrary “matched classical inverse” description. A new September 2026 matrix-free Gauss--Newton preprint is cited as a distinct, non-reproduced eikonal/topography alternative; no numerical ranking is inferred from it. The paper does not support algorithmic novelty, field transfer, or method superiority.

## Technical report

The 0.04.003 report PDF is 48 pages. Its coverage map declares M01-M13 and BS-1 method sections, data-readiness, private API and browser-model contracts. The content-bar checker measures 16,851 words, 32 equations, 10 figures, 9 tables, 32 references and 3 algorithms and passes. Its text consistently separates synthetic evidence from field acceptance; it remains a descriptive implementation report, not independent scientific review.

## Resulting changes and verification

- Updated the BS-1 design text to state the A/Q operator split and prevent the false matched-operator interpretation.
- Updated the manuscript's literature comparison with Huang et al. (2026), a matrix-free Gauss--Newton method on full-metric deformed grids, and removed the unverified phrase that the MIMIR comparison uses a matched forward solver.
- Refreshed the BS-1 PDF from the edited source after successful XeLaTeX compilation; the source and PDF remain paired.
- `python scripts/check_manuscript_depth.py --report`: both manuscripts pass.
- The review does not change BS-1 scientific acceptance or any release-gate state.

## References added in this review

- Huang, Z. et al. (2026), *Efficient Matrix-Free Gauss--Newton Traveltime Tomography on Full-Metric Deformed Grids*, arXiv:2609.14982: https://arxiv.org/abs/2609.14982
- SciPy `signal.welch` API reference used by the waveform lesson: https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.welch.html
