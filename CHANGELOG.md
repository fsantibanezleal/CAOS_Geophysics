# Changelog

All notable changes to Inverse Earth Studio. Display versions use X.XX.XXX.

## [0.04.001] - 2026-09-26

- Adds a source-hashed, 42-frequency measured Clear Lake EDI tensor screen with explicit unit/variance assumptions, DOI attribution, and a failed necessary isotropic-1D test. It exports no field inversion or geological target; the original synthetic inversion fixtures remain separate.
- Compares coupled joint inversions with an optimized uncoupled baseline for both density and susceptibility. The conflicting-boundary structural and mixture cases remain negative controls.
- Requires active and withheld noise-normalized waveform fit for FWI recovery. Serializes FWI float32 model states at ten significant digits and replays all 48 final models on CUDA to verify observations, predictions, residuals, metrics and verdicts.
- Corrects autoencoder coverage scoring against the interpolated network input. Raw-observation discrepancy is separate; individual threshold crossings no longer imply calibrated geological detection.
- Enlarges the case instrument under the existing CAOS shell, adds measured EDI source/plots, bilingual evidence and verdicts, responsive legible scientific axes, and desktop/mobile interaction tests.
- Adds an explicit 20-case/120-condition/348-result source-matched artifact contract, candidate-only release assembly, and a safer VPS release switch. Existing failed and unresolved scientific outcomes remain visible.

## [0.04.000] - 2026-09-26

- Regenerates 120 conditions and 348 method results with noise-weighted spatial potential inverses, physical cross-gradient and independently fitted two-property Gaussian-mixture prior.
- Adds matched full-band and frequency-continuation FWI with 1.6 s traces, withheld receivers, accepted-state replay, and explicit recovery and cycle-skipping verdicts.
- Matches MT objectives across TRF, Adam and neural parameterizations; adds provenance-preserving EDI fixtures, strict ingestion and fixed-thickness conditional uncertainty.
- Retrains the CNN and autoencoder with disjoint calibration/test roles and the same noisy observations for classical comparison. Records the autoencoder's 0/80 withheld-family detection result.
- Adds per-method recovery criteria, PGI/EDI/uncertainty views, common physical colour scales and selected-final versus replay state disclosure. The numerical matrix, artifacts and rendered local browser routes passed their stated gates.
- Retains unresolved and failed cases. No field validation, calibrated geological posterior, or new inverse algorithm is claimed.

## [0.03.000] - 2026-09-24

The `VERSION` file of this release read `0.02.000` until 2026-09-26; the tag, the manifest and this
entry named `0.03.000`, and the file now does too.

- Restores the canonical CAOS shared-shell palette, sans-serif fonts, controls, page layout and tab styles. Removes the rejected custom CSS and promotional page headings.
- Rewrites Introduction, Methodology, Implementation, Experiments and Benchmark with bilingual physical models, objectives, numerical sequences, settings, history semantics, units and assumptions. Documents eleven actual algorithms rather than repository plumbing.
- Adds metric definitions and numerical results to case analysis; corrects the legacy MT optimizer label to bounded TRF.
- Refines potential fields from 1,344 to 10,752 cells and seismic sections from 64×48 to 128×96. Regenerates all 120 experiments and retrains both neural checkpoints.
- Adds labelled isosurfaces, retained cell inspection, property threshold and dynamic section indexing. Expands the default model area by putting secondary camera controls in a disclosure.
- Replaces all five architecture SVGs with bilingual, theme-aware diagrams. Adds frontend content/geometry contracts and a persisted three-grid forward diagnostic, including non-monotone geometric discretization cases.
- Does not add EDI inversion, PGI, posterior inference or a new geophysical algorithm.

## [0.02.000] - 2026-09-23

- Replaces the rejected repeated-shape renderer and all v1 scientific artifacts with 20 distinct geological questions, 120 computed conditions and 324 method results.
- Adds actual SimPEG 3D operators and scalar/vector inversions, complex MT solvers, compiled CUDA Deepwave FWI, coupled inversion, trained CNN and autoencoder checkpoints.
- Rebuilds the interface, neutral theme, 3D scene, scientific plots, waveform/time cursor, inversion replay, angle controls, bilingual investigations, live MT import/export and benchmark.
- Adds numerical gradient/parity tests, complete artifact hashes, external tutorial preprocessing, user CSV inversion and a software technical report.
- Removes the internal Python package and editable installs. CI performs cheap guards and static builds only.
- The earlier release's completion and research-grade claims were overstated; v1 remains recoverable in Git history, not served as v2 evidence.

## [0.01.000] - 2026-09-13

### Added

- Complete twenty-case geophysics workbench across potential fields, MT, acoustic FWI, learned priors, and joint evidence.
- Deterministic staged processing with ingestion and replay contracts, manifests, source ledger, and compact artifacts.
- Shared CAOS shell, six documented routes, bilingual UI, light/dark theme, architecture modal, linked maps, profiles, residuals, and pointer readouts.
- GPU setup lane for the local RTX workstation and CPU-safe static deployment model.
- Deep documentation wiki and manuscript framing for multi-physics identifiability.
