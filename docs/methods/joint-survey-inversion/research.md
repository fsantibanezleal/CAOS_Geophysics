# Primary research and source applicability

Verified on2026-10-04. Document/source inspection is not execution evidence.

## Verified primary sources

1. [SimPEG0.25.2 joint tutorial](https://docs.simpeg.xyz/v0.25.2/content/user-guide/tutorials/13-joint_inversion/plot_inv_3_cross_gradient_pf.html)
   was read for survey creation, data errors, Wires, separate regularizers,
   coupling, optimizer and directives. It supplies a real joint recipe but uses
   synthetic data, anomaly-relative errors and a preset coupling weight. Its
   printed run ends at the iteration cap; neither that stop nor tutorial plots
   establishes convergence. We do not inherit these settings as survey admission,
   uncertainty estimates, independent baseline or field acceptance.
2. [CrossGradient API0.25.2](https://docs.simpeg.xyz/v0.25.2/content/api/generated/simpeg.regularization.CrossGradient.html)
   and [versioned implementation](https://github.com/simpeg/simpeg/blob/v0.25.2/simpeg/regularization/cross_gradient.py)
   were checked against the full actually installed class source. Its optimized
   scalar uses averaged squared/product face gradients; its diagnostic averages
   vector gradients first. Exact and PSD-approximate Hessian branches differ.
   The loaded class constructs its volume-averaging matrix directly; this feature
   uses no arbitrary custom weights and does not infer their effect from generic
   API prose. Scaled formulas and scope are in the feature algorithms document.
3. [Vatankhah et al., author preprint2001.03579](https://arxiv.org/pdf/2001.03579),
   methodology section2 and model-study2, were read. They explicitly formulate
   separate gravity/magnetic data weights, independent comparators, bounded
   models and a cross-gradient coupling; an additional structure may occur in
   only one property. Their IRLS/depth weights and stopping rule are not adopted
   here. This feature begins with fixed weighted L2 and KKT-aware stopping, not
   a reproduction of every result or a universal improvement claim.
4. [Choclo gravity_u](https://www.fatiando.org/choclo/latest/api/generated/choclo.prism.gravity_u.html)
   and [magnetic_field](https://www.fatiando.org/choclo/latest/api/generated/choclo.prism.magnetic_field.html)
   resolve to official v0.3.2 documentation. Independent gravity is upward m/s²;
   magnetic components are tesla for magnetization A/m. Explicit declared prism
   bounds, kg/m³ density and M=chi*B0(T)/mu0 permit independent units/sign/Jacobian
   controls. Dynamic latest URLs are not executable pins: actual0.3.2 loaded
   source bytes and constants must be externally audited before accepting runs.

## Partially accessible or unavailable

[Haber and Gazit2013](https://link.springer.com/article/10.1007/s10712-013-9232-4):
publisher identity/abstract verified; full article is subscription-only here.
The abstract discusses regularization and structural coupling; no unviewed
theorem, equation or experiment is claimed verified.
[Gallardo and Meju2003 DOI](https://doi.org/10.1029/2003GL017370) did not yield
accessible full text in this audit. The GJI2018 coupling-strategies page also
failed retrieval. These citations are leads, not a substitute for the inspected
official implementation and accessible author methodology above. The underscore
`13_joint_inversion` tutorial link was unavailable; the actual versioned primary
tutorial uses `13-joint_inversion`. No provider dataset was downloaded and no
third-party data redistribution rights were established by this research.

## Existing product source findings

Accepted ordinary gravity and induced magnetic forward functions are reusable
public physical seams with explicit output units and independently tested prism
geometry. They are not survey ingestion or inverse solvers. Cached `joint.py`
creates synthetic magnetic observations and uses fixed cached geometry plus
initial-fit cross-gradient normalization; it is not the supplied-survey pipeline.
Current gravity weighted-L2 implementation exposes a gravity-specific public
workflow but private generic optimizer internals. It does not yet provide a
tested public `physical_optimizer` seam applicable to nonlinear joint objectives.
Importing its private builder/optimizer/metadata helpers is specifically excluded.

## Independent reasoning to validate

The face-averaged Gram expression, gradients and PSD approximation can be audited
from sparse public mesh operators, independent neighbor enumeration and Torch
autograd. This is an independent numerical implementation, not an independent
continuum discretization. Choclo plus converged volume integration test different
physical kernels; refined-source observations mitigate the inverse crime.
Nonconvex coupling cannot establish uniqueness, geological truth or guaranteed
benefit. Flat gradients, wrong field/geometry and disjoint property sources are
mandatory scientific counterexamples. Hypotheses become acceptance only through
the predeclared numerical and full-pipeline gates, not through this document.
