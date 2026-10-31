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


def test_precision_gate_excludes_only_explicit_nonconverged_candidates():
    path=Path(__file__).resolve().parents[2]/'scripts/validate_joint_precision.py'
    spec=importlib.util.spec_from_file_location('trusted_precision_summary',path)
    control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)
    good={key:True for key in ('objective_gate','model_gate','prediction_gate','stationarity_gate')}
    bad={key:False for key in good}
    rows=[]
    for index in range(384):
        status='nonconverged' if index<37 else 'converged'
        rows.append({'production_status':status,'actual':{'objective_gate':True,'model_gate':False,
            'prediction_gate':False,'stationarity_gate':False} if status=='nonconverged' else good,
            'reference_stationarity_gate':True})
    summary=control.summarize_precision(rows)
    assert summary['accepted_candidate_count']==347
    assert summary['retained_nonconverged_candidate_count']==37
    assert summary['all_scientific_predicates_pass']
    rows[-1]['actual']=bad
    assert not control.summarize_precision(rows)['all_scientific_predicates_pass']
    rows[-1]['actual']=good;rows[-1]['production_status']='engine_error'
    assert not control.summarize_precision(rows)['all_scientific_predicates_pass']
