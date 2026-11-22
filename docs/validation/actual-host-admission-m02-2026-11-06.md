# Actual ML VPS M02 uploaded-survey admission

**Outcome:** scoped CPU runtime and uploaded ordinary-L2 path passed on 2026-11-06. This is not full M02, field-data, release-capacity, or product acceptance.

## Frozen inputs

- Source commit: `58635abaa1194b1291e1651863b9ab3b40de8305`.
- Immutable run: `g2-20261106-58635ab`.
- Source archive SHA-256: `e9f4550941381570e4c1d8e646412c98779870b21626b6e4ef5d62fa8ac451a5`.
- Runtime: hash-pinned CPython 3.12.16, x86_64 Linux, Python tree SHA-256 `977918a7254411b0a587d94f0f359ff497d207ea0f7fbeef817dec6487533706`.
- Gravity requirements SHA-256: `f34ad3ea85ebb0e1127fa9d36bcf558517c3d09a209dff856f8d2a46fceedd0e`.
- SimPEG and PyMatSolver were built from their pinned pure-Python source distributions; `pip check` passed for both API/test and gravity environments. The runtime verifier matched all 21 pinned installed source files.
- The registered workspace closure used these exact loaded SciPy binaries: `linsolve` `17e29fa532a795497e657a033e743fda363d366b200720220ec31a3c79c74458`, SuperLU `110fa0117a967f64ea347166a21e51123eedf283515fdc86f7adac92497a5bef`, and `flapack` `0e20d023fd23064cc73d610ebf248652dca1d6db5232fb058a0ed503824c23e1`.

## Executed validation

The isolated test command covered `tests/numerics/test_gravity_l2.py`, `tests/numerics/test_gravity_l2_metric.py`, and `tests/api/test_gravity_l2_upload.py`.

- Result: **165 passed, 0 failed**, 93 deprecation warnings, in 290.05 seconds.
- Systemd runtime: 297.318 seconds; CPU time: 318.457 seconds; memory peak: 408,387,584 bytes; swap peak: 0 bytes.
- The authenticated upload test used an authored synthetic 12-by-12 station survey generated from one prism. It created the dataset, passed M02 eligibility, ran two parameter variants in the isolated CPU child, exported the result, independently replayed the prism response with Choclo, checked withheld residual metrics, and verified the original uploaded bytes.
- The separate server-only run used `DynamicUser`, read-only source, private network/temp state, a 2 GiB memory maximum, zero swap, two CPU cores, 96 tasks, and a 30-minute runtime maximum. Its uploaded-case test passed in 84.57 seconds; measured peak memory was 345.3 MiB, with no swap.

The test result and runtime receipt hashes are recorded in `runtime-pins-linux-cp312.json`. Earlier failed runs remain classified as setup/guard/test-contract findings: the Linux test had resolved the venv symlink to the base interpreter; the metric initially lacked the exact Linux binary tuple; and two tests incorrectly applied Windows-only source/platform assumptions. Each issue was corrected before the final 165-test replay.

The three named local R-006 gates (gravity preflight, uploaded gravity solve, and uploaded MT independent-oracle solve) also passed together on the current branch: 3 passed in 66.06 seconds. Raw host logs and runtime receipts are retained privately at `E:\_Datos\CAOS_Geophysics\host-admission-m02-2026-11-06`.

## Boundaries after the run

The test generated synthetic data only. It does not establish recovery of field geology, the full M02 method ladder, arbitrary survey shapes, production concurrency, full VPS capacity, public API availability, field eligibility, GPU execution, or release acceptance. The online M02 flag and production services were not enabled. The current release pointer and its two rollback releases were unchanged; the existing release ledger remains at one failed and 18 unresolved requirements.

The repository-wide SDD convergence checker still reports a stale evidence hash for `tests/api/test_gravity_l2_upload.py`: its assessed ledger revision is `7d395bed436334158d46ce3ccb5fd69265b0a352`, while this branch contains a subsequent Linux venv-path correction that was validated in this replay. The full SDD ledger has not been reassessed on this branch, so this receipt does not authorize PR merge or release promotion.
