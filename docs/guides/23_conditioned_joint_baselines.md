# Original compiled joint baseline conditioning

This source-bound scientific validation lane does not replace the [full local
workflow](22_local_joint_survey.md), the historical nonlinear source or earlier
precision receipts. Public dependency c184e3cadcd94a94f46b129009bfc7b6810d115b
and five exact file pins in joint_survey_conditioned.PINS are required. No
online worker, browser fit, coupled quartic or field acceptance is implied.

## Literal original potential and sufficient error units

The compiler freezes A=whiten(Js),d=whiten(observed),R and normalized property
reference q0. The unchanged original evaluations are

\[
F(q)=\tfrac12\|Aq-d\|_2^2+\tfrac\beta2\|R(q-q_0)\|_2^2,\quad
g=A^T(Aq-d)+\beta R^TR(q-q_0),\quad Hv=A^TAv+\beta R^TRv.
\]

The closed public quadratic DTO uses actual frozen A,d with identity W, not
an alternate unwhitened product that changes floating coefficients. Stored
positive smallness and signed neighbor rows reconstruct R exactly, with no
volume/length/beta coefficient recalculation. Joseph conditioning changes only
the metric; the installed native CG still applies original H/g. Every chord
uses the public literal1/2 normalized nested-factor34/50/80-digit certificate,
strict negative native slope and outward upper Armijo margin below zero.
No private helper, supplied pass boolean, copied CG or oracle optimum is used.

Original diagonal smallness supplies directed curvature lower bound mu>0.
For exact-bound normal-cone residual r, the public source computes sufficient
bounds ||q-q*||<=||r||/mu, objective gap<=||r||²/(2mu), and physical prediction
error<=max-row-norm(Js)||r||/mu. Full source geometry supplies prediction rows;
no held-out observations or truth tune the fit. Absolute model1e-5/gap1e-10/
prediction1e-8 are conservative, not replacements for independent original
relative-objective1e-8/model1e-5/prediction1e-8/exact-KKT1e-5 and near-optimum
atol1e-10/rtol1e-9 gates. No global convexity is inferred for quartic coupling.

Linear accepted200/CG200/LS20/120s and lower caller deadline remain binding.
NonlinearCG512 is a different recipe. Allocation conservatively charges the
entire existing joint problem plus public metric phase maximum under unchanged
2GiB ceiling. Public actual native closure and single-thread checks must pass.

## Exclusive original24/384 validation

Integrate/install the exact public product dependencies before importing this
adapter. The validation harness can explicitly select a committed read-only
dependency checkout with GEOPHYSICS_M11_PUBLIC_DEPENDENCY; survey inputs cannot
supply an import/factory. Configure data/scratch roots externally and set
OPENBLAS_NUM_THREADS, OMP_NUM_THREADS and MKL_NUM_THREADS to1.

```powershell
python -B scripts/validate_joint_conditioned_baselines.py `
  --data-root $env:GEOPHYSICS_LOCAL_DATA_ROOT `
  --output-root $env:GEOPHYSICS_JOINT_CONDITIONED_OUTPUT `
  --scratch-root $env:GEOPHYSICS_JOINT_CONDITIONED_SCRATCH
```

The exclusive source-frozen matrix performs384 actual fits on24 original cases.
Independent test-only exact-face optima are never passed to production fitting.
Every fit preserves full trace arrays, actual conditioning/terminal diagnostics,
all scalar line-search trials, failed trial and original comparison values.
Exit1 denotes unaccepted scientific comparisons, not crash-free acceptance.
Historical matrices stay unchanged. Full26-fit/freeze/selection/archive/client
integration needs its own reviewed source epoch and coupled graph contract.
