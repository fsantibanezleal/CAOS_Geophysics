# Source-bound compiled separate-property baselines

The independent `joint_survey_compiled_baseline` adapter exposes the actual
stored training operands to the public `physical_compiled_optimizer` contract.
It does not replace the joint worker, the nonlinear coupled objective, the
original fit matrix, or the frozen selection policy. This module alone does
not qualify an online method or establish scientific acceptance.

## The original physical objective stays native

For one normalized property block, with its original fixed coefficient beta,

\[
\phi(q)=\tfrac12\lVert Aq-d\rVert_2^2+
\tfrac12\beta\lVert R(q-q_{\mathrm{ref}})\rVert_2^2.
\]

`A` and `d` are the stored principal-marginal-whitened training operands from
the joint compiler. `R` is the actual volume-normalized positive smallness and
active-neighbor first-order prior. The adapter returns those original objects,
not a reconstructed whitened likelihood, changed prior, or rounded substitute.
Evaluation, gradient, Hessian action and binding diagonal remain the original
single-property native implementations. The three scalar component keys are
the exact data, weighted prior and total values required by the linear ABI.

The canonical native identity retains all thirteen keys, `beta_engine=1.0`,
and the original one-element physical-scale tuple. The public compiler binds
the actual scientific beta and half-quadratic convention in a separate proof
identity. That proof identity never replaces the native identity or parameters.
The physical prediction source is the original unscaled full Jacobian `J`, not
`A` or a pre-rounded `J * scale`. The compiler's outward binary-operand proof
then applies the exact physical scale to its error bound.

This is a separate-property baseline. Its original coupling coefficient is
zero. A coupled model must still preserve the full physical gradient/Hessian/
potential and independently qualify its nonlinear source. Neither an SPD
prior-only metric nor a valid quadratic baseline certificate admits a quartic
cross-gradient graph, proves global optimality, or upgrades a failed fit.

## Source and resource domains

The adapter pins the complete public defining-source closure at commit
`f3022ef999b79004faa45e54c33adb3fdc9e0441`, including the original 4096-cell
full-mesh guard. Loaded and on-disk source digests must agree before use.
No caller-selected matrix factor, CG implementation, source root, terminal
witness, certificate callback, or independent SPD grant is accepted.

The public allocation plan charges both full gravity and magnetic kernels,
the original development arrays, and literal compiled A/d/model/geometry/
R-data arrays retained by the caller. Native int32/bool structural arrays are
not converted into a falsely admissible f64/i64 declaration. It adds all
coexisting original native, source-copy/endpoint, audit/mapping/history and
terminal factor/witness phases by SUM, not MAX or subtraction. The original
2 GiB RSS and 256 MiB scratch limits remain, as does one absolute 1800-second
workflow deadline. Each baseline has at most 120 seconds including construction
and proof, 200 CG steps, 200 accepted steps, 201 states and 20 line-search trials.

The120-second absolute fit clock is now constructed **before** native/public
source inventory, adapter construction and allocation binding. An internal frozen
budget view checks that same deadline before/after defining-source reads,
constructor/allocation phases and inherited native action checkpoints. It also
checks after actual global RSS/scratch sampling. The public optimizer and its
source/terminal proof receive this already-running absolute deadline; construction
and proof never receive a fresh120seconds. The original global budget's start,
deadline, sampler and measured debt remain unchanged across later fits. No caller
clock, callback proof or modified global deadline is admitted by the solve entry.
The view requires the actual finite original start/deadline pair and unchanged
1800-second duration, then retains both values immutably. A changed, narrowed,
extended or nonfinite workflow clock refuses before inventory; mutation during
actual sampling refuses before further construction/proof. It never repairs the
caller state or rewrites the original measured budget.

The adapter checks every literal native/vendor defining file directly under
this clock, preserving the complete legacy inventory identities. It does not
delegate multiple unguarded reads to the old inventory routine or inject a
checkpoint callback into it. A read crossing120s refuses before the next read;
the original scientific optimizer and framework definitions remain unchanged.

Cooperative boundary checks do not promise hard-realtime interruption inside an
individual library/file action. An action crossing the deadline is refused at
its next source-bound boundary before another allocation or the solver starts;
no expired construction can return a fit. Changed virtual-clock refusal controls
exercise inventory crossing, constructor allocation crossing, immutable clock,
no reset and expired inherited H action. They produce no passed scientific solve.

A temporary identity hash is used only to obtain the count-derived plan. The
adapter then installs its exact digest and reconstructs the model binding.
Recomputing the plan must produce the identical declaration; the placeholder
must not survive into the exported identity.

The original 64 MiB retained framework/sparse partition is an independent
compiler structural-closure obligation. A public source-control test, an
allocation dictionary, actual sampled RSS, or this adapter's byte inventory
does not by itself prove that obligation or reserve OS memory. The result
therefore does not assert retained-framework resource acceptance or scientific
acceptance. Those require independent original source-bound gates.

## Independent acceptance remains mandatory

The original exact-bound KKT and model-error limits of 1e-5, objective gap of
1e-10 and physical prediction error of 1e-8 are unchanged. Native historical
near-bound stopping logic is not a waiver of the independent exact-bound
comparison. Preserve a differing trace, precision failure or resource refusal;
do not rewrite the receipt or loosen the assertion.

Portable controls exercise literal operand identities, canonical identity/
allocation rebinding, independent binary-rational half-quadratic values and
unchanged native H/g delegation. They execute no fit and produce no synthetic
passed solve. One original case prerequisite must qualify before the dependent
full comparison matrix. Scientific replay, frozen validation selection, sealed
evaluation, coupled fits, field rights and deployed authority remain distinct.

See [local supplied joint methodology](../guides/22_local_joint_survey.md) and
[exact local inspection contract](../data-contract/04_joint-local-inspection.md).
