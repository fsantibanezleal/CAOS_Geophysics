# Original gravity optimizer first-fold replay, 2026-10-31

## Scope and outcome

The source-bound original gravity optimizer passed its locked family 0,
condition 0, development fold 0 comparison against an independently assembled
BVLS oracle: 1 test passed, with no failures or skips. The solver converged in
37 iterations in 7.391 seconds. Relative model error was `3.4583e-11`, physical
model relative error `1.1279e-10`, relative objective error `2.11997e-15`, and
maximum physical prediction error `7.2091e-14`.

This establishes one first-fold numerical control only. It does not establish
candidate selection, the original24 matrix, held-out outer evaluation, field
eligibility, or M02/product acceptance. The result reports the existing native
resource plan at 692,868,820 bytes and retains `full_M02_accepted=false` and
`host_accepted=false`.

## Exact run

- Product revision at run start: `f0ec2fc37fdae1f0c1c7d40b6cae386a85d7e6ac`.
- Test: `tests/numerics/test_gravity_original_optimizer.py::test_original_locked_firstfold_accuracy`.
- Engine epoch: `physical-gncg-gravity-original-reduced-joseph-candidate-7`.
- Input SHA-256: `e0876f05f9ce2450c0d00b9b3b50a1bb16a6197286b91a56fb83416db7bf77c0`.
- Solver source inventory SHA-256: `5760b733dc3df0dc92fdd808242158cf17a262058250fa292cbb25bdc9ce6e87`.
- External receipt SHA-256: `e1182e72f5becb2df0297db83d4c2c38013aa27af570fe84680612a9959da489`.
- External JUnit SHA-256: `785dd2b675aa0e30c05e64a36fa9ec720276abae71fcec2031e9a1f097643099`.
- Runtime: CPython 3.12.10, Windows, `.venv-pipeline`, BLAS/OpenMP threads set to 1.
- Receipt: `E:\_Datos\CAOS_Geophysics\validation\m02-gravity-original-firstfold-20261031\receipt.json`.

The initial batched run recorded 55 passing tests before stopping at this
first-fold test because its harness did not preflight the required external
receipt-path variable. The blocked test was then run alone with an immutable
external path and passed. The missing-path case now has a fast preflight
regression test; remaining optimizer and physical test modules are still
separate gates.
