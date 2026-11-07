# CAOS Geophysics methods wiki

This repository wiki explains the scientific methods implemented or proposed in the product. Each method chapter distinguishes an executable component from a complete accepted workflow, identifies the input and units, states assumptions and failure controls, links the implementation and tests, and gives reproducible commands or names the missing prerequisite.

## Method chapters

- English: [M01–M06: potential fields, magnetics and magnetotellurics](methods/m01-m06.md) · [M07–M13: ERT, seismic processing and inversion, coupled methods and learned phase picking](methods/m07-m13.md)
- Español: [M01–M06: campos potenciales, magnetismo y magnetotelúrica](methods/m01-m06.es.md) · [M07–M13: ERT, procesamiento e inversión sísmica, métodos conjuntos y detección de fases aprendida](methods/m07-m13.es.md)

The chapters are grouped for navigation; each method remains separately identified. Use the [product SDD method ladder](../design/SDD.md#4-method-ladder-and-acceptance-oracle) for the current system requirements and [source-to-content review](../validation/source-to-content-review.md) for the scope of the structural wiki check.

## Evidence boundary

The `scripts/check_docs_matrix.py` command checks English and Spanish method IDs, minimum scientific and reproducibility sections, implementation-path density, and local link targets. It is a documentation structure check. It does not certify mathematical correctness, source rights, field-data suitability, acceptance quality, or a release. The SDD convergence ledger and method-specific evidence remain authoritative for those decisions.
