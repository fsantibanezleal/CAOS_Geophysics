"""Actual frozen QR receipt fences, NOT job admission or a scientific rerun.

Uses explicitly supplied retained external bytes; does not rewrite run_id or
register a fictional owner job. Native/HTTP whole lifecycle remains separate.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
from uuid import UUID

import pytest

from app.errors import ApiError
from app.magnetic_line_survey_lifecycle import _publication_receipts,_qr_publication_execution,collect_inventory
from app.magnetic_line_survey_wire import BoundSurveyFile


def actual():
    value=os.environ.get('GEOPHYSICS_M03_QR_RETAINED_ROOT')
    if not value:pytest.skip('Explicit external retained QR evidence required; no fixture replacement')
    root=Path(value)/'worker';raw=(root/'result/result.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='275ae3a46c287f4d44db95608bff0fb674e7f4bf752a47e75c56be768f0d4c76'
    def read(name):return json.loads((root/name).read_bytes())
    result=json.loads(raw);inventory=collect_inventory(root.parent,root)
    parent=BoundSurveyFile(UUID(int=1),result['input']['original']['csv_sha256'],result['input']['original']['csv_bytes'],root/'not-read.csv')
    return root,result,inventory,parent,read('qr-fit-ready.json'),read('fit/physical-fit.json'),read('lifetime.json')['source_sha256']


def test_actual_qr_readiness_and_execution_file_source_binding():
    root,result,inventory,parent,ready,fit,pins=actual()
    actual_result=next(v for v in inventory if v['name']=='result/result.json')
    fit_file=next(v for v in inventory if v['name']=='fit/physical-fit.json')
    _publication_receipts(result,ready,actual_result,parent,fit,fit_file)
    _qr_publication_execution(result,root,inventory,pins)
    assert result['fit']['fit_count']==97 and result['verdict']['overall']=='unresolved'
    assert result['run_id']=='opened-original-s3-augmented-direct-qr-v3'  # Never a fictional job UUID.


@pytest.mark.parametrize('fault',['lsmr_alias','wrong_epoch','partial_fit','outer_twice','wrong_original','wrong_fit_hash'])
def test_actual_qr_readiness_adverse_fences(fault):
    root,result,inventory,parent,ready,fit,pins=actual()
    result,ready,fit=deepcopy(result),deepcopy(ready),deepcopy(fit)
    if fault=='lsmr_alias':fit['schema']='m03-global-physical-fit/2'
    elif fault=='wrong_epoch':ready['policy_epoch']='resolution_v2'
    elif fault=='partial_fit':result['fit']['fit_count']=96
    elif fault=='outer_twice':ready['evaluation_count']=2
    elif fault=='wrong_original':result['input']['original']['csv_sha256']='0'*64
    elif fault=='wrong_fit_hash':ready['fit_sha256']='0'*64
    with pytest.raises(ApiError):
        _publication_receipts(result,ready,next(v for v in inventory if v['name']=='result/result.json'),parent,
            fit,next(v for v in inventory if v['name']=='fit/physical-fit.json'))


def test_actual_qr_execution_pin_manifest_missing_or_changed_refuses():
    root,result,inventory,parent,ready,fit,pins=actual()
    for wrong in [{},dict.fromkeys(pins,'0'*64)]:
        with pytest.raises(ApiError):_qr_publication_execution(result,root,inventory,wrong)
    changed=deepcopy(inventory)
    next(v for v in changed if v['name']=='result/qr-execution.json')['sha256']='0'*64
    with pytest.raises(ApiError):_qr_publication_execution(result,root,changed,pins)
