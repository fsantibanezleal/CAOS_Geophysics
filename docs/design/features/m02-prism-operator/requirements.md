# M02 ordinary prism forward operator requirements

Status: narrowed implementation authorized at design head `361b66f`; local
controls executed as recorded in validation, independent pinned code review pending.
This is a separate amendment after merged PR120, not inverse approval or full
M02 acceptance. Scope: [design](design.md), [gates](validation.md), [tasks](tasks.md).
Approved principles: CPU Geoana, separate Choclo/volume oracle and exact units.

P02-01 THE operator SHALL accept exactly the six typed in-memory request keys
and reject unknown/missing keys, wrong enums/types/shapes or nonfinite arrays
before constructing an engine; it SHALL NOT coerce an untyped survey.
Gate: tests/numerics/test_gravity_forward.py::test_exact_protocol_and_types

P02-02 WHEN geometry is admitted, THE operator SHALL require a declared local
east/north/up metre frame, 1..2048 receivers and capped positive-width tensor
cells, finite strictly increasing edges/volumes and at least one active cell.
Gate: tests/numerics/test_gravity_forward.py::test_geometry_counts_and_frame

P02-03 IF any receiver is not strictly outside the closed full tensor source
volume, THEN THE operator SHALL reject before evaluating any prism, even when
the containing cell is inactive or has zero density.
Gate: tests/numerics/test_gravity_forward.py::test_receiver_outside_volume_policy

P02-04 THE operator SHALL retain caller ordering and x-fast cell/active mapping,
export explicit six-bound cell geometry and never mutate submitted arrays.
Gate: tests/numerics/test_gravity_forward.py::test_xfast_activity_and_input_immutability

P02-05 THE operator SHALL call actual pinned SimPEG/Geoana using float64 RAM
sensitivities, one process and an identity active-density map; it SHALL NOT use
a substitute kernel, disk cache or a configurable backend hook.
Gate: tests/numerics/test_gravity_forward.py::test_actual_required_engine_and_precision

P02-06 WHEN density is mapped, THE operator SHALL convert physical kg/m3 contrast
to g/cc by 1/1000 once and return upward mGal and Jacobian mGal/(kg/m3) with
the same 1/1000 factor; signed and zero density SHALL remain valid.
Gate: tests/numerics/test_gravity_forward.py::test_sign_units_linearity_and_jacobian

P02-07 THE operator SHALL meet direct Choclo and independent quadrature/physical
limits under the frozen forward tolerances, without an engine-own-oracle comparison.
Gate: tests/numerics/test_gravity_forward.py::test_independent_choclo_prisms
Gate: tests/numerics/test_gravity_forward.py::test_volume_quadrature_and_physical_limits

P02-08 WHEN a result is returned, THE operator SHALL satisfy the exact six-key
result protocol, finite shapes, immutable output copies and mathematical state
identity; engine nonfinite/shape/precision failures SHALL raise literal errors.
Gate: tests/numerics/test_gravity_forward.py::test_output_protocol_and_engine_failures

P02-09 THE review harness SHALL verify fixed runtime and targeted source/binary
pins externally and retain actual tool/operator provenance; THE pure operator
SHALL NOT falsely report that it performed filesystem source verification.
Gate: tests/numerics/test_gravity_forward.py::test_runtime_epoch_and_external_source_pins

P02-10 THE operator SHALL have no application file/network/GUI/CLI/environment/
canonical I/O, optimizer, preprocessing, defaults for missing field metadata,
callbacks, plugin hooks or host/GPU admission behavior.
Gate: tests/numerics/test_gravity_forward.py::test_no_io_hooks_or_inverse_behavior

P02-11 THE implementation review SHALL retain rejected geometry, null/signed
controls, wrong unit/factor/precision/source negatives and all forward failures;
it SHALL NOT infer field eligibility, geological truth or inverse convergence.
Gate: tests/numerics/test_gravity_forward.py::test_negative_controls_and_literal_scope

The named gates now exist with local results in [validation](validation.md);
this is not independent acceptance or full M02. Broad survey types/asset binding,
calibration seeds/epsilon/null inverse policy and pinned optimizer stops remain
pending under the separate [merged plan](../m02-survey-inversion/tasks.md).
