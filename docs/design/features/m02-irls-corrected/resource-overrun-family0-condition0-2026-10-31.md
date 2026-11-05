# CPU2 terminal-certificate family 0 / condition 0 resource result

Date: 2026-10-31. This is a source-bound calibration result that fails the
unchanged per-fit resource gate. It is not an accepted calibration, scientific
selection, or release.

## Reproduction and custody

- Gate: `tests/numerics/test_gravity_irls_corrected_matrix.py::test_original24_corrected_science[0-0]`.
- Runtime epoch: `m02-survey-irls-cpu-2-terminal-certificate-1`.
- Policy: `safeguarded-irls-interior-threepair-log17-terminal-certificate-1`.
- Request SHA-256: `e21bc4f1bb9c5b0830a913909f19252c0ce0a2ed098da43c4a8a657d1915a81c`.
- Result SHA-256: `576e4f6f9a67bbd6eddb0e7078adfc722d5a686dbc2615dff2969220e80c704f`.
- Source-inventory SHA-256: `29e7defaf7a24e9ec48eed4934a29b5b26966a5f5a085ff9b8d5e6629f775523`.
- Archive: `E:\_Datos\CAOS_Geophysics\validation\m02-irls-terminal-cert-20261031\data\corrected-family0-condition0-6a6cc455b731c70b.gza`.
- Archive SHA-256: `176678998a38710d4a91ce848456f6fd4dbe0f9be9442372aed7e2aba78e7c03`.
- JUnit: `E:\_Datos\CAOS_Geophysics\validation\m02-irls-terminal-cert-20261031\corrected-original24-0-0.xml`.
- JUnit SHA-256: `8eecb4169ec1ad8a55b58fca71905332c9df499c49a7c912f00fe39a35837a7e`.
- BLAS, OpenMP and MKL thread limits: one each.

The complete 24-fold calibration and development refit were archived and
source-replayed. Its measured aggregate calibration time was 987.563 s, under
the 1,800 s cap. The selector reported candidate index 5, but the test stopped
at the per-fit resource assertions before computing the held-out outer
evaluation. Two folds exceeded the 120 s fit wall cap: fit index 5 (beta 1,
fold 2) at 120.500 s and fit index 6 (beta 2, fold 0) at 120.031 s. The
otherwise complete calibration therefore fails this gate; the selected index
is diagnostic only.

The larger overrun occurred in a native L2 initialization whose non-interruptible
work returned after its deadline. The workflow passed the full 120 s allowance
to solver code but left no time for that work to return and serialize its
terminal receipt. The implementation now reserves two seconds inside the same
120 s fit limit for that tail. This is a conservative execution budget; it does
not change the published cap or any scientific threshold. The fresh calibration
must use the new workflow source hash and a new receipt.
