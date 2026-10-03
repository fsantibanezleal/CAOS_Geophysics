# M01 local feature convergence and integration handoff

Date: 2026-10-03. Verdict: **local station-corrections unit passed; full M01 method unaccepted**. No field observations were fabricated or downloaded by this branch. Main owns Bartlett acquisition/profile work; this branch consumed one member of main's existing author archive in memory for a negative admission check. No app, backend, frontend, canonical cases, release version or shared documentation index is changed.

## Requirement gates

All gate names below are in `tests/numerics/test_gravity_processing.py`. The exact product-SDD M01 gate exists as `test_station_correction_lineage`; its local PASS verifies correction lineage, not the other open M01 responsibilities.

| Requirement | Gate | Result |
| --- | --- | --- |
| G01 originals, state and hashes | `test_station_correction_lineage` | PASS |
| G02 independent normal gravity | `test_normal_gravity_oracles` | PASS |
| G03 plate formula, units and signs | `test_plate_formula_and_sign` | PASS |
| G04 no duplicate/ambiguous correction | `test_no_double_correction` | PASS |
| G05 rejected invalid metadata/values | `test_invalid_contract`, `test_invalid_metadata`, `test_duplicate_and_unapplied_instrument`, `test_author_principal_fact_bytes_require_physical_metadata` | PASS, including parametrized cases and actual author principal-fact bytes |
| G06 height/geoid/error propagation | `test_height_datum_and_uncertainty`, `test_uncertainty_reference_cancellation_and_poles` | PASS |
| G07 residual terrain semantics | `test_terrain_semantics` | PASS |
| G08 maps/outliers preserve every station | `test_qc_preserves_outliers` | PASS |
| G09 CLI/hash/overwrite/protected paths | `test_cli_roundtrip`, `test_config_and_resume_metadata_rejection` | PASS |
| G10 wiki contract and scope | `test_wiki_contract`, `test_worked_request_is_synthetic_and_closes_formula` | PASS; diagram additionally rendered and inspected |

Command: `.venv-m01/Scripts/python.exe -m pytest tests/numerics/test_gravity_processing.py -o addopts='' -q`. With `M01_PRINCIPAL_FACT_ARCHIVE` pointing to main's already acquired author archive, **29 tests pass**, including the actual-byte negative admission control. Without that separate field acquisition, the same command explicitly skips the field control and runs 28 local tests; it never substitutes synthetic bytes. Ruff check and format check pass for the two new Python files. `pip check` reports no broken requirements. After all scoped files were staged, the existing tracked-content, template-residue and CI-budget guards passed; their tracked-file scanners included this unit. Exact final run time is recorded with the PR self-review.

## Environment and mathematical evidence

Isolated, ignored `.venv-m01`, Python **3.12.10** on Windows x64. Boule **0.5.0**, Harmonica **0.7.0**, NumPy **2.2.6**, SciPy **1.15.2**, pytest **9.1.1**, Ruff **0.15.18**. Complete direct/transitive pins live in `data-pipeline/requirements-m01.txt`. Boule and Harmonica carry BSD-3-Clause licences. Existing agent environments were not modified. This is ordinary pipeline code, without an internal installable package.

Independent numerical oracles: Somigliana versus rounded/truncated USGS WGS84 constants (`1e-5 mGal`, justified by decimal precision), the published Boule 45-degree/1000-m value (`1e-7 mGal`), north/south symmetry, monotonic height behavior, explicit plate formula (`1e-10 mGal`), zero plate, SI/microGal/upward-sign parity, independent latitude derivative, height derivative from the published table, shared-geoid derivative, malformed/tampered history and already-applied-state negative controls. Reference/height records are not propagated as independent noise sources.

The worked synthetic mathematical definition returns **12.000000000024315 mGal** after removing a **111.96875606754226 mGal** plate. Its deliberately selected marginal SDs give a conservative propagated contribution sum of **1.148909022890369 mGal**, not field precision or geological confidence. Actual PowerShell and Git Bash invocations produce identical result bytes. Execution times in separate receipts differ, as intended.

Final production module SHA-256: `7863699269b491c2895bcf030d3fb65cf27ac32a652fce91112bc2c7c9c73321`.
Synthetic request file SHA-256: `11c68ecd3c938591fe705bca95be6a89702f6e92963e371dded4fd837748b052`.
Input dataset SHA-256: `fd34156aea7d62ae85e9198827a83f628383c990b24ed4bcede7457b6170f86f`.
Derived dataset SHA-256: `3ce5c4e0bf17d14e53be4115b640603e41d4e78ea2a31ce592e669eb76815ed6`.
Paired-script result file SHA-256: `3a0a7ab501ace407cd720018828be16abb3cc167907c3c2fef046e88bc0292cc`.
Full local receipts are in ignored `data/raw/gravity-m01/ps1-final/` and `bash-final/`; they are intentionally not canonical case artifacts.

Actual author CSV control: 335,377 bytes, SHA-256 `7cb3ed0c3cbac60f896a11f213ba40209c3083cb7635ab80ab7c0fd0382a1055`, read directly from the existing archive's `data/ground_gravity_data.csv` member without extraction. Its first row remains unchanged, with distinct OG/FAA/SBA/TTC/CBA/ISO columns. A column-only request is rejected for missing explicit physical metadata rather than receiving inferred heights, corrections or uncertainty. The source's upstream instrument facts are not denied; they require an explicit mapper and the still-unresolved height/reference semantics. This is a passed negative control, with processing eligibility **ineligible**, no field reduction/result and full M01 unaccepted. The committed [receipt](evidence/field-admission-rejection.json) is local gate evidence, not a duplicate full source profile.

The SVG renders at 960x620 in light and dark; all 27 text elements are inside bounds. Measured background/ink are `rgb(248,250,252)`/`rgb(23,36,53)` in light and `rgb(17,26,37)`/`rgb(237,244,252)` in dark. Both screenshots were visually inspected for readable labels/arrows and are retained under [evidence](evidence/). This verifies the wiki diagram only; it is not a scientific-web browser acceptance receipt.

## Exact scoped files

- `data-pipeline/gravity_processing.py`
- `data-pipeline/requirements-m01.txt`
- `scripts/run_m01_gravity.ps1`
- `scripts/run_m01_gravity.sh`
- `tests/numerics/test_gravity_processing.py`
- `docs/design/features/m01-gravity-corrections/research.md`
- `docs/design/features/m01-gravity-corrections/requirements.md`
- `docs/design/features/m01-gravity-corrections/design.md`
- `docs/design/features/m01-gravity-corrections/tasks.md`
- `docs/design/features/m01-gravity-corrections/bartlett-integration.md`
- `docs/design/features/m01-gravity-corrections/convergence.md`
- `docs/design/features/m01-gravity-corrections/evidence/svg-light.png`
- `docs/design/features/m01-gravity-corrections/evidence/svg-dark.png`
- `docs/design/features/m01-gravity-corrections/evidence/field-admission-rejection.json`
- `docs/methods/gravity-processing.md`
- `docs/methods/gravity-processing/gravity-processing.md`
- `docs/methods/gravity-processing/01_station-corrections.md`
- `docs/methods/gravity-processing/station-corrections.svg`
- `docs/methods/gravity-processing/examples/station-control.json`

## Remaining full method gates and main-owned integration

1. Field source: actual **eligible** field bytes/hash/rights and calibrated observation meaning. Main's author archive supplies real principal-fact station bytes; this branch verified the member hash and exercised the rejected direct-CSV admission. The Bartlett XML/archive hash is not the individual CSV hash, and the author bytes are not proven byte-identical to USGS originals. See [provider-column and alternative-author-source seam](bartlett-integration.md). Do not use the synthetic control as a replacement. The available author source does not resolve its `zWGS84` height/reference semantics or by itself pass physical-correction eligibility.
2. Datum/error/reference: resolve NAD27 transformation and `elevation_ft_NVD29`; establish compatible receiver/surface/geoid heights, uncertainty and permanent-tide/reference context. Preserve observed IGSN1971 gravity and all principal-fact anomaly/correction columns separately. Already tide/drift-adjusted observations never get another instrument adjustment, and complete Bouguer/isostatic products never get another Bouguer/terrain reduction.
3. Actual map/selected transforms and spatially heldout predictions: no equivalent-source/gridding/continuation model or heldout metric is generated here. Freeze spatial partitions before tuning. Provider comparison must state normal gravity, curvature and terrain extent/density differences.
4. Project/worker/export integration and online admission: main integrates the ordinary function and strict rejection behavior into its owned services, persists transforms and map/uncertainty arrays, measures resources/cancellation, and connects import/export identity. This branch changes no API or worker.
5. Scientific web evidence: main wires selected-project original/derived/map/flags and honest correction-state displays, obtains EN/ES light/dark/phone interaction verification, and links the new wiki landing from its owned navigation index. No frontend, app, browser parity or deployment is claimed here.

The reviewable deliverable is [PR #99 to develop](https://github.com/fsantibanezleal/CAOS_Geophysics/pull/99), linked to #43 with self-review and named tests. It must remain open for main integration; this branch does not merge, release, deploy or close the parent full-method issue.
