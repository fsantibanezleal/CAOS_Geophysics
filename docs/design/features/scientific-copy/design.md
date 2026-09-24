# Design and review

This correction replaces the rejected visual-language paragraph of the product SDD. The shell owns
fonts, themes, page measure, tabs, controls and responsive header/footer. Use `.page-body.wide` for
the workbench and `.page-body.prose` for reading pages. Product CSS contains only geophysics widget
geometry, scoped plotting rules and RotorVitals-derived component patterns; no root palette,
Georgia headings, global form styles, page-width overrides or mobile shell unlocking.

Content is authored from the inspected numerical sources. A typed bilingual method registry separates
physical reasoning from exact algorithm steps. Six family tabs group related algorithms; shared
SubTabs distinguish L2/IRLS/vector, three MT optimizers and the two seismic variants. CNN and
autoencoder theory remain separate. Scientific SVGs show sensitivity, impedance recursion, acquisition,
cross-gradients and network dimensions. Every equation defines its symbols and has a translated caption.
References accompany the section they support. Software deployment is supplementary, not the explanation
of scientific implementation.

Benchmark descriptions resolve metrics by method/family, not by replacing underscores in identifiers.
History axes reflect saved evaluations, optimizer steps or training epochs as appropriate. Results are read at runtime, not manually copied into headline claims. The subsequent mesh
refinement described below regenerates the canonical artifacts.

Review: the current potential solver does not whiten by sigma; the MT optimizer with internal key
`mt-lm` actually uses SciPy TRF; MT losses have different normalizations; FWI histories exclude the
regularizer and continuation filter; joint gradients use cell-index spacing; the regenerated AE threshold still misses
both withheld reference geometries. These are mandatory content distinctions, not new solver claims.
No EDI, PGI, posterior uncertainty, field validation or novel algorithm is implied by this rewrite.

## Authorized mesh refinement (subsequent user request)

Refine potential fields to 28×24×16 (80×80×70 m), preserving physical extent and stations.
Refine acoustic models to 128×96 at 12.5 m and dt0.5ms; keep 1.1s record, physical source
positions and 300m PML. Continuation windows41/17/1 preserve approximately the old20/8ms support;
scale velocity difference regularization by4 for halved cell spacing. Refine CNN targets to24×28
columns and retrain both checkpoints with the same leakage-safe split policy. Regenerate all
case variants; earlier numerical values are historical only. Validate in a separate smoke directory
before the explicit canonical bake. Default 3D representation becomes a labelled isosurface of
the computed cell field, with a cell view for discretization inspection; interpolation is display,
not claimed extra resolution.
