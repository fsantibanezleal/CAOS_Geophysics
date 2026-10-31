# M11 nonzero synthetic case replay and instrument validation, 2026-10-31

## Correction to the earlier audit

The earlier audit incorrectly compared two different digest fields: the digest
of the compiled development model (`problem.development_sha256`) and the intake
receipt's `input_bindings.development_sha256`. They do not identify the same
object. The reported mismatch between `56d8...` and `99d0...` was therefore not
evidence that the solver output used different input bytes. The earlier
conclusion that this case was mismatched is withdrawn.

The older retained output still fails the current calibration replay with
`calibration: reviewed source/allocation drift`. I regenerated the output with
the current pinned pipeline from the exact retained case inputs. The current
workflow's intake identity is
`99d074fcaf4ee6185ff52aeab318e9fc280176ced7877a3c3ca32b76a7a142a5`, matching
the retained workflow identity for those same inputs.

## Current-source case result

The selected external case is `joint-control-00`, declared `co_structural /
dense`. Its intake-matrix manifest SHA-256 is
`946ca7904d5d9d063d0c3f57e1e78ffeb96453f04e4e9f25ff14601a746c659d`. Both
modalities contain nonzero observations. The solve, independent workflow
validator, instrument export, and separate instrument validator all completed
on the same copied, hash-checked inputs and current source.

| Measure | Gravity | Magnetics |
|---|---:|---:|
| Training samples | 16 | 16 |
| Training RMSE | 0.004540 mGal | 0.855767 nT |
| Validation samples | 16 | 16 |
| Validation RMSE | 0.004063 mGal | 1.312575 nT |
| Sealed samples | 16 | 16 |
| Sealed RMSE | 0.006474 mGal | 0.766111 nT |

The calibration contains 26 candidate fits: 22 converged, 4 nonconverged, and
0 failed. Nine positive-coupling candidates were eligible under the local
selection rule. The selected stage is 24 with gravity beta 100, magnetic beta
1000, and coupling 10. The nonconverged attempts remain in the ledger.

The workflow receipt says `inverse_completed=true`, while the result's
independent claims retain `inverse_completed=false`, `recovery_verified=false`,
`field_eligible=false`, and `rights_verified=false`. The source diagnostics
also deny verified source bytes and correction science. The instrument receipt
records `refit=false`, `scientific_acceptance_verified=false`, and
`public_activation=false`. Thus this is a reproducible nonzero synthetic
workflow and an artifact-parity result, not field-data acceptance or a claim
that M11 is scientifically accepted.

The separate top-level control in the retained run has exactly zero gravity
and magnetic observations and zero residuals. It is excluded from substantive
case evidence; a completed command on that zero-signal control is not a useful
recovery demonstration.

## Executable evidence

- `scripts/run_joint_survey.py solve` completed on the selected nonzero case;
  the receipt binds the exact intake, current frozen model and calibration.
- `scripts/run_joint_survey.py validate` returned `validated=true` and verified
  the physical model and exported result. It retained `field_eligible=false`.
- `scripts/export_joint_survey_instrument.py export` and `validate` both
  returned `validated=true`; the instrument manifest SHA-256 is
  `540fce1b801740bf9c8808d4221867b58f7c114a757dddb923bca7c6b21cfb08`.
- Frontend `joint-input.test.ts` plus `joint-custody.test.ts`, configured with
  the retained intake, Python custody receipt and current nonzero instrument,
  passed 51 tests with 0 failures.
- The full frontend suite with the retained joint inputs, current nonzero
  instrument, output matrix and maximum-resource fixture reported 427 passed
  and 12 skipped. The two remaining suites fail during setup because the exact
  retained M04 selected-final extraction and owned-custody browser controls are
  absent. No frontend assertion failed in this configured run. The default
  unconfigured run reports 380 passed, 23 skipped and 36 fixture failures.
- The full numerical release harness separately lacks retained M01 custody
  packets, a profile receipt and the exact M11 native database.

All generated inputs, outputs, arrays, and scratch remain in the configured
external data root. No output was edited to force replay, and no scientific
acceptance or public activation flag was raised. M11, full product acceptance,
and deployment remain open.
