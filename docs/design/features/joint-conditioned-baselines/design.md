# Literal compiled quadratic adapter

Reviewed public source c184e3cadcd94a94f46b129009bfc7b6810d115b; M02 directly
confirmed original compiled-factor applicability. M11 source freezes
A=whiten(J_train*s),d=whiten(observed_train). Its literal original potential is
F=.5||Aq-d||²+.5 beta||R(q-reference)||². Therefore QuadraticOperands uses
g=ACTUAL frozen A,w=identity,dobs=ACTUAL d,likelihood_scale=.5. An alternate
unwhitened nested G/noise product would change floating coefficients and is
not substituted. Original scientific H/g continue to use the same A and R.
Full original J*s supplies the physical-unit prediction-row bound, not fit-only
rows, duplicated rows or a change to sealed selection.

R's first n rows are exact positive diagonal smallness. QuadraticTerm alpha=.5,
W=that stored diagonal,D=identity. Remaining rows contain exact opposite signed
coefficients, one nearest neighbor in one mesh axis; preserve their stored
absolute weight and signed incidence, split into at most three axis terms.
Each factor reconstructs the exact original CSR entry, with no sqrt/beta/volume
recalculation. Natural active ordering gives at most three earlier/later neighbors
and beta R^T R is an exact symmetric positive-diagonal/nonpositive-offdiagonal
first-order7n graph. The public metric validates actual storage/graph, not prose.

The public source owns Joseph factor/action/lifetime and installed native CG.
Adapter passes actual whitened A, original total receiver-component count,
training component count and literal original covariance kind. Source budget
max(old M11 whole problem envelope, public allocation.maximum) is bound to a
new allocation digest; no observed-RSS subtraction or native tuple guessing.
Actual single-thread binary/runtime checks remain public kernel authority.

Original relative objective/model oracle thresholds use denominator>=1. Thus
absolute model1e-5 and objective gap1e-10 are conservative sufficient conditions,
not weaker replacements. Physical prediction bound1e-8 is in original mGal/nT;
normalized exact-boundKKT1e-5 is retained. The same native minimize must pass
the stronger outward terminal within200 accepted/CG200/LS20/120s and lower
caller clock. Failure retains real native trace/terminal/conditioning/chord rows.
Old nonlinear250/CG512/LS30 source and exact quartic coupling are separate.

New data-pipeline/joint_survey_conditioned.py and tests plus exclusive matrix
CLI first establish this narrowed single-property contract. They do not silently
replace solve_joint_workflow, mixed-epoch calibration/archive schema or browser
contracts. Full26-fit/freeze/selection integration requires explicit later
reviewed schema and coupled factor graph/peak proof. Old384 failures and all
historical source-frozen24 exports remain original.
