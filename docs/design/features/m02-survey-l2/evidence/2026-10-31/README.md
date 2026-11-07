# M02 locked L2 rerun, 2026-10-31

This is a local replay of the frozen 24-cell synthetic L2 control matrix. It is
not independent review, a field-data study, or M02/product scientific acceptance.
The exact JUnit payloads, per-file hashes, machine-checked summary, and source
hash manifest are beside this receipt. The run used dirty checkout
`0cf38910ff69a90bf895ea1fde417bf62c049068`; `source-hashes.json` identifies the
actual local solver/test bytes. This is not claimed as a clean commit run.

## Results

All 24 unique cells completed without a pytest failure, error, or skip. All eight
beta candidates and three calibration folds are retained per cell, and all 24
produced a selected result. The declared-noise conditions had held-out WRMS
ranges of 0.9420–1.2327 (diagonal), 0.9008–1.2203 (correlated), and
0.8184–1.2742 (masked). The six condition-3 cases contain the declared unmodelled
nuisance and all were flagged poor under the declared noise: WRMS 2.6126–2.9572.
They are preserved as negative controls, not solver successes.

The matrix's predeclared nominal quality assertions are limited to families 0
and 1 under conditions 0 and 1. Their outer WRMS and truth-relative model RMSE
assertions passed in the executed pytest cases. Broader per-cell outcomes are
descriptive controls; they do not add a field-quality guarantee. The validator
sets `scientific_acceptance=false` and `field_eligibility=false`.

## Replay discrepancy

An additional process replay of condition 1/family 1 used identical input and
plan hashes and returned the same selected beta and outer WRMS, but a different
calibration hash. Two fold fits stopped at the cooperative wall cap at different
iteration counts (44 vs 53; 49 vs 61), with different model hashes. The full
details are in `replay-discrepancy.json`; the extra JUnit receipt is
`09-gph-l2-replay-d-r1.xml` and is deliberately excluded from the unique-cell
summary. Since both changed fits are explicitly nonconverged wall-cap outcomes,
this demonstrates runtime-cap sensitivity in the recorded calibration trace.
It does not demonstrate different input data or a changed selected result, and
it prevents a bitwise-repeatability claim. Do not delete this replay or merge it
as an identical duplicate.

## Replay the receipt checker

From the repository root, pass the nine unique-cell JUnit files to
`scripts/validate_gravity_l2_matrix.py`; include the replay file only when
testing that the validator rejects nonidentical duplicate evidence. The
validator verifies the 24-cell set, retained candidate/fold counts, errors and
skips, and declared-noise classifications. It does not decide scientific,
field, deployment, or independent-review acceptance.

## Files

- `matrix-summary.json`: 24 unique cells; scientific and field acceptance false.
- `source-hashes.json`: source revision and exact product solver/test hashes.
- `junit-sha256.json`: hashes for the nine source reports plus the additional
  nonidentical replay report.
- `00-...xml` through `08-...xml`: the nine reports covering the full matrix.
- `09-gph-l2-replay-d-r1.xml`: additional same-input process replay.
- `replay-discrepancy.json`: exact differences for the same-input replay.
