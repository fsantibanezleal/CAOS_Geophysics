# Exact optimizer-state replay amendment

**Status: exact-q replay implementation and focused controls passed. Its 24-cell
matrix completed and exposed a separate initialization-path regression; the
targeted follow-up is recorded in
`exact-q-initialization-preservation-amendment-2026-11-01.md`.**

## Observed defect

The first corrected original24 batch reached family 3 / condition 0 with a
selected calibration: eight candidates, selected index 5, 709.969 seconds of
calibration, and result SHA-256
`8c026ea9433c62aa6e65a0a3ccbfadd9cb7a8ef24f760668f075260801af4373`. Its
independent outer evaluation failed while replaying an earlier native L2 fit
with `corrected replay: physical E Armijo proof`.

The diagnostic gate is retained outside the repository at
`E:\_Datos\CAOS_Geophysics\validation\m02-irls-terminal-cert-20261031\corrected-family3-condition0-diagnostic.xml`
(SHA-256 `215601a6a171a1643bc6e70b223c57ffe2ce2d4aa02c9a202fae8bb4b7d20f5d`).
The calibration archive is also retained outside Git at
`E:\_Datos\CAOS_Geophysics\validation\m02-irls-terminal-cert-20261031\data\corrected-family3-condition0-99d852931d26848a.gza`
(SHA-256 `be969ae976400c5fa4c7333895cc51da3b35da7e3860de782071436f8041b35e`).
These artifacts bind the previous `terminal-certificate-1` runtime and are
diagnostic only; neither is eligible as a receipt for the amended source.

## Numerical cause

At candidate index 2, fold 1, the original solver accepted the state transition
at iteration 4, trial 1. The exact normalized-density displacement was
`7.382983113757291e-15`. The solver's positive control recorded a 34-digit
Armijo margin interval of approximately `[-8.798591941368524e-29,
-8.798591941368518e-29]`, so the step was correctly certified as descending.

The public L2 trace retained only physical density `q * 1000` in kg/m3. Replay
reconstructed q by dividing that rounded physical state by 1000. For the same
state pair, the reconstructed Armijo margin became approximately
`[1.314577670197960e-29, 1.314577670197966e-29]`, incorrectly rejecting the
historically accepted transition. The failure is a serialization precision
defect in the replay contract; it is not a solver failure or an objective
change.

## Source change

The L2 partition solver now has an opt-in internal `preserve_exact_q` path. The
corrected CPU2 workflow stores the exact optimizer q states in its initialization
trace next to the physical kg/m3 states, validates their exact `q * 1000`
identity, and uses the exact q states for IRLS initialization, thresholds,
stage construction and Armijo replay. Ordinary L2 results keep their original
trace contract. The CPU2 policy and runtime epoch are bumped to
`safeguarded-irls-interior-threepair-log17-terminal-certificate-exact-q-1` and
`m02-survey-irls-cpu-2-terminal-certificate-exact-q-1`.

No objective, noise, candidate, split, threshold, iteration, time or stopping
rule changes. CPU1 is unchanged. Old CPU2 archives remain immutable and cannot
be reused under the new source inventory.

## Focused verification so far

- Python compilation passes for the changed pipeline and test files.
- The opt-in q trace contract test passes with BLAS/OpenMP/MKL threads fixed at
  one.
- The corrected positive and replay test passes with the same pinned-thread
  environment.
- Running the latter without those thread limits produced the expected
  `metric: reviewed single-thread native workspace required` fail-closed result;
  that invocation is an environment failure, not a scientific result.

The exact-q-1 original24 matrix completed under its source hashes; its outcomes
and the family2/condition2 nonconverged final refit are preserved in
`exact-q-original24-2026-11-01.md`. The follow-up keeps the exact L2 trace for
replay while restoring the established corrected-IRLS physical round-trip start.
Its targeted family2/condition2 rerun passed under a new source identity. The
full original24 matrix and one source-bound 32-draw corrected noise-refit
control have since passed under the preserved-initialization source identity.
The 20-repeat resource gate, other methods, whole-product acceptance and
release qualification remain open. No release or deployment follows from
those gates alone.
