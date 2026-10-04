# Supplied gravity-magnetic structural inversion (M11)

This local method asks whether a shared structural constraint improves separately
weighted predictions of two compatible supplied surveys relative to **two real
independent inversions**. It does not infer that density and susceptibility obey
a single rock-property relation. It does not replace missing observations,
geometry, uncertainties, permissions or co-registration with a curated example.

The exact [native contract](../../design/features/joint-survey-inversion/contracts.md),
[objective/algorithm proposal](../../design/features/joint-survey-inversion/algorithms.md),
[requirements](../../design/features/joint-survey-inversion/requirements.md),
[frozen controls](../../design/features/joint-survey-inversion/validation.md) and
[primary research](research.md) define this method. Planner and numerical-oracle
milestones are not a complete inverse/export workflow. The nonlinear optimizer
and serialized full-pipeline seams require their stated applicability review and
actual tests before a runnable complete recipe is advertised.

In particular, separate model regularization and uncertainty-weighted data terms
remain visible. Cross-gradient measures certain shared changes but can vanish for
flat, parallel or antiparallel gradients. The optimized discrete objective and
the cell-centre structural diagnostic are distinct quantities. A selected
uncoupled outcome is meaningful negative evidence, not a missing joint result
to conceal. A synthetic recovered volume is a controlled inverse experiment,
not a true subsurface model for a field survey.

Rights, input bytes, mesh, physical signs/units, split provenance, every candidate,
convergence/fit/coverage diagnostics, predictions/residuals and export hashes must
travel with a final result. Local CPU/GPU execution does not imply VPS admission,
browser equivalence, source-rights verification or full M01-M13 release acceptance.
