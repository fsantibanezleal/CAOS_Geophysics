# Problem types and methods

## Forward and inverse framing

The forward problem evaluates d_pred = F(m) for a proposed density, susceptibility, conductivity, or velocity model. The inverse problem minimizes a data objective plus a prior:

Φ(m) = ||W_d(F(m) - d_obs)||² + β R(m).

W_d encodes data uncertainty, β balances fit and prior, and R may express smoothness, compactness, depth weighting, or a learned manifold. Non-uniqueness is part of the result.

## Potential fields

Gravity is sensitive to density contrast and decays with distance. Magnetics is sensitive to susceptibility and the inducing field direction. The app includes forward, weighted inverse, sparse IRLS, depth-weighting, scalar magnetic, vector-direction, and cross-gradient diagnostics. The outputs are profiles and maps with units, not unlabeled heatmaps.

## MT

For a one-dimensional layered earth, the complex impedance is propagated from the bottom half-space upward. Apparent resistivity and phase are separate observables. A differentiable parameterization can optimize log resistivity, but it remains conditioned by frequency band and the smoothness prior.

## FWI

The acoustic equation u_tt = v² nabla²u + s is discretized in time and space. The source wavelet, receiver geometry, taper, and update are explicit. Frequency continuation and residual inspection are essential because cycle skipping can produce a plausible but wrong model.

## Learned and joint tools

The CNN prior and autoencoder novelty tools are measured on held-out case groups. The cross-gradient diagnostic compares structural alignment between two model images. None of these tools creates information absent from acquisition.

References: [SimPEG](https://doi.org/10.1016/j.cageo.2015.09.015), [FWI review](https://doi.org/10.1190/1.3238367), [physics-informed review](https://doi.org/10.1190/geo2023-0615.1).
