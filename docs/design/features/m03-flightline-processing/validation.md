# M03 mapped flight-line processing validation

Run on the local pinned pipeline environment (NumPy 2.2.6, SciPy 1.15.2):

```powershell
.venv-pipeline\Scripts\python.exe -m pytest tests\numerics\test_magnetic_processing.py -q
.venv-pipeline\Scripts\python.exe -m ruff check data-pipeline\magnetic_processing.py tests\numerics\test_magnetic_processing.py
```

Observed during implementation: the initial random whole-line holdout selected an exterior line, giving zero convex-hull support. The failing control exposed the defect. The split was changed to select a seeded contiguous interior block along the measured flight-line-normal coordinate. The current focused suite passes 14 M03 tests. Controls construct crossing flight/tie lines on an analytic plane, recover a deliberately injected 7 nT tie offset from independent segment interpolation, reject duplicate per-line sample-order keys and excessive segment-pair work, and exclude parallel/collinear segment pairs. These are authored algorithm controls, not field evidence.

The SDD-declared `tests/numerics/test_magnetic_processing.py::test_blocked_line_holdout` symbol is now present. This structural gate does not confer scientific acceptance. M03 remains unaccepted because provider assets, source-specific comparison and continuation, integrated project/worker/view flows, and live browser/host gates remain incomplete.
