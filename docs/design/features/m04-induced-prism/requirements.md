# M04 ordinary induced prism requirements

Status: proposed, implementation and all named gates NOT_RUN.
This bounded local unit is a prerequisite, not full parent M04 closure.

P04-01 THE operator SHALL accept only the exact typed request in contracts and
check metadata bounds for every array before scans, snapshots or kernel allocation.
Gate: tests/numerics/test_magnetic_forward.py::test_exact_protocol_preallocation

P04-02 THE operator SHALL preserve ENU metre geometry, actual tensor bounds,
x-fast active-cell order and receiver order without mutating caller arrays.
Gate: tests/numerics/test_magnetic_forward.py::test_geometry_order_and_immutability

P04-03 IF a receiver is inside or on the closed full tensor volume, THEN THE
operator SHALL reject before evaluating any kernel, independent of activity/chi.
Gate: tests/numerics/test_magnetic_forward.py::test_receiver_volume_rejection

P04-04 THE operator SHALL require explicit nT amplitude and positive-down
inclination/clockwise-from-north declination, with no field default or inference.
Gate: tests/numerics/test_magnetic_forward.py::test_field_direction_and_units

P04-05 THE operator SHALL invoke pinned actual SimPEG/Geoana scalar induction
with float64 RAM sensitivities, one process and an identity active susceptibility map.
Gate: tests/numerics/test_magnetic_forward.py::test_actual_engine_precision_order

P04-06 THE operator SHALL return component flux densities, projected linear TMI,
its susceptibility Jacobian and exact scalar magnitude anomaly as distinct quantities.
Gate: tests/numerics/test_magnetic_forward.py::test_components_projection_exact_magnitude

P04-07 THE operator SHALL satisfy separate Choclo and volume-dipole quadrature
controls, null/linearity/far-field/field-change controls under frozen tolerances.
Gate: tests/numerics/test_magnetic_forward.py::test_independent_prism_and_quadrature

P04-08 WHEN an induced interpretation is evaluated, THE tests SHALL retain an
independently constructed remanent/wrong-field counterexample; THE operator
SHALL NOT claim that forward agreement proves absence of remanence.
Gate: tests/numerics/test_magnetic_forward.py::test_remanence_and_wrong_field_nonclaims

P04-09 THE operator SHALL reject wrong runtime, dtype, shape or nonfinite kernel
output and return exact immutable owned arrays with no filesystem/network I/O.
Gate: tests/numerics/test_magnetic_forward.py::test_runtime_output_and_scope

P04-10 THE independent harness SHALL retain actual pins, commands, failed and
successful evidence separately; a local forward result SHALL NOT admit a host/method.
Gate: tests/numerics/test_magnetic_forward.py::test_external_pins_and_acceptance_boundary
