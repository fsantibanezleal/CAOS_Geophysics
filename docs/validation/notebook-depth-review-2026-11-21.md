# Bilingual notebook depth follow-up: 2026-11-21

## Scope

This review resolves the two M07 ERT lesson pairs that failed the current notebook-depth bar. It preserves the checker thresholds and keeps the field-data rights and synthetic-evidence boundaries explicit.

## Changes

- Expanded `notebooks/en/05-ert/02-ert-inversion.ipynb` and its Spanish counterpart with the conductive forward equation, a schematic weighted/regularized inverse objective, mesh and error sensitivity, held-out split interpretation, and a concrete field-data intake checklist.
- Expanded `notebooks/en/05-ert/03-ert-method-comparison.ipynb` and its Spanish counterpart. Corrected a false claim that the notebook computed a linearized proxy; the notebook actually runs the product pyGIMLi workflow on a seeded synthetic control. Clarified that replay through the same engine is not an independent algorithm comparison.
- Added a side-by-side model and Jacobian-coverage figure from the fresh solver receipt, with captions stating that coverage is not resolution or uncertainty.
- Added an actual QC-only call to the product `ert.run` entry point, asserting that inversion remains `not-run` for this explicit QC-only path.
- Added the primary pyGIMLi paper and official ERT API to the SDD research basis and the lesson references.

## Validation

- The two inversion lessons measure above the level-2 floors in both languages: English 1,941 words; Spanish 2,147 words; each has 3 figures, 2 displayed equations and 5 distinct sources. Both executed top-to-bottom in fresh kernels under `scripts/run_notebooks.py --check` with unchanged committed outputs.
- The two method-comparison lessons measure above the level-3 floors: English 2,564 words; Spanish 2,510 words; each has 3 figures, 2 displayed equations and 4 distinct sources. Both executed top-to-bottom in fresh kernels and their outputs were refreshed by the runner.
- `scripts/check_notebooks.py` reports no finding for these four M07 ERT notebooks. The repository-wide check still fails on other lessons.
- `scripts/check_notebook_depth.py . --report` decreased from 113 to 95 findings. The 95 remaining findings are outside these four ERT lessons; whole-course acceptance remains open.

These notebook checks establish structural and execution evidence for the named lessons only. They do not close the product SDD, prove field-transfer accuracy, or authorize a release or VPS deployment.
