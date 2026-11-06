# Local job resource-limit controls — 2026-11-06

## Result

The three declared API worker-limit gates passed on the current Windows source:

| Gate | Result | Exercised behavior |
| --- | --- | --- |
| `test_cancel_timeout_failure_and_recovery` | pass | queued/running cancellation, child timeout and termination, a scientific failure, then interrupted-job recovery |
| `test_scratch_limit_terminates_child` | pass | child exceeds the configured 1 MiB scratch ceiling and is terminated without publishing a result |
| `test_rss_limit_terminates_child` | pass | child exceeds the configured 80 MiB RSS ceiling and is terminated with measured peak RSS |

Pytest reported **3 passed, 0 failed, 0 skipped**; the JUnit report records
zero errors/failures/skips and 6.718 seconds across the test bodies. The command
reported 51.13 seconds total wall time. The run used Python 3.12.10, pytest
9.1.1, and `.venv-api` on Windows. One upstream `TestClient` deprecation warning
was emitted; it did not affect these results.

## Reproduction and source identity

The source revision was `d1028a2b7be184228b8525d3c0b570958da04a74`.

```powershell
& .venv-api\Scripts\python.exe -m pytest -vv `
  --junitxml='E:\_Datos\CAOS_Geophysics\validation\worker-limits-current-source-20261106\pytest.xml' `
  tests/api/test_job_limits.py::test_cancel_timeout_failure_and_recovery `
  tests/api/test_job_limits.py::test_scratch_limit_terminates_child `
  tests/api/test_job_limits.py::test_rss_limit_terminates_child
```

| Source or output | SHA-256 |
| --- | --- |
| `tests/api/test_job_limits.py` | `275ff0037723ffdc8a3ea534f25690f3cc6c084b61c1ac60a22879e580e65376` |
| `app/worker.py` | `fd9614d2dfa604158ad8a815a508cb072f06cd02d7d6112e4279601d80893eb9` |
| `app/compute.py` | `f509dccfba0c8ff78e37d7ae82f4b4713d22f702147251c3dbdcc9a8d138b78d` |
| JUnit report | `ed9c1ca8de39a67f3b589c1b24278d63e468c0985ef1f4b394cb4b6f2daabe59` |

The JUnit report is retained outside Git at
`E:\_Datos\CAOS_Geophysics\validation\worker-limits-current-source-20261106\pytest.xml`.

## Acceptance boundary

This is local process-level evidence only. It does not qualify Linux service
limits, actual VPS admission, concurrent-job capacity, replacement service
startup, or recovery of a deployed worker. R-007 remains unresolved until its
host and deployment-specific requirements are measured.
