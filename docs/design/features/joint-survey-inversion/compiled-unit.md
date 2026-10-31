# Reusable development objective, before fitting integration

`compile_joint_development(request)` accepts exactly schema
`joint-survey-compile-request-1`, survey_request and development. It performs the
same complete preallocation/native/data/uncertainty admission as the existing
objective unit, then builds the actual public physical Jacobians once. It returns
a trusted in-process object, never a serialized callback or an upload engine.
No file, environment or network lookup occurs; no sealed observations are read.

`state(q, weights)` takes a native float64 normalized two-property vector and the
same frozen beta/lambda dictionary. It returns the actual five terms, F, normalized
gradient and a PSD-search LinearOperator. The exact Hessian is available separately
through `hessian(q,weights,exact=True)`. Physical predictions remain J times the
physical property, with declared partition IDs and units. All bounds remain exact.
The two independent single-property objective adapters will use this same admitted
problem, not independently reconstructed or altered inputs.

The volume smallness and physical active-neighbor differences are assembled as
a sparse rectangular R. No dense combined Hessian or inverse is formed. W uses
the original diagonal SD or separate training covariance Cholesky; validation
observations never enter F/g/H. Real pinned SimPEG CrossGradient objects use
exact and approximate Hessians separately, with Lc^4/V. Solver source/certificate
integration remains subject to the existing shared public seam applicability.

Gate: tests/numerics/test_joint_survey_compiled.py::test_actual_objective_equivalence
checks the existing public evaluation, exact and PSD Hv, physical units and
independent sparse R on nonuniform inactive-hole controls. Gate:
tests/numerics/test_joint_survey_compiled.py::test_no_sealed_and_train_only
checks mutation/custody and rejects callback, truth and sealed keys. Gate:
tests/numerics/test_joint_survey_compiled.py::test_kernel_once
checks actual public forward calls happen once at construction and do not recur
in objective evaluations. This is scientific computation, not solver acceptance.
