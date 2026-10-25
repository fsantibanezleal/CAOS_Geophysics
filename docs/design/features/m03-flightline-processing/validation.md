# M03 mapped flight-line processing validation

Run on the local pinned pipeline environment (NumPy 2.2.6, SciPy 1.15.2):

```powershell
.venv-pipeline\Scripts\python.exe -m pytest tests\numerics\test_magnetic_processing.py -q
.venv-pipeline\Scripts\python.exe -m ruff check data-pipeline\magnetic_processing.py tests\numerics\test_magnetic_processing.py
```

Observed during implementation: the initial random whole-line holdout selected an exterior line, giving zero convex-hull support. The failing control exposed the defect. The split was changed to select a seeded contiguous interior block along the measured flight-line-normal coordinate. The final focused run passed 8 tests, including zero-error interpolation of an independently declared planar field, original-byte hashing in the CSV CLI, retained height flags, tie-line exclusion from fitting and no-overwrite behavior. These are authored algorithm controls, not field evidence.

The strict product checker still reports `M03` missing its SDD-declared `tests/numerics/test_magnetic_processing.py::test_blocked_line_holdout` symbol. The test module exists and the focused tests pass, but use a more explicit function name; the planned named gate will be reconciled after the full source-specific feature is accepted. M03 is not accepted because provider assets, segment-level tie crossover analysis, continuation, integration and live browser/host gates remain incomplete.
