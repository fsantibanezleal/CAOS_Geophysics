# R-005 uploaded-data eligibility check

Date: 2026-11-06. This is scoped local evidence for the selected-dataset method
eligibility path. It does not establish product acceptance or host admission.

## Checks run

- `pytest -q tests/api/test_method_eligibility.py tests/api/test_uploaded_method_eligibility_matrix.py tests/api/test_physical_root_route.py`: **10 passed**. The cases cover gravity station contracts, magnetic flight-line uploads, native EDI, ERT and travel-time profiles, waveform pairs, and the physical-root method lane. Unavailable methods must carry a lane, a reason and field paths; unsupported fallback methods are rejected.
- `npm run test:e2e:eligibility -- --output E:\_Datos\CAOS_Geophysics\validation\r005-eligibility-current-20261106-rerun`: **1 passed**. The browser case verifies gravity QC eligibility, unavailable M02/M05 reasons, disabled method-specific submission, and Spanish field-path rendering.
- The additional real MT upload/workbench browser evidence is recorded in [mt-workbench-browser-local-2026-11-06.md](mt-workbench-browser-local-2026-11-06.md). Across its full visual run and focused rerun, all five distinct MT cases passed at least once, including actual M05/M06 execution, response controls, and the measured Clear Lake QC-only negative case. The complete five-case harness did not pass in one invocation; the report preserves the failed intermediate assertion and exact scope.
- The browser server served `frontend/dist`, built at 2026-11-06 02:21 local time. The latest application source change was `721f7fc` at 00:53; the later checkout changes affect tests and QA shutdown, not the rendered application bundle.

## Boundary

The API matrix checks several uploaded modalities, and local browser evidence now
covers gravity plus the MT EDI workbench. It does not prove browser parity for
magnetic, profile, waveform and physical-root workbenches as a complete set. The
default host execution lanes also remain closed pending their separate resource
and acceptance evidence. R-005 therefore remains **unresolved**.
