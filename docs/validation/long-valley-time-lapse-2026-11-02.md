# Long Valley gravity time-lapse validation — 2026-11-02

## Scope

This validation covers one field-data preparation and exploration path built from the USGS Long Valley gravity table. It does not validate a complete gravity reduction chain, spatial inversion, density model, or geophysical interpretation.

The pinned source table has eight occupations from June 1980 through July 1999, 37 station locations, and 212 available station-occupation values. The exported June 1982 to July 1999 comparison contains 37 paired stations. Differences use later minus earlier. The propagated standard uncertainty is `sqrt(sigma_earlier^2 + sigma_later^2)` under an explicit independent-error assumption. Cross-epoch covariance is unavailable. The source table does not provide station elevations, and this workflow does not apply corrections for vertical deformation or water-table change.

During visual QA, selecting September 1982 exposed a +24.605 mGal station difference. Source inspection found that the 1JD1952 value 979255.21 mGal is identical to the value listed for 1JCM1952, while the other 1JD1952 occupations are near 979279.9 mGal. USGS [Open-File Report 87-77, Table 3](https://pubs.usgs.gov/of/1987/0077/report.pdf) lists 979279.87 for “1 JDI 952” and 979255.21 for “1 JCM”. This supports a *suspected* cross-copy/transcription flag but does not establish which record or epoch is wrong. The pipeline preserves the original data and binds its QC flag to the exact source hash and observation tuple; default comparisons exclude it, while an explicit UI toggle includes it for investigation. No correction is asserted.

## Reproduction and observed checks

| Check | Result |
|---|---|
| Source retrieval and normalized metadata hash | Passed; `scripts/download_long_valley.py` |
| Derived artifact deterministic replay | Passed; `data-pipeline/long_valley_timelapse.py --check` |
| Parser and source-contract tests | 8 passed, including exact-source QC flagging and default/opt-in pairing; `tests/data/test_long_valley_timelapse.py` |
| Frontend Long Valley data tests | 5 passed, including preservation of the raw value, default exclusion, explicit inclusion, and malformed-QC rejection |
| Production frontend build | Rebuilt after correcting the source citation to Table 3; TypeScript and Vite passed, Vite transformed 1,944 modules and emitted the source-bound field artifact. Existing warning: Workbench chunk is 549.96 kB minified. |
| EN/ES and responsive visual matrix | 4 passed: EN light desktop, EN dark phone, ES light phone, ES dark desktop. Each selected a station, opened paired values, changed the earlier epoch to 1982-09, verified 23 default points then 24 after explicitly including the flagged observation, selected 1JD1952 and confirmed its flagged value appears in station history only after opt-in, checked horizontal overflow, and observed zero browser errors. Captures include both default-QC and flagged-included states. The test navigates to Experiments → “What evidence does each method show?” → “Long Valley field record”; final receipt and screenshots: `E:\_Datos\CAOS_Geophysics\validation\long-valley-visual-2026-11-02-final`. |
| Bilingual notebook execution | 2 passed in fresh kernels (English and Spanish); subsequent `--check` replay passed without modifying notebook files |
| Long Valley raw-source QC regression | 8 passed; exact flagged raw value retained, default pair count 23, explicit inclusion count 24 |
| Notebook structure/content gate | 64 current bilingual notebooks passed |
| Documentation matrix and source-to-content coverage | Passed; 13 methods and 64 notebooks bound to the review manifest |
| Full frontend unit suite | Not rerun in this QC-focused pass. The last recorded full-suite run in the active validation log had 445 passed, 12 skipped, and 2 setup-failing suites because original M04 selected-final and owner-custody fixtures were absent. See [frontend fixture report](frontend-fixture-suite-2026-11-02.md). |

The QC-aware four-view browser run used `frontend/playwright.long-valley.config.ts`; its final screenshots and JSON result are under `E:\_Datos\CAOS_Geophysics\validation\long-valley-visual-2026-11-02-final`. Desktop captures were visually inspected after the citation update. The earlier run remains preserved under `D:\_Temp\gravity-playback-qa\long-valley-browser-matrix`.

## Data lineage and interpretation boundary

The processed artifact is `data/derived/field/long-valley/1982-06_to_1999-07.json`. It carries the source URL, retrieval date, source checksum, normalized metadata checksum, units, datum statement, uncertainty semantics, processing history and limits. The app displays actual station coordinates and values; it does not interpolate a continuous field between stations.

The raw table documents solid-Earth-tide and daily-instrument-drift removal and least-squares station averaging. Those source-side statements are provenance, not computations performed by this pipeline. The app's error bars express the stated independent-error propagation model and must not be read as calibrated detection probabilities. No density, depth, magma source, or causal attribution is inferred.

## References

- U.S. Geological Survey, [DDS-81 Long Valley Caldera GIS Database](https://pubs.usgs.gov/dds/dds-81/intro.html), [gravity data format](https://pubs.usgs.gov/dds/dds-81/Intro/MonitoringData/Gravity/DataFormat.html), and [gravity metadata](https://pubs.usgs.gov/dds/dds-81/Intro/MonitoringData/Gravity/gravitymetadata.htm).
- Battaglia, M., Roberts, C., and Segall, P. (1999), [Modeling of ground deformation and gravity changes in the Long Valley Caldera, California](https://doi.org/10.1126/science.285.5436.2119).
- Battaglia et al. (2003), [The Long Valley Caldera GIS Database](https://doi.org/10.1016/S0377-0273(03)00171-9).

## Release status

These results validate this bounded field-data feature and its local processing/replay path. They do not close SDD requirements for full method coverage, user-provided uploads across modalities, authenticated project jobs, host acceptance, or scientific acceptance of field inversions. The convergence ledger's existing verdicts remain unchanged.
