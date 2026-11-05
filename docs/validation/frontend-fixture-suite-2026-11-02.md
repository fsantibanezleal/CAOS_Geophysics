# Frontend fixture-backed suite — 2026-11-02

## Run identity

- Checkout: direct product checkout on `task/geophysics-client-first-completion`.
- HEAD at run start: `f0ec2fc37fdae1f0c1c7d40b6cae386a85d7e6ac`; the checkout was dirty, so this identifies the base revision only.
- Command: `npm test` from `frontend/`.
- Current rerun: **446 passed, 12 skipped, 2 failed suites**, across 55 files (458 tests total). The actual joint fixtures were bound from the retained validation directory. The two setup failures stop before test execution because the retained M04 source controls are absent: `GEOPHYSICS_MAGNETIC_STATE_BROWSER_CONTROL` and `GEOPHYSICS_MAGNETIC_BROWSER_CONTROL`. This is not a passing full-suite gate.
- A no-fixture diagnostic run is excluded from this result: without the authentic joint fixtures, 36 custody-dependent tests fail closed at setup. It did not modify source or fixture data.

## Original fixtures used

The authentic joint survey fixtures were read from the external validation workspace, without editing their bytes:

- Input matrix: `combined-joint-input-matrix-20261031`.
- Output matrix: `combined-joint-output-matrix-20261031`.
- Selected output: `combined-joint-output-matrix-20261031/joint-control-00/output`.
- Maximum output: `combined-joint-maximum-resource-20261031/output`.
- Native state instrument: `joint-instrument-replay-20261031/current-instrument-case00`.
- Failed Python custody export: `combined-api-custody-20261031`.

The frontend suite passed its 24-case output import, native custody/API export, import scheduling, and result instrumentation checks with those original directories bound to their documented `GEOPHYSICS_JOINT_*` environment variables. The run preserves each artifact's explicit `scientific_acceptance=false`, `field_eligible=false`, and `public_activation=false`; it does not accept the joint inverse scientifically or authorize host admission.

## Remaining failures

The exact M04 selected-final audit extraction and owned-custody browser controls referenced by the test setup were not found at the recorded `E:\_Temp\geophysics-m04-owned-survey-20261008\...` paths. The processing suite also requires the authentic dataset/source mapping control and Python-produced dataset bytes. No replacement data was created. `magnetic-model-states.test.ts` and `magnetic-processing.test.ts` therefore fail during module setup. Their current source hashes are respectively `35c9f4ffd6edf241a44bf93ebbd82dff917a725080b3dd5f08ec21cc3e0370ae` and `062384b8b9352ed6ea6f6105d26e958a870bc5ce87f3e4621cb948ea029ba0b6`.

The unrelated Long Valley feature, production build, notebook, documentation, and convergence checks are recorded in [its scoped validation record](long-valley-time-lapse-2026-11-02.md). Neither run establishes whole-product or VPS release acceptance.
