"""Frozen global prediction and selection controls, not field acceptance."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'data-pipeline'))
import magnetic_line_survey as core


def test_frozen_inner_tie_prefers_larger_damping_then_depth():
    from magnetic_line_survey_fit import select_candidate
    candidates = [dict(depth_m=200.,damping=.01,mean_rmse_nT=1.),
                  dict(depth_m=500.,damping=1.,mean_rmse_nT=1.+5e-10),
                  dict(depth_m=200.,damping=100.,mean_rmse_nT=1.+2e-9)]
    assert select_candidate(candidates)==candidates[1]
    with pytest.raises(core.SurveyError):
        select_candidate([dict(depth_m=200.,damping=.01,mean_rmse_nT=float('nan'))])


def test_global_query_prediction_matches_independent_all_source_kernel():
    from magnetic_line_survey_fit import predict_global
    np,_ = core.engines()
    query = np.array([[37.,-54.,91.],[-120.,83.,113.],[191.,132.,121.]],dtype=np.float64)
    sources = np.array([[0.,0.,-200.],[43.,21.,-200.],[-193.,85.,-200.]],dtype=np.float64)
    coefficients = np.array([2300.,-1100.,700.],dtype=np.float64)
    for array in (query,sources,coefficients):
        array.flags.writeable=False
    expected = (1/np.sqrt(np.sum((query[:,None,:]-sources[None,:,:])**2,axis=2)))@coefficients
    assert np.max(np.abs(predict_global(query,sources,coefficients)-expected)) <= 1e-11*max(1.,float(np.max(np.abs(expected))))


def test_large_query_requires_actual_job_before_native_import(monkeypatch):
    from magnetic_line_survey_fit import predict_global
    monkeypatch.setattr(core,'engines',lambda:pytest.fail('Refusal must precede numerical import'))
    with pytest.raises(core.SurveyError,match='resource_refused'):
        predict_global(None,None,None,job_handle=True)


def test_owned_mappings_close_before_external_directory_cleanup(tmp_path):
    from magnetic_line_survey_fit import mapped_array,mapping_lifetime
    import magnetic_line_survey_io as io
    np,_ = core.engines()
    source = tmp_path/'input'
    source.mkdir()
    ref = io.write_array(source,'owned','magnetic',[1.,2.],[2],'float64','nT','1'*64)
    with io.scratch_directory(tmp_path) as scratch, mapping_lifetime() as mappings:
        value = mapped_array(io.Reader(source),ref,Path(scratch)/'mapped.bin',np,registry=mappings)
        assert list(value)==[1.,2.] and value.flags.writeable is False
        handle = value._mmap
        assert not handle.closed
    assert handle.closed and not Path(scratch).exists()
