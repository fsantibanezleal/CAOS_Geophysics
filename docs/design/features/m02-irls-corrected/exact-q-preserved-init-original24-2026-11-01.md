# Exact-q replay with preserved corrected initialization: original24 matrix

**Status: source-bound 24-cell matrix passed; noise/refit, repeated resource,
and independent review gates remain open.**

## Run identity and receipt

- Runtime: `m02-survey-irls-cpu-2-terminal-certificate-exact-q-replay-legacy-init-1`.
- Policy: `safeguarded-irls-interior-threepair-log17-terminal-certificate-exact-q-replay-legacy-init-1`.
- Tests: archive identity/resume plus all 24 frozen family/condition cells.
- JUnit: `E:\_Datos\CAOS_Geophysics\validation\m02-irls-terminal-cert-20261031\corrected-preserved-init-original24.xml`.
- JUnit SHA-256: `1330AE5EA195835594B368306087B4CC76E379516737D149971A1B1DA8C9B242`.
- Result: 25 tests; 0 failures, 0 errors, 0 skips; 18,568.264 s (5 h 9 min 28 s).
- One calibration archive was resumed, the already verified family 2 / condition 2 receipt. The other 23 were generated under this exact source/runtime identity. Every selected calibration was independently evaluated and archived with its exact observation/noise/calibration identity.

## Scientific outcomes

All 24 calibrations selected a candidate and passed the matrix's archive,
resource, and independent replay/evaluation assertions. WRMS ranges by frozen
condition were:

| Condition | Cases | Outer WRMS range | Interpretation |
|---|---:|---:|---|
| 0 | 6 | 0.9684–1.2212 | Nominal controls accepted |
| 1 | 6 | 0.8994–1.1989 | Nominal controls accepted |
| 2 | 6 | 0.8133–1.2788 | Nominal controls accepted |
| 3 | 6 | 2.5965–2.9621 | Seeded nuisance controls remain poor under declared noise |

The 18 nominal cases have WRMS below 1.5. The six condition-3 controls are
intentionally retained as negative/noise diagnostics; their elevated WRMS is a
scientific limitation, not evidence that those nuisance cases fit the declared
noise model. Do not describe all 24 as equally successful fits. The matrix
asserts positive scientific thresholds on the four predeclared family 0/1,
condition 0/1 positives; other cells retain their observed metrics without
loosening thresholds.

Truth-relative model RMSE is undefined for all four family-4 cells because the
locked family-4 case has no truth prism. It remains null rather than being
invented or scored against a nonexistent model.

The maximum calibration duration was 931.360 s and the slowest individual fit
took 118.375 s, below the current 1,800 s calibration and 120 s fit caps.
These observed maxima do not replace the separately required 20-repeat
nominal/cap-bound resource gate.

## Decision

## Fixed-recipe noise-refit control

Using the selected family 0 / condition 0 calibration, 32 independent
PCG64-seeded development-only noise refits were computed. All 32 converged:
2 by the ordinary fixed-point rule and 30 by the approved exact terminal
certificate. Their 17,637,926-byte archive was replay-verified against the
frozen request and calibration.

- Calibration SHA-256: `107675e76f13c31b03a695ed58592c13c8cd381b58058b076d17e02583cbde4d`.
- Refit result SHA-256: `81822ec26eba61b7efe0bff3c5957fd50715e9c49339e6aec2fd39736928f5d4`.
- Archive SHA-256: `0F874A1474F84423A5826814251B77E62F2C6EC1071974C5B40971A7067521D3`.
- Verification receipt: `E:\_Datos\CAOS_Geophysics\validation\m02-irls-terminal-cert-20261031\corrected-noise-refits-family0-condition0-validation.report.json`.
- Source-bound archive: `E:\_Datos\CAOS_Geophysics\validation\m02-irls-terminal-cert-20261031\data\corrected-noise-refits-family0-condition0.gza`.

The first CLI attempt computed the same fits but failed before saving because
the validator charged the refit result together with its separately validated
request and calibration, double-counting input arrays against the 256 MiB
limit. The validator now charges the serialized refit result and independently
validates the frozen request/calibration through `_frozen`; no size limit was
raised. The existing 32-fit archive was then replayed successfully, so no
second fit batch was run. This is one nominal noise-refit control, not posterior
sampling, uncertainty coverage, or field acceptance.

The source-bound original24 matrix and this 32-refit control are complete for
this runtime. The 20-repeat nominal/cap-bound resource controls and independent
review remain required. Product-wide acceptance and VPS deployment remain
gated on those and the other open product checks.
