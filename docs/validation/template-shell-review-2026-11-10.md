# Template and shell reconciliation: 2026-11-10

## Current references

- Product branch: `task/geophysics-client-first-completion`, starting commit `929deb789e2eda6be7c72e3405f9c1ec74e4a6ac`.
- Shared shell: product dependency and lockfile pin `@fasl-work/caos-app-shell` 0.25.0. The adoption commit is `929deb7`; it also moves the product shell gate to the current shell release.
- Template origin: `.template-version` records CAOS_PRODUCT_TEMPLATE 0.13.001, the release from which this repository was instantiated. It remains an origin record, not a claim that every file now matches the template.
- Current template reviewed: CAOS_PRODUCT_TEMPLATE 0.15.006, which pins the same shell 0.25.0 and adds the declared-file publication contract and product hook.

## Product changes in this reconciliation

The SDD now names shell 0.25.0 and distinguishes the instantiation origin from the reviewed template release. The product adopts the template's `declared.mjs`, `copy-data.mjs`, and their base tests. A generated index maps the existing versioned catalog into the template contract: 20 cases, 120 artifact paths, six additional catalog/model records, and a required readiness document. `copy-data.product.mjs` retains product-specific STEAD, M01 course, field-study, M12 browser-model, and FWI gzip packaging. Vite now serves the rebuilt `frontend/public` directory, while the authored SVG source remains in that directory for Vite imports.

The STEAD manifest still says `browser_parity_verified: false`; this is an export-state marker, while the separate committed runtime receipt records the measured browser result. That receipt binds the current manifest and model hashes, the public-directory verifier, and the phase-picker implementation unchanged since the measured run. It reports all 23 QC-valid held-out traces within `0.001` probability error (maximum `5.0664e-6`) and zero peak displacement; the QC-rejected trace was excluded. A separate, stricter comparison against newly generated native ONNX arrays was attempted during this review but stopped before completion and produced no receipt; it is not substituted for the existing approved parity gate. Independent PyTorch-oracle accuracy and full M13/product acceptance remain open. The successful build demonstrates packaging and compilation only, not release readiness.

## Remaining baseline gaps against template 0.15.006

The preserved template-gap audit at `docs/validation/template-gap-baseline-2026-11-10.md` measured the product at commit `3c6f131` before shell 0.25.0 adoption. It is a baseline, not a current pass. It reported:

- version-coherence and technology-matrix failures, including conflicting dependency pins;
- notebook implementation and measured-depth failures;
- no declared manuscripts, no technical-report coverage record, and no BS-1 manuscript;
- deployment-place/unit mismatch, readiness and base-integrity findings;
- a document guard crash and template-residue, document-path, and content-standard timeouts.

The internal-name manuscript findings were corrected in this branch; `python scripts/check_internal_names.py` now passes. The other findings remain open until their corresponding current-branch guards pass. The audit skipped npm installation, frontend build/tests, the live-host gate, CI parsing, and the template's own adversarial test suite. No product deployment or template-compliance acceptance follows from that audit.

## Scientific publication status

The technical report and the separate nullspace study remain below the CAOS manuscript content floor. The nullspace manuscript explicitly states that it cannot establish a new method and uses a different experiment from BS-1; it is not mapped to BS-1. The required manuscript for the geometry-normalized, physics-conditioned travel-time refinement has not been authored. The local depth audit recorded 3,357 report words and 2,838 nullspace-study words, with missing coverage records; both are far below their 12,000-word and 7,000-word floors, respectively. No DOI or publication claim is assigned here.

## Release consequence

This reconciliation is documentation and packaging work only. A successful frontend build, CI job, or VPS upload would not close the missing real-trace parity, scientific, manuscript, or actual-host acceptance gates. Promotion and VPS activation remain gated on those current-commit receipts.
