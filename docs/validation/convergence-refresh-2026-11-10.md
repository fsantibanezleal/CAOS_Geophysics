# SDD evidence refresh: 2026-11-10

This refresh binds `docs/design/convergence.json` to the current SDD and source revision after the shell/template version correction. The EARS requirements and their named gates are unchanged; this records identity and evidence-source changes, not a release acceptance.

## Evidence files reviewed

- `frontend/e2e/eligibility.spec.ts` now includes synthetic magnetic-flightline and ERT eligibility paths. Those additions have not been replayed in this refresh. Other uploaded modalities and hosted admission remain open, so R-005 remains unresolved.
- `frontend/src/api/processing-contracts.ts` adds a discriminated receipt for source-bound magnetic originals. Existing gravity, MT, profile, and waveform branches are unchanged. The existing local-only R-006 result remains bounded to its named tests; R-013 and R-014 remain unresolved because the complete modality and view matrices are still open.
- M13's committed 2026-11-05 public-directory receipt was checked against the current manifest (`3e8fac54427eeb5525c70317c508d1f55188deac3a5964ad78931561fe3c32f0`), ONNX model (`4e5962ed0a9037e545991c218ae770ae7aff2c01f1e6a919c338705780ce5f4c`), verifier (`b7c61a197d232d66aeab79cedd964c3b6bce426e5830d9ae004b55c1ee7951f6`) and gate (`eabe3f2031ad57912fea569e97f11f669616dc3225784684e32091d7105fb0e4`). The phase runtime has no later source change in this checkout. The receipt reports 23/23 QC-valid traces within `0.001`, maximum error `5.0664e-6`, zero peak displacement, and one QC-rejected trace excluded. It is same-checkpoint browser/CPU parity, not independent model accuracy.

The current changes do not alter the existing R-019 verdict: method quality, the separate independent-model comparison, owner acceptance and full product/release acceptance remain open. The extra native-ONNX comparison attempted during this review was stopped before completion and generated no receipt; it is not part of the evidence ledger.

## Verification boundary

The current SDD hash and source revision are recorded in the ledger. The existing requirement verdicts are preserved. A structural ledger pass only verifies that the source, evidence hashes and declared gates agree; it does not upgrade any scientific, host, manuscript, or product acceptance verdict.
