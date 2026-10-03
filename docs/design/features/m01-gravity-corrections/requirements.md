# M01 local corrections requirements

Status: planned. Authorized by the approved product SDD and 2026-10-03 bounded implementation instruction.

R-G01 THE processor SHALL preserve input values, source identity, units, sign and correction lineage in a deterministic derivative.
Gate: tests/numerics/test_gravity_processing.py::test_station_correction_lineage

R-G02 WHEN normal gravity is requested, THE processor SHALL invoke pinned Boule WGS84 and satisfy independent Somigliana and published-height checks.
Gate: tests/numerics/test_gravity_processing.py::test_normal_gravity_oracles

R-G03 WHEN land plate removal is requested, THE processor SHALL invoke pinned Harmonica and subtract its effect with independent formula parity.
Gate: tests/numerics/test_gravity_processing.py::test_plate_formula_and_sign

R-G04 IF reference, elevation, plate or terrain has already been applied or the history is ambiguous, THEN THE processor SHALL reject duplicate or inconsistent processing.
Gate: tests/numerics/test_gravity_processing.py::test_no_double_correction

R-G05 IF units, datum, geometry, calibration, finite values or station identity are invalid, THEN THE processor SHALL reject with a field-specific reason.
Gate: tests/numerics/test_gravity_processing.py::test_invalid_contract

R-G06 WHEN orthometric heights are supplied, THE processor SHALL require named geoid undulation and propagate receiver/surface/common-geoid uncertainty.
Gate: tests/numerics/test_gravity_processing.py::test_height_datum_and_uncertainty

R-G07 WHERE terrain is included, THE processor SHALL accept only a traceable signed residual to the selected plate and reject a total-effect or density/reference mismatch.
Gate: tests/numerics/test_gravity_processing.py::test_terrain_semantics

R-G08 THE processor SHALL retain coordinate/value map arrays and flag outliers without exclusion or averaging.
Gate: tests/numerics/test_gravity_processing.py::test_qc_preserves_outliers

R-G09 WHEN the local CLI exports results, THE recipient SHALL obtain reproducible hashes, engine/config identity and fail on overwrite or malformed input.
Gate: tests/numerics/test_gravity_processing.py::test_cli_roundtrip

R-G10 THE documentation SHALL supply equations, assumptions, an other-data guide, a theme-aware diagram and an explicit unresolved full-M01 verdict.
Gate: tests/numerics/test_gravity_processing.py::test_wiki_contract
