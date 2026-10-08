# Induced survey inversion: primary basis and physical limits

This continuation covers the complete M04 survey, L2, sparse/IRLS, user-data,
export, field evaluation and linked-view vertical. It does not redefine the
intrinsic [prism contract](../m04-induced-prism/contracts.md) or its frozen
[validation](../m04-induced-prism/validation.md). Read all seven files:
[requirements](requirements.md), [design](design.md), [contracts](contracts.md),
[algorithms](algorithms.md), [validation](validation.md), [tasks](tasks.md).

## Retrieved, installed, versioned sources

The following official v0.25.2 HTTP bodies were actually retrieved and compared
byte-for-byte with installed source. These are reproducibility identifiers for
method definitions, not a claim of inverse execution or supply-chain completeness.

| Source | Bytes | SHA256 |
| --- | ---: | --- |
| [Sparse](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/regularization/sparse.py) | 48268 | ea6782098d51f098cd00b5dc8e1dd74ab4166c7c7f1b6a280016f2a697e58c76 |
| [WeightedLeastSquares](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/regularization/base.py) | 87142 | aae7dbd3cb4887246f38c8ceba4fe8fbeeb5592110341635e06fdb70246a92b5 |
| [UpdateIRLS](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/directives/_regularization.py) | 15864 | 032f0dc71f4deb8cb278ffae19a296b60f3d50468a72410e8fa1ecd3bccf2abc |
| [L2DataMisfit](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/data_misfit.py) | 11166 | 1e223879152b1764db5e08d198ebfcd4faf5864601a842a90a0e31975fe9c843 |
| [ProjectedGNCG](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/optimization.py) | 50412 | 0ac858cc310b32bb9aa59c78aaaa9c79b5f28438db52fb06ec73d976b63196a4 |
| [Magnetic simulation](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/potential_fields/magnetics/simulation.py) | 79547 | 3895dfdd3295c71a29df841b59d8967ddc7b5eeb0608ddd092707e333a9a339e |
| [Regularization mesh](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/regularization/regularization_mesh.py) | 21622 | 5283b4f854906aeb05c216ff1c83174c99a7c53fe6a3ce8227b8ea483e785f44 |

Additional actual official source reads:
[magnetic Simulation3DIntegral](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/potential_fields/magnetics/simulation.py),
[RegularizationMesh](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/regularization/regularization_mesh.py),
[SciPy 1.15.2 BVLS](https://docs.scipy.org/doc/scipy-1.15.2/reference/generated/scipy.optimize.lsq_linear.html).
The [official induced tutorial](https://simpeg.xyz/user-tutorials/inv-magnetics-induced-3d/)
is synthetic and demonstrates an inversion workflow. Its noise, starts, beta
schedule and plots are not our field uncertainty or acceptance oracle.

## Observed semantics that constrain this design

Simulation3DIntegral constructs physical secondary components. Its amplitude
switch applies the norm of those components; it does not add the inducing field.
The present design therefore never uses that switch for total-field magnitude.
Its getJtJdiag weights through a diagonal extracted from W, so a dense covariance
cannot use that shortcut. The physical kernel remains the actual SimPEG/Geoana
operator, not a locally written prism kernel.

L2DataMisfit uses an unhalved squared whitened residual. We define the same
factor of two in gradients and GN Hessians. The regularizer's length_scale
property is relative to its mesh base length, not a length in metres. We set
physical alpha coefficients explicitly and independently check stencil distances,
active faces, averaging and volume factors. No sensitivity or depth weighting
is silently enabled.

Sparse supplies the actual IRLS weights. We explicitly disable its optional
max-dependent scaling and freeze p=1 smallness, p=2 first-order smoothness.
The application controls a recorded positive threshold schedule, while vendor
Sparse evaluates the weights. This is a proposed, reviewable policy, not the
unmodified default UpdateIRLS directive: that directive can replace the threshold
by a zero percentile on a null model and adjusts beta while it runs.
Executable gradient_type is "components": the installed validator rejects the
singular spelling "component" despite that spelling appearing in a parameter
description. The design follows actual installed semantics, not that shorthand.

## Physics, data, and non-identifiability

For ENU, positive-down inclination I and clockwise-from-north declination D,
f=(cos I sin D, cos I cos D, -sin I); B0=F f in nT.
M=chi B0(T)/mu0 is induced magnetization in A/m. Secondary vector b, linear
projection f dot b, secondary amplitude |b|, and total-field anomaly
|B0+b|-F are four different quantities. This continuation fits the first, second
or fourth only when the uploaded quantity is explicitly declared.

Scalar susceptibility cannot describe general remanent magnetization, unknown
field direction, anisotropy or self-demagnetization. A low residual is not proof
of their absence. Wrong-field and remanent controls are mandatory comparisons,
not classifiers that pronounce a field survey induced. Reduced-to-pole or
harmonic equivalent-source coefficients are not susceptibility data.

Field coordinates, height datum, source epoch, field-reference provenance,
processing graph, error covariance and rights must be supplied. We neither
evaluate IGRF nor infer a missing height or license. M03 outputs can enter only
through a typed quantity/lineage adapter; interpolation and physical continuation
do not become raw observations by renaming them. Bartlett's 200 m magnetic grid
is not flight lines. Charleston's approximately 2.58 GB provider acquisition
retains its full-coverage/rights/offline-workflow obligations; a bounded subset
cannot close the parent case.

## Dependency boundary

A gravity-specific private solver is not a generic magnetic optimizer.
The earlier inspected M02 cpu-3 source has gravity constructor dependencies.
Current cpu-4 candidate source adds certified decrease and bounded selection,
but still imports gravity_forward/gravity_survey_l2 and does not establish an
accepted generic magnetic ABI. No accepted M02 binding is inferred here.
The required composition protocol in algorithms is
a proposal to bind to that accepted core, not permission to copy it or replace
it with the legacy spatial_inverse solver. A released accepted core must supply
the exact binding before inverse source development; all parser, geometry,
oracle and documentation definitions here are independent of that pending pin.

Independent components use actual Choclo 0.3.2; tiny scalar algebra uses portable
Decimal80 direct norms, separately. Sparse images and deterministic regularization
diagnostics are not posterior uncertainty, geological truth or resolution proof.
