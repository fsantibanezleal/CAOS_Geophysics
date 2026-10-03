# Inverse Earth Studio documentation wiki

This wiki is the durable technical record of the workbench. It explains what the product is and is not, the physics, exact data contracts, local scripts, offline and browser lanes, framework choices, cases, experiments, and deployment boundary.

The [approved replacement SDD](design/SDD.md), [current plan review](design/plan-status-2026-10-03.md) and [requirement ledger](design/convergence.json) govern the active rebuild. The 0.04.001 release and its completed checklists below are historical; they do not establish acceptance of the user-data platform.

- [Architecture](architecture/architecture.md): system flow, determinism, lanes, and release boundary.
- [Frameworks](frameworks/frameworks.md): research-selected engines and why each is used.
- [Problem types](problem-types/problem-types.md): gravity, magnetics, MT, FWI, learned, and joint methods.
- [M06 measured MT admission](problem-types/mt-field-admission.md): attributed field EDI, independent full-tensor QC, ineligible verdict, and exact local reproduction.
- [Earthquake phase picking](problem-types/phase-picking.md): M08/M13 theory, frozen input and asset contracts, held-out denominator, browser inference and parity gate.
- [M12 learned velocity validation](problem-types/04_learned-velocity-validation.md): synthetic first-arrival tomography, independent forward oracle, matched classical comparison and retained failure.
- [Data contract](data-contract/data-contract.md): accepted inputs, units, outlier policy, replay schema, and provenance.
- [Source to result](data-contract/01_source-to-result.md): rights, immutable raw bytes, typed observations, physical eligibility, processing and evidence boundaries, with a reproducible current API calculation.
- [Source acquisition](guides/05_sources.md): reviewed provider links, immutable raw assets, rights, format dispatch and local receipts.
- [Private EDI M05/M06 jobs](guides/08_online_edi_mt.md): authenticated original-byte tensor QC, conditional layered inverse, host admission and re-import.
- [Cases](cases/README.md): category taxonomy and 20-case coverage matrix.
- [Guides](guides/README.md): setup, precompute, GPU, and bring-your-own-data workflows.
- [Manuscript](../manuscripts/geophysics-identifiability/README.md): research framing and evidence plan.
- [0.04.001 scientific and browser validation](validation/scientific-ui-0.04.001.md): candidate/canonical hashes, numerical gates, rendered inspection and remaining limits. Public deployment is recorded separately.
- [0.04.001 public deployment](validation/deployment-0.04.001.md): corrected main/CI/Pages and VPS release identifiers, exact-byte TLS receipts and production browser checks.

The public UI is bilingual English and Spanish. Technical source and documentation remain English for reproducibility.
