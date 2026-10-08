# Explicit first-contact composition and directed dot enclosure

This amendment precedes code. Existing source epochs, matrices and failed
receipts remain immutable. It adds an explicit local LINEAR-only composition
of the public `physical_feasible_optimizer.solve_bounded_linear` first-contact
epoch. The public owner owns the initial ray, native projected Armijo, CG and
same-run terminal policy. No private optimizer helper, copied CG, callback ray,
bound snapping, extra trial, jitter or tolerance/cap increase is permitted.

## Requirements and gates

R-C01 WHEN the operator selects the separate first-contact source, THE pipeline
SHALL bind its actual public module, export, hash, policy and linear epoch plus
the complete conditioned dependency inventory before kernel birth. Exact norm
does not acquire a nonlinear contact variant. Gate:
`tests/numerics/test_magnetic_contact_adapter.py` and
`tests/data/test_magnetic_conditioned_cli.py`.

R-C02 WHEN a fixed native coefficient multiplies an interval in a certificate
dot product, THE certificate SHALL enclose the same exact stored-real sum using
sign-selected endpoints and separately directed fused multiply-add contexts.
Gate: `tests/numerics/test_magnetic_directed_dot.py` independently enumerates
rational interval corners and compares the former multiplication/add enclosure.

R-C03 THE certificate SHALL retain original operands, precision ladder34/50/80,
range/domain/deadline refusals, caller-context isolation, strict projected slope
and Armijo sign tests. Gate: `tests/numerics/test_magnetic_inverse_precision.py`
and original independent complete-objective and nonlinear controls.

R-C04 THE full calibration SHALL retain original200 combined accepted steps,
linearCG200/20LS, nonlinearCG512/30LS, absolute120-second fit clock and768MiB
source envelope. Gate: `scripts/run_magnetic_frozen_matrix.py` actual original
288-row/528-cell receipts plus `scripts/check_magnetic_native_abort.py` actual
cap/cancel/controller-crash and retained failures. These are not host admission.

## Directed evaluation design

For exact native coefficient a and interval [l,u], multiplication is monotone:
select (l,u) for a>=0 and (u,l) for a<0. Accumulate
L'=round_floor(a*selected_lower+L),
U'=round_ceiling(a*selected_upper+U) in explicit Context.fma operations.
Induction encloses the same exact real dot product. No intermediate product is
rounded before addition; this can tighten the interval, not weaken its proof.
The coefficient still comes from Decimal.from_float of the actual stored
binary64 value. No rounded decimal coefficient, float BLAS estimate, error
heuristic or cached Decimal matrix substitutes for the original operands.

Only two scalar accumulators and one exact coefficient are live per dot.
Original native snapshots and allocation envelope do not shrink. There is no
new dense matrix/cache or persistent decimal expansion. Deadline checks remain
at each dot and are added at bounded128-term intervals inside long dots.
Failure clears partial certificate endpoints as before.

Reference: [Python3.12 Decimal and Context fused multiply-add](https://docs.python.org/3.12/library/decimal.html#decimal.Decimal.fma),
which specifies an unrounded intermediate product and explicit context methods.
Independent rational corners, not this implementation, decide enclosure tests.

## Implementation sequence and acceptance

1. Bind separate public contact identity; test rejection and physical parity.
2. Implement directed FMA dot with independent rational/cancellation/subnormal/
   mixed-sign/caller-context/expiry guards and unchanged full certificate tests.
3. Measure actual original full528 fit under the original deadline. Retain any
   failed contact or incomplete independent precision as failed, not acceptance.
4. Execute full original matrix, numerical bundle/replay/evaluation/export and
   actual native lifetime gates with fresh external roots and source hashes.

Candidate4 contact alone has already failed the owner's original full528 clock;
this design does not infer completion from source correctness or small controls.
Exact-field proof remains the original norm chain, never quadratic admission.
Authenticated API mounting, native Linux host qualification and field eligibility
remain independent gates owned by their respective implementation lanes.
