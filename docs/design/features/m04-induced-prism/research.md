# M04 induced magnetic prism research and implementation gap

Status: research and proposed local operator, not M04 acceptance.
Date: 2026-10-03. Parent issue [46](https://github.com/fsantibanezleal/CAOS_Geophysics/issues/46).
Base: e700b8d087dc3ae9f9c2b0fa4333d2f4a5ba2dbe.

## Existing implementation and missing scientific contract

The fully inspected potential.py uses actual SimPEG magnetic integral matrices,
but its replay survey fixes amplitude50000 nT, declination12 degrees, a16x16
receiver grid and one tensor domain. Its remanent case uses a separate vector
matrix. This is not a typed user-survey M04 forward/inverse vertical. Legacy
ingest.py likewise fixes the field and mesh; those files and released artifacts
will not be edited or rebaked by this unit. Regression green is not field validity.

## Primary sources inspected online

- [SimPEG induced inversion tutorial](https://simpeg.xyz/user-tutorials/inv-magnetics-induced-3d/): weighted L2 and IRLS, active topography cells, declared inducing amplitude/inclination/declination, uncertainty and regularization. Its observed example is synthetic; tutorial defaults or displayed convergence do not constitute this product's acceptance oracle. The tutorial's Geoana/Choclo choices are not automatic runtime substitutions.
- [SimPEG0.25.2 field source](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/potential_fields/magnetics/sources.py): inclination is positive down, declination clockwise from geographic north, amplitude matches data units.
- [SimPEG0.25.2 coordinate source](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/utils/mat_utils.py): dip_azimuth2cartesian returns ENU, with negative upward component for positive inclination.
- [Choclo0.3.2 prism magnetic field](https://www.fatiando.org/choclo/v0.3.2/api/generated/choclo.prism.magnetic_field.html): metre geometry, ENU magnetization in A/m, returned flux density in tesla, interior/edge singular policies.
- [Choclo magnetic source](https://www.fatiando.org/choclo/latest/_modules/choclo/prism/_magnetic.html): separate analytic prism implementation and physical units, not a second invocation of the candidate's kernel. Latest rendered documentation is contextual; the installed0.3.2 source identity below is the oracle pin.

Actual web retrieval included failed opens of the generic Choclo prism index and
an incorrect nested SimPEG API URL. Those failures are not successful source
receipts or proof that the provider is unavailable. The exact versioned source
and magnetic-field API above were subsequently read successfully. No field data,
tutorial archive, unlicensed notebook or whole-survey asset was downloaded.

## Read-only installed source and runtime evidence

Actual existing interpreter metadata: CPython3.12.10 Windows AMD64; SimPEG0.25.2,
Geoana0.8.1, discretize0.12.0, NumPy2.2.6, SciPy1.15.2, Choclo0.3.2,
Numba0.67.0, llvmlite0.49.0. No environment was created or changed. These are
observed installed versions, not a new numerical execution or host epoch.

| Installed relative source | Actual SHA256 |
| --- | --- |
| simpeg/potential_fields/magnetics/simulation.py | 3895dfdd3295c71a29df841b59d8967ddc7b5eeb0608ddd092707e333a9a339e |
| simpeg/potential_fields/magnetics/sources.py | 72e040648eaf7e3b86cbee3c9e61ff478dc5b386cef1adb6842536bd341ed0d2 |
| simpeg/potential_fields/magnetics/receivers.py | 04a99ac0d1771438f3bd7b25e23d62da2674e4ae6bc8843a19abc53b5e843139 |
| choclo/prism/_magnetic.py | 4e41feee63a5d7a5997dd35d99fe17d62016db003568fe7f7f6108724163254b |

Installed simulation.py117..309 and567..830 were read: scalar magnetization
matrix repeats the declared background vector; returned component rows divide
by4pi. BasePFSimulation's actual linear_operator iterates receiver-first,
component-second, and defaults to float32 unless explicitly overridden. The
proposed implementation therefore requires float64 and checks interleaved
component order explicitly. n_processes=1 and RAM storage are required. No
private SimPEG geometry or custom magnetization override is selected.

Choclo's installed permeability is1.25663706212e-6 N/A2. Its oracle magnetization
is chi times B0 in tesla divided by that same permeability, so the physical
permeability cancels in the induced kernel. Do not introduce a rounded4pi1e-7
conversion in only one side or call susceptibility an A/m model.

## Scientific decision

First implement and independently validate an ordinary induced-prism forward
operator with explicit field/geometry and linear-TMI versus exact scalar
magnitude diagnostics. Then design the typed magnetic survey/whitening,
bounded L2 and IRLS selection/evaluation vertical, using the corrected M02
optimizer only after its own accepted dependency. These are separate gates:
a forward pass does not claim an inverse, remanence detection, field eligibility,
online submission, native resource admission or the full M04 method.

See [requirements](requirements.md), [contracts](contracts.md), [design](design.md),
[algorithms](algorithms.md), [validation](validation.md).
