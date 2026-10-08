# M03 requirements and exact prospective gates

Status: planned

Date: 2026-10-03. Every implementation path and gate below is prospective. No entry reports a running test or accepted feature. Parent SDD R-001..009, R-011..016 and R-018; M03 / BL-013 / issue 45. The [research](research.md), [contracts](contracts.md), [algorithms](algorithms.md), [validation](validation.md) and [tasks](tasks.md) define the terms and thresholds.

M03-001 WHEN original magnetic data are imported, THE M03 loader SHALL retain exact immutable bytes, source kind, independent raw SHA-256/size and an explicit rights decision without treating a user attestation as provider authentication.
Implementation: data-pipeline/magnetic_line_contract.py::load_lines
Gate: tests/data/test_magnetic_lines.py::test_original_identity_and_rights

M03-002 IF schema, scalar quantity, nT units, metric XY, datum/sign, row/line/sensor identity or correction-state meaning is absent or ambiguous, THEN THE loader SHALL return a field-specific inspection-only or ineligible verdict without coercion.
Implementation: data-pipeline/magnetic_line_contract.py::validate_lines
Gate: tests/data/test_magnetic_lines.py::test_physical_metadata_and_exact_keys

M03-003 WHEN line records are parsed, THE loader SHALL preserve supplied acquisition order, full flight/tie/reflight identities, separate sensor channels, missingness and duplicate diagnostics without sorting away reversals, averaging or thinning.
Implementation: data-pipeline/magnetic_line_contract.py::parse_csv
Gate: tests/data/test_magnetic_lines.py::test_order_identity_duplicates_and_masks

M03-004 IF a grid, magnetic potential, vector, gradient or RGB raster is offered as flight-line scalar observations, THEN THE loader SHALL reject that substitution and retain the original object's distinct kind.
Implementation: data-pipeline/magnetic_line_contract.py::validate_lines
Gate: tests/data/test_magnetic_lines.py::test_bartlett_grid_and_charleston_rgb_are_not_lines

M03-005 WHEN a correction is requested, THE processor SHALL require its verified input state, eligible metadata, sign/units, explicit parameters and ordered immutable lineage; an already applied or unknown correction SHALL not be applied again, except a distinct verified current-to-target rereference transaction as explicitly contracted.
Implementation: data-pipeline/magnetic_lines.py::apply_corrections
Gate: tests/numerics/test_magnetic_processing.py::test_correction_state_and_no_double_application

M03-006 IF tagged survey_reference versus row_utc epoch, main-field generation, coordinate basis, independently evaluated old/new reference or altitude semantics cannot be established, THEN THE processor SHALL reject IGRF subtraction or typed rereference without broadcast/re-evaluation defaults or invented date/vector/height.
Implementation: data-pipeline/magnetic_lines.py::apply_reference
Gate: tests/numerics/test_magnetic_processing.py::test_igrf_epoch_vector_datum_and_rereference

M03-007 WHEN lag, diurnal or heading corrections are requested, THE processor SHALL use the declared signed lag/navigation overlap, synchronized base-relative perturbation or independently calibrated heading terms, preserve masks at unsupported times and emit separate before/after channels.
Implementation: data-pipeline/magnetic_lines.py::apply_instrument_corrections
Gate: tests/numerics/test_magnetic_processing.py::test_lag_diurnal_heading_and_overlap

M03-008 WHEN crossover QC is computed, THE processor SHALL retain every candidate line/tie intersection with segment IDs, interpolating weights, signed difference, time/height separation and reasons why any comparison is ineligible.
Implementation: data-pipeline/magnetic_lines.py::crossovers
Gate: tests/numerics/test_magnetic_processing.py::test_crossing_geometry_height_and_gap

M03-009 WHEN tie-offset leveling is selected, THE processor SHALL solve only eligible training crossovers, record each connected-component gauge, rank and offsets, and reject application to an uncalibrated held-out line.
Implementation: data-pipeline/magnetic_lines.py::level_offsets
Gate: tests/numerics/test_magnetic_processing.py::test_level_graph_gauges_and_sealed_lines

M03-010 WHEN a directional residual-filter diagnostic is selected, THE processor SHALL retain removed and retained arrays, transfer function, acquisition azimuth and attenuation of line-parallel geological controls, and label it conditional microlevel filtering.
Implementation: data-pipeline/magnetic_lines.py::microlevel_diagnostic
Gate: tests/numerics/test_magnetic_processing.py::test_microlevel_stripes_and_parallel_geology

M03-011 WHEN gridding alternatives are evaluated, THE processor SHALL invoke pinned Harmonica float64 single-thread equivalent sources on an admitted scalar anomaly with deterministic training-only half-open source-block maps, column scaling, raw weights and explicitly dimensioned/rescaled damping, and use SciPy geometric interpolation only where height comparability is established.
Implementation: data-pipeline/magnetic_lines.py::fit_grid
Gate: tests/numerics/test_magnetic_processing.py::test_dense_independent_fit_and_height_baseline

M03-012 WHEN output cells or predictions are created, THE processor SHALL report local line/along-track spacing, sampling bounds, hull/distance/height/gap/QC masks and all excluded counts, without interpreting grid pixel size as resolved wavelength.
Implementation: data-pipeline/magnetic_lines.py::support_masks
Gate: tests/numerics/test_magnetic_processing.py::test_sampling_aliasing_and_support_masks

M03-013 WHEN model parameters or correction choices are selected, THE evaluator SHALL freeze actual complete-line outer/inner partitions, boundary anchors, segment-wise tie buffers, support/candidates and geometry-only coverage before value processing, refit calibration/source choices inside each inner training fold and keep final test values sealed until one evaluation.
Implementation: data-pipeline/magnetic_line_validation.py::make_partitions
Gate: tests/numerics/test_magnetic_processing.py::test_blocked_line_holdout

M03-014 WHEN field predictions or provider comparisons are reported, THE evaluator SHALL distinguish unweighted nT residuals, conditional provider-product prediction, independently sealed processing, verified comparable numeric grids and unavailable field uncertainty; it SHALL not score field geology against synthetic truth.
Implementation: data-pipeline/magnetic_line_validation.py::evaluate
Gate: tests/numerics/test_magnetic_processing.py::test_field_metrics_and_provider_comparison

M03-015 WHEN a higher-plane harmonic prediction or FFT upward continuation is requested, THE processor SHALL enforce height/datum/source-free domain, explicit positive displacement and boundary/support assumptions, and distinguish physical continuation from same-plane interpolation.
Implementation: data-pipeline/magnetic_lines.py::continue_upward
Gate: tests/numerics/test_magnetic_processing.py::test_dipole_and_fourier_continuation_oracles

M03-016 IF RTP, downward continuation, vector recovery, susceptibility inversion or a spatially varying field outside the declared scalar approximation is requested, THEN THE M03 contract SHALL return an explicit unsupported/ineligible verdict and retain the assumptions needed for a reviewed M04 or extended-transform workflow.
Implementation: data-pipeline/magnetic_line_contract.py::validate_operation
Gate: tests/numerics/test_magnetic_processing.py::test_scalar_vector_remanence_and_rtp_rejection

M03-017 WHEN spectral diagnostics are exported, THE evaluator SHALL preserve window, mean removal, sampling, normalizations, frequency/wavenumber axes, coverage rectangle and missingness refusal without converting directional power into an unvalidated depth estimate.
Implementation: data-pipeline/magnetic_line_validation.py::spectrum
Gate: tests/numerics/test_magnetic_processing.py::test_spectrum_parseval_axis_and_holes

M03-018 IF input, nodes, rows, segments, sources, candidates, output or CPU/wall/RSS/scratch bounds are exceeded, THEN THE local processor SHALL reject or stop without scientific resolution substitution, overwritten evidence or a successful terminal result.
Implementation: data-pipeline/magnetic_line_contract.py::preflight; data-pipeline/magnetic_lines.py::run
Gate: tests/numerics/test_magnetic_processing_resources.py::test_bounds_no_thinning_and_cold_profiles

M03-019 WHEN a local request succeeds, THE paired scripts SHALL export exact request/result hashes, arrays, masks, diagnostics, correction/split/source/environment lineage and replay recipe into a new destination and reject overwrite.
Implementation: scripts/magnetic-lines.ps1; scripts/magnetic-lines.sh; data-pipeline/magnetic_lines.py::export_run
Gate: tests/data/test_magnetic_line_export.py::test_paired_scripts_replay_and_no_overwrite

M03-020 WHEN rights-restricted results are exported, THE exporter SHALL honor separate private-processing, derivative-publication and raw-mirroring permissions and retain denied members with reasons without a restrictive-source bypass.
Implementation: data-pipeline/magnetic_lines.py::export_run
Gate: tests/data/test_magnetic_line_export.py::test_rights_and_member_custody

M03-021 WHILE online M03 is unadmitted, THE method interface SHALL expose CLOSED with the exact local recipe and reason, and SHALL not enqueue or replay a result as a new computation.
Implementation: app/magnetic_contract.py::eligibility; frontend/src/api/magnetic-contracts.ts
Gate: tests/api/test_magnetic_jobs.py::test_closed_profile_and_zero_dispatch

M03-022 WHEN future online M03 activation is reviewed and admitted, THE owned child workflow SHALL run this exact core on newly submitted data, enforce attempt-bound native CPU/wall/RSS/disk custody and retain failed/cancelled attempts durably.
Implementation: app/magnetic_contract.py; app/magnetic_compute.py; app/worker.py
Gate: tests/api/test_magnetic_jobs.py::test_real_owned_child_limits_cancel_and_recovery

M03-023 WHEN future magnetic datasets/results are integrated with durable storage/export/recovery, THE persistence contract SHALL bind owned source/input/result hashes and method version and refuse unknown or deleted objects without extending the current recovery inventory silently.
Implementation: app/magnetic_contract.py; app/bundle.py; app/database.py
Gate: tests/api/test_magnetic_recovery.py::test_child_export_restore_and_deletion_authority

M03-024 WHEN the M03 instrument is integrated, THE shared-shell selected-project workbench SHALL link map, line/tie profiles, crossover table, residuals and directional power through stable row/segment/cell identities, physical axes and truthful masks/lane labels.
Implementation: frontend/src/components/MagneticLineInstrument.tsx; frontend/src/components/magnetic-view-data.ts; frontend/src/pages/Workbench.tsx
Gate: frontend/e2e/magnetic-lines.spec.ts::linked_values_masks_and_parameter_recompute

M03-025 WHEN M03 documentation and architecture content are integrated, THE wiki/course SHALL transcribe this source-backed physics and worked user/synthetic/field eligibility distinctions, with EN/ES equations, assumptions, inline Cite/per-section Refs and theme-aware diagrams using existing shell primitives.
Implementation: docs/methods/magnetic-processing/01_lines-and-grids.md; frontend/src/components/MagneticLineCourse.tsx; frontend/public/svg/tech/magnetic-lines.svg; frontend/src/architecture.ts
Gate: tests/data/test_magnetic_docs.py::test_sources_worked_commands_and_scope; frontend/e2e/magnetic-lines.spec.ts::shell_language_theme_phone_and_diagrams

M03-026 WHEN acceptance is proposed, THE convergence report SHALL record every requirement separately with exact input/source/config/environment/result pins and pass/fail/unresolved/ineligible verdicts, including the unfinished field, host and durability gates.
Implementation: docs/design/features/m03-aeromagnetic-lines/convergence.json (future); scripts/check_magnetic_artifacts.py
Gate: scripts/check_magnetic_artifacts.py::main

No gate above currently exists as an M03 implementation. Requirement M03-022 cannot use a mocked child, supplied accounting trace or MT host receipt as its positive proof. M03-004's scientific rejection must use actual retrieved provider metadata. M03-026 must not rewrite the parent convergence ledger to pass from documentation presence.

Revision2 corrects26f0916 transparently. Literal gates also cover closed nested schemas/missing-null/counts, rereference transaction duplication/old-new receipt binding, epoch-mode swaps, weights/damping units and scale invariance, source-block edge/row mapping, metre-versus-dimensionless tolerances and the fixed authored geometry partition. Every field/online/native gate remains unexecuted. Full-survey parent acceptance cannot follow from this bounded400-row contract.
