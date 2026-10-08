# Full original development-refit prerequisite

## Requirement

R-484 BEFORE a downstream original S2 matrix or scientific abort controller is
eligible, THE prospective source SHALL pass the full unchanged S2-A development
refit: 216 original development rows, 648 ENU likelihood components, 528 active
cells and all eight sparse thresholds. THE gate SHALL enforce the original
120-second fit clock, 200 total accepted steps, 200 native CG per direction,
20 line-search trials and 805306368-byte source allocation envelope. Independent
Choclo/BVLS final-surrogate model/prediction thresholds1e-6, relative objective
1e-8 and independently refreshed true-p1 normalized KKT1e-7 remain unchanged.
Gate: source-bound full final-fit and independent precision record, published
only after all original predicates pass. A432-component firstfold record is
not a648-component final-refit record.

## Design and tasks

Reuse the actual supplied full_request generator, production allocation and
fit_partition, and existing independent final_precision observer. Selection is
not exercised or claimed by this prerequisite: the frozen first beta/sparse
control is used unchanged. Never read outer observations or evaluator truth.
Record failure before physical-kernel construction if allocation refuses;
otherwise preserve actual fit traces/status/deadline and original audit results.
Stop the fit clock before the independent observer, as in the original firstfit
gate. Only complete passed science and source identity produce the closed
magnetic-original-final-fit-qualification-1 record consumed by the abort gate.
No source-private optimizer, native cap expansion, fallback, data thinning,
independent tolerance change or nonlinear/field admission is introduced.

1. Supply the full final216-row original prerequisite and truthful failure record.
2. Bind complete loaded sources, request/original bytes, caps and independent
   precision to the qualifier only after all checks pass.
3. Keep execution behind changed public allocation and shared timed-lane gates;
   do not retry the known failed unchanged648 allocation as a numerical fit.
