# Source-owned reduced-space linear candidate5

Prospective closed export `physical_reduced_optimizer.solve_bounded_linear`.
Epoch `physical-gncg-linear-reduced-joseph-candidate-5`; policy
`closed-reduced-firstorder-joseph-native-true-residual-terminal-1`.
Original candidate2/3/4 failure archives and exports remain unchanged.

The native current physical gradient and exact bounds define the initial
binding mask. Native ProjectedGNCG solves the original principal free Hessian
with the closed source-owned Joseph metric. Its active-gradient add-on is
disabled before the call. Only after a successful actual true-residual check
are outward-at-exact-bound coordinates frozen for a further free solve.
No caller mask, inverse, factor, SPD approval, copied CG, failed-CG/LS fallback,
oracle, physical perturbation or independent accuracy waiver is admitted.

Each direction shares200 actual CG iterations across every refinement, at
original rtol1e-6/atol0. Each native free residual is checked using original H.
Newly frozen index deltas reconstruct all working faces from the original q/g.
Outside direction construction the native physical binding mask is restored.
Original full physical projected KKT, fixed initial normalization, objective
stability and same-run stronger terminal are not working-face acceptance.

The successful inward-feasible direction uses coordinate-wise exact stored-real
first-contact ratios, capped1 and upward-rounded once, before the native Armijo
loop. Original projection, strict actual physical certificate,20 trials,
200 accepted states plus initial state,120 seconds and lower caller budgets
remain binding. No nonlinear/quartic export or mathematical theorem is inherited.

Resource admission independently recomputes the original factory maximum. New
8MiB reserve covers transient vectors/bookkeeping. Each retained phase charges
8*a+8192 bytes, each original direction16*a for q/g, each newly frozen index8.
Before a phase, admission includes the prospective8*a index delta. Source-bound
admitted_bytes and original resource_limit_bytes cannot be exceeded. At most512
phase records under the original32768-scalar envelope; refusal is retained.
This source dictionary is not native/RSS, host, online or Linux qualification.
The old base allocation digest does not admit the new audit reserve: the trusted
adapter must bind the new dictionary and both budgets. Original output gates
remain256MiB arrays/256KiB metadata and may refuse a large audit without truncation.

PETSc BNK's inactive principal Hessian construction motivates the investigation:
https://petsc.org/main/src/tao/bound/impls/bnk/bnk.c.html . The project-specific
working-face refinement is an inference requiring original numerical tests,
not PETSc fallback/perturbation authorization or an imported complexity theorem.
R7c retained full528 states23/26 produced feasible strict-certified chords with
summed4/16 actual CG, original true residual8.52e-7/6.60e-7. These are only
direction-level research, not full-fit or matrix acceptance.
