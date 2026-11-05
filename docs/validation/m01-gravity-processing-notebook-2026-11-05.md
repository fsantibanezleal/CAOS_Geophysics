# M01 gravity processing lesson: source and execution receipt

Status: bilingual lesson execution and structural checks passed. This receipt covers the M01 station-correction lesson and does not accept the full M01 field workflow or the product release.

## Scope and inputs

The English and Spanish lesson pair reads the committed analytic one-station control at `docs/methods/gravity-processing/examples/station-control.json` and calls `data-pipeline/gravity_processing.py::process_survey`. The control is explicitly synthetic, authored under Apache-2.0, and defines a 12 mGal residual. It is not field evidence. The lesson now derives the reference and simple-plate equations, varies density through 21 production-pipeline calls, distinguishes conditional marginal uncertainty from omitted covariance, and documents the local station-bundle contract for a reader's own data.

The optional field-contract cell looked for `data/incoming/gravity-stations.json`. No such file was present, so no field observation was ingested or represented as processed.

## Execution

Both notebooks were run top-to-bottom in fresh kernels by the repository runner:

```powershell
$env:CAOS_TEMP_ROOT = 'E:\_Datos\CAOS_Geophysics\_Temp\m01-notebooks-20261105'
python scripts/run_notebooks.py --only notebooks/en/02-gravity/02-m01-station-corrections.ipynb --only notebooks/es/02-gravity/02-m01-station-corrections.ipynb
```

Result: **2 notebooks executed successfully**. The final density sweep measured a slope of −0.04193586369570859 mGal/(kg m⁻³); the infinite-slab derivative at the declared 1000 m thickness is −0.04193586369570871 mGal/(kg m⁻³). Their difference is 1.18×10⁻¹⁶. The processor returned 12.000000000024315 mGal for the authored control, and a +100 kg/m³ density change produced −4.193586369570852 mGal. Duplicate correction was refused by the state contract.

`python scripts/check_notebooks.py` passes for all 66 notebooks in both language trees. The CAOS_MANAGE depth checker reports this English/Spanish pair above the level-2 floors: respectively 1,510/1,757 explanatory words, three image outputs, two display equations and four cited sources. The repository-wide depth check still reports gaps in other lessons; this local pass does not resolve them.

## Source identity

| File | SHA-256 |
|---|---|
| `notebooks/en/02-gravity/02-m01-station-corrections.ipynb` | `2d3d7a8ce9f18aa634b520e1e95b1d1874638e351abc76346a84e7488f627fa2` |
| `notebooks/es/02-gravity/02-m01-station-corrections.ipynb` | `7092cea9405f1a68dbf425a8ce21998ab3b430fec5cdc3921e28fa0b2956dd93` |
| `data-pipeline/gravity_processing.py` | `dc6d529bdaef766012d076a5786feefd8388f6e6ad310c6239aa91ca43da425fe` |
| `docs/design/SDD.md` | `ad7906e056c30188daefe7d2640e439b49d3f384c3a2dd7b6592997ada758f54` |

The SDD research basis now records the USGS reduction and elevation-data references used by this lesson. The infinite slab remains an approximation; this evidence does not supply terrain correction or field validation.
