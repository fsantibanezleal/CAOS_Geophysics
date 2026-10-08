# Protected surveyed-input and local-replay requirements

Status: planned

This unit implements the existing survey-inversion R-414..417 custody boundary.
It does not authorize online inversion or accept a failed scientific matrix.

R-441 WHEN original bytes and a physical request are supplied, THE adapter SHALL
verify their exact owned asset/source relationship, full source hash/count and
explicit ENU datum/units/quantity before creating a geometry-only dataset.
Gate: tests/api/test_magnetic_owned_survey.py::test_owned_original_dataset.

R-442 IF source, physical metadata, request bytes or ownership drift, THEN THE
adapter SHALL refuse without native inversion or a successful result reference.
Gate: tests/api/test_magnetic_owned_survey.py::test_input_drift_refused.

R-443 WHILE online admission is unaccepted, THE method registry SHALL map the
actual parser, calibration, evaluation and export functions to a closed online
lane and an explicit local replay lane, without queuing an inverse.
Gate: tests/api/test_magnetic_owned_survey.py::test_source_backed_mapping_and_closed_online.

R-444 WHEN a local complete generation is imported, THE custody adapter SHALL
verify every numeric member, exact dataset request and generation identities,
retain a single bounded ZIP under its owned job receipt and publish only after
exclusive fsync/readback and an owned SQLite transaction.
Gate: tests/api/test_magnetic_owned_custody.py::test_real_generation_owned_roundtrip.

R-445 IF quota, duplicate path, corruption, wrong owner or interrupted publication
occurs, THEN THE adapter SHALL preserve originals/prior results and refuse
successful partial pointers; uncertain commits SHALL retain recoverable debt.
Gate: tests/api/test_magnetic_owned_custody.py::test_custody_refusals.

R-446 WHEN a result is read or exported, THE adapter SHALL recheck the owned
dataset/job/source/request and exact stored ZIP hash and bytes before returning
the verified scientific projection or original numeric archive.
Gate: tests/api/test_magnetic_owned_custody.py::test_read_export_drift_refused.

R-447 WHEN the selected job changes or a request aborts, THE client SHALL retain
selected-receipt binding, same-origin CSRF and abort semantics and verify all
native descriptors before making a view available.
Gate: frontend/src/test/magnetic-processing.test.ts.
