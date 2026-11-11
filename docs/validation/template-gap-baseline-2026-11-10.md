# Base gap: CAOS_Geophysics @ task/geophysics-client-first-completion against template v0.15.006

- Repository: fsantibanezleal/CAOS_Geophysics
- Ref: task/geophysics-client-first-completion
- Commit: 3c6f131e80dcc22b7ddcf6f7216a0f3f33e66ff3
- Template tag: v0.15.006 (fsantibanezleal/CAOS_PRODUCT_TEMPLATE)
- Date: 2026-11-10
- Interpreter: C:\Users\fsant\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\python.exe
- Copy: depth-1 clone, 2135 files, 874.8 MB, 79.7 s
- Residue allow-list (scripts/.template_residue_allow): the product's own, kept
- Product's own guards kept (template's are bound to its example): check_artifacts.py
- Overlay: 26 template files laid over the copy (scripts/check_base_integrity.py, scripts/check_ci_budget.py, scripts/check_content_standards.py, scripts/check_contract_versions.py, scripts/check_contracts.py, scripts/check_deploy_place.py, scripts/check_doc_paths.py, scripts/check_documents.py, scripts/check_internal_names.py, scripts/check_live.py, scripts/check_manuscript_depth.py, scripts/check_manuscripts.py, scripts/check_notebook_depth.py, scripts/check_notebooks.py, scripts/check_readiness.py, scripts/check_readme_areas.py, scripts/check_sdd.py, scripts/check_skeleton.py, scripts/check_svg_animation.py, scripts/check_tech_matrix.py, scripts/check_template_residue.py, scripts/check_version_coherence.py, scripts/check_web_baseline.py, scripts/notebook_bar.json, scripts/notebook_depth.json, scripts/svg_animation.mjs)

## Summary

pass 6, fail 11, crash 1, timeout 2, skipped 9

| Guard | Verdict | Exit | Seconds | Note |
|---|---|---|---|---|
| npm ci | skipped |  | 0 | --no-npm |
| check_artifacts.py | pass | 0 | 44.3 | product's own guard (template's is bound to its example) |
| check_version_coherence.py | fail | 1 | 37.7 |  |
| check_sdd.py | skipped |  | 0 | --no-npm: npm ci was not run |
| check_notebooks.py | fail | 1 | 11.3 |  |
| check_notebook_depth.py | fail | 1 | 5.6 |  |
| check_internal_names.py | fail | 1 | 39.0 |  |
| check_manuscripts.py | fail | 1 | 0.5 |  |
| check_manuscript_depth.py | fail | 1 | 0.7 |  |
| check_readme_areas.py | pass | 0 | 0.3 |  |
| check_svg_animation.py | skipped |  | 0 | --no-npm: npm ci was not run |
| check_deploy_place.py | fail | 1 | 0.2 |  |
| check_tech_matrix.py | fail | 1 | 0.9 |  |
| check_contract_versions.py | pass | 0 | 0.8 |  |
| check_contracts.py | pass | 0 | 0.3 |  |
| check_readiness.py | fail | 1 | 0.2 |  |
| check_documents.py | crash | 1 | 0.3 | a Python traceback: the product's tree broke the guard |
| check_skeleton.py | pass | 0 | 0.3 |  |
| check_web_baseline.py | skipped |  | 0 | --no-npm: npm ci was not run |
| check_base_integrity.py | fail | 1 | 1.2 |  |
| check_template_residue.py | timeout |  | 120.3 | no result within 120 s |
| check_doc_paths.py | fail | 1 | 112.6 |  |
| check_content_standards.py | timeout |  | 120.3 | no result within 120 s |
| check_ci_budget.py | pass | 0 | 0.5 |  |
| check_live.py | skipped |  | 0 | needs a deployed URL and the deployed SHA (run by the deploy workflow) |
| ruff | skipped |  | 0 | lint step of the template CI, not a guard |
| workflows parse | skipped |  | 0 | step of the template CI, not a guard |
| tests/adversarial | skipped |  | 0 | pytest suite of the template's own guards, not a measure of a product |
| npm build / test | skipped |  | 0 | no frontend build and no npm test in the copy |

## Output (first 40 lines of each guard that did not pass cleanly)

### check_artifacts.py: pass

Command: `python scripts/check_artifacts.py`

```text
PASS: 20 distinct truths / 120 experiments / 348 method results; all SHA-256 and sizes match
```

### check_version_coherence.py: fail

Command: `python scripts/check_version_coherence.py`

```text
version: data-pipeline/artifact_versions.py:10: a version literal in code; read VERSION instead
version: data-pipeline/artifact_versions.py:11: a version literal in code; read VERSION instead
version: data-pipeline/artifact_versions.py:13: a version literal in code; read VERSION instead
version: data-pipeline/artifact_versions.py:14: a version literal in code; read VERSION instead
version: data-pipeline/artifact_versions.py:15: a version literal in code; read VERSION instead
version: data-pipeline/artifact_versions.py:16: a version literal in code; read VERSION instead
version: data-pipeline/artifact_versions.py:60: a version literal in code; read VERSION instead
version: data-pipeline/artifact_versions.py:61: a version literal in code; read VERSION instead
version: data-pipeline/artifact_versions.py:64: a version literal in code; read VERSION instead
version: data-pipeline/assemble_fwi_candidate.py:30: a version literal in code; read VERSION instead
version: data-pipeline/assemble_fwi_candidate.py:32: a version literal in code; read VERSION instead
version: data-pipeline/assemble_fwi_candidate.py:157: a version literal in code; read VERSION instead
version: data-pipeline/provenance.py:13: a version literal in code; read VERSION instead
version: data-pipeline/provenance.py:19: a version literal in code; read VERSION instead
version: data-pipeline/provenance.py:36: a version literal in code; read VERSION instead
version: data-pipeline/provenance.py:43: a version literal in code; read VERSION instead
version: data-pipeline/rebuild.py:16: a version literal in code; read VERSION instead
version: data-pipeline/rebuild.py:17: a version literal in code; read VERSION instead
version: frontend/src/architecture.ts:15: a version literal in code; read VERSION instead
version: frontend/src/architecture.ts:17: a version literal in code; read VERSION instead
version: frontend/src/architecture.ts:25: a version literal in code; read VERSION instead
version: frontend/src/architecture.ts:27: a version literal in code; read VERSION instead
version: frontend/src/architecture.ts:35: a version literal in code; read VERSION instead
version: frontend/src/architecture.ts:37: a version literal in code; read VERSION instead
version: frontend/src/architecture.ts:45: a version literal in code; read VERSION instead
version: frontend/src/architecture.ts:47: a version literal in code; read VERSION instead
version: frontend/src/architecture.ts:55: a version literal in code; read VERSION instead
version: frontend/src/architecture.ts:57: a version literal in code; read VERSION instead
version: frontend/src/main.tsx:60: a version literal in code; read VERSION instead
version: frontend/src/test/foundation-architecture.test.ts:12: a version literal in code; read VERSION instead
version: frontend/src/test/online-mt-course.test.ts:111: a version literal in code; read VERSION instead
version: frontend/src/test/online-mt-course.test.ts:113: a version literal in code; read VERSION instead
version: frontend/src/test/waveform-browser-entry.tsx:17: a version literal in code; read VERSION instead
version: scripts/check_artifacts.py:157: a version literal in code; read VERSION instead
version: scripts/import_fwi_candidate.py:113: a version literal in code; read VERSION instead
version: scripts/import_fwi_candidate.py:114: a version literal in code; read VERSION instead
version: scripts/import_fwi_candidate.py:138: a version literal in code; read VERSION instead
version: scripts/import_fwi_candidate.py:199: a version literal in code; read VERSION instead
version: scripts/import_fwi_candidate.py:232: a version literal in code; read VERSION instead
version: scripts/import_fwi_candidate.py:234: a version literal in code; read VERSION instead
... (39 more lines; the full output is in the --keep folder)
```

### check_notebooks.py: fail

Command: `python scripts/check_notebooks.py`

```text
NOTEBOOKS CHECK FAILED:
  - notebooks/en/01-foundations/01-inverse-problem-and-evidence.ipynb: bar: method cells 0, the floor at level 1 is 3
  - notebooks/en/01-foundations/01-inverse-problem-and-evidence.ipynb: bar: figures 1, the floor at level 1 is 2
  - notebooks/en/01-foundations/01-inverse-problem-and-evidence.ipynb: bar: explanatory prose words 601, the floor at level 1 is 1000
  - notebooks/en/01-foundations/02-residuals-and-identifiability.ipynb: bar: method cells 0, the floor at level 2 is 5
  - notebooks/en/01-foundations/02-residuals-and-identifiability.ipynb: bar: figures 2, the floor at level 2 is 3
  - notebooks/en/01-foundations/02-residuals-and-identifiability.ipynb: bar: explanatory prose words 868, the floor at level 2 is 1500
  - notebooks/en/02-gravity/01-gravity-reference-and-units.ipynb: bar: code cell 22 has a line of 166 characters, the limit is 120
  - notebooks/en/02-gravity/02-m01-station-corrections.ipynb: bar: code cell 30 line 19 holds 3 statements, one statement per line
  - notebooks/en/02-gravity/03-long-valley-time-lapse-processing.ipynb: bar: method cells 0, the floor at level 2 is 5
  - notebooks/en/02-gravity/03-long-valley-time-lapse-processing.ipynb: bar: the figure of code cell 11 is followed by 39 words, the floor is 40
  - notebooks/en/02-gravity/03-long-valley-time-lapse-processing.ipynb: bar: the first cell does not state the question (**Question:**)
  - notebooks/en/02-gravity/03-long-valley-time-lapse-processing.ipynb: bar: the Results section does not answer it (**Answer:**)
  - notebooks/en/02-gravity/03-long-valley-time-lapse-processing.ipynb: bar: code cell 7 has a line of 163 characters, the limit is 120
  - notebooks/en/02-gravity/03-long-valley-time-lapse-processing.ipynb: bar: code cell 9 has a line of 165 characters, the limit is 120
  - notebooks/en/02-gravity/03-long-valley-time-lapse-processing.ipynb: bar: code cell 11 has a line of 123 characters, the limit is 120
  - notebooks/en/02-gravity/03-long-valley-time-lapse-processing.ipynb: bar: code cell 13 has a line of 126 characters, the limit is 120
  - notebooks/en/02-gravity/03-long-valley-time-lapse-processing.ipynb: bar: code cell 13 line 9 holds 3 statements, one statement per line
  - notebooks/en/02-gravity/03-long-valley-time-lapse-processing.ipynb: bar: code cell 16 has a line of 275 characters, the limit is 120
  - notebooks/en/02-gravity/03-long-valley-time-lapse-processing.ipynb: bar: code cell 18 has a line of 137 characters, the limit is 120
  - notebooks/en/02-gravity/03-long-valley-time-lapse-processing.ipynb: bar: code cell 20 has a line of 204 characters, the limit is 120
  - notebooks/en/02-gravity/03-long-valley-time-lapse-processing.ipynb: bar: code cell 22 has a line of 134 characters, the limit is 120
  - notebooks/en/02-gravity/04-m02-prism-forward-and-inverse-limits.ipynb: bar: method cells 1, the floor at level 3 is 5
  - notebooks/en/02-gravity/04-m02-prism-forward-and-inverse-limits.ipynb: bar: method cells that call the product's own method (package or pipeline) 0, the floor at level 3 is 2
  - notebooks/en/02-gravity/04-m02-prism-forward-and-inverse-limits.ipynb: bar: code cell 42 has a line of 204 characters, the limit is 120
  - notebooks/en/03-magnetics/01-magnetic-quantities-and-frame.ipynb: bar: figures 1, the floor at level 1 is 2
  - notebooks/en/03-magnetics/01-magnetic-quantities-and-frame.ipynb: bar: explanatory prose words 545, the floor at level 1 is 1000
  - notebooks/en/03-magnetics/03-m04-induced-prism-forward.ipynb: bar: explanatory prose words 1131, the floor at level 3 is 1500
  - notebooks/en/03-magnetics/03-m04-induced-prism-forward.ipynb: bar: code cell 26 has a line of 176 characters, the limit is 120
  - notebooks/en/03-magnetics/04-m04-fit-objective-validation.ipynb: bar: method cells 1, the floor at level 3 is 5
  - notebooks/en/03-magnetics/04-m04-fit-objective-validation.ipynb: bar: method cells that call the product's own method (package or pipeline) 1, the floor at level 3 is 2
  - notebooks/en/03-magnetics/04-m04-fit-objective-validation.ipynb: bar: figures 1, the floor at level 3 is 3
  - notebooks/en/03-magnetics/04-m04-fit-objective-validation.ipynb: bar: explanatory prose words 409, the floor at level 3 is 1500
  - notebooks/en/03-magnetics/04-m04-fit-objective-validation.ipynb: bar: the figure of code cell 14 is followed by 30 words, the floor is 40
  - notebooks/en/03-magnetics/04-m04-fit-objective-validation.ipynb: bar: the first cell does not state the question (**Question:**)
  - notebooks/en/03-magnetics/04-m04-fit-objective-validation.ipynb: bar: the Results section does not answer it (**Answer:**)
  - notebooks/en/03-magnetics/04-m04-fit-objective-validation.ipynb: bar: no method cell under Comparison: a level 3 notebook runs the published method it compares
  - notebooks/en/03-magnetics/04-m04-fit-objective-validation.ipynb: bar: no figure under Comparison: a level 3 notebook compares the methods with a figure
  - notebooks/en/04-mt/01-mt-response-observables.ipynb: bar: method cells 0, the floor at level 1 is 3
  - notebooks/en/04-mt/01-mt-response-observables.ipynb: bar: the Results section does not answer it (**Answer:**)
... (222 more lines; the full output is in the --keep folder)
```

### check_notebook_depth.py: fail

Command: `python scripts/check_notebook_depth.py`

```text
  - notebooks/en/01-foundations/01-inverse-problem-and-evidence.ipynb: prose 601, current level1 floor is 1000
  - notebooks/en/01-foundations/01-inverse-problem-and-evidence.ipynb: figures 1, current level1 floor is 2
  - notebooks/en/01-foundations/01-inverse-problem-and-evidence.ipynb: equations 0, current level1 floor is 1
  - notebooks/en/01-foundations/01-inverse-problem-and-evidence.ipynb: sources 1, current level1 floor is 3
  - notebooks/en/01-foundations/02-residuals-and-identifiability.ipynb: prose 868, current level2 floor is 1500
  - notebooks/en/01-foundations/02-residuals-and-identifiability.ipynb: figures 2, current level2 floor is 3
  - notebooks/en/01-foundations/02-residuals-and-identifiability.ipynb: equations 0, current level2 floor is 2
  - notebooks/en/01-foundations/02-residuals-and-identifiability.ipynb: sources 1, current level2 floor is 4
  - notebooks/en/01-foundations/02-residuals-and-identifiability.ipynb: no third-level own data heading
  - notebooks/en/03-magnetics/01-magnetic-quantities-and-frame.ipynb: prose 545, current level1 floor is 1000
  - notebooks/en/03-magnetics/01-magnetic-quantities-and-frame.ipynb: figures 1, current level1 floor is 2
  - notebooks/en/03-magnetics/01-magnetic-quantities-and-frame.ipynb: equations 0, current level1 floor is 1
  - notebooks/en/03-magnetics/01-magnetic-quantities-and-frame.ipynb: sources 1, current level1 floor is 3
  - notebooks/en/03-magnetics/02-m03-survey-geometry-and-holdout.ipynb: no third-level own data heading
  - notebooks/en/03-magnetics/03-m04-induced-prism-forward.ipynb: prose 1131, current level3 floor is 1500
  - notebooks/en/03-magnetics/03-m04-induced-prism-forward.ipynb: equations 0, current level3 floor is 2
  - notebooks/en/03-magnetics/03-m04-induced-prism-forward.ipynb: sources 1, current level3 floor is 4
  - notebooks/en/03-magnetics/03-m04-induced-prism-forward.ipynb: no third-level own data heading
  - notebooks/en/03-magnetics/04-m04-fit-objective-validation.ipynb: prose 409, current level3 floor is 1500
  - notebooks/en/03-magnetics/04-m04-fit-objective-validation.ipynb: figures 1, current level3 floor is 3
  - notebooks/en/03-magnetics/04-m04-fit-objective-validation.ipynb: equations 0, current level3 floor is 2
  - notebooks/en/03-magnetics/04-m04-fit-objective-validation.ipynb: sources 1, current level3 floor is 4
  - notebooks/en/03-magnetics/04-m04-fit-objective-validation.ipynb: no third-level sensitivity/limits heading
  - notebooks/en/03-magnetics/04-m04-fit-objective-validation.ipynb: no third-level own data heading
  - notebooks/en/05-ert/01-ert-rights.ipynb: prose 613, current level1 floor is 1000
  - notebooks/en/05-ert/01-ert-rights.ipynb: figures 1, current level1 floor is 2
  - notebooks/en/05-ert/01-ert-rights.ipynb: equations 0, current level1 floor is 1
  - notebooks/en/05-ert/01-ert-rights.ipynb: sources 2, current level1 floor is 3
  - notebooks/en/05-ert/02-ert-inversion.ipynb: prose 975, current level2 floor is 1500
  - notebooks/en/05-ert/02-ert-inversion.ipynb: equations 0, current level2 floor is 2
  - notebooks/en/05-ert/02-ert-inversion.ipynb: sources 2, current level2 floor is 4
  - notebooks/en/05-ert/02-ert-inversion.ipynb: no third-level sensitivity/limits heading
  - notebooks/en/05-ert/02-ert-inversion.ipynb: no third-level own data heading
  - notebooks/en/05-ert/03-ert-method-comparison.ipynb: figures 2, current level3 floor is 3
  - notebooks/en/05-ert/03-ert-method-comparison.ipynb: equations 0, current level3 floor is 2
  - notebooks/en/05-ert/03-ert-method-comparison.ipynb: sources 2, current level3 floor is 4
  - notebooks/en/05-ert/03-ert-method-comparison.ipynb: no third-level own data heading
  - notebooks/en/06-seismology/01-waveforms.ipynb: figures 1, current level1 floor is 2
  - notebooks/en/06-seismology/01-waveforms.ipynb: equations 0, current level1 floor is 1
  - notebooks/en/06-seismology/01-waveforms.ipynb: sources 1, current level1 floor is 3
... (150 more lines; the full output is in the --keep folder)
```

### check_internal_names.py: fail

Command: `python scripts/check_internal_names.py`

```text
manuscripts/m12-nullspace-refinement-v0.01/main.tex: line 61: the tier name 'state-of-the-art' (internal; name the method instead, CAOS_MANAGE conventions/method-tiers-and-manuscripts.md section 0)
manuscripts/m12-nullspace-refinement-v0.01/main.tex: line 120: the tier name 'classical model' (internal; name the method instead, CAOS_MANAGE conventions/method-tiers-and-manuscripts.md section 0)
check_internal_names: 2 finding(s): the tier names are internal (CAOS_MANAGE conventions/method-tiers-and-manuscripts.md section 0)
```

### check_manuscripts.py: fail

Command: `python scripts/check_manuscripts.py`

```text
MANUSCRIPTS CHECK FAILED:
  - product.json has no 'manuscripts': a product declares its Zenodo manuscripts, at least one technical report ("kind": "technical-report"), see CAOS_MANAGE conventions/method-tiers-and-manuscripts.md section 2
```

### check_manuscript_depth.py: fail

Command: `python scripts/check_manuscript_depth.py`

```text
MANUSCRIPT CONTENT CHECK FAILED (5 findings; conventions/manuscript-content-bar.md):
  - manuscripts/geophysics-identifiability: no LaTeX main file with \documentclass: a CAOS manuscript is written in LaTeX (conventions/manuscript-content-bar.md section 2)
  - manuscripts/inverse-earth-studio-report-0.04.003: coverage.json is missing (conventions/manuscript-content-bar.md section 5)
  - manuscripts/m12-nullspace-refinement-v0.01: coverage.json is missing (conventions/manuscript-content-bar.md section 5)
  - manuscripts/: no technical report (a folder whose coverage.json has kind technical-report) (conventions/manuscript-content-bar.md section 3)
  - manuscripts/: the proposed method BS-1 of the SDD has no manuscript (coverage.json claims) (conventions/manuscript-content-bar.md section 3)
```

### check_deploy_place.py: fail

Command: `python scripts/check_deploy_place.py`

```text
deploy place: the target is VPS and deploy/ holds no service unit
```

### check_tech_matrix.py: fail

Command: `python scripts/check_tech_matrix.py`

```text
TECH MATRIX CHECK FAILED:
  - pandas: pinned as 3.0.6 in requirements-api.txt and as 2.2.3 in requirements-precompute.txt (one package, one version)
  - matplotlib: pinned as 3.11.2 in requirements-api.txt and as 3.10.8 in requirements-precompute.txt (one package, one version)
  - pandas: pinned as 3.0.6 in requirements-api.txt and as 2.2.3 in requirements-gravity-runtime.txt (one package, one version)
  - numpy: pinned as 2.2.6 in requirements-api.txt and as 2.5.3 in data-pipeline/requirements-ert.txt (one package, one version)
  - scipy: pinned as 1.15.2 in requirements-api.txt and as 1.17.1 in data-pipeline/requirements-ert.txt (one package, one version)
  - llvmlite: pinned as 0.49.0 in requirements-api-test.txt and as 0.50.0 in data-pipeline/requirements-m01.txt (one package, one version)
  - numba: pinned as 0.67.0 in requirements-api-test.txt and as 0.68.0 in data-pipeline/requirements-m01.txt (one package, one version)
  - matplotlib: pinned as 3.11.2 in requirements-api.txt and as 3.10.8 in data-pipeline/requirements-m01-transforms.txt (one package, one version)
  - pytest: pinned as 9.1.1 in requirements-dev.txt and as 9.0.3 in data-pipeline/requirements-m08.txt (one package, one version)
  - setuptools: pinned as 84.0.0 in data-pipeline/requirements-ert.txt and as 81.0.0 in data-pipeline/requirements-m08.txt (one package, one version)
  - numpy: pinned as 2.2.6 in requirements-api.txt and as 2.5.3 in data-pipeline/requirements-traveltime.txt (one package, one version)
  - scipy: pinned as 1.15.2 in requirements-api.txt and as 1.17.1 in data-pipeline/requirements-traveltime.txt (one package, one version)
  - pandas: pinned as 3.0.6 in requirements-api.txt and as 2.2.3 in notebooks/requirements.txt (one package, one version)
  - matplotlib: pinned as 3.11.2 in requirements-api.txt and as 3.10.8 in notebooks/requirements.txt (one package, one version)
  - torch: pinned as 2.14.0+cu126 in requirements-gpu.txt and as 2.14.0 in notebooks/requirements.txt (one package, one version)
  - pillow: pinned as 12.3.0 in data-pipeline/requirements-m01-transforms.txt and as 13.0.0 in notebooks/requirements.txt (one package, one version)
  - SDD.md 'Technology and versions' has no table with the columns component | package | version | use | alternative considered
```

### check_readiness.py: fail

Command: `python scripts/check_readiness.py`

```text
readiness: invalid admission provider
  No module named 'pipeline'
```

### check_documents.py: crash

Command: `python scripts/check_documents.py`

```text
Traceback (most recent call last):
  File "D:\_Temp\base-gap\CAOS_Geophysics-task-geophysics-client-first-completion\copy\scripts\check_documents.py", line 42, in <module>
    import contract_schemas as cs  # noqa: E402  (the schema registry, shared with the contract tests)
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
ModuleNotFoundError: No module named 'contract_schemas'
```

### check_base_integrity.py: fail

Command: `python scripts/check_base_integrity.py`

```text
::error::tracked .sh files must have Git mode 100755
  deploy/activate-service.sh
  scripts/dev.sh
  scripts/fetch-data.sh
  scripts/intake-potential-sources.sh
  scripts/local.sh
  scripts/precompute.sh
  scripts/process_waveform_m08.sh
  scripts/provision-account.sh
  scripts/run_m01_gravity.sh
  scripts/run_m01_transforms.sh
  scripts/run_m12_velocity.sh
  scripts/server_gravity_l2_admission.sh
  scripts/server_mt_admission.sh
  scripts/setup.sh
  scripts/smoke.sh
::error::a tracked model file is not admitted: named by no catalog row (add its path to a row's documents cell in docs/contracts/catalog.md)
  data/derived/phase/browser-assets/stead/model.onnx
  models/experimental/m12-physics-cuda-20261004/m12-physics.onnx
::error::a local machine path in a tracked file
  docs/design/features/fwi-user-data/validation.md:104:are under external `E:/_Temp/geophysics-resume-20261008`, not a repository cache.
  docs/design/features/joint-survey-inversion/course-unit.md:47:E:/_Temp/geophysics-m11-20261008. Product curated data were not rebaked.
  docs/design/features/joint-survey-inversion/integration-status-20261025.md:18:`E:\_worktrees\_runs\CAOS_Geophysics-M11-integrated-20261025`.
  docs/design/features/joint-survey-inversion/integration-status-20261025.md:140:`E:\_worktrees\_runs\CAOS_Geophysics-M11-integrated-20261025\data`; the
  docs/design/features/joint-survey-inversion/integration-status-20261025.md:163:`E:\_worktrees\CAOS_Geophysics-data\joint-matrix-20261027`; its manifest
  docs/design/features/m01-current-stage/design.md:69:artifacts use external E:/_Datos and E:/_Temp paths. Main owns final source review,
  docs/design/features/m01-current-stage/root-transaction-integration.md:51:`E:/_Temp/m01-root-assembly-r7-20261008.xml`, SHA256
  docs/design/features/m01-current-stage/root-transaction-integration.md:73:`E:/_Temp/m01-union-delete-threeheads-r9-20261008.xml`, SHA256
  docs/design/features/m01-gravity-station-adapter/research.md:9:Owned worktree: D:/_worktrees/geophysics-m01-corrections. Documentation-only branch: task/geophys
  docs/design/features/m02-prism-operator/evidence/final-geometry-execution.json:61:  "interpreter": "D:/_Repos/_Web_Projects/CAOS_Geophysics/.venv-pipeline/Scrip
  docs/design/features/m02-prism-operator/evidence/final-geometry-execution.json:88:      "interpreter": "D:/_worktrees/geophysics-m01-corrections/.venv-m01/Scrip
  docs/design/features/m02-prism-operator/evidence/local-execution.json:72:  "interpreter": "D:/_Repos/_Web_Projects/CAOS_Geophysics/.venv-pipeline/Scripts/python
  docs/design/features/m02-prism-operator/evidence/local-execution.json:95:      "interpreter": "D:/_worktrees/geophysics-m01-corrections/.venv-m01/Scripts/python
  docs/design/features/m02-prism-operator/evidence/ready-execution.json:11:  "interpreter": "D:/_Repos/_Web_Projects/CAOS_Geophysics/.venv-pipeline/Scripts/python
  docs/design/features/m02-prism-operator/validation.md:178:`D:\_worktrees\geophysics-m01-corrections\.venv-m01\Scripts\python.exe`
  docs/design/features/m02-result-inspection/ui-volume-qa-2026-11-01.md:40:The M02 instrument now reads `final_solve.trace.models_kg_m3` and its paired `phi_engin
  docs/design/features/m02-survey-l2/terminal-certificate-validation-2026-11-02.md:37:`D:\_Temp\gravity-playback-qa\m02-terminal-cert-matrix`; existing evidence i
  docs/design/features/m03-flightline-processing/validation.md:82:npm run benchmark:m03 -- --output 'E:\_Temp\CAOS_Geophysics\m03-profile.json' --repeats 3
  docs/design/features/m12-velocity-validation/convergence.md:24:at `E:\_worktrees\CAOS_Geophysics-data\experiments\m12-residual-v3-20261027`;
  docs/design/features/m12-velocity-validation/nullspace-v1-protocol.md:12:`E:\_worktrees\CAOS_Geophysics-data\experiments\m12-nullspace-v1-20261027`;
```

### check_template_residue.py: timeout

Command: `python scripts/check_template_residue.py`

```text

```

### check_doc_paths.py: fail

Command: `python scripts/check_doc_paths.py`

```text
doc paths: STRUCTURE.md:11: names models/training.json
doc paths: docs/design/features/joint-survey-inversion/design.md:56: names scripts/process_joint_survey.py
doc paths: docs/design/features/joint-survey-inversion/integration-status-20261025.md:142: link to evidence/m11-fresh-workflow-20261026.json
doc paths: docs/design/features/m01-gravity-corrections/bartlett-integration.md:26: names data/ground_gravity_data.csv
doc paths: docs/design/features/m01-gravity-corrections/convergence.md:39: names data/ground_gravity_data.csv
doc paths: docs/design/features/m02-survey-inversion/design.md:249: names data-pipeline/gravity_survey.py
doc paths: docs/design/features/m02-survey-inversion/validation.md:49: names tests/data/test_gravity_survey.py
doc paths: docs/design/features/m02-survey-inversion/validation.md:50: names tests/data/test_gravity_survey.py
doc paths: docs/design/features/m02-survey-inversion/validation.md:51: names tests/data/test_gravity_survey.py
doc paths: docs/design/features/m02-survey-inversion/validation.md:52: names tests/data/test_gravity_survey.py
doc paths: docs/design/features/m02-survey-inversion/validation.md:53: names tests/data/test_gravity_survey.py
doc paths: docs/design/features/m02-survey-inversion/validation.md:54: names tests/numerics/test_gravity_inverse.py
doc paths: docs/design/features/m02-survey-inversion/validation.md:54: names tests/numerics/test_gravity_inverse.py
doc paths: docs/design/features/m02-survey-inversion/validation.md:55: names tests/numerics/test_gravity_inverse.py
doc paths: docs/design/features/m02-survey-inversion/validation.md:56: names tests/numerics/test_gravity_inverse.py
doc paths: docs/design/features/m02-survey-inversion/validation.md:56: names tests/numerics/test_gravity_inverse.py
doc paths: docs/design/features/m02-survey-inversion/validation.md:57: names tests/numerics/test_gravity_inverse.py
doc paths: docs/design/features/m02-survey-inversion/validation.md:58: names tests/numerics/test_gravity_inverse_selection.py
doc paths: docs/design/features/m02-survey-inversion/validation.md:58: names tests/numerics/test_gravity_inverse_selection.py
doc paths: docs/design/features/m02-survey-inversion/validation.md:59: names tests/numerics/test_gravity_inverse_selection.py
doc paths: docs/design/features/m02-survey-inversion/validation.md:60: names tests/numerics/test_gravity_inverse.py
doc paths: docs/design/features/m02-survey-inversion/validation.md:61: names tests/numerics/test_gravity_inverse_selection.py
doc paths: docs/design/features/m02-survey-inversion/validation.md:61: names tests/numerics/test_gravity_inverse.py
doc paths: docs/design/features/m02-survey-inversion/validation.md:62: names tests/data/test_gravity_inverse_bundle.py
doc paths: docs/design/features/m02-survey-inversion/validation.md:62: names tests/data/test_gravity_inverse_bundle.py
doc paths: docs/design/features/m02-survey-inversion/validation.md:63: names tests/data/test_gravity_inverse_bundle.py
doc paths: docs/design/features/m02-survey-inversion/validation.md:64: names tests/numerics/test_gravity_inverse_resources.py
doc paths: docs/design/features/m02-survey-inversion/validation.md:64: names tests/numerics/test_gravity_inverse_resources.py
doc paths: docs/design/features/m02-survey-inversion/validation.md:65: names tests/numerics/test_gravity_inverse.py
doc paths: docs/design/features/m02-survey-inversion/validation.md:66: names tests/numerics/test_gravity_inverse_field.py
doc paths: docs/design/features/m02-survey-inversion/validation.md:66: names tests/numerics/test_gravity_inverse_field.py
doc paths: docs/design/features/m02-survey-inversion/validation.md:67: names tests/numerics/test_gravity_inverse.py
doc paths: docs/design/features/m06-field-mt/requirements.md:12: names tests/numerics/test_mt_inverse.py
doc paths: docs/design/features/m07-slagdump-ert/tasks.md:13: names tests/ops/test_profile_host_admission.py
doc paths: docs/design/features/m08-waveform-user-data/design.md:14: link to ridgecrest-case.md
doc paths: docs/design/features/m08-waveform-user-data/design.md:14: link to tasks.md
doc paths: docs/design/features/m08-waveform-user-data/design.md:39: link to ridgecrest-case.md
doc paths: docs/design/features/m08-waveform-user-data/design.md:39: names docs/design/features/m08-waveform-user-data/evidence/ridgecrest-case-receipt.json
doc paths: docs/design/features/m08-waveform-user-data/validation-plan.md:87: link to ridgecrest-case.md
doc paths: docs/design/features/m12-protocol-launcher/requirements.md:8: link to ../../validation/m12-launcher-forwarding-2026-10-27.md
... (16 more lines; the full output is in the --keep folder)
```

### check_content_standards.py: timeout

Command: `python scripts/check_content_standards.py`

```text

```
