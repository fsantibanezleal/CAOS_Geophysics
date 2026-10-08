# Public nonlinear native optimizer contract

This separate contract composes the reviewed M11 physical objective with actual
SimPEG `ProjectedGNCG`. It does not revise the gravity linear export, its directed
quadratic certificate, or any retained precision control. The face-averaged
CrossGradient quartic is nonconvex: no quadratic convergence theorem, global
minimum, exact-real acceptance or interval certificate is claimed.

Public export: `physical_nonlinear_optimizer.solve_bounded_nonlinear`.
Epoch: `physical-gncg-nonlinear-candidate-1`. Policy:
`exact-bound-native-gncg-actual-armijo-1`. Candidate means that an adapter must
independently review the source inventory and validate its entire pipeline.

`NonlinearBinding` has exactly `accepted_export`, `optimizer_source_sha256`,
`vendor_source_sha256`, `source_inventory_sha256`, `runtime_epoch`, `policy`.
The vendor digest binds the actually imported SimPEG optimization source.
`NonlinearBudget` has `deadline`, `remaining_steps`, `resource_limit_bytes`,
`admitted_bytes`, `allocation_plan_sha256`. Deadline is the original absolute
monotonic workflow deadline, never reset for a fit; it must be no more than
1800 seconds in the future. Steps are 0..250; allocation is positive, no more
than 2 GiB. These are driver declarations, not measured resource certification.

Trusted adapter methods: `identity`, `evaluate`, `components`,
`binding_diagonal`, `free_metric`, `exact_hessian`, `release_state`. No upload
callback, factory, retry or caller-selected solver is accepted. Identity has
the same thirteen conceptual fields as the linear seam, but mode is
`nonlinear_gauss_newton`, epoch is distinct, `physical_scale` is a positive
one/two-element tuple, `beta_engine` is exactly float 1.0, `stage_index` 0..25,
and components are one/two observation modalities. `physical_unit` explicitly
names `kg_m3`, `si`, or `kg_m3_and_si`; `q_unit` names normalized coordinates.
Components have exactly `phi_d`, `phi_m`, `phi_engine`: the first sums training
data terms and the second sums the weighted physical regularizers and coupling.
Their sum must equal actual F. M11 separately retains all five unweighted terms.

`evaluate(q, return_g, return_H)` returns actual F, optionally its exact
normalized gradient and refreshed PSD search `LinearOperator` (float64 n by n).
`exact_hessian(q)` returns a separate exact-Hv operator for independent
derivative verification, never the search matrix. Positive initial diagonal is
fixed for a fit, with no jitter or hidden floor. `free_metric(q, indices)` is
the n by n inverse diagonal restricted to exact sorted free indices, zero on
active indices. The seam checks its actual actions against that fixed policy.

Exact feasible-gradient infinity norm divided by max(1, initial total-gradient
infinity norm) <= 1e-5 is the only success predicate. Exactly lower/upper
coordinates use min(g,0)/max(g,0); there is no near-bound epsilon and no
objective-stability or absolute-gradient substitute. Any active-not-binding
coordinate selects clip(q-D0^-1 g)-q. Otherwise actual vendor free-face CG uses
refreshed PSD H, max512, rtol1e-6, atol0. Its true free-H residual is checked
before vendor disposal of H; failure has no fallback.

Actual vendor projected line search starts alpha1, halves, max30 trials. Reject
no-op, nonfinite and nonnegative actual g dot(qtrial-q). Acceptance uses the
actual float64 margin `(Ftrial-F)-1e-4*slope <= 0`. This keeps a rounded-zero
change from passing via a rounded RHS; it is not an exact-real certificate.
Before acceptance capture the actual trial gradient/metrics. Every accepted
state survives a later deadline or Hessian failure. Limits/precision failures
remain explicit failures, never successful terminal states.

Results have the linear seam's ten conceptual fields; traces additionally
retain branches, active/binding counts, CG residuals with explicit availability,
line-search alpha, actual projected slope and actual Armijo margin. Branch0 is
fixed diagonal release, branch1 native free-face CG. Unavailable CG quantities
are canonical zero with false availability, not fabricated measurements.

Gates: exact bounds (including nextafter interior), literal limits, typed/source
binding, immutable operands, identity mutation, expired deadline, accepted-state
retention, non-descent/no-op, native CG action and true residual, independent
actual SimPEG CrossGradient exact-Hv finite differences/PSD quadratic form, and
actual physical M11 integration. Integration acceptance requires M11's complete
frozen pipeline, not just this seam's unit tests.
