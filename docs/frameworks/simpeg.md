# SimPEG

SimPEG provides the modular vocabulary used for gravity, magnetics, and electromagnetic inversion: mesh, survey, simulation, data misfit, regularization, optimization, sensitivity, and directives. The app uses this structure as the conceptual reference for the offline lane and records the installed version in the engine inventory.

Gravity uses active cells, density contrast, an integral forward response, weighted residual, depth weighting, and a regularization context. Magnetics makes the inducing field explicit and retains the scalar susceptibility assumption. The UI mirrors the resulting observation and model relationship without pretending that a small browser map is the full solver.

Reference: [Cockett et al. 2015](https://doi.org/10.1016/j.cageo.2015.09.015), [SimPEG user guide](https://docs.simpeg.xyz/latest/content/user-guide/index.html).
