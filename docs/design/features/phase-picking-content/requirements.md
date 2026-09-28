# M08/M13 scientific-content requirements

Authority: approved product SDD (2026-09-27), methods M08/M13 and section 7; ADR-0016/0017/0071/0075. This is an explanatory frontend and wiki vertical, not a numerical-method release. Source review: [research.md](research.md).

R-PC01 THE Methodology and Implementation routes SHALL expose separate M08 classical and M13 learned phase-picking sections through grouped navigation, while retaining all six released chapters and keeping each visible sibling tab set at six or fewer. Gate: `frontend/src/test/phase-picking-content.test.ts::grouped_navigation_preserves_legacy_chapters` and `frontend/scripts/qa-phase-picking.mjs::pointer_reachability_and_fit`.

R-PC02 THE M08 sections SHALL explain three-component waveform identity, counts versus response-corrected units, sample/time conversion, response epoch, QC/filter provenance, the dimensionless STA/LTA ratio, the distinction between onset triggering and P/S labelling, and an independent analyst-pick comparison. Gate: `frontend/src/test/phase-picking-content.test.ts::m08_content_and_units` and `frontend/scripts/qa-phase-picking.mjs::rendered_m08`.

R-PC03 THE M13 sections SHALL explain the literature PhaseNet-family input, per-component normalization, 1D encoder-decoder with skips, noise/P/S softmax, Gaussian analyst targets and cross-entropy, peak selection, and the precise boundary between reference-paper settings and a not-yet-trained product model. Gate: `frontend/src/test/phase-picking-content.test.ts::m13_architecture_loss_and_honesty` and `frontend/scripts/qa-phase-picking.mjs::rendered_m13`.

R-PC04 WHEN evaluation is discussed, THE content SHALL require event-AND-station-disjoint real traces, frozen train/validation preprocessing and thresholds, a same-trace M08 comparator, one-to-one phase matching, per-phase misses/confusions and timing residuals, quality strata, and separate probability calibration; it SHALL NOT present any unmeasured score. Gate: `frontend/src/test/phase-picking-content.test.ts::disjoint_same_trace_evaluation_without_results`.

R-PC05 THE new method sections SHALL include bilingual, captioned equations, scoped inline primary citations and Refs, a themed original scientific SVG for each method, an assumptions/failure callout, and faithful EN/ES wording. Gate: `frontend/src/test/phase-picking-content.test.ts::equations_citations_and_diagrams` and `frontend/scripts/qa-phase-picking.mjs::bilingual_theme_diagram`.

R-PC06 WHILE M08/M13 engines, rights-cleared data, a trained checkpoint and browser parity are absent, THE UI SHALL identify the sections as approved method design, with no runnable control, fabricated trace, metric, or claim of trained/deployed inference. Gate: `frontend/src/test/phase-picking-content.test.ts::no_false_operation_claim` and `frontend/scripts/qa-phase-picking.mjs::rendered_status_boundary`.

R-PC07 THE feature SHALL add a source-linked technical wiki chapter and change only this content vertical's frontend components/data/tests and corresponding docs. Gate: `frontend/src/test/phase-picking-content.test.ts::wiki_source_links` and staged-path audit `git diff --cached --name-only`.
