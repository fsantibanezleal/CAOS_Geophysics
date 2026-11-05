# Original24 IRLS first case, current source, 2026-10-31

## Exact outcome

The current-source family 0, condition 0 calibration is a **failure** of the
frozen gate, not a passing solver or a completed matrix. It consumed
`1800.422` seconds against the 1800 second total limit. None of the eight beta
candidates was eligible, so no final refit or outer evaluation was produced.
Across the 24 fold attempts, one converged, four reached the 200-iteration cap,
and nineteen reached `wall_cap`. Eleven fit records exceeded the strict
120-second per-fit replay ceiling, with observed durations from `120.031` to
`120.047` seconds. Independent archive replay therefore rejected the
allocation/time/phase ledger. No limits or candidate rules were relaxed.

The other 23 family/condition pairs were not run. The complete original24 IRLS
matrix, held-out efficacy, field-data eligibility, independent review and M02
acceptance remain open.

## Source-bound evidence

- Product revision at run start: `f0ec2fc37fdae1f0c1c7d40b6cae386a85d7e6ac`.
- Test: `tests/numerics/test_gravity_irls_original_matrix.py::test_original24_source_correct_science[0-0]`.
- Runtime: CPython 3.12.10, Windows, `.venv-pipeline`; BLAS/OpenMP threads set to 1.
- Exact request SHA-256: `21df6770b31fcc94b67025a202cc589e0df4412f156f41bf4b8db1f4bd9b2cc6`.
- Result SHA-256: `bd9f23a759bcff35a1c3af68ff9abfe0f3e68fb8aa792ecda50909c55a5f4a99`.
- Complete embedded source-inventory SHA-256: `538c7b4d54b4334796e73d9237ab10433c19fbdf9c33d6be335f818f83e526be`; the inventory was compared with the current `cpu3` source set and matched.
- Archive SHA-256: `8b002030c1c3653c1fdfcfd5b49f61dd35d1da59cb19ab7f0ab05b42f89fc2ab` (41,053,054 bytes).
- Pytest JUnit SHA-256: `3895fd186a91c7931eb179770e78fad2bbf1b692aa5d9608ac0829a51030fb1e` (one test, one failure, zero errors/skips; 2,052.104 seconds including archive replay).
- External archive: `E:\_Datos\CAOS_Geophysics\validation\m02-original24-irls-20261031\archives\family0-condition0-0e048c4bf4fefe36.gza`.
- External JUnit: `E:\_Datos\CAOS_Geophysics\validation\original24-current-source-case00-20261031\junit.xml`.

The archive key predates the harness's stricter complete-source key, but the
archive's embedded request, result hash and complete source inventory were
verified. The harness now searches preserved family/condition archives and
reuses one only when its embedded request, runtime epoch and full source
inventory match; a fast regression test covers those exact-match rules. This
avoids repeating the 30-minute calibration when only the cache filename rule
changes. The scientific failure remains visible and unchanged.
