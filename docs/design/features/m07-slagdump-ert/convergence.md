# M07 Slagdump local convergence and publication boundary

Date: 2026-09-28. This is a **local scientific-verification receipt index**, not a public Slagdump field-data release. The exact field observations, model cells, residuals and numerical result receipt are ignored under `data/downloads/` and `data/raw/ert/`. Source-data redistribution and any field-derived public aggregate require a separate rights decision. The approved product M07 also includes interface and release work outside this branch.

| Requirement | Local gate evidence | Boundary |
| --- | --- | --- |
| ERT-01 | The pinned byte/hash acquisition and Git-ignore test runs against the local provider object. | No raw asset or result receipt is tracked. |
| ERT-02 | Strict parser positive/negative fixtures exercise counts, units/column names, finite positions and resistances, ABMN indices, duplicates and trailers. | No fallback CSV or guessed geometry. |
| ERT-03 | Local QC preserves all readings; reciprocity and instrument-error availability are explicit. | A robust flag does not delete or reweight a reading. No reciprocal-derived precision is available. |
| ERT-04 | Independent four-electrode flat formula, pyGIMLi flat-factor agreement, and mesh-refined homogeneous forward oracle are exercised; field factors use numerical topography. | Flat control checks sign/scale, not field geology. |
| ERT-05 | The ignored code-named, checksummed receipt records source, configuration, engine-version and actual mesh fingerprints, plus an explicitly assumed error formula. | Conditional chi-square is not instrument-calibrated. |
| ERT-06 | The live local numerical test evaluates both predeclared interleaved and central spatial-blocked holdouts against separate training-only homogeneous baselines; signed residual and Jacobian coverage stay local. | Shared profile/electrodes, 2D physics, mesh and weights limit inference; coverage is not resolution. |
| ERT-07 | Negative controls require `ineligible`, `not-converged` or `unverified` when a source or inverse gate fails. | No failed computation becomes an inverse or known truth. |
| ERT-08 | The [source guide](../../../guides/05_sources.md) states provenance, rights, units, reproduction, equation, holdouts and limitations. | Provider link only; no public field arrays or model. |

Verification command: `.venv-ingestion\Scripts\python.exe -m pytest -o addopts= tests/data tests/numerics/test_ert.py tests/test_edi.py` (66 passed, one pre-existing EDI/Pydantic warning); ERT lint, content standards and Git checks are run before the branch is pushed. A checkout without the ignored field asset skips the live inverse test and **cannot** claim a field gate from that run; the documented local acquisition is required. The local `data/raw/ert/slagdump-m07-inverse-<code-sha12>.json` and `.sha256` are the detailed scientific receipt, including actual per-split verdicts. Nothing here grants publication rights or asserts a unique subsurface interpretation.

## Separate synthetic teaching control

The notebook's committed [synthetic control receipt](synthetic-control.json) is SHA-256 pinned (`b278bb3a06461dd537f85224348eac2e2b918cac916b4f2f3f55fa4528d4bb9d`). It contains 82 numerically simulated readings from a 28-electrode irregular-topography line, generated from a 100 Ω m background and finite 25 Ω m body, with seeded 1% log-normal noise. The repository inverse returned `passed` for this synthetic case's predeclared gates: interleaved held-out log-RMSE 0.03128, central spatial-block held-out log-RMSE 0.06562, and cellwise log10 resistivity RMSE 0.12083. Those figures are reproducibility evidence for this controlled example only; they do not alter the field M07 status, source-rights boundary, or acceptance criteria. Regenerate from the repo root with `.venv-ert/Scripts/python.exe data-pipeline/ert_synthetic_experiment.py --output <new-local-path>.json`; setup is `scripts/setup.ps1 -Ert` or `scripts/setup.sh --ert`.
