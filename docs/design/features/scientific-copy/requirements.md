# Scientific content and shared UI correction

Authority: user requests of 2026-09-24: rewrite all text, explain the algorithms and analysis,
remove custom CSS and use the ADR styles, fonts and UI/UX. Issue #11.

R-C01 THE website SHALL replace promotional headings and self-congratulatory comparisons with descriptive scientific text on every route and in the architecture panel. Gate: `frontend/src/test/content.test.ts` rejected-copy scan and six-route browser review.

R-C02 THE Methodology and Implementation pages SHALL explain the actual forward models, unknowns, objectives, numerical updates, constants, stopping rules and limitations in English and Spanish. Gate: source-to-content audit in `docs/research/scientific-implementation.md`, rendered KaTeX and content tests.

R-C03 WHEN results are displayed, THE website SHALL define the metric, units, population and meaning of the history axis. Gate: metric/history unit tests and browser checks on each family.

R-C04 THE product CSS SHALL inherit shared-shell palette, typography, page primitives and navigation appearance without overriding them. Gate: CSS contract test and computed-style checks against shell tokens in light/dark at desktop/mobile widths.

R-C05 THE corrected site SHALL preserve working scientific controls and validate regenerated numerical artifacts. Gate: artifact check, existing frontend tests, build and six-family interaction checks.

R-C06 THE release SHALL publish identical validated content on both existing public hosts. Gate: develop/main integration builds, Pages deployment, VPS deployment and external route/data verification.

R-C07 THE numerical cases SHALL use a refined spatial discretization and expose its resolution without equating grid refinement to geological resolving power. Gate: refinement forward-model check, numerical suite, complete regenerated case matrix and mesh/section browser checks. Added after explicit user rejection of low-resolution block geometry.
