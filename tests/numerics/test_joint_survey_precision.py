"""Independent exact-face comparison never changes an actual production model."""
import importlib.util
from pathlib import Path

import numpy as np

from test_joint_survey_optimizer import calibrated as calibrated


def test_actual_baseline_precision_receipt_retains_failures(calibrated):
    _,case,_,ledger,_=calibrated
    path=Path(__file__).resolve().parents[2]/'scripts/validate_joint_precision.py'
    spec=importlib.util.spec_from_file_location('trusted_precision_control',path)
    control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)
    before=[c['result']['q'].copy() for c in ledger['candidates'][:16]]
    records=control.compare_baselines(case,ledger)
    assert len(records)==16
    assert all(r['reference_stationarity_gate'] for r in records)
    assert any(not r['raw_reference_stationarity_gate'] for r in records)
    assert any(not r['actual']['prediction_gate'] for r in records)
    for candidate,original in zip(ledger['candidates'],before):
        assert np.array_equal(candidate['result']['q'],original)
