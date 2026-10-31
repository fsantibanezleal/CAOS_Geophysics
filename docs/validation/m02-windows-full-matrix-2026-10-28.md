# M02 locked gravity L2 matrix on Windows

The current branch reran the complete 4-condition × 6-family ordinary gravity
L2 matrix using `scripts/run_m02_control_matrix.ps1`, which isolates every
condition/family pair in its own process and writes per-case JUnit and logs to
external scratch. The run covered all 24 pairs with the declared single-thread
native environment.

Result: **24 passed, 0 failed, 0 errors, 0 skipped** on Windows 11,
CPython 3.12.10. No GPU was used. The slowest case took 1,214.054 seconds.
Per-case selection, outer WRMS/model ratio, runtime, and JUnit/log SHA-256
values are recorded in the [machine-readable receipt](m02-windows-full-matrix-2026-10-28.json).
The external raw JUnit/log directory is identified there by run ID.

This rerun is current for the source hashes in the receipt, including the
gravity objective, metric and locked-selection test that had changed after the
older 2026-10-25 full-matrix receipt. It verifies the frozen authored synthetic
controls on this Windows runtime. It does not establish field eligibility,
full M02 acceptance, VPS admission, or whole-product release acceptance.
