# M03 mapped flight-line processing requirements

Status: local component gates pass; full M03 remains unaccepted. The component does not replace the SDD's provider-data acceptance gate.

R-M03-01 THE CSV adapter SHALL require an explicit one-to-one map for projected easting/northing, field value, line ID, flight/tie role and sensor height.
Gate: tests/numerics/test_magnetic_processing.py::test_csv_adapter_requires_explicit_columns_and_hashes_original_bytes

R-M03-02 THE request SHALL declare its source digest, citation, rights, processing state, measured quantity, value unit, sensor-height reference, CRS and projected metric coordinate frame.
Gate: tests/numerics/test_magnetic_processing.py::test_value_quantity_and_sensor_height_reference_are_mandatory and tests/numerics/test_magnetic_processing.py::test_geographic_degrees_are_rejected_for_metric_spacing

R-M03-03 WHEN height QC identifies an outlier, THE processor SHALL report it and retain the observation without applying a correction.
Gate: tests/numerics/test_magnetic_processing.py::test_height_outlier_is_reported_and_original_observation_is_retained

R-M03-04 THE holdout partition SHALL keep complete flight lines together and separate fit and held-out line IDs.
Gate: tests/numerics/test_magnetic_processing.py::test_blocked_whole_line_holdout_recovers_plane_without_fit_leakage

R-M03-05 THE held-out interpolation SHALL be scored only where the fit-supported triangulation predicts a finite value and SHALL report support coverage separately.
Gate: tests/numerics/test_magnetic_processing.py::test_blocked_whole_line_holdout_recovers_plane_without_fit_leakage

R-M03-06 THE gridded result SHALL preserve axes, units and an explicit support mask; unsupported cells SHALL NOT be presented as measured values.
Gate: tests/numerics/test_magnetic_processing.py::test_blocked_whole_line_holdout_recovers_plane_without_fit_leakage

R-M03-07 IF duplicate fit coordinates occur, THE processor SHALL reject them rather than silently averaging line observations.
Gate: tests/numerics/test_magnetic_processing.py::test_exact_duplicate_training_coordinate_fails_instead_of_averaging

R-M03-08 THE result SHALL make no correction, provider-grid equivalence, inverse-model or scientific-release claim without the corresponding source data and independent evidence.
Gate: tests/numerics/test_magnetic_processing.py::test_blocked_whole_line_holdout_recovers_plane_without_fit_leakage
