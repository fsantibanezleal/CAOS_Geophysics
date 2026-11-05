# M04 bundle container, array and history controls — 2026-11-02

This is a scoped validation record for the NPY member primitives in
`data-pipeline/magnetic_survey_bundle.py`. It is **not** acceptance of R-415,
the fitted-result bundle, a completed magnetic inverse, or release readiness.

## Implemented boundary

- Encodes and decodes only native NumPy `float64`, `int64`, and `bool` arrays.
- Enforces the contract's dimensionality, product, unit-to-dtype, member-byte,
  flat-name, descriptor-key, and SHA-256 rules before constructing the result.
- Writes NPY v2 without pickle; reads NPY v1/v2/v3 with a 65,536-byte header
  cap, rejects Fortran order, object/other dtypes, wrong payload lengths,
  trailing bytes, descriptor disagreement, and nonfinite floating values.
- Returns an owned decoded array. The existing geometry JSON writer remains a
  separate format and was not relabelled as a fitted-result bundle.
- Encodes and decodes solver history as the contract's three arrays: int64
  indices, float64 numeric columns, and four signed little-endian int64 words
  per exact SHA-256 model identity. Preserves record order and the fixed
  beta-major/L2-before-sparse candidate mapping; zero rows are allowed only
  when the history codec explicitly requests them.
- Rejects invalid phase/status/fold/counter/hash values, mismatched beta,
  reordered candidates, nonfinite or negative metrics, unexpected member
  inventory, and invalid decoded indices.
- Validates the bounded manifest envelope, canonical generation digest,
  request/original source identity agreement, false acceptance claims, member
  reference uniqueness, NPY member inventory, and total/member/manifest byte
  ceilings before array decode.
- Writes a fresh generation directory, fsyncs files, reads the generation back,
  and atomically replaces `CURRENT.json`. Injected mid-write and pointer-swap
  failures leave the previous pointer selected. Readers reject symlinks,
  corrupt members, and unlisted generation files.
- Request metadata arrays are reconstructed through the existing bounded request
  parser; typed units are checked against scientific request paths, and request
  semantics are revalidated. The writer still refuses `status=complete` because
  the complete scientific Result validator is absent. Failed/ineligible structural
  fixtures test atomic storage only; they are not solver outputs.

## Validation

Command: `.venv-pipeline/Scripts/python.exe -m pytest -q tests/data/test_magnetic_survey_bundle.py tests/data/test_magnetic_bundle_generation.py tests/data/test_magnetic_history_codec.py tests/data/test_magnetic_result_array_members.py --junitxml=E:\\_Datos\\CAOS_Geophysics\\m04-bundle-generation-20261102.xml`

Result: 48 passed, 0 failures, 0 errors, 0 skips. This includes conversion of
valid big-endian NPY payloads to owned native arrays, empty/nonempty history
round trips, and atomic pointer interruption controls. JUnit SHA-256:
`45106e1d1cd87d18d99fdcf19eb54f5e4235d75bb763aa4a80fe12cfd8b7e6da`.

Ruff, `py_compile`, and scoped `git diff --check` also passed. Source SHA-256:

- `data-pipeline/magnetic_survey_bundle.py`:
  `5981be7e2bb25b3b8801ae38e9cdd3a97fc2faca17502b95e1c20940ca116e8e`
- `tests/data/test_magnetic_bundle_generation.py`:
  `87c3c0ed9b03d46ec9bf79af556512335fd71cbf63938a77ea12dba5d7378e1f`
- `tests/data/test_magnetic_history_codec.py`:
  `fedeadab46e4610f5ad89021badc8b1f76160f4ea2813faa0235fe32051bbcf2`
- `tests/data/test_magnetic_result_array_members.py`:
  `548b41057cf7331981174792d1afc3d8c9ce0d777d46761bf974fff301868a46`
- `tests/data/test_magnetic_survey_bundle.py`:
  `e6dbc4de8447afe8c390ed32ac9fb705ad31063de723423a24fa1d7bede965e3`
- `tests/data/magnetic_bundle_support.py`:
  `7b4836c44ab4c02db5bb2003c401c63be3e197e75c27f2d1c128eb66c1779728`

## Still required for R-415

Request semantics and request-array units are validated by reconstructing and
reparsing the closed request; complete scientific Result semantics, Result-array
field units/shapes, and fitted-result identity binding remain unimplemented. The
generation tests use a structural failure fixture, not a valid fitted Result.
Directory fsync and power-loss behavior are not proven on Windows; interrupted
writes can leave an unreferenced partial generation while preserving the selected
prior generation. The optimizer binding is unchanged.
R-415 and the full M04 inverse remain open.
