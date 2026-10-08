# Original IR-C06 positive regression: prescribed recurrence incompatibility

The original nonnull positive assertion remains unchanged and FAIL. This is
not an expected-negative replacement, an IRLS acceptance waiver or a new
algorithm. Its fixed beta, scientific weights, 1e-6 criteria, log17/floor3
schedule, 21 stages, shared200 accepted steps and120s fit budget remain literal.

## Actual cause, not merely stage replay

The original12-cell, four-observation full-covariance fixture has zero reference,
bounds[-1.5,1.5]g/cc and beta_engine0.04. All21 native fixed-stage solves converge;
initialization plus stages consume37 accepted steps. Nevertheless, reaching the
epsilon floor at stage17 leaves a nonstationary weight/model recurrence. The
log17 correction made the floor attainable within20 updates; it did not prove
that the following three transitions would satisfy the fixed-point criterion.

For the admitted native `SparseSmallness` p1/scaled policy and nonzero q, put
M=max_i|q_i| and S=sqrt(M^2+epsilon^2). The actual weights are
w_i(q)=S/sqrt(q_i^2+epsilon^2). Directional p2 weights are1. The null special
case has S=1, not epsilon; it must not be silently substituted. This formula
is derived from the pinned [SimPEG0.25.2 implementation](https://github.com/simpeg/simpeg/blob/v0.25.2/simpeg/regularization/sparse.py).

For this zero-reference fixture, let A=W_d G and d=W_d d_obs. Let B_j be the
three sqrt(beta_engine*alpha_j)-weighted physical directional operators, and
v_i=beta_engine*alpha_s*(W_s[ii])^2>0. The independently prescribed recurrence is

    H0 = A.T A + sum_j B_j.T B_j
    H(q_previous,epsilon) = H0 + diag(v_i*w_i(q_previous,epsilon))
    q_next = solve(H, A.T d).

H is positive definite because its smallness diagonal is strictly positive.
Every independently solved q is strictly interior, so each stage has a unique
box-constrained optimum. The observed failure is not bound identification,
CG exhaustion, Armijo rejection, accumulated accepted-step limits or inaccurate
inner minimization. Making a converged inner solve more accurate cannot make
these unique prescribed optima stationary after the same finite schedule.

The full21-stage recurrence was independently evaluated at80 and120 decimal
working precision from exact conversions of the original binary64 input
factors. Their maximum q difference is3.72e-80. No stage beyond20 was evaluated.
The three required final transitions are:

| Stage | Independent model-relative change | Independent weight-relative change |
| --- | --- | --- |
| 18 | 0.0008239546123292975 | 0.1172179746466864 |
| 19 | 0.0006722197547386627 | 0.03483941457123901 |
| 20 | 0.0005556138353996440 | 0.008718461872879723 |

Both columns must be<=1e-6 at all three stages. Model displacements exceed the
threshold by556..824 times, and weight displacements by8718..117218 times.
At those stages the native/independent recurrence q discrepancies are<=2.05e-15.
Separate high-precision solves of each actual frozen binary64 stage operator
agree with native q within9.91e-13 over all21 stages and1.82e-15 over18..20.
The residual/lower-eigenvalue estimate
||q_native-q_optimum||_2 <= sqrt(12)*||H q_native-A.T d||_inf/min_i(v_i*w_i)
is at most1.25e-11 at18..20, still far below the required model displacements.
The independent trajectory has minimum interior margin>0.555g/cc and minimum
smallness eigenvalue lower bound>0.0012. These are high-precision numerical
checks, not directed-rounding interval certificates.

The actual scaled policy also changes S(q), and therefore the effective
smallness coefficient beta_engine*S(q), even when beta_engine stays fixed.
An unscaled fixed-beta smoothed-L1 majorization argument cannot be imported
without accounting for that factor. No global L1 optimum is claimed. The
analytic local recurrence Jacobians on the three existing floor transitions
have spectral radii approximately0.80561,0.81820,0.82876; the max branch is unique.
These explain continued local movement but are diagnostics, not a global
convergence or finite-iteration bound, nor authority for extra updates.

## Reproduction and unchanged gate

`tests/numerics/test_gravity_irls_recurrence.py` independently derives the
positive normal equations and recursively solves exactly21 stages, checks
native states/weights/recorded changes against them, checks interior/positive
Hessians, and checks the weight Jacobian against actual native finite
differences. It uses NumPy only and adds no product runtime dependency or
production fallback. Passing these diagnostics establishes stage accuracy,
not convergence of IR-C06. The original gate is still
`test_gravity_irls.py::test_IR_C06_nonnull_actual_fixed_floor_stages_shared_budget_no_step_fabrication`.

Research-only80/120-digit source, complete inputs/states/residuals/source hashes
and original pytest XML are retained privately with receipt bytes on an
external device root. Initial diagnostic-script indexing assertions are also
recorded: zero-alpha second-order WLS terms must be filtered rather than
mistaken for the four positive scientific terms. No production change was
needed for that research-only indexing mistake.

Conclusion: the positive expectation is mathematically inapplicable to this
particular prescribed finite recurrence, although its assertion intentionally
continues to fail. No same-policy optimizer fix is supported by the independent
evidence. A different continuation/outer algorithm would be a separately
reviewed scientific policy, not a permissible tolerance/budget/weight edit here.
Non-null IRLS acceptance and full M02 scientific acceptance remain open.
