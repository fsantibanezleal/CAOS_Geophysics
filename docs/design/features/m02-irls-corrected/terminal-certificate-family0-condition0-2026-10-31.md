# CPU2 terminal-certificate family 0 / condition 0

Date: 2026-10-31. This is a successful frozen synthetic positive control for
the terminal-certificate source epoch. It does not establish full M02, product,
field, native-platform, host, or release acceptance.

## Reproduction and custody

- Gate: `tests/numerics/test_gravity_irls_corrected_matrix.py::test_original24_corrected_science[0-0]`.
- Request SHA-256: `e21bc4f1bb9c5b0830a913909f19252c0ce0a2ed098da43c4a8a657d1915a81c`.
- Result SHA-256: `68aa969792d4e5791ee3e6ac2c62a3194ef436b8a5d158f9dc698d57e72c5385`.
- Source-inventory SHA-256: `a78d9f74e0f29d62e068f5cb50e6d38f99b867256c756126ca8821fc316d458f`.
- Calibration archive: `E:\_Datos\CAOS_Geophysics\validation\m02-irls-terminal-cert-20261031\data\corrected-family0-condition0-012ace4591e77b90.gza`.
- Calibration archive SHA-256: `ac0e348afe70b78052b1dd318bd9eff94b9c3a97e8c7113dd52277aef6a1dc00`.
- Outer evaluation archive: `E:\_Datos\CAOS_Geophysics\validation\m02-irls-terminal-cert-20261031\data\corrected-outer-family0-condition0.gza`.
- Outer archive SHA-256: `859d94c9c35fb60d111e09b0597cbfec235fb9a5673a6730673def37ba12ad99`.
- JUnit: `E:\_Datos\CAOS_Geophysics\validation\m02-irls-terminal-cert-20261031\corrected-original24-0-0-reserved.xml`.
- JUnit SHA-256: `b8a1d5269359b7b0d2e91611fa5ddfd4f680fc11386cf9002d5fb68b4e533d4a`.
- BLAS, OpenMP and MKL thread limits: one each.

## Result

The source-bound 8-beta by 3-fold calibration selected beta index 5 and
completed its development refit. Calibration wall time was 1,234.063 s; the
maximum fit time was 118.25 s, below the unchanged 120 s cap. Eleven fits used
the additive terminal certificate; ordinary three-transition successes kept
their original terminal path. Archive replay, all candidate/fold and iteration
checks, independent Choclo forward comparison, and outer evaluation passed.

The held-out outer WRMS is 1.221 mGal-equivalent under the declared noise, with
prediction quality `within_declared_noise`. The selected model's synthetic
truth RMSE ratio is 0.7829. The complete test gate, including archive replay
and outer evaluation, took 1,782.75 s. The earlier same-source receipt without
the workflow finalization reserve remains separately documented as a per-fit
resource failure and is not reused.

This closes only the family-0 / condition-0 positive gate for this source
epoch. The other 23 family/condition cells and the corrected noise/refit and
repeat-resource gates remain open.
