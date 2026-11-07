"""Literal original24 supplied controls; genuine positive failures stay red."""
import json
from time import monotonic

import choclo
import numpy as np
import pytest

import gravity_irls as irls
import gravity_survey_l2 as survey
import gravity_workflow_io as workflow
from test_gravity_irls import policy
from test_gravity_l2_selection import _LOCKED_PRISMS, locked_request, outer_request


@pytest.mark.parametrize('family',range(6))
@pytest.mark.parametrize('condition',range(4))
def test_original24_irls_science(family,condition,tmp_path,record_property):
    request,values,covariance=locked_request(family,condition)
    request['schema']='gravity-survey-irls-calibration-request-1'
    request['runtime_epoch']=irls.RUNTIME_EPOCH
    request['policy']['name']=irls.POLICY
    request['policy']['irls']=policy()
    started=monotonic()
    result=irls.calibrate_gravity_irls(request)
    outcome={'family':family,'condition':condition,'seed':700001+100*family+condition,
        'request_sha256':survey._digest(request),'result_sha256':result['result_sha256'],
        'selection_status':result['selection_status'],'selected_index':result['selected_index'],
        'outer_wrms':None,'model_rmse_ratio':None,
        'fits':tuple({'status':f['status'],'reason':f['reason'],'iterations':f['iterations'],
            'weight_updates':f['irls_terminal']['weight_updates']} for f in result['fits'])}
    # Persist literal actual outcomes before subsequent structural/science gates.
    record_property('original24_irls_outcome',json.dumps(outcome,sort_keys=True,allow_nan=False))
    complete={'schema':'gravity-calibration-archive-1','request':request,'result':result}
    workflow.publish_archive(tmp_path/'data',tmp_path/'temp','actual.gza',complete)
    irls.validate_gravity_irls(result,request)
    workflow.verify_calibration(workflow.read_archive(tmp_path/'data','actual.gza'))
    if result['selection_status']=='selected':
        rows=result['plan']['outer_rows']
        outer=outer_request(result,values[rows].copy())
        outer['schema']='gravity-survey-irls-evaluation-request-3'
        outer['calibration_request']=request
        if covariance is not None:
            outer['noise'].update(kind='full_covariance',values=covariance[np.ix_(rows,rows)],
                unit='mGal^2',cross_partition_dependence='possible_not_removed')
        else: outer['noise']['values'][:]=.005
        outer['noise']['values_sha256']=survey._digest({k:outer['noise'][k] for k in ('kind','unit','values')}|{'rows':rows})
        evaluated=irls.evaluate_gravity_irls(outer)
        outcome['outer_wrms']=evaluated['wrms']
        bounds=result['plan']['geometry']['active_cell_bounds_m']
        truth=np.zeros(len(bounds))
        for box,density in _LOCKED_PRISMS[family]:
            lengths=np.maximum(0.,np.minimum(bounds[:,1::2],box[1::2])-np.maximum(bounds[:,::2],box[::2]))
            truth+=density*np.prod(lengths,axis=1)/np.prod(bounds[:,1::2]-bounds[:,::2],axis=1)
        model=result['fits'][24]['model_kg_m3']
        baseline=float(np.linalg.norm(truth))
        outcome['model_rmse_ratio']=float(np.linalg.norm(model-truth)/baseline) if baseline>0. else None
        independent=np.array([sum(choclo.prism.gravity_u(*point,*box,float(density))*1e5
            for box,density in zip(bounds,model)) for point in request['plan']['request']['stations']['receivers_m']])
        np.testing.assert_allclose(independent,result['predictions']['gz_up_mgal'],rtol=1e-7,atol=1e-10)
    outcome['wall_seconds']=monotonic()-started
    record_property('original24_irls_scored',json.dumps(outcome,sort_keys=True,allow_nan=False))
    if family in (0,1) and condition in (0,1):
        assert result['selection_status']=='selected',outcome
        assert outcome['outer_wrms']<=2.,outcome
        assert outcome['model_rmse_ratio']<1.,outcome
