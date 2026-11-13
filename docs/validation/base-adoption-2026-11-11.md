# Current CAOS base adoption, 2026-11-11

This candidate adopts the currently released shared UI base after reviewing the Shell 0.26.000 and Product Template 0.15.008 releases.

| Component | Released identity | Candidate adoption |
|---|---|---|
| CAOS App Shell | 0.26.0, main `d2b3351`; GitHub release `v0.26.000`; npm `latest` and `gitHead` match | `frontend/package.json` and lockfile pin 0.26.0. The product-owned gate and exact-package assertions use the same version. |
| CAOS Product Template | 0.15.008, main `7dce8c9`; exact-main CI and Pages build/deploy passed | The `.template-version` file remains the 0.13.001 instantiation-origin record. The 0.15.008 review is a separate current-adoption record, not a rewritten origin claim. |

Shell 0.26.0 corrects PlotCard header sizing, redraws moving chart marks, publishes settled callout-band measurements, gives long callout values a dedicated row, and exposes carousel semantics only when cards are hidden. It also adds explicit UTC/local calendar-time axis handling and formatter caching. Geophysics does not add product CSS or fonts to reproduce shell-owned behavior.

The Template 0.15.007 stage-input refusal applies to its `scripts/local/workflow.py` runner. This product does not use that runner; its data pipelines remain product-owned. Notebook depth remains an open content gap: the CAOS_MANAGE notebook bar reported 181 findings on this checkout, so no notebook-content pass is claimed. The product-specific guard and notebook remediation remain pending.

This source update does not establish product acceptance. Rebuild and run the complete product unit, browser, visual, artifact, scientific, CI and actual-host gates against the exact package before promotion. Existing validation records remain historical for their named source identities. The VPS continues serving its existing release until the full release bar passes; this adoption does not authorize a GitHub Pages deployment.
