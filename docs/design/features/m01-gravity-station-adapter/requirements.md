# M01 ordinary gravity station adapter requirements

Status: local gates passed; main's independent pinned review/integration remains pending. Main approved the persisted design before code on 2026-10-03, including the explicit imported-file shadow check. All named gates below exist in the one new scoped test file. Parent product SDD approval is retained; this feature grants no API/host/field/full-M01 acceptance. Exact results and boundaries: [convergence](convergence.md).

R-GA01 WHEN the ordinary adapter receives a request, THE adapter SHALL accept only the exact version/method/dataset/config/integrity boundary in design.md and reject CSV/provider/flag-only objects, unknown operational variants and additional keys without scientific reinterpretation. Gate: tests/numerics/test_gravity_station_adapter.py::test_exact_contract_and_unsupported_inputs.

R-GA02 BEFORE copying, hashing or executing a request, THE adapter SHALL reject non-native objects, cycles, nonfinite values and declared station/depth/node/string/canonical-size overruns, without executing object hooks, thinning observations or invoking the core. Gate: tests/numerics/test_gravity_station_adapter.py::test_bounded_native_request_before_numerics.

R-GA03 WHEN parent/config hashes are supplied, THE adapter SHALL compare them to the exact submitted canonical objects and retain separate submitted/normalized config identities without equating either to a raw-file or provider-source hash. Gate: tests/numerics/test_gravity_station_adapter.py::test_exact_input_and_config_identity.

R-GA04 WHEN a valid correction request executes, THE adapter SHALL invoke the existing pinned process_survey exactly once on unchanged scientific inputs and return the complete unchanged core dataset/processing/qc result in a separate versioned envelope. Gate: tests/numerics/test_gravity_station_adapter.py::test_real_core_parity_preserves_request.

R-GA05 WHILE a known earlier correction state is supplied, WHEN a later target is requested, THE adapter SHALL retain verified history/originals and exact parent identity; repeated/backward targets or altered prior parameters/values/hashes SHALL reject rather than apply another correction. Gate: tests/numerics/test_gravity_station_adapter.py::test_exact_parent_resume_and_no_double_correction.

R-GA06 THE adapter's real-engine output SHALL satisfy the existing independently documented normal/height/plate/sign/unit and primitive-uncertainty oracles, with missing datum/error/instrument metadata rejected and no additional height/terrain/raw-instrument effect invented. Gate: tests/numerics/test_gravity_station_adapter.py::test_formula_sign_and_uncertainty_oracles.

R-GA07 THE adapter SHALL preserve full uncertainty model/components/warnings and reversible QC flags, including conservative bounds and legitimate primitive zero SD, without converting them into covariance, geological confidence, exclusions or later-transform eligibility. Gate: tests/numerics/test_gravity_station_adapter.py::test_uncertainty_kind_and_flags_preserved.

R-GA08 IF request/core/environment/result verification fails, THEN THE adapter SHALL emit only the fixed safe error record in design.md, no success/partial scientific result, raw exception text, arbitrary keys, citations, values, paths or tracebacks. Gate: tests/numerics/test_gravity_station_adapter.py::test_safe_errors_do_not_disclose_input.

R-GA09 IF the reviewed core fingerprint, imported resolved __file__, pinned engine versions or declared runtime lane differs, THEN THE adapter SHALL fail closed without numerical execution or dependency/environment changes, including a preloaded shadow module. Gate: tests/numerics/test_gravity_station_adapter.py::test_runtime_and_core_pin_fail_closed.

R-GA10 WHEN a result is returned, THE adapter SHALL verify fresh core receipt invariants and bind complete result/input/submitted-config/normalized-config/output/module/engine identities, preserving exact known keys and false acceptance declarations. Gate: tests/numerics/test_gravity_station_adapter.py::test_result_receipt_integrity.

R-GA11 THE adapter SHALL perform no user-directed file/network/subprocess/storage/log/API/registry/worker action, no field acquisition or host authorization, and its ownership SHALL be confined to the two new implementation paths after approval. Gate: tests/numerics/test_gravity_station_adapter.py::test_pure_boundary_and_false_acceptance.
