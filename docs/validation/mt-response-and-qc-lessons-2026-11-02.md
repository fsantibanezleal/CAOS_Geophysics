# MT response and QC lesson validation ; 2026-11-02

## Scope

Expanded the measured-data MT curriculum in English and Spanish. The Level 1 lesson derives apparent resistivity and the product's orientation-specific phase convention from the actual 42-period cl061 complex tensor, verifies the result against the committed response arrays, and plots the two oriented curves and complex-impedance locus. The Level 2 lesson runs the actual M05 tensor gate and phase-tensor/tipper diagnostics, adds an uncertainty-multiplier sweep and per-period score map, documents the tensor/variance input contract, and retains the failed sounding as QC-only.

The MT notebook sequence is now numbered 01 through 04; both indexes, the SDD method link, the coverage map and source-to-content review point to the new paths. The SDD research basis lists the added primary phase-tensor and MTPy software references.

## Executed checks

| Check | Result | Boundary |
|---|---|---|
| `scripts/check_notebooks.py` | Pass: 66 English/Spanish notebook files, mirrored, numbered and structurally valid. | Structure and committed output hygiene; not full notebook-content acceptance. |
| `scripts/run_notebooks.py` | Pass: the four changed MT notebooks executed top-to-bottom in fresh kernels; a subsequent `--check --keep-results` run reproduced committed outputs. | These four files only. |
| CAOS notebook depth measurement | Level 1 response lesson: EN 1,076 words / ES 1,039; two figures, two display equations and five references per language. Level 2 QC lesson: EN 1,612 / ES 1,703 words; three figures, two display equations and five references per language. Required sensitivity and own-data headings are present. | The four changed files pass the measured floors. The repo-wide checker still reports 286 findings elsewhere; its prose parser can misattribute multi-heading markdown cells, so the aggregate requires manual review before being treated as an exact notebook deficit count. |
| `tests/numerics/test_mt_field_qc.py -q -ra` | 4 passed, 3 skipped. | Skips require the separately acquired ignored C15 EDI; no substitute was created. |
| Focused frontend Vitest | 22 passed across four files. | Route/shell contracts, online MT course, processing contracts and Long Valley API only. |
| Production frontend build | Pass with CAOS App Shell 0.19.12. | Vite reports the existing Workbench chunk at 551.05 kB, above its 500 kB advisory threshold. |

## Scientific boundaries

The response figures show the measured surface transfer function, not a recovered subsurface. Phase for the plotted components is checked using the product convention: arg(Zxy) and arg(−Zyx), wrapped to 0–360 degrees. The M05 eligibility decision uses the source uncertainty at multiplier one; the sweep is sensitivity analysis and does not change the stored decision. cl061 remains QC-only, and the synthetic calibration remains a separate software control.

The revised learned-recovery layout was measured by the CAOS App Shell 0.19.12 product gate at desktop and phone widths, across English/Spanish, light/dark, standard/large-font and interaction states. The final run measured 720 states with zero failures and produced 71 screenshots in `E:\_Datos\CAOS_Geophysics\validation\shell-0.19.12-recovery-layout-final2-20261102`. The two primary learned-recovery maps now share the first desktop row at their physical aspect ratio; the signed-error map occupies the following full-width row. This is layout evidence, not a numerical or method-acceptance result.

This scoped MT work does not close the other notebook-depth findings, unavailable M04 custody fixtures, unresolved convergence rows, actual-host qualification, release admission or deployment.

## Independent SimPEG comparison follow-up ; 2026-11-03

The Level 3 bilingual MT method-comparison lesson now runs a SimPEG 0.25.2 `Simulation1DRecursive` reference on the same synthetic three-layer target. SimPEG's bottom-up model order and negative impedance sign are converted explicitly; the independently evaluated complex forward response agrees with the product operator to maximum relative error `1.017e-10`. A bounded SciPy TRF fit of that response uses the product's active-frequency mask, per-component sigma, bounds, initial model, beta and log-resistivity smoothness objective. It recovers `[79.98706, 12.00064, 249.98435]` ohm m, active component WRMS `0.000616253`, and withheld component WRMS `0.000595638`. The comparator is accurately scoped as an independent forward engine and convention check; SciPy TRF/objective are shared, so it is not an independent optimization algorithm or a field result.

Both Level 3 notebooks now pass the CAOS_MANAGE content floors: EN 1,538 prose words / 3 figures / 2 display equations / 7 sources; ES 1,523 / 3 / 2 / 4. Both include sensitivity/failure boundaries and an own-data workflow. Validation: `scripts/run_notebooks.py --check --keep-results --tmp E:\\_Datos\\CAOS_Geophysics\\validation\\mt-simpeg-depth-final-20261103 --only notebooks/en/04-mt/04-mt-method-comparison.ipynb --only notebooks/es/04-mt/04-mt-method-comparison.ipynb` passed both notebooks in fresh kernels with committed outputs matching. The retained fresh outputs are under `E:\\_Datos\\CAOS_Geophysics\\validation\\mt-simpeg-depth-final-20261103\\run-notebooks-sux35_of\\results`.

The repo-wide content checker still fails with 276 findings; these two notebooks no longer appear among them. This scoped result does not resolve the remaining notebook deficits, frontend fixture failures, convergence and SDD evidence mismatch, VPS qualification, or release/deployment gates.

## MT forward lesson expansion ; 2026-11-03

Separated and documented the two distinct synthetic experiments in the forward lesson: the committed 48-realization two-layer bootstrap coverage calibration, and the independently seeded three-layer noisy sounding used for the beta/holdout sweep. Added the recursive layered-earth equations, phase/apparent-resistivity convention, interpretation of fixed-thickness local sensitivity and bootstrap sampling unit, 1D failure assumptions, and an EDI/QC-to-inversion own-data workflow. Added a third frequency-domain figure showing standardized complex residuals at fitted and withheld frequencies for each beta. The chart was inspected from the executed English notebook output.

The forward and comparison notebooks pass the individual CAOS_MANAGE content floors in both languages. Measured content: forward EN 1,546 prose words / 3 figures / 2 equations / 5 sources; ES 1,692 / 3 / 2 / 4. Comparison EN 1,538 / 3 / 2 / 7; ES 1,523 / 3 / 2 / 4. All four were replayed in fresh kernels with `scripts/run_notebooks.py --check --keep-results --tmp E:\\_Datos\\CAOS_Geophysics\\validation\\mt-lessons-final-20261103 --only ...`; result: 4/4 passed and committed outputs matched. Retained artifacts: `E:\\_Datos\\CAOS_Geophysics\\validation\\mt-lessons-final-20261103\\run-notebooks-xc16cb3c\\results`.

`check_notebooks.py` still passes repository structure for all 66 bilingual notebooks. `check_notebook_depth.py` still fails repo-wide with 264 findings; these four MT lessons now satisfy their measured floors. This does not close the remaining lesson deficits or the unrelated scientific, application, host, release and deployment gates.
