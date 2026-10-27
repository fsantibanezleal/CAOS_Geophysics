# Notebook execution and content review: 2026-10-27

## Current evidence

- `scripts/check_notebooks.py`: 52 notebooks satisfy the structural bilingual bar.
- `scripts/run_notebooks.py --check --tmp E:\_worktrees\_notebook-check-release`: the 52-notebook full fresh-kernel replay passed on 2026-10-27 before the later M02/M04/M10/M11 additions. After those edits, all four changed bilingual pairs were separately executed in fresh kernels and passed strict output checks. The M09 pyGIMLi lesson fixes NumPy and native numerical-library thread settings. Its plots deliberately show 100 m/s velocity bins and a binary nonzero-ray-support mask; reported metrics are rounded, while full-precision model and path-length arrays remain in the notebook result object.
- The four ERT solver notebooks declare a narrowly bounded PNG pixel tolerance for repeat-run floating-point drift. Their text, numeric outputs and source inputs still compare exactly. The 94 saved PNGs were re-encoded canonically; decoded pixels were unchanged.
- `scripts/check_method_matrix.py`: 13/13 structural gates are present; it reports `scientific_acceptance=false`.
- Focused M07 tests: 6 passed, 3 skipped because the rights-restricted Slagdump raw asset is absent locally. The source ledger says provider-link-only; this review does not authorize mirroring it.

## Independent content review findings

These are content-review results, not execution failures.

### English

The initial review passed 12 of 25 notebooks and found 13 needing correction. It identified a wrong M03 holdout count, stale learning and OOD metrics, a waveform lesson that reimplemented and mislabelled the product filter, a travel-time lesson whose main inverse was notebook-only LSQR, three Level 3 lessons without an independent reference solve, an M11 lesson that mainly replayed a stored receipt, an M13 lesson without picker inference, and missing source-rights attribution for external data.

The English repair pass changed and executed the affected notebooks. It corrected the M03 row count, held-out OOD counts and learning comparison, replaced the waveform filter reproduction with the product call, added rights attribution, and made the joint objective lesson report separate terms. The M09 lesson now also calls the exact product pyGIMLi Dijkstra inverse core on a generated refracting two-layer survey, compares a complete-shot holdout against its training-only homogeneous baseline, and plots known truth, recovered velocity and training-ray coverage. The M10 notebook now executes full-band and frequency-continuation product FWI against a declared 1-D start. Both schedules remain unresolved because fit and withheld WRMS exceed the declared noise-consistency target. Broader FWI regimes and an independent solver comparator remain open, alongside independent MT/ERT comparisons, multi-family M11 optimizer/baseline analysis beyond the one new 26-candidate control, and the 23-trace M13 ONNX private-oracle replay.

### Spanish

The initial Spanish-content audit passed 0 of 25 notebooks. It found untranslated prose/comments, cross-topic magnetic text, an M04 result contradiction, a rank-versus-noise identifiability error, and terminology violations. The repair pass translated prose, comments, and labels and fixed the M03/M04 and identifiability explanations. It then executed 20 notebooks; M11 had a receipt enum mismatch and four learning notebooks remained to run.

An independent final review found three defects: a stale saved count in Spanish M03 (4 instead of 72), conflicting saved/prose counts in Spanish M08 (1 false positive instead of 3), and a Spanish M11 objective notebook that plotted the diagnostic but did not call the product objective. All three were corrected; the M11 receipt enum was corrected; affected Spanish notebooks were executed again in fresh kernels. The M09 addition is now mirrored in Spanish and freshly executed. Its result is synthetic method evidence only; it does not establish the provider-linked Koenigsee case. The final content review found no other high-severity bilingual mismatch. This review does not claim exhaustive copy-editing or whole-course owner acceptance.

The M03 lesson now executes the shared line-processing implementation on an authored survey: source hashing, explicit column mapping, line/tie/height QC, crossover residuals, blocked-line holdout, support-masked gridding, a spacing-sensitivity comparison and a separate analytic continuation control. A browser-local workbench also runs the same Python processor through Pyodide/SciPy. These authored controls do not close provider-data acceptance, broad magnetic inversion, randomized browser parity or supported-device resource qualification.

## Release effect

The bilingual notebook set passes its structural gate and every notebook has fresh-kernel execution evidence. The four added M02/M04 inversion notebooks were each replayed again in fresh kernels after their final edits; all four passed. The M10 bilingual lesson now runs actual product FWI in full-band and frequency-continuation schedules; both are unresolved (fit/withheld WRMS 13.820/13.720 and 15.285/15.162, versus 1 as the noise-consistency target), while model RMSE improves only to 0.963/0.962 of the declared start. This is one synthetic, same-engine experiment, not field validation. The M11 bilingual lesson now executes the actual 26-candidate train-only calibration on one synthetic control in fresh kernels and strict check mode: 22 candidates converged, four did not. The selected coupling changed gravity validation WRMS from 0.81268699 to 0.81268635 and magnetic from 1.31257541 to 1.31257439; these roughly 1e-6 changes are numerically tiny and do not support a meaningful-benefit claim. This is one authored control, not field evidence. The notebook runner unit tests pass (5); focused ERT tests pass 6 with 3 skips because rights-restricted Slagdump raw bytes are absent. The docs-matrix structure gate passes. The convergence ledger remains 1 failed and 18 unresolved.

The bilingual notebook set is not accepted as complete course content. M02/M04's new 3D inversion lessons, M03's line-processing lesson and M09's exact-core synthetic inverse are meaningful scoped additions; provider-source validation and the broader survey inverse remain unaccepted. Additional FWI regimes and an independent solver comparison, multi-family M11 optimizer and paired single-modality analysis beyond one fresh calibration, M12 velocity-checkpoint inference, independent MT/ERT comparisons, a fresh 23-trace M13 ONNX/private-oracle browser parity run, complete user-data workflows, rendered acceptance and actual-host gates remain open under `docs/design/SDD.md` and `docs/design/convergence.json`. No release cutover is authorized by these notebook checks.

The notebook/harness milestone is evidence-backed and ready to persist on the task branch; it does not satisfy full product promotion or deployment acceptance.
