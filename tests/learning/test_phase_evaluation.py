"""Classical and learned pickers must use the same trace IDs and failure denominator."""

import pytest

import numpy as np

from phase_picking import classical_stalta_picks, evaluate_matched_picks


def test_matched_inputs_and_failed_picks():
    labels = {
        "a": {"P": 1.0, "S": 2.0},
        "b": {"P": 1.1, "S": 2.2},
    }
    classical = {
        "a": {"P": 1.1, "S": None},
        "b": {"P": None, "S": 2.4},
    }
    learned = {
        "a": {"P": 1.0, "S": 2.1},
        "b": {"P": None, "S": None},
    }
    result = evaluate_matched_picks(labels, {"M08": classical, "M13": learned}, tolerance_s=0.2)
    assert result["M08"]["P"]["total"] == result["M13"]["P"]["total"] == 2
    assert result["M13"]["P"]["missed"] == 1
    assert result["M13"]["S"]["missed"] == 1
    assert result["M08"]["P"]["recall"] == pytest.approx(0.5)
    assert result["M08"]["S"]["timing_absolute_s"] == [pytest.approx(0.2)]
    with pytest.raises(ValueError, match="identical"):
        evaluate_matched_picks(labels, {"M08": classical, "M13": {"a": learned["a"]}}, tolerance_s=0.2)


def test_classical_picker_does_not_use_reference_times():
    values = np.zeros((1024, 3), dtype=np.float32)
    values[320:360, 2] = 1
    values[680:730, 2] = 1.5
    picked = classical_stalta_picks(values, sample_interval_s=0.01, threshold=2.5)
    assert picked["P"] == pytest.approx(3.2, abs=0.1)
    assert picked["S"] == pytest.approx(6.8, abs=0.1)
    assert classical_stalta_picks(np.zeros_like(values), sample_interval_s=0.01) == {"P": None, "S": None}
