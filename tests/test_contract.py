from geophysicslab.io.contract import validate_observations


def test_observation_contract_accepts_valid_row():
    report = validate_observations([{"station_id": "s01", "x_m": 0, "y_m": 0, "frequency_hz": 1.0, "value": 4.2, "unit": "ohm_m"}])
    assert len(report["accepted"]) == 1
    assert not report["rejected"]


def test_observation_contract_rejects_nan_unknown_unit_and_bad_frequency():
    rows = [
        {"station_id": "nan", "x_m": 0, "y_m": 0, "frequency_hz": 1.0, "value": float("nan"), "unit": "ohm_m"},
        {"station_id": "unit", "x_m": 0, "y_m": 0, "frequency_hz": 1.0, "value": 1, "unit": "unknown"},
        {"station_id": "freq", "x_m": 0, "y_m": 0, "frequency_hz": 0, "value": 1, "unit": "ohm_m"},
    ]
    report = validate_observations(rows)
    assert len(report["rejected"]) == 3


def test_extreme_finite_value_is_flagged_not_silently_dropped():
    report = validate_observations([{"station_id": "s", "x_m": 0, "y_m": 0, "frequency_hz": 1, "value": 2e10, "unit": "gravity_mgal"}])
    assert len(report["accepted"]) == 1
    assert report["flagged"]
