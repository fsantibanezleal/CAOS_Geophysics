# M02 original-noise magnetic control replay, 2026-10-31

## Scope and result

`scripts/run_magnetic_original_controls.py` ran the complete focused physical
original optimizer test module with the retained M04 six-file source snapshot.
The runner sets BLAS/OpenMP limits before numerical imports, verifies the
source snapshot hashes, and preloads the historical magnetic modules before
pytest adds the current M02 solver. Result: **8 passed, 1 skipped** in 6.59 s.

The four `actual_original_noise_native_accuracy` cases passed across
`secondary_enu_nT` and `linear_tmi_nT`, each with diagonal-SD and stored
covariance noise. The passing checks include independently bound actual-source
objects, strict physical-domain admission, native terminal audit and an
independent bounded least-squares comparison. The retained 528-parameter
first-fold case was skipped because its exact frozen request and external
receipt path are not provisioned in this environment. It remains unresolved;
this skip is not a scientific pass.

## Reproduction and receipts

```powershell
.venv-pipeline\Scripts\python.exe scripts\run_magnetic_original_controls.py `
  --source-root E:\_Datos\CAOS_Geophysics\validation\m02-magnetic-control-source-20261031 `
  --junitxml=E:\_Datos\CAOS_Geophysics\validation\m02-magnetic-control-source-20261031\physical-original-controls.xml
```

- Retained source root: `E:\_Datos\CAOS_Geophysics\validation\m02-magnetic-control-source-20261031`.
- Retained source commit: `63c9790264ddced3bc71e0d4a9c52bb4e5ec714e`.
- JUnit: 1,922 bytes; SHA-256 `25197a265db393be522ecdaadbdae337c68e5efb75b48300b0d2d50e18b88acd`.
- Current source tree was whitespace-checked; Ruff passed for the runner and control module.

This is a focused local solver control only. It does not close the broader
M01-M13 method matrix, the failed R-008 verdict, the remaining convergence
requirements, or VPS release acceptance.

## Current-checkout rerun, 2026-11-02

The same runner and same retained six-file source closure were run against the
current direct checkout, with a fresh external JUnit destination. Outcome:
**8 passed, 1 skipped, zero failed/errors**. The only skip remains
`test_actual_original_full528_firstfold_strong_accuracy`: its exact frozen
528-parameter request and external receipt are not provisioned. The 8 passed
tests include the source preflight, three strict-domain endpoint controls and
four native-noise accuracy controls. No solver policy, tolerance or test
selection changed.

- Current checkout base: `f0ec2fc37fdae1f0c1c7d40b6cae386a85d7e6ac` (dirty).
- Current JUnit: `E:\_Datos\CAOS_Geophysics\validation\m04-controls-current-20261102\m04-original-optimizer-current.xml`.
- JUnit SHA-256: `aa049bc3a76fd288a2d562d5530f3bde32ca25f69eb7461af51c6ee5ecb0a0f8`.
- `data-pipeline/magnetic_original_optimizer.py` SHA-256:
  `f0eef347ad2ac6dcfde9f1622e3c181d4de229e41479ffdf08f20848247ca6a1`.
- `data-pipeline/physical_original_optimizer.py` SHA-256:
  `5e7f9863362255dcc94bcb851a886840c611fcab7b1b6e9656e2ab1f641e3217`.
- `tests/numerics/test_physical_original_optimizer.py` SHA-256:
  `d0f468401687c3fd90f25176bec9293e6377bb75d3c91ce7f91932c9782f3128`.
- `scripts/run_magnetic_original_controls.py` SHA-256 after the harness fix:
  `61e93dd239ac562ff01589cad066d5ed39fd7378abc6b9315a213695b73c8976`.
- Default-target JUnit from the verified runner invocation SHA-256:
  `f246a092edeccd529c7893d5ffab7dea2078c2aa338cda9a772fa9c82d9d16e8`.

The first attempt exposed a launcher defect: `--junitxml <path> -q` contained
a non-option value, so the runner did not inject its default test module and
pytest collected the repository. That collection-only attempt failed on
unrelated environment imports before M04 tests ran and is not counted. The
runner now detects an explicit test target separately from option values; the
default invocation above then ran exactly the intended module with the same
8-pass/1-skip outcome.

This current-source run strengthens only the local M04 optimizer controls. The
528-parameter gate, full survey workflow, real owned-custody browser controls,
hosted admission and broader M04/product acceptance remain open.
