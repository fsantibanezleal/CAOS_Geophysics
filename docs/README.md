# Inverse Earth Studio documentation wiki

This wiki is the durable technical record of the workbench. It explains what the product is and is not, the physics, exact data contracts, local scripts, offline and browser lanes, framework choices, cases, experiments, and deployment boundary.

- [Architecture](architecture/architecture.md): system flow, determinism, lanes, and release boundary.
- [Frameworks](frameworks/frameworks.md): research-selected engines and why each is used.
- [Problem types](problem-types/problem-types.md): gravity, magnetics, MT, FWI, learned, and joint methods.
- [M06 measured MT admission](problem-types/mt-field-admission.md): attributed field EDI, independent full-tensor QC, ineligible verdict, and exact local reproduction.
- [Earthquake phase-picking design](problem-types/phase-picking.md): M08 classical and M13 PhaseNet-family theory, units, evaluation and pending gates.
- [Data contract](data-contract/data-contract.md): accepted inputs, units, outlier policy, replay schema, and provenance.
- [Source acquisition](guides/05_sources.md): reviewed provider links, immutable raw assets, rights, format dispatch and local receipts.
- [Cases](cases/README.md): category taxonomy and 20-case coverage matrix.
- [Guides](guides/README.md): setup, precompute, GPU, and bring-your-own-data workflows.
- [Manuscript](../manuscripts/geophysics-identifiability/README.md): research framing and evidence plan.
- [0.04.001 scientific and browser validation](validation/scientific-ui-0.04.001.md): candidate/canonical hashes, numerical gates, rendered inspection and remaining limits. Public deployment is recorded separately.
- [0.04.001 public deployment](validation/deployment-0.04.001.md): corrected main/CI/Pages and VPS release identifiers, exact-byte TLS receipts and production browser checks.

The public UI is bilingual English and Spanish. Technical source and documentation remain English for reproducibility.
