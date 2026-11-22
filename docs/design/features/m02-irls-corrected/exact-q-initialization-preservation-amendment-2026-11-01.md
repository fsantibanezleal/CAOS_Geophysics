# Exact-q replay with legacy corrected-IRLS initialization

**Status: implementation, current-epoch 24-cell matrix, and one 32-draw
nominal noise-refit control pass; repeated resource controls and independent
review remain pending.**

## Cause found in the completed exact-q matrix

The exact-q replay matrix at
`exact-q-original24-2026-11-01.md` passed its 25-test pytest gate, but its
family 2 / condition 2 final development refit returned
`final_nonconverged / zero_free_direction` after 26 accepted steps and four
weight updates. The corresponding prior-policy family/condition archive had a
converged final refit, but it is not an exact same-request comparison because
its source/runtime identity differs.

The actual initialization arrays isolate the changed path: the exact-q matrix
used the original L2 optimizer `models_q` array as the corrected IRLS start. The
prior corrected workflow started from `models_kg_m3 / 1000`. For the decoded
family 2 / condition 2 final refit, those prefixes differed in two of 240
values, by at most `6.938893903907228e-18`. The exact trace is required to
replay the L2 solver's accepted Armijo transitions; using it as the next method's
start also changed the established corrected-IRLS solve trajectory.

## Amendment

Keep both numerical roles explicit:

1. Retain and validate the exact optimizer `models_q` trace in the L2
   initialization archive. Use it to replay the native L2 solve and its
   accepted line-search proofs.
2. Start the corrected IRLS method and compute its initial thresholds using the
   established physical-state round trip, `models_kg_m3 / 1000`, exactly as
   before the exact-q amendment.
3. Record the corrected IRLS `models_q` trajectory from those actual starts and
   require the corrected replay to reproduce that exact prefix.

No objective, data, bound, beta, threshold formula, optimizer tolerance,
stopping rule, iteration limit, retry, or resource cap changed. The policy and
runtime identity are now:

- `safeguarded-irls-interior-threepair-log17-terminal-certificate-exact-q-replay-legacy-init-1`
- `m02-survey-irls-cpu-2-terminal-certificate-exact-q-replay-legacy-init-1`

The completed 24-cell exact-q matrix remains preserved as evidence for its own
runtime. It is diagnostic for this new identity and cannot satisfy the new
source-bound matrix gate.

## Targeted evidence

- Focused exact-q trace and corrected positive-control tests: 2 passed, 0 failed,
  JUnit at
  `E:\_Datos\CAOS_Geophysics\validation\m02-irls-terminal-cert-20261031\exact-q-preserve-init-focused.xml`.
- Family 2 / condition 2 full calibration, replay and outer validation: 1 test
  passed, 0 failed/errors/skips; JUnit SHA-256
  `F7BC466BBD1E0258337523116D1FC4E402C581B07E25B5C25DA5CED6F0E2B346` at
  `E:\_Datos\CAOS_Geophysics\validation\m02-irls-terminal-cert-20261031\corrected-preserved-init-family2-condition2.xml`.
- Exact source-epoch calibration archive:
  `E:\_Datos\CAOS_Geophysics\validation\m02-irls-terminal-cert-20261031\data\corrected-family2-condition2-29ccc86815c12344.gza`.
- Exact source-epoch outer archive:
  `E:\_Datos\CAOS_Geophysics\validation\m02-irls-terminal-cert-20261031\data\corrected-outer-family2-condition2-473d915159a8-93ce1b82dbdb-43891770fc89.gza`.
- Result SHA-256: `473d915159a8a3a2a54b9163c91d7a46a7a02d18e7773f073ffb6f03101324c9`.
- Outcome: selected candidate index 7; final refit converged; calibration
  735.110 s; outer WRMS `0.895348057302513`; truth-relative model RMSE
  `0.625486952274732`.

The current runtime's full matrix and one source-bound 32-draw corrected
noise-refit control are complete. The 20-repeat nominal/cap-bound resource
gate, independent review, other methods, product-wide acceptance, and VPS
release checks remain open.

