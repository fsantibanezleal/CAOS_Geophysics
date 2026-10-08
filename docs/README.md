# Inverse Earth Studio documentation wiki

This wiki is the durable technical record of the workbench. It explains what the product is and is not, the physics, exact data contracts, local scripts, offline and browser lanes, framework choices, cases, experiments, and deployment boundary.

The [approved replacement SDD](design/SDD.md), [current plan review](design/plan-status-2026-10-03.md) and [requirement ledger](design/convergence.json) govern the active rebuild. The 0.04.001 release and its completed checklists below are historical; they do not establish acceptance of the user-data platform.

- [Architecture](architecture/architecture.md): system flow, determinism, lanes, and release boundary.
- [Frameworks](frameworks/frameworks.md): research-selected engines and why each is used.
- [Problem types](problem-types/problem-types.md): gravity, magnetics, MT, FWI, learned, and joint methods.
- [M01 gravity station corrections](methods/gravity-processing.md): normal gravity, height/reference conventions, Bouguer plate and residual terrain terms, uncertainty propagation, independent oracles and explicit field-admission failures. Authenticated physical children and eligible field modelling remain incomplete.
- [M01 equivalent-source transforms](methods/gravity-processing/02_equivalent-source-transforms.md): blocked Harmonica/Verde fitting and upward continuation, physical oracle controls and conditioning limits; these coefficients are not 3D density contrasts.
- [Ordinary physical station adapter](guides/13_local_station_adapter.md): executable local correction recipe, exact native request/result identities and safe-error boundary, not an online worker claim.
- [Local physical gravity JSON workflow](guides/15_local_physical_json.md): bounded original bytes and parser-to-correction calculation, separate raw/scientific identities and structural-versus-physical limitations.
- [M02 submitted-survey research and plan](research/m02-survey-inversion-2026-10-03.md): verified engine/units/objective references and explicit unimplemented survey/inverse/resource/field gates.
- [Local M02 forward calculation](guides/14_local_gravity_forward.md) and [independent acceptance](validation/gravity-forward-independent-review-2026-10-03.md): actual declared prism geometry, signed density, physical Jacobian and two independent oracles; full inverse/field/host gates remain open.
- [M04 induced magnetic forward calculation](methods/magnetic-forward.md): actual SimPEG/Geoana components, linear TMI and physical susceptibility Jacobian, independent Choclo/quadrature/Decimal controls and reproducible strict local inputs; inverse, field and online gates remain open.
- [Local M11 supplied joint workflow](guides/22_local_joint_survey.md): actual separate beta calibration, bounded nonlinear coupling candidates, frozen marginal evaluation, private export and strict replay; original precision failures and field/activation limits remain explicit.
- [Local M11 native scientific instrument](data-contract/04_joint-local-inspection.md): every accepted-state physical model/response/residual, post-freeze partition diagnostics, exact face-averaged Gram contributions and byte-exact private exports; no browser fitting or scientific certificate.
- [Paired source-bundle protocol](operations/03_paired_source_bundle.md): selected committed objects, archive/manifest identity and independent trust prerequisites; Linux restore remains unaccepted.
- [M06 measured MT admission](problem-types/mt-field-admission.md): attributed field EDI, independent full-tensor QC, ineligible verdict, and exact local reproduction.
- [M05/M06 online MT course](problem-types/05_online-mt-course.md): complete complex mathematics, source/variance/frame QC, actual TRF/array protocol, independent worked fixed-h/wrong-h controls and conditional limits.
- [Use and reproduce the MT course](guides/09_online-mt-course.md): bilingual in-app exercises, exact numerical/render gates and separately pending host admission.
- [Earthquake phase picking](problem-types/phase-picking.md): M08/M13 theory, frozen input and asset contracts, held-out denominator, browser inference and parity gate.
- [M12 learned velocity validation](problem-types/04_learned-velocity-validation.md): synthetic first-arrival tomography, independent forward oracle, matched classical comparison and retained failure.
- [Local first-arrival user-data tools](guides/19_local_velocity_data.md): supplied physical rays/times/errors, actual weighted classical estimate and optional frozen-checkpoint inference, verified local exports and explicit approximation/negative-model limits.
- [Data contract](data-contract/data-contract.md): accepted inputs, units, outlier policy, replay schema, and provenance.
- [Source to result](data-contract/01_source-to-result.md): rights, immutable raw bytes, typed observations, physical eligibility, processing and evidence boundaries, with a reproducible current API calculation.
- [Source acquisition](guides/05_sources.md): reviewed provider links, immutable raw assets, rights, format dispatch and local receipts.
- [Private EDI M05/M06 jobs](guides/08_online_edi_mt.md): authenticated original-byte tensor QC, conditional layered inverse, host admission and re-import.
- [Pinned potential-field source intake](guides/11_potential_source_intake.md): reviewed archive/member hashes, bounded selective extraction, all-row profiling and the unresolved physical-metadata eligibility gate.
- [Bartlett Springs source/correction review](research/bartlett-source-review-2026-10-03.md): original provider versus attributed author-transformed bytes, correction-state meanings, unresolved height/error semantics and licence boundaries.
- [Cases](cases/README.md): category taxonomy and 20-case coverage matrix.
- [Guides](guides/README.md): setup, precompute, GPU, and bring-your-own-data workflows.
- [Manuscript](../manuscripts/geophysics-identifiability/README.md): research framing and evidence plan.
- [0.04.001 scientific and browser validation](validation/scientific-ui-0.04.001.md): candidate/canonical hashes, numerical gates, rendered inspection and remaining limits. Public deployment is recorded separately.
- [0.04.001 public deployment](validation/deployment-0.04.001.md): corrected main/CI/Pages and VPS release identifiers, exact-byte TLS receipts and production browser checks.

The public UI is bilingual English and Spanish. Technical source and documentation remain English for reproducibility.
