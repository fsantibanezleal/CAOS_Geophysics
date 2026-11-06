# M04 independent synthetic acquisition matrix : 2026-11-02

## What was generated

The geometry fixture is planned before any Choclo truth evaluation or noise draw.
The generator verifies the frozen 12-flight membership: 72 outer rows, 216
development rows, three folds of 144 fitting and 72 validation rows, no buffered
rows, and 216 final-refit rows. The four-flight F case is rejected by that same
geometry planner before any values are made.

The reproducible matrix contains six regimes (A–F) crossed with three separate
measurement channels (secondary ENU, linear TMI, and exact total-field anomaly):
18 survey requests and 18 separately stored truth files. A–C are induced-body
controls, D adds the frozen remanent vector, E generates with the A field while
declaring the wrong field for inversion, and F is an exact zero realization
with insufficient coverage. A–E have independent conditional Gaussian noise
with 0.5 nT standard deviation per scalar component. Scalar exact-anomaly truth
uses direct Decimal80 norm subtraction. The off-grid rectangular-prism truth is
computed by Choclo 0.3.2, separately from the SimPEG inversion mesh. NumPy
2.2.6 PCG64 and the per-regime/channel seed sequence are pinned.

Truth bodies, remanence, clean predictions, and the truth field stay outside the
survey request. The manifest binds every request and truth file by byte count
and SHA-256; the truth file also records its request source hash. Every artifact
explicitly disclaims field-observation, geological-truth, inversion-result, and
method-acceptance status.

## Validation

The current-source focused M04 regression run passed 453 tests, with zero
failures, errors, or skips. It includes the new exact R-412 gate
`tests/numerics/test_magnetic_inverse.py::test_independent_case_matrix`, which
checks all 18 generated cases and the manifest-bound request/truth separation.
Additional controls independently recompute selected remanent off-grid values
with direct Choclo calls, verify the exact scalar channel with Decimal80, and
check the wrong-field and four-flight negative outcomes.

The JUnit report is outside the checkout at
`E:\_Datos\CAOS_Geophysics\validation\m04-post-s2-controls-20261102.xml`;
SHA-256: `97a0b19da36b0b536a29f1b126137c4109d3b55a162c3c0a4e2d7115ae8715ad`.
The generated fixture manifest is
`tests/fixtures/magnetic_survey/generated/manifest.json`, SHA-256
`8b1b541cfe36d024cfb2f2354c6669a9bd5794da6b05d1bd4873fa3111b7ae08`.
The generator's `--check` mode reproduced this exact manifest and all 36
member files. Ruff, Python compilation, the EN/ES documentation matrix, and
`git diff --check` also passed for this change.

## Boundary

This closes the independent synthetic acquisition-generation control only. It
does not fit any model, establish that sparse fitting improves recovery, close
R-405–R-411 or R-413–R-420, validate any field survey, or accept M04. The M02
optimizer binding and complete inverse remain unaccepted; no VPS admission or
release cutover follows from these fixtures.
