# Ordinary gravity L2 current-source suite

Status: local current-source software and calibration evidence. This is not field validation, independent scientific acceptance, full M02 acceptance, actual-host capacity acceptance, or product release acceptance.

## Command and environment

The focused suite covered the ordinary weighted L2 engine, its metric ownership and certified-delta path, precision controls, and the complete six-family by four-condition locked calibration matrix. It ran in the repository's existing `.venv-pipeline` with the three required native-library thread limits set to one:

```powershell
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
python -m pytest tests/numerics/test_gravity_l2.py tests/numerics/test_gravity_l2_metric.py tests/numerics/test_gravity_l2_precision.py tests/numerics/test_gravity_l2_selection.py -q --junitxml="$env:CAOS_DATA_ROOT/validation/m02-current-source-audit-20261105/gravity-l2-focused-single-thread.xml"
```

Runtime was Windows CPython 3.12.10 in `.venv-pipeline`. The source-bound metric guard verified the registered native library hashes and single-thread settings before solving. No dependency was installed or modified for this run.

## Result

| Measure | Result |
|---|---:|
| Test cases | 281 |
| Passed | 281 |
| Failed, errored, skipped | 0, 0, 0 |
| Pytest recorded duration | 8,977.710 seconds |
| Locked calibration cells | 24 of 24 completed |
| Local resource sampling | Not performed by this suite |

The 24 locked matrix tests each run the fixed eight-candidate beta grid, three training folds and separate held-out rows. Their combined runtime dominates the suite. The slowest family-condition cells were family 3 / conditions 5 and 3 at 749.722 and 725.118 seconds. These are within the frozen per-fit and calibration limits; this local timing does not qualify VPS capacity.

JUnit is stored outside the repository under `CAOS_DATA_ROOT/validation/m02-current-source-audit-20261105/`. Its SHA-256 is `8ed5206d5914c21e1f3368ee3cfc581405805d55597bf052dd0966b3c1f72b52` (248,479 bytes). The suite began at 2026-11-05 12:38:25 -03:00. The earlier invocation without the required thread environment is excluded; its metric admission refusal is retained in the same external validation directory.

## Source identity

| Path | SHA-256 |
|---|---|
| `data-pipeline/gravity_forward.py` | `000992755f06859340b725f5fa504d59695a45814328ef785a9b91e61c389678` |
| `data-pipeline/gravity_l2.py` | `fc6fd9216edd43c02b83fddedca007a782bc627073a9d08da069d29f75d4d016` |
| `data-pipeline/gravity_l2_metric.py` | `d09a2b4630258d2c26a1a82ea92a3cd79b42143695d3e630d5252df5ba8dfe8b` |
| `data-pipeline/gravity_l2_precision.py` | `9b841bfb11c61ed9663886cd5ab9d3a878f95738ce56b8f103d2be36eeaa4f80` |
| `data-pipeline/gravity_survey_l2.py` | `50934e1f56fcd468787b113598d01966b0a0eb1b124cb95363605fea8278da97` |
| `tests/numerics/test_gravity_l2.py` | `d8599ba60f45919cf42d2dccdf054fb5e009034577c2294303e81d75b7c444a4` |
| `tests/numerics/test_gravity_l2_metric.py` | `90109d1e58b2e80186f29c7be36540555c2c4eba15d389a82d5f26ed93694997` |
| `tests/numerics/test_gravity_l2_precision.py` | `21d8fdd6e97552fd6efcb0e8910fd90237f8aceecb828e00487a88aa6e295d27` |
| `tests/numerics/test_gravity_l2_selection.py` | `f6557c33df18599ec8d511b9656a67456d1434ff84430ea4cf87b86e1bc82028` |

## Boundary

The results establish that these 281 authored local tests pass against the listed working-tree sources. They do not independently validate the authored oracle, establish geological recovery on field data, prove an allocation upper bound, accept host resource use, or close requirements R-001 through R-019. Ordinary L2 survey integration, field eligibility, broader sparse/IRLS behavior, independent review, and the hosted project/job path remain separate gates.
