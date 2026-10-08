# Actual low-beta Armijo failure: search scale, not a precision waiver

This is separate from the [original IRLS recurrence](irls-positive-cause.md).
The original 48-cell family0/condition0 beta0.0001 fold0 L2 initialization
returns `line_search_failed` after seven accepted steps, normalized KKT
0.9263832353736619. It is not a near-optimal successful fit. No objective,
scientific weight, tolerance, cap or original assertion is changed.

## Native search and independent verification

At the failed state both official active and binding sets are empty. Native
free-face CG gives ||p||_inf=18.87540851532522 and g dot p=-1758.617293798241.
The direction is descent before projection, but cell37 reaches its bound at
t=1.5754335131881886e-6. The inherited20-trial projected line search evaluates
1,1/2,...,2^-19; the last trial1.9073486328125e-6 is above that feasible horizon.
There is no missing twentieth evaluation or IRLS epsilon in this initialization.

Projection changes the direction asymmetrically. Trials0..2 have negative
slopes but positive objective changes. Trials3..19 have positive actual slopes
and correctly reject before certification. At trial19 the native slope is
0.015251920669189678. Independent80-digit nested-operand arithmetic gives
slope0.0152519206691896413, objective change0.0152519959667580738 and Armijo
margin0.0152504707746911549. All20 rejection signs agree. The original archived
accepted trace reproduces bitwise, with no rejected trial counted as progress.

This is a search-scale cause, not false precision rejection or authority to
bypass stationarity. More known failed matrix runs do not correct it.

## Tested prospective correction remains unsuccessful

A prospective feasible native-direction horizon is

```text
t_box = min(1, min_{p_i>0} (upper_i-q_i)/p_i,
               min_{p_i<0} (lower_i-q_i)/p_i)
```

At the actual failed state, independently analyzing clip(q+t_box*p) gives
slope-0.00277058462111363668, change-0.00277058243867769027 and Armijo
margin-0.00277030538021557890. That is a mathematical candidate, not an added
accepted native trial. Pre-search scaling would preserve objective/box/weights
and the20-trial cap, but change the reviewed search recipe. It is not the
current epoch or an allowed post-failure fallback.

A research-only fresh fit from the SAME original start tested this pre-search
scaling with the same native CG, certified Armijo, objective, tolerances and
200/20/120 caps. It returns `iteration_cap`,200 actual accepted steps,
normalized KKT0.003524136648219414 in45.36s. Simple feasible-horizon scaling alone
does NOT fix this actual fit. Both original and unsuccessful proposal are
retained, not promoted. Endpoint rounding, true free-H residual, full original
controls and negative precision cases remain required for any reviewed new recipe.

The interior12-cell IR-C06 has a different cause: all21 inner solves converge
and independent unique prescribed optima still violate the unchanged1e-6 last
three transitions. Better bound search or inner accuracy cannot repair that
particular fixed finite outer recurrence. No accepted correction is established
here; original positive assertions and scientific failures remain unchanged.
