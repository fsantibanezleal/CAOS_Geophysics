# Local rendered acceptance: scientific recovery 0.04.000

Date: 2026-09-26. This is local built-bundle evidence, not public deployment or user aesthetic acceptance. The tested bundle was produced by `npm run build` from the 0.04 canonical tree and served by Vite preview at `127.0.0.1:5179`.

- Build HTML SHA-256: `95cc95eded4d68ed50063455690278d156d97b82ff951cb4e75a151ed16dd2d3`.
- Catalogue SHA-256: `a6b785563362ae13f164cc26bd842e3f018533a0cc0a0a02e0b77a76cead579a`.
- Browser: local Playwright Chromium with software WebGL. [Machine-readable report](browser-0.04/report.json) contains fifteen viewport captures, canvas dimensions, computed font families, document widths and offscreen-text checks. Page exceptions, HTTP errors, document overflow and text clipping: zero in the final run.
- Numerical gates: 93 Python tests, 36 frontend tests, all 120 experiment hashes and 348 method records, and 348 recovery-validator results passed. The validator retained 170 unresolved, 15 failed and 30 negative-control verdicts; passing the gate does not relabel them successful inversions.

The captured views cover [gravity final model](browser-0.04/desktop-gravity-final.png), [synthetic target](browser-0.04/desktop-gravity-truth.png), [inverse replay](browser-0.04/desktop-replay.png), [PGI](browser-0.04/desktop-pgi.png), [MT](browser-0.04/desktop-mt-uncertainty.png), [FWI](browser-0.04/desktop-fwi-model.png), [signed CNN output](browser-0.04/desktop-signed-cnn.png), the five research/benchmark routes, [EDI](browser-0.04/desktop-edi.png), [Spanish mobile EDI](browser-0.04/mobile-es-experiments.png) and [Spanish mobile workbench](browser-0.04/mobile-es-workbench.png).

The first rendered run exposed a Benchmark initial-load exception (`metricInfo` received an undefined metric). The second run exposed EDI text clipping at 390 px despite `document.scrollWidth` reporting 390 px. Both were corrected in the 0.04 source, and the final built-bundle run has no recorded error. Screenshots show the selected viewport and section, not every scrolled panel. External Pages and VPS hydration still require separate verification after promotion.
