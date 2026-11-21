# Manuscript and shared-base review: 2026-11-21

## Scope

Reviewed the current shared-shell and product-template bases, the product's exact pins, the 0.04.003 technical report, and the BS-1 geometry-normalized residual-learning manuscript. This is a repository and claim review, not independent peer review or product scientific acceptance.

## Shell and template

The product pins `@fasl-work/caos-app-shell` 0.26.2 in its frontend manifest, lockfile and exact-version gate. It records CAOS_PRODUCT_TEMPLATE 0.15.014 in `.template-version`. The current local `develop` and `main` refs in the shell and template have identical trees (`git diff develop..main` is empty); their `main` histories are respectively two and seven merge commits ahead. The product's recorded adoption identifies the relevant shell and template contracts and their local adaptation. No newer tree delta was available to port, so no shared repository was modified.

## BS-1 manuscript

The manuscript is an explicitly unreviewed, DOI-unassigned preprint and a negative synthetic comparison. The current source reports 8,789 prose words, 16 equations, 8 figures, 7 tables, 44 references and one algorithm; the content-bar checker passes. The refreshed source compiles successfully to a 29-page PDF. The rendered literature page was inspected after separating the newly added reference into its own paragraph.

The core claim is appropriately bounded: for this authored 16 by 16 experiment, the residual CNN loses to the regularized straight-ray reference on the frozen cohorts. The primary joint-shift ratios are 2.194 for velocity RMSE and 5.585 for Q-scored travel-time RMSE; all 160 cases exceed the fixed validation-derived threshold. A second CUDA execution reuses the same training seed and therefore is execution sensitivity, not independent initialization uncertainty. The ablations are post-hoc and exploratory. Data are synthetic, and the generator families were known by design.

The principal interpretive limitation is operator mismatch: Q creates and scores the observations, while A constructs CNN features and the reference inverse. The paper states that this design cannot isolate mismatch as a cause. This review corrected the SDD's contrary “matched classical inverse” description. The literature section also classifies Yang et al.'s untrained deep-network velocity reparameterization for a Central Chile application and Zeng et al.'s dual-network eikonal PINN, alongside a 2026 matrix-free Gauss--Newton method. These are context, not executed product baselines. The Yang data record contains test observations and model outputs but no method source code; its reviewed metadata has no declared reuse license. EKtomo says supporting data are available by request. The manuscript therefore does not yet meet the content-bar requirement that published methods be run on shared product data. No numerical ranking is inferred from the papers. The paper does not support algorithmic novelty, field transfer, or method superiority.

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

## Fresh content-bar remeasurement: 2026-11-21

`scripts/check_manuscript_depth.py . --report` was rerun against the current checkout. It measures the technical report at 16,851 prose words, 32 equations, 10 figures, 9 tables, 32 references and 3 algorithms; the geometry-normalized travel-time study measures 8,789 prose words, 16 equations, 8 figures, 7 tables, 44 references and one algorithm. Both documents pass the repository's structural depth and coverage checks.

The proposed-method paper remains a negative, fixed-simulator synthetic comparison. Its current literature coverage distinguishes contemporary forward solvers and inverse methods by operator, data, objective and validation protocol; cited methods were not reproduced as matched baselines. The manuscript meets measured depth, but its same-data comparator requirement remains open. The measurements do not support a claim of novelty, superiority, field transfer or advancement beyond the state of the art. Structural depth is not peer review or product scientific acceptance.

## Literature scope clarification

A current literature check identified Lee and Pyun's 2026 Swin masked-autoencoder/Swin-Unet method for reconstructing missing samples in 3D first-arrival travel-time data. This is a data-domain completion task, not velocity inversion. The manuscript now names that distinction and excludes its reconstruction errors from comparisons with velocity or inversion metrics. The citation was verified against the journal record: [Journal of Geophysics and Engineering, 23(3), 951-974](https://doi.org/10.1093/jge/gxag032). No performance claim from that paper is adopted as evidence for BS-1.

The manuscript is now v0.04. Its updated 29-page PDF was built successfully from a disposable copy, and rendered pages 4, 5, and 28 were inspected. The new paragraph remains together across the page break; the new bibliography item is legible and its DOI resolves to the cited journal record. The content check measures 8,789 prose words and 44 references, with the same 16 equations, 8 figures, 7 tables and one algorithm. The technical report remains unchanged at 16,851 words, 32 equations, 10 figures, 9 tables, 32 references and 3 algorithms.

## Current comparison gap

The expanded literature review identifies two relevant candidate methods for a future controlled comparison: the Central Chile deep-network reparameterization and EKtomo's dual-network eikonal inversion. Neither can currently be claimed as reproduced. The former's data record contains public test and result files but no implementation source or declared reuse license; the latter's supporting data are available by request. The next scientifically valid step is to select an openly reusable implementation, port its forward/data contract to the frozen survey cases, and evaluate it with a shared held-out split and compute budget. Until that gate is complete, the manuscript remains a negative result about BS-1 against its implemented regularized-ray comparator, not a benchmark of current learned inversion methods.
