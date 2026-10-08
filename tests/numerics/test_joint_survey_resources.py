"""Actual resource measurements and explicit adverse budget controls."""
import numpy as np
import pytest

import joint_survey_resources as resources


def test_actual_rss_and_scratch_receipt(tmp_path):
    assert resources.process_rss_bytes()>0
    with resources.JointResourceBudget(str(tmp_path)) as budget:
        array=np.ones((256,256),dtype=np.float64)
        with (tmp_path/'measured.npy').open('xb') as stream: np.save(stream,array,allow_pickle=False)
        receipt=budget.receipt(workflow_completed=False)
        assert receipt['peak_sampled_rss_bytes']>0
        assert receipt['peak_sampled_scratch_bytes']==(tmp_path/'measured.npy').stat().st_size
        assert receipt['samples']>=2
        assert not receipt['complete_workflow_resource_pass']
        assert not receipt['os_reservation']


@pytest.mark.parametrize('bad',['wall','rss','scratch','unmeasured'])
def test_real_gate_failure_not_allocation_estimate(tmp_path,monkeypatch,bad):
    budget=resources.JointResourceBudget(str(tmp_path))
    if bad=='wall': budget.deadline=budget.started-1.
    elif bad=='rss': monkeypatch.setattr(resources,'process_rss_bytes',lambda:resources.MAX_RSS+1)
    elif bad=='scratch': monkeypatch.setattr(resources,'scratch_bytes',lambda root:resources.MAX_SCRATCH+1)
    else:
        def unavailable(): raise OSError('unavailable measurement')
        monkeypatch.setattr(resources,'process_rss_bytes',unavailable)
    with pytest.raises((RuntimeError,OSError)): budget.checkpoint()


def test_repository_scratch_rejected(tmp_path):
    (tmp_path/'.git').mkdir()
    with pytest.raises(ValueError,match='repository'): resources.JointResourceBudget(str(tmp_path))
