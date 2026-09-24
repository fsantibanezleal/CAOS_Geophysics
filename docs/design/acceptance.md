# Replacement acceptance record

Date: 2026-09-24. This record maps the replacement SDD to executed checks, not to the rejected v1 completion claim.

| Requirement | Executed evidence |
|---|---|
| R-001, R-007 | `scripts/check_artifacts.py`: 20 distinct truths, 120 case/condition artifacts, 324 method results; finite values, identities, sizes and SHA-256 verified. |
| R-002 | Independent Choclo prism comparison, linearity, L2/IRLS data-fit improvement and residual closure in `tests/test_rebuild.py`. |
| R-003 | Homogeneous MT halfspace/split-layer identity, NumPy/Torch impedance parity, directional derivative and all exported MT forward responses. Browser/offline parity covers all 24 truth soundings. |
| R-004 | Executed double-precision Deepwave CUDA adjoint directional derivative; every seismic cell has lower final data misfit than its starting model. Receiver coordinates match the actual truncated integer acquisition nodes. |
| R-005 | All 1120 train/validation/test realizations hash-distinct; persisted CNN and autoencoder weights reload and reproduce exported inference. The withheld oblique/ring failures remain in the report. |
| R-006, R-008 | Browser walkthrough: all 20 renderers, all 54 case/method selections, all 120 distinct variant hashes. 3D orbit/angle-step/cut controls, wave play/pause/scrub, inversion replay and responsive layouts inspected. See `docs/validation/browser.md`. |
| R-009 | `docs/research/review.md` maps primary sources to actual implementations and explicitly separates surveyed-only methods. Methods, units, assumptions and limitations were checked against the scripts; the technical report does not claim algorithmic novelty. |
| R-010 | Shared shell retained; six route bodies, EN/ES, light/dark, five architecture diagrams and project-base routing verified in the browser. |
| R-F03 | Frontend artifact-load regression rejects HTTP failure without fabricating a numerical fallback; the workbench presents a visible error state. |

Numerical receipt: `docs/validation/numerical.xml` (15 passing tests). Frontend: six passing contract tests after the HTTP-failure regression was added. Type/build/lint/content/template/CI-budget guards pass. All scientific computation was local, including actual RTX 4070 execution; CI and both public hosts build/serve artifacts only.

The initial v2 release passed external HTTPS verification of every experiment, all six direct routes and the three model files on both hosts. Production inspection found and corrected the Pages brand navigation and the benchmark fallback metric. Exact deployment hashes and the corresponding release identifiers are recorded separately in `docs/validation/deployment.json` and `deployment.md`.

Acceptance means the recorded engineering/scientific gates passed. It does not assert aesthetic approval by the user, field validation, posterior uncertainty, a new inversion algorithm or SOTA superiority.
