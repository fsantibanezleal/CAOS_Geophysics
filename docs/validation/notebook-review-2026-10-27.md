# Notebook execution and content review: 2026-10-27

## Current evidence

- `scripts/check_notebooks.py`: 50 notebooks satisfy the structural bilingual bar.
- `scripts/run_notebooks.py --check --tmp E:\_worktrees\_notebook-check-release`: the final 50-notebook full fresh-kernel replay passed on 2026-10-27 after all current edits. Both M09 notebooks were also individually checked repeatedly. Their pyGIMLi subprocess fixes NumPy and numerical-library thread settings; report metrics are rounded only for reproducibility, while full-precision model and coverage arrays remain in the notebook result object.
- The four ERT solver notebooks declare a narrowly bounded PNG pixel tolerance for repeat-run floating-point drift. Their text, numeric outputs and source inputs still compare exactly. The 94 saved PNGs were re-encoded canonically; decoded pixels were unchanged.
- `scripts/check_method_matrix.py`: 13/13 structural gates are present; it reports `scientific_acceptance=false`.
- Focused M07 tests: 6 passed, 3 skipped because the rights-restricted Slagdump raw asset is absent locally. The source ledger says provider-link-only; this review does not authorize mirroring it.

## Independent content review findings

These are content-review results, not execution failures.

### English

The initial review passed 12 of 25 notebooks and found 13 needing correction. It identified a wrong M03 holdout count, stale learning and OOD metrics, a waveform lesson that reimplemented and mislabelled the product filter, a travel-time lesson whose main inverse was notebook-only LSQR, three Level 3 lessons without an independent reference solve, an M11 lesson that mainly replayed a stored receipt, an M13 lesson without picker inference, and missing source-rights attribution for external data.

The English repair pass changed and executed the affected notebooks. It corrected the M03 row count, held-out OOD counts and learning comparison, replaced the waveform filter reproduction with the product call, added rights attribution, and made the joint objective lesson report separate terms. The M09 lesson now also calls the exact product pyGIMLi Dijkstra inverse core on a generated refracting two-layer survey, compares a complete-shot holdout against its training-only homogeneous baseline, and plots known truth, recovered velocity and training-ray coverage. Remaining notebook method-coverage gaps include independent MT/ERT comparisons, a fresh FWI comparison, M11 optimizer/baseline execution and a 23-trace M13 ONNX private-oracle replay.

### Spanish

The initial Spanish-content audit passed 0 of 25 notebooks. It found untranslated prose/comments, cross-topic magnetic text, an M04 result contradiction, a rank-versus-noise identifiability error, and terminology violations. The repair pass translated prose, comments, and labels and fixed the M03/M04 and identifiability explanations. It then executed 20 notebooks; M11 had a receipt enum mismatch and four learning notebooks remained to run.

An independent final review found three defects: a stale saved count in Spanish M03 (4 instead of 72), conflicting saved/prose counts in Spanish M08 (1 false positive instead of 3), and a Spanish M11 objective notebook that plotted the diagnostic but did not call the product objective. All three were corrected; the M11 receipt enum was corrected; affected Spanish notebooks were executed again in fresh kernels. The M09 addition is now mirrored in Spanish and freshly executed. Its result is synthetic method evidence only; it does not establish the provider-linked Koenigsee case. The final content review found no other high-severity bilingual mismatch. This review does not claim exhaustive copy-editing or whole-course owner acceptance.

The M03 lesson now executes the shared line-processing implementation on an authored survey: source hashing, explicit column mapping, line/tie/height QC, crossover residuals, blocked-line holdout, support-masked gridding, a spacing-sensitivity comparison and a separate analytic continuation control. A browser-local workbench also runs the same Python processor through Pyodide/SciPy. These authored controls do not close provider-data acceptance, broad magnetic inversion, randomized browser parity or supported-device resource qualification.

## Release effect

The bilingual notebook set passes its structural gate and every notebook has fresh-kernel execution evidence. The notebook runner unit tests pass (5); focused ERT tests pass 6 with 3 skips because rights-restricted Slagdump raw bytes are absent. The docs-matrix structure gate passes. The convergence ledger remains 1 failed and 18 unresolved.

The bilingual notebook set is not accepted as complete course content. M03's new line-processing lesson and M09's new exact-core synthetic inverse are meaningful scoped additions; provider-source validation and the broader survey inverse remain unaccepted. Independent MT/ERT comparisons, a fresh FWI comparison, M11 optimizer and paired single-modality baselines, a fresh 23-trace M13 ONNX/private-oracle browser parity run, complete user-data workflows, rendered acceptance and actual-host gates remain open under `docs/design/SDD.md` and `docs/design/convergence.json`. No release cutover is authorized by these notebook checks.

The notebook/harness milestone is evidence-backed and ready to persist on the task branch; it does not satisfy full product promotion or deployment acceptance.
