# Original gravity source bridge

`gravity_original_optimizer.solve_bounded_linear` constructs the actual
ordinary SimPEG gravity problem from the original supplied request, declared
observations/noise, prior, fit rows and scientific beta. There are no objective,
metric, factor, mask, terminal-success or optimizer injection parameters. Source
and native-host admission remain controller obligations, not numerical grants.

The normalized variable is density in g/cc, with physical density1000q in
kg/m3. The independently fixed background is subtracted once into native
`data.dobs`, exactly as in the original producer. The native source sensitivity,
potential, gradient and physical Hessian actions stay unchanged:

\[
\Phi(q)=\|W(Gq-d_{engine})\|^2+
\beta_{engine}\sum_j\alpha_j\|W_jD_j(q-q_{ref})\|^2,
\quad\beta_{engine}=n_{fit}\beta_{candidate}.
\]

Diagonal SD retains source division by original supplied SD. Original full
covariance uses the principal fitting marginal and the original producer's
stored symmetric precision-root W, not Cholesky L. Its recipe is the unchanged
`eigh(driver='evd')` construction followed by symmetrization of W only; the
original covariance is never symmetrized or jittered. The source validator
reproduces that recipe and requires exact stored-root equality. Outward source
actions interpret the actual stored W entries, without silently replacing the
native objective by a differently rounded inverse or Cholesky action. The
source SD and stored-L magnetic recipe remain distinct branches.

The public owner constructs its own Joseph metric on the native reduced free
face. All original CG200, rtol1e-6, atol0, accepted200, states201, LS20, original
2GiB and absolute120s limits remain. Construction, solve, original Armijo
arithmetic and stronger terminal consume the same clock; no finish/restart.
Every successful native CG phase must satisfy its true original physical-H
residual. Failure preserves its actual states and best line-search receipt;
there is no fallback, oracle or cap/tolerance/weight adjustment.

The owned source terminal streams the original principal Hessian columns and
stored Joseph actions. A strict contraction \(\|I-MH_{FF}\|_\infty<1\), exact
active-sign preservation and strictly interior free error intervals bound the
unique original box optimum. Positive scientific smallness supplies curvature,
not a claim about nonlinear Gauss-Newton. Additional normalized KKT1e-7,
model error2 in q<=1e-8, gap<=1e-8, and physical prediction sup<=1e-6 gates are
sufficient requirements, not replacements for unchanged independent tests.

Exactly zero outward source feasible gradient has the separate direct strongly
convex KKT proof: q is already the unique box optimum. Record proof_basis
`exact_source_feasible_kkt` and unavailable kappa/eta, not fabricated contraction
values. Original operand/native/source KKT, active/free and positive-mu checks
still apply. Nonzero source gradients retain `free_face_neumann` unchanged;
no nearzero test, callback approval or failed-solver fallback is introduced.

Resource receipts distinguish the original native phase dictionary, source
snapshots/endpoints/sparse-transpose phases, free factors/endpoints/workspace
and actual retained native traces/audits. Before construction and use each must
fit the original declared2GiB. The original cap is not extra memory and the
dictionary is not measured RSS, native allocator or host containment approval.

This bridge is prospective provenance only. It does not mutate old L2/plain
IRLS/cpu2 archive policies or their actual failures. The original corrected
IRLS recurrence, full24/noise/refits, API/UI and deployment gates remain separate
until their actual source-correct prerequisites and complete workflows pass.
There is no M11 compiled identity-W, quartic or nonlinear admission here.
