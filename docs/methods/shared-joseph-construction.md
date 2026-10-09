# Closed Joseph constructors and original source phases

The default `JosephMetric` and `OwnedMetric` use the original natural IC0
factor. `CompleteFirstOrderJosephMetric` and `OwnedCompletePriorMetric` are
separate literal constructors for a complete natural sparse LDLT of the
source first-order prior. There is no caller factor or policy selector.

For stored unit-lower L, positive D, finite B and F, the stored-real action is

    P = (I - F B) L^-T D^-1 L^-1 (I - B^T F^T) + F F^T.

This symmetric positive-definite metric does not replace the native physical
Hessian. Actual CG must still satisfy its original true physical-action
residual. Complete factorization retains every nonzero natural fill entry,
refuses nonpositive/nonfinite pivots and has no shift, retry or dense-H fallback.
The free face is a principal prior matrix; vectors retain the full native
parameter ABI and are restricted/embedded only by the owning constructor.

The complete constructors add `128*a*a + 128*a + 65536` bytes to the existing
prospective live-phase dictionary before factor construction. Default IC0
constructors retain the old dictionary exactly. The complete reserve is not
deducted from another phase or obtained from measured RSS. Unknown class,
storage, source/build identity or expired deadline refuses construction.
Each owner disposes its factors on close or failed construction.

Original source-phase quadratic operands have a separate responsibility:
source-bound nested H/g/chord/terminal arithmetic and disjoint factory versus
certificate lifetimes. Their allocation epoch and phase formulas are
unchanged by adding the complete constructor. Both sensitivity/prediction
occurrences remain charged even when aliased. No new constructor automatically
selects complete-prior arithmetic for the default magnetic optimizer.

Independent rational LDLT/fill controls, stored-action SPD/principal controls,
real object-size bounds, source/lifetime negatives and original-noise native
precision tests verify these distinct responsibilities. Passing construction
does not accept an IRLS recurrence, full scientific matrix, nonlinear global
optimum, uploaded arbitrary operator or native deployment.

The native triangular and Cholesky actions use the examined SciPy build;
see the [SciPy triangular solve API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.spsolve_triangular.html)
and [Cholesky solve API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.cho_solve.html).
These APIs describe the native operations, not this product's resource proof.
