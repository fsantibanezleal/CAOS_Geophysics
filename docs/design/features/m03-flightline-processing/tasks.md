# M03 mapped flight-line processing tasks

1. [x] Verify the approved M03 scope and retrieve/hash official metadata outside Git.
2. [x] Inspect the source dictionary/report acquisition gap and record tested official URLs and HTTP outcomes.
3. [x] Specify an explicit-mapping, no-correction contract for eligible user CSVs.
4. [x] Implement line/height QC, contiguous whole-line holdout, supported-only linear grid and held-out interpolation metrics.
5. [x] Add analytic planar controls and malformed-geometry/duplicate/height/CSV checks.
6. [x] Add bounded segment-intersection crossover interpolation, explicit acquisition-order input, and independent tie-line residual controls; no leveling is applied.
7. [ ] Acquire and parse the Charleston CSV, dictionary, contractor report and provider grid; bind every asset by URL, size and SHA-256.
8. [ ] Implement source-lineage-aware leveling/correction operations only where the source report and raw inputs establish eligibility.
9. [x] Add the optional source-bound upward continuation with regular-grid, support and independent analytic controls; padding/seam assumptions remain documented.
10. [x] Integrate source-bound intake, isolated child execution, typed result storage, bounded export and case-specific workbench; keep online admission closed until actual host evidence is accepted.
11. [ ] Measure and review numerical/resource admission, cancellation and browser result parity on the actual ML VPS.
12. [ ] Acquire provider field deliverables and independently validate source-specific processing and held-out results before changing the method acceptance verdict.
13. [x] Add a browser-local Pyodide Web Worker path that calls the canonical Python M03 processor, has explicit resource limits/cancellation, renders support-aware outputs and exports the computed receipt.
14. [x] Verify exact-result parity on a controlled fixture and verify pre-runtime rejection at the browser row limit; document the runtime version delta and limits of that evidence.
15. [ ] Complete browser/native parity and resource characterization: eight deterministic rotated/reversed surveys and degenerate rejection cases pass; a 25,000-row cold/warm timing and WASM heap profile is recorded for one local host. Measure total worker/process memory and latency across supported device classes before closing.
