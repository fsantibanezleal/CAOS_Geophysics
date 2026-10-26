# EARS requirements and future named gates

Status: FIXED_REQUIREMENTS / PARTIAL_LOCAL_IMPLEMENTATION. The original proposed all-NOT_RUN/file-absent status is historical; ordinary modules now exist. Requirements and thresholds below are unchanged. Current executed coverage and explicit missing CLI/resource/field gates are in [tasks](tasks.md) and the [local review packet](continuation-review-packet.md). A documentation/source-invariance check is not a numerical or admission PASS. These requirements implement one local subvertical, not whole #42/#50 acceptance.

R-W08-001 THE local boundary SHALL use exactly supplied immutable MiniSEED/StationXML bytes and independently measured byte counts/SHA, keeping request/scientific/binary/source-declaration hash dialects distinct. Gate: `tests/data/test_waveform_input.py::test_exact_bytes_hash_domains_and_immutability`.

R-W08-002 WHEN untrusted records exceed raw/record/sample/encoding bounds or contain malformed headers/blockette chains, THE boundary SHALL reject before the relevant native decoder/allocation call, including records outside the conditioning slice. Gate: `tests/data/test_waveform_input.py::test_record_preflight_before_native_decode`.

R-W08-003 WHEN XML contains DTD/entities/ambiguous namespace, excessive depth/nodes/text/coefficients or invalid grammar, THE boundary SHALL reject before native inventory construction and never retrieve external content. Gate: `tests/data/test_waveform_input.py::test_stationxml_preflight_before_inventory`.

R-W08-004 THE boundary SHALL preserve exact NSLC/UTC correction/sample-grid semantics and reject unsupported clocks/rates without interpolation or silent merging. Gate: `tests/data/test_waveform_input.py::test_time_corrections_rates_gaps_and_overlaps`.

R-W08-005 WHEN nested identity/epoch coverage is missing, ambiguous or partial, THE result SHALL remain QC-only with no physical/pick arrays and no fabricated response. Gate: `tests/data/test_waveform_input.py::test_nested_identity_full_window_epoch_and_qc_only`.

R-W08-006 THE local calculation SHALL validate complete linear stage units/gains/decimation/response consistency and retain native component orientation without unit/sign/axis guesses. Gate: `tests/numerics/test_waveform_picks.py::test_stage_chain_units_gain_orientation_and_polarity`.

R-W08-007 WHEN samples are flat, detected/suspected clipped or carry blocking flags, THE result SHALL retain original counts/QC and suppress physical/candidate products; unknown rails/clock sigma SHALL remain unknown. Gate: `tests/data/test_waveform_input.py::test_clipping_flags_unknown_rails_and_missing_components`.

R-W08-008 THE actual scientific engine SHALL produce the specified native conditional response-corrected trace, audited complex operator and correct time/unit metadata on an admitted real-format control; incompatible/missing engine SHALL not be mocked or installed implicitly. Gate: `tests/numerics/test_waveform_picks.py::test_response_epoch_and_classical_picks`.

R-W08-009 THE native response result SHALL satisfy independent constant-gain, analytic poles/zeros and direct-DFT oracles within predeclared tolerances, retaining water-level and prefilter assumptions. Gate: `tests/numerics/test_waveform_picks.py::test_independent_response_oracles_and_stabilization`.

R-W08-010 THE filter SHALL use recorded SOS/padding/forward-backward semantics and expose its edge mask/acausality without promising unbiased real-time picks. Gate: `tests/numerics/test_waveform_picks.py::test_sos_filter_oracle_edges_and_acausality`.

R-W08-011 THE spectra SHALL have explicit window/overlap/normalization and physical density units, satisfy independent DFT/Parseval controls and never use PSD as amplitude or magnitude. Gate: `tests/numerics/test_waveform_picks.py::test_welch_dft_parseval_and_units`.

R-W08-012 THE classical detector SHALL implement exact trailing squared windows/hysteresis/refractory/truncation semantics with phase/sigma null, not frozen comparator P/S relabelling. Gate: `tests/numerics/test_waveform_picks.py::test_direct_stalta_onsets_and_no_phase_fabrication`.

R-W08-013 WHEN an actual submitted numerical parameter changes, THE corresponding computed arrays/control receipt SHALL change as predicted by an independent oracle while source bytes/hashes stay fixed; labels SHALL never influence prediction. Gate: `tests/numerics/test_waveform_picks.py::test_actual_parameter_effects_and_reference_noninterference`.

R-W08-014 WHEN analyst references are available, THE evaluator SHALL use only sealed predictions, exact source-valid reference conversion and fixed one-to-one unlabelled matching with complete failure denominators, never claim posterior/calibrated P/S F1. Gate: `tests/numerics/test_waveform_picks.py::test_sealed_reference_conversion_matching_and_residuals`.

R-W08-015 WHEN a future original Ridgecrest case is acquired, THE case SHALL pin actual provider bytes/rights/epoch and retain any original ineligible/unavailable outcome without replacement or synthetic truth. Gate: `tests/data/test_waveform_ridgecrest.py::test_original_bytes_response_epoch_and_retained_outcome`.

R-W08-016 THE CLI SHALL read only explicit bounded local regular-file handles and write only a fresh requested private output, with no acquisition/overwrite/private error content or API activation. Gate: `tests/data/test_waveform_input.py::test_local_paths_safe_errors_and_no_network`.

R-W08-017 THE derived artifact SHALL pre-count/write/verify bounded uncompressed finite typed arrays and exact hashes, without a whole-graph ZIP or scientific reserialization of original inputs. Gate: `tests/data/test_waveform_input.py::test_bounded_artifact_arrays_and_independent_reopen`.

R-W08-018 WHEN nominal/upper/malformed/native-crash/timeout/cancel profiles execute, THE local receipt SHALL report actual child/parent/process-tree wall/CPU/peak/scratch and terminal outcome without assumed telemetry, device or VPS admission. Gate: `tests/data/test_waveform_resources.py::test_cold_matrix_cancel_timeout_crash_and_measurements`.

R-W08-019 THE implementation/test lane SHALL preserve all frozen M08/M13 source/model/cohort/parity/canonical identities and avoid API/frontend/source-ledger/environment mutations outside explicit approval. Gate: `tests/data/test_waveform_input.py::test_frozen_sources_and_local_only_nonclaims`.

R-W08-020 WHEN required engines/private originals/rights/telemetry are missing, THE handoff SHALL disclose skipped/unresolved gates and SHALL NOT claim whole M08, #42/#50, method, provider, browser or host acceptance. Gate: `tests/data/test_waveform_resources.py::test_missing_engine_case_and_telemetry_closed`.
