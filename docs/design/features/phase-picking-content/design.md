# M08/M13 content design

Status: implementation design for the approved product SDD's bounded scientific-content unit. The live 0.04.001 release remains synthetic replay and bounded EDI/MT display; the new sections are not evidence of M08/M13 computation.

## Structure and navigation

Retain the six released `chapters` in `frontend/src/data/methods.ts` and their existing figures/algorithms. Add separate typed M08/M13 content in `frontend/src/data/phase-picking.ts` and presentation components for the theory and implementation views. This avoids presenting a planned picker as one of the 13 currently recorded synthetic algorithms.

Methodology uses three compact `Tabs` groups: Fields (potential fields, MT, joint); Waves (acoustic FWI, M08); Learning (current inverse CNN, current autoencoder, M13). Each selected group exposes at most three vertical `SubTabs`. Implementation uses four compact groups: Fields (potential fields, MT and joint, with their existing algorithms nested by method), Waves (existing FWI algorithms plus M08), Models (existing CNN/autoencoder plus M13), and Checks (unchanged numerical validation). The top group labels are deliberately short enough to remain visible in one row on a phone. Shared-shell `Tabs` and `SubTabs` own interaction and keyboard semantics. No top-level route is added.

## Scientific narrative and representation

M08 theory starts from a trace sample `x_c[n]` in digital counts and the epoch-matched channel response; any corrected ground velocity is labelled m/s. `f_s` is samples/s, `t_n=t_0+n/f_s` is UTC-relative seconds. A squared-amplitude short/long energy ratio is dimensionless whether the homogeneous input unit is counts or m/s. A threshold crossing produces an onset candidate, not a phase class. Published S-wave polarization and AR-AIC refinement is a source-backed example, not selected M08 configuration. A separate phase-specific context/quality decision labels P or S, and uncertain/ambiguous arrivals remain unresolved.

M13 theory identifies the PhaseNet *reference* configuration: 3 components, 100 Hz, 3001 samples, four encoder/decoder stages, Gaussian pick labels with 0.1 s standard deviation and categorical cross-entropy. It explains normalization as dimensionless and requires the chosen checkpoint's input units, channel order, preprocessing and hash to be fixed before inference. These are not this product's frozen hyperparameters. The planned product run trains or fine-tunes on rights-cleared real traces and is accepted only after the numerical and browser parity gates in the product SDD.

Implementation content is an executable specification, not invented execution: immutable raw bytes and source rights; response epoch/QC and transform receipt; event/station partition before fitting; M08 window/threshold tuning only on train/validation; M13 label/train/infer/export with a selected checkpoint; one-to-one phase/time matching on identical test windows; stratified errors and abstention; browser export parity as a later gate. No code path in this unit calls an API, downloads waveforms, trains a model or produces picks.

## Figures, references and verification

Two authored schematic SVG views in a single `PhasePickingDiagram` component show (a) M08 sample-to-trigger-to-labelled-pick and (b) M13 standardized channels-to-encoder/decoder-to-probability classes. They use the shared `.method-diagram` token classes and `Figure`, no custom palette/font, and state that they are diagrams, not measured traces. Content uses shell `Equation` with bilingual captions, `Cite` in each section and local `Refs`, backed by DOI/official URLs in the central citation registry.

Vitest verifies the data model, KaTeX compilation, citation integrity, source-linked wiki and non-claim language. Playwright drives actual pointer navigation on desktop and phone in EN/ES and light/dark, checks visible tab density, document fit, headings, figures and status text, and captures screenshots for inspection. Existing tests/build and scientific interactions run to detect regressions. The convergence record goes in `tasks.md` after those gates run.
