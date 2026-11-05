# M02 uploaded-prism browser run — 2026-11-01

## Result

The isolated owner-workbench browser run completed **2/2 selected tests**. The
uploaded-case path used a 144-station authored Choclo prism control dataset,
validated its source and physical metadata, launched the real bounded M02 child
worker, rendered the returned inverse, and exported a result ZIP which the
separate Python bundle verifier accepted. This is evidence for the exercised
synthetic control path only; it is not field-data eligibility, full M02
acceptance, or host acceptance.

The run produced a converged ordinary weighted-L2 fit with 36 withheld
stations and 48 active cells. The captured workbench showed the physical 3D
cell volume, recorded accepted-state replay, held-out diagnostics, worker
resource estimates, and result export controls. The 3D view is a visualization
of returned solver arrays and recorded solver states; camera, slice, and
vertical exaggeration are display controls.

## Measured receipt

| Quantity | Recorded value |
| --- | ---: |
| Stations / held out | 144 / 36 |
| Active cells | 48 |
| Fit status | converged |
| Child wall time | 37,015 ms |
| Peak RSS | 205,414,400 bytes |
| Scratch | 549,774 bytes |
| Configured wall / memory / scratch limits | 600 s / 2 GiB / 256 MiB |
| Preflight memory / scratch estimates | 628,684,560 bytes / 16,785,354 bytes |

The receipt explicitly records `field_eligible=false`,
`full_M02_accepted=false`, and `host_accepted=false`.

## Reproduction

From `frontend/` in the Windows repository checkout:

```powershell
& '.\node_modules\.bin\playwright.cmd' test `
  --config '.\playwright.processing.config.ts' `
  --grep 'owner upload to flag result|authored prism upload'
```

This invokes the opt-in loopback QA server and local `.venv-gravity` child
runtime; it does not enable the lane in production settings or contact the VPS.
The generated result bundle was verified by the test's independent Python
`verify_bundle` path.

## Evidence identities

| Artifact | SHA-256 |
| --- | --- |
| Source CSV | `fc5c61f4d9fdea8bd47e74f9226195cea4718f0acb4918f88ba879ab13df8f06` |
| Bound dataset | `6421a2a50ba7b17fbf14d3fbcef15e7566ee09d1a8b2bd791fdb95d5d6d994fb` |
| Job request | `e39fd8af267d21b76afcf627eee3cb0fe0491425fe9774fe866d83dd4ba4c0fc` |
| Result | `228aca6921ff86e58daa7d83de98e24158a5623d3d085c9220e7a4d7909da0f9` |
| Calibration | `f3c48630edda2cb5a8f830e5e608db6611db133b0bf0034b3ea2ae3889437d20` |
| Evaluation | `b66b8f472839de21a1fed60fa6197831056a266d69fa566e09fae556a93dd6a4` |
| Browser screenshot | `85a1d133301e27182417b1d7ed51b5df21a367acfea66e4617197218a809dbe8` |
| QA receipt | `daa93dfee90b637d701961f025235fdabec6a0fa358e2c9b170e15d4cbe0e3f3` |
| Browser-exported ZIP | `80166d1596059109e7b1739c40886eecc8db8e49b144a39bc176d03cef8da5af` |

Screenshot, receipt, and ZIP were retained outside Git under
`D:\_Temp\gravity-playback-qa\` to avoid committing transient browser data.

## Remaining acceptance work

This run closes only the authored local-frame uploaded-result desktop/light/EN
slice. It does not close actual field-source admission, held-out scientific
acceptance, shared Python/TypeScript packet parity, adversarial replay controls,
two-owner isolation, expiry/cancellation/tamper/resource-rejection cases,
mobile, dark theme, Spanish, complete chart/table interactions, host gates, or
release acceptance. The convergence ledger remains authoritative and must not
be advanced to accepted based on this synthetic control.
