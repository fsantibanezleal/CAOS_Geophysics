# M08 local scientific and service checks — 2026-11-02

## Results

| Check | Result | Boundary |
|---|---|---|
| `tests/numerics/test_waveform_picks.py` in `.venv-pipeline` | 24 passed, 1 skipped. | The skipped comparison requires the separately retained external waveform evidence root. |
| `tests/data/test_waveform_full_workflow.py` in `.venv-m08` | 3 passed. | Authored ordinary controls exercise the actual calculation and export/reopen workflow; they are synthetic mechanics evidence, not field qualification. |
| `tests/api/test_waveform_service.py` in `.venv-api`, with `M08_TEST_SCIENCE_PYTHON` pointing to `.venv-m08` | 22 passed using an external short pytest scratch root. | The first default-temp invocation failed closed on a Windows path-length limit before publication. Re-running with `--basetemp E:\_Temp\m08-service-short-path-20261102` passed; the API correctly rejects unsupported long destinations. |
| `process_waveform_record` on the authored nominal 1-channel MiniSEED/StationXML control | `computed`; response sensitivity mismatch 0; unit-bearing counts, physical, filtered and Welch products emitted; no candidate intervals. | The control is a steady periodic signal, so the empty candidate set is expected and is not a pick-accuracy result. |

## Release boundary

These local checks do not qualify the protected worker supervisor on an installed Windows or Linux host, validate field timing, establish an actual-host capacity envelope, or pass product convergence. M08 scientific acceptance and VPS release acceptance remain open.
