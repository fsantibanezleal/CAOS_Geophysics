# Closed owned SPD metric and terminal requirements

Prospective source epoch, approved after full-shape conditioning research on
2026-10-08. This packet is persisted BEFORE implementation. Historical exports,
archives, assertions and numerical limits remain unchanged. [Design](design.md),
[tasks](tasks.md). No native/Linux/host/scientific admission follows from this SDD.

SPD01 THE new public API SHALL construct its own Joseph metric from an exact
closed, source/model/allocation-bound physical operand DTO; it SHALL NOT accept
an arbitrary metric action, callback acceptance, jitter, shift or failed-factor
fallback. Gate: tests/numerics/test_physical_owned_spd.py::test_closed_operands

SPD02 THE API SHALL retain original native H/g, nested Armijo certificates and
original full initial PG diagonal, and check the true physical free residual
within the actual native CG before H disposal. Linear CG200/accepted200/LS20/120s;
nonlinear CG512/accepted250/LS30/1800s; caller remaining200/120s is binding for
M04. No finish/restart or cap/tolerance increase.
Gate: tests/numerics/test_physical_owned_spd.py::test_native_caps_and_residual

SPD03 THE API SHALL validate component counts and original resource dictionary
before factor allocation; original M04 limit805306368 bytes, source864/fit432
components/528 parameters, not216 components. Unknown first-order CSR graph,
native binary workspace or allocation overlap SHALL refuse. M11 quartic coupled
face factors are NOT automatically admitted by this epoch.
Gate: tests/numerics/test_physical_owned_spd.py::test_original_resource_dictionary

SPD04 WHEN q/free face changes, THE API SHALL dispose the previous factor before
construction and refresh the actual nonlinear Jacobian. All construction/action/
terminal time belongs to the same fit; failures retain actual accepted and failed
states and factor/residual/terminal diagnostics without rescue.
Gate: tests/numerics/test_physical_owned_spd.py::test_refresh_disposal_failure

SPD05 THE native original terminal predicate AND stronger declared exact-bound
physical KKT SHALL pass within the same minimize. Optional quadratic error
bounds SHALL be calculated by the API from ORIGINAL nested physical factors,
positive smallness and directed arithmetic, not a supplied scalar mu/boolean.
Nonlinear GN PSD SHALL NOT imply a global exact-Hessian/convexity bound.
Gate: tests/numerics/test_physical_owned_spd.py::test_terminal_bounds

SPD06 THE source epoch, DTO/resource/lifetime/terminal manifest and real test
receipts SHALL be relayed to adapters after push. All original M04 full-fit
matrix and M02 tests/refits retain their original independent scientific gates.
No full-fit accuracy PASS is inferred from the two-iteration research direction.
Gate: tests/numerics/test_physical_owned_spd.py::test_original_physical_fit

SPD07 WHEN a half-normalized linear source requires a chord proof, THE public
closed QuadraticOperands API SHALL compute actual nested physical delta/slope/
strict Armijo with literal ORIGINAL c=.5or1 and the unchanged34/50/80 ladder,
same clock/resource caps, without a private adapter helper or supplied decision.
Gate: tests/numerics/test_physical_owned_spd.py::test_public_half_certificate_fit
