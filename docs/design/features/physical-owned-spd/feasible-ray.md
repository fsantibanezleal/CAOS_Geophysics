# Source-owned feasible initial ray

Separate public LINEAR epoch `physical-gncg-linear-joseph-feasible-candidate-3`,
policy `closed-firstorder-joseph-feasible-native-true-residual-terminal-1`.
The existing candidate-2 contract and historical failures are not upgraded.
Export `physical_feasible_optimizer.solve_bounded_linear`, exact loaded binding,
original physical DTO, closed owned metric, native CG and terminal contracts.

For an actually successful free-face CG direction p, choose BEFORE line search
alpha0=min(1, positive (upper_i-q_i)/p_i for p_i>0 and
(lower_i-q_i)/p_i for p_i<0). Evaluate each ratio as the quotient of the exact
stored binary64 inputs (including exact subtraction), then round DOWN to binary64.
No positive representable ratio means explicit failure, not an alpha floor.
Exact-bound nonzero active directions refuse before proposal construction;
free directions must match the public native actual active set. Null direction,
invalid box/q/p, nonfinite native slope or native g dot p>=0 refuses, not retry.
If the positive quotient is above1, alpha0 remains1. No step exceeds1.
Original PG full initial-diagonal bound-release chord remains alpha0=1.

Pass alpha0*p once to the ORIGINAL installed vendor projected Armijo loop.
It still starts its multiplier at1 and halves at most20actual trials. Record
both alpha0 and actual effective alpha0*vendor multiplier; native projected
qt, physical slope, ORIGINAL certificate and strict actual merit descent retain
their original authority. This is initialization, never failed-CG/LS fallback,
curvature choice, extra trial or an assertion/tolerance/weight/cap change.
Successful native true residual must precede initialization. No private operator.
No nonlinear/quartic admission is added by this LINEAR-only epoch.

Shared accounting: ORIGINAL200CG/rtol1e-6/atol0,200accepted/201states,
20LS/120seconds/lower caller budgets and768MiB original M04 dictionary unchanged.
Ray metadata has at most200closed scalar/hash records (<512bytes/row) plus
one transient vector <=32768bytes, within the existing8MiB wrapper reserve.
No additional factor, dense H, copied CG or retained proposal matrix. Exact
Fraction temporaries have bounded binary64 exponent/significand width and are
processed coordinate-wise, not an n-sized rational ledger. This source envelope
is distinct from actual native/RSS qualification. Same clock covers ratios.

Gates: independent exact-rational breakpoint/one-ulp/tiny/active/free/zero/non-
descent/PG guards; actual native original caps/true residual/lifetime; original
independent physical objective/model/prediction/KKT controls; original full528
same-run stronger terminal and retained best failed LS; then original M04 matrix
by its owner and M02 original24/noise/refits. No PASS inferred from one chord.
