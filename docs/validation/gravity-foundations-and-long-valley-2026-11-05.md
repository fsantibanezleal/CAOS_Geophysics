# Gravity foundations and Long Valley lesson receipts

Status: the bilingual gravity foundations and field-processing lessons execute in fresh kernels and meet their individual notebook content floors. The whole notebook library and product remain below the complete content/release bar.

## Foundations lesson

`01-gravity-reference-and-units.ipynb` uses the authored one-station control and the real `process_survey` pipeline. The lesson distinguishes WGS84 gravity disturbance from the separate infinite-slab operation, states dimensions/signs and the mGal/μGal conversion, and shows the observed/reference and anomaly-scale stages in separately labelled windows. Its EN/ES word counts are 1,053/1,006; both have two display equations, two image outputs and four references. The data remains explicitly synthetic.

## Long Valley field case

`03-long-valley-time-lapse-processing.ipynb` reads the actual source-bound USGS Long Valley gravity table and metadata. The raw table has SHA-256 `d7cca18741ef85fa7ea6fe448dabfee40900de6ed45ba5ea3d13b9e9f9ec1424`. Its date/epoch pairing, reported errors, QC flag and authored derived artifact remain source-bound. Eight focused tests pass, the committed time-lapse JSON reproduces byte-identically, and the repository runner executed both language versions successfully in fresh kernels.

The lesson teaches station pairing, missing-visit handling, independent-error and covariance formulas, a correlation sensitivity curve, source-QC preservation, and a local normalized-data adapter. It compares the cited paper's 1982–1998 values (−107 ± 6 μGal raw and +64 ± 15 μGal after uplift/water-table corrections) in mGal while explicitly separating them from the lesson's 1982–1999 raw pair. It does not claim to reproduce the published correction because the table lacks matching station elevations and water-level observations.

| Language | Prose words | Figures | Display equations | Cited sources |
|---|---:|---:|---:|---:|
| English | 1,687 | 3 | 4 | 5 |
| Spanish | 1,718 | 3 | 4 | 5 |

The complete notebook path is ordered by lesson level: foundations (1), M01 correction (2), Long Valley processing (2), then M02 prism inversion (3). `notebooks/README.md`, SDD method links, source-to-content review and coverage paths were updated together.

## Commands and evidence

```powershell
$env:CAOS_TEMP_ROOT = 'E:\_Datos\CAOS_Geophysics\_Temp\m01-notebooks-20261105'
python scripts/run_notebooks.py --only notebooks/en/02-gravity/01-gravity-reference-and-units.ipynb --only notebooks/es/02-gravity/01-gravity-reference-and-units.ipynb --only notebooks/en/02-gravity/02-m01-station-corrections.ipynb --only notebooks/es/02-gravity/02-m01-station-corrections.ipynb --only notebooks/en/02-gravity/03-long-valley-time-lapse-processing.ipynb --only notebooks/es/02-gravity/03-long-valley-time-lapse-processing.ipynb
python scripts/check_notebooks.py
python -m pytest -q tests/data/test_long_valley_timelapse.py
python data-pipeline/long_valley_timelapse.py --check
```

Results: six lesson notebooks executed; template check passed all 66 notebooks in both trees; eight Long Valley tests passed; derived source-bound JSON replay passed. The repository-wide CAOS_MANAGE notebook-depth check still reports 240 findings in other lessons. These scoped results do not validate the VPS workflow, field corrections, source inversion, M01/M02 acceptance, or release readiness.

## SHA-256

| File | SHA-256 |
|---|---|
| `data-pipeline/long_valley_timelapse.py` | `8c3292ac0ddcba1a8e63e7b1a628b2b13403e34063df1d25b188ba771058dce9` |
| `data/downloads/long-valley/GravitySurveys.txt` | `d7cca18741ef85fa7ea6fe448dabfee40900de6ed45ba5ea3d13b9e9f9ec1424` |
| `data/downloads/long-valley/gravitymetadata.htm` | `57dd3c0486405b92482d5dba491d15d9f5db6ede48b030792312787f0136a97c` |
| `data/derived/field/long-valley/1982-06_to_1999-07.json` | `25d856bad85575f400eb4d1c3ec21096ea603134170a807289956d14d6ecfbe2` |
| `notebooks/en/02-gravity/01-gravity-reference-and-units.ipynb` | `09f98adc5b862ff99997025244ccf7293294d5e808849bddaaba1b6f2ce38b86` |
| `notebooks/es/02-gravity/01-gravity-reference-and-units.ipynb` | `7b8a70162f8a5b14790a2e2fdc1917b41794737b7d4961a807f6b3e698161de4` |
| `notebooks/en/02-gravity/03-long-valley-time-lapse-processing.ipynb` | `c80b4e8797ca705e79bd7e9eb0ffaf56a3ed9f5ddc999bd4363b0b5c49c5b3b9` |
| `notebooks/es/02-gravity/03-long-valley-time-lapse-processing.ipynb` | `c0d9234377f85998be188e51c1b5c1a2ae1c3f64c088da72402961ea2b02a4ad` |

The published Long Valley interpretation and USGS source records are mapped into the SDD research basis; the observed pair remains raw until the missing elevation and hydrology corrections are sourced and audited.
