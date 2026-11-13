# Frontend fixture validation: 2026-11-12

## Identity and result

The direct product checkout was on `task/geophysics-client-first-completion` at
`5c06aa1` (`fix(notebooks): ignore fenced headings in content structure`). The
retained joint-survey fixtures were read in place from
`E:\_Datos\CAOS_Geophysics\validation`; no fixture bytes were regenerated.

The repository runner `scripts/run_joint_frontend_validation.ps1` completed
with **7 test files passed, 86 passed, 4 skipped, 0 failed**. The skips require
separate evaluation, abort and durable-abort artifacts that were not configured.
The four retained roots and their hashes are recorded in
[`frontend-joint-fixtures-2026-11-05.md`](frontend-joint-fixtures-2026-11-05.md).

The full `npm test` run used those same six documented joint-fixture roots and
completed with **504 passed, 12 skipped, 2 failed test files**. Both failures
occurred during module setup because the retained M04 controls are absent:
`GEOPHYSICS_MAGNETIC_STATE_BROWSER_CONTROL` and
`GEOPHYSICS_MAGNETIC_BROWSER_CONTROL`. The latter suite also requires the
authenticated input mapping and the exact Python-produced dataset bytes. The
current external `m04-controls-current-20261102` directory contains optimizer
XML controls, not these browser fixtures. No replacement was synthesized.

The no-fixture `npm test` invocation is excluded as a validation result; it
failed closed because it bypassed the fixture-binding runner. The measured
story and visual shell gate is separate from these unit-test totals. On the same
build, `npm run gate -- --out E:\_Datos\CAOS_Geophysics\validation\visual-gate-20261112`
passed **1,684 measured states**; the story-mode check passed all three declared
routes. Desktop and 390-by-844 captures were inspected for the default offset
intrusive stock case. This verifies the measured shell contract and those
specific captures; it is not acceptance of every case view or scientific
result.

## Scientific boundary

These tests validate real-byte custody, parsing, export/import contracts,
resource limits and browser result views for the retained synthetic joint
artifacts. The joint matrix itself records `scientific_precision_accepted=false`,
`field_eligible=false` and `public_activation=false`. Passing importer tests
does not accept the joint inverse or the product release. The missing M04
controls also keep the complete frontend suite open.
