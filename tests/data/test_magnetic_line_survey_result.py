"""Actual original-row cold Result; schema shape alone cannot accept mutations."""
from copy import deepcopy
import os
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'data-pipeline'))
sys.path.insert(0,str(Path(__file__).parent))
import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_contract_v2 as schema
import magnetic_line_survey_result as results
import magnetic_line_survey_runtime as runtime
from magnetic_line_survey_export import export_result,verify_export
from test_magnetic_line_survey_corrections import full_case


@pytest.mark.parametrize('raw_mirroring',['denied','allowed'])
def test_actual_original_s3_full_result_semantics(tmp_path,raw_mirroring):
    metadata,_,inspection,_,request,_,_,roots,definitions=full_case(tmp_path,raw_mirroring=raw_mirroring)
    request['export_policy']['raw_requested']='include'
    worker=tmp_path/'worker'
    worker.mkdir()
    plan=dict(schema='m03-full-result-plan/1',csv_path=str(tmp_path/'s3-original.csv'),
        geometry_root=str(tmp_path/'geometry'),inspection=inspection,metadata=metadata,request=request,
        request_root=str(tmp_path/'request'),navigation_root=str(tmp_path/'navigation'),
        auxiliary_roots={key:str(value) for key,value in roots.items()},reference_definitions=definitions,
        run_id='original-s3-full-result-control')
    path=worker/'plan.json'
    path.write_bytes(base.canonical_bytes(plan))
    receipt=runtime.run_worker(Path(sys.base_prefix)/'python.exe',Path(os.environ['GEOPHYSICS_EXISTING_PACKAGE_ROOT']),worker,path)
    assert receipt['verdict']=='component_pass',(receipt,(worker/'stderr.log').read_text(),(worker/'stdout.log').read_text())
    assert receipt['active_processes']==0 and receipt['total_processes']==1
    result=base.strict_json((worker/'result/result.json').read_bytes())
    ready=base.strict_json((worker/'result-ready.json').read_bytes())
    assert ready['result_sha256']==base.digest(result) and ready['rows']==363
    assert schema.validate('SurveyResult',result)==result
    assert result['policy_epoch']=='fixed_basis_v1' and result['geometry']['schema']=='magnetic-line-survey-geometry/1'
    assert result['fit']['fit_count']==25 and result['partitions']['evaluation_count']==1
    assert result['inventory']['original_rows']==result['inventory']['retained']==363
    assert result['verdict']['overall']=='unresolved' and result['verdict']['numerical_success'] is True
    assert result['evaluation']['verdict']['overall']=='unresolved'
    assert len(result['channels'])==5 and len(result['grid'])==2
    raw=next(member for member in result['artifacts'] if member['role']=='raw')
    assert raw['permission']==raw_mirroring and raw['disposition']==('denied' if raw_mirroring=='denied' else 'unresolved')
    assert raw['bytes']==0 and raw['sha256'] is None
    assert not (worker/'result/original.csv').exists()
    verified=results.verify_result(worker/'result',temp_root=tmp_path)
    assert verified['rows']==363 and verified['custody_and_semantics']=='pass'
    assert verified['selected_model_recomputation']=='not_executed' and verified['replay_originals']=='not_available'
    assert verified['logical_members']<=192 and verified['physical_bytes']>0
    private=export_result(worker/'result',tmp_path/'private',scope='private',temp_root=tmp_path,
                          original_csv=tmp_path/'s3-original.csv')
    assert private['raw_disposition']==('denied' if raw_mirroring=='denied' else 'included')
    assert private['replay']==('unresolved' if raw_mirroring=='denied' else 'available')
    assert verify_export(tmp_path/'private',temp_root=tmp_path)==private
    assert results.verify_result(tmp_path/'private/result',temp_root=tmp_path)['result_sha256']==base.digest(result)
    assert (tmp_path/'private/original.csv').exists()==(raw_mirroring=='allowed')
    public=export_result(worker/'result',tmp_path/'public',scope='public',temp_root=tmp_path,
                         original_csv=tmp_path/'s3-original.csv')
    assert verify_export(tmp_path/'public',temp_root=tmp_path)==public
    if raw_mirroring=='denied':
        assert public['result'] is None and public['original'] is None and public['raw_disposition']=='denied'
        assert {item.name for item in (tmp_path/'public').iterdir()}=={'export.json'}
        assert all(member['role']=='withheld' and member['name'].startswith('withheld-') for member in public['redacted'])
        # A forged receipt plus copied exact original cannot override the
        # recorded transitive denial. No historical control rights are changed.
        forged=deepcopy(private)
        forged.update(original=dict(name='original.csv',bytes=metadata['original']['csv_bytes'],
            sha256=metadata['original']['csv_sha256']),raw_disposition='included',replay='available')
        (tmp_path/'private/export.json').write_bytes(base.canonical_bytes(forged))
        (tmp_path/'private/original.csv').write_bytes((tmp_path/'s3-original.csv').read_bytes())
        with pytest.raises(core.SurveyError):
            verify_export(tmp_path/'private',temp_root=tmp_path)
        (tmp_path/'private/export.json').write_bytes(base.canonical_bytes(private))
        (tmp_path/'private/original.csv').unlink()
    else:
        from magnetic_line_survey_cli import replay_local,verify_local
        assert public['result'] is not None and public['original'] is not None
        # A separately rights-scoped authored control, not the denied original
        # or a field licence: identical raw/science, declared generator grant.
        replay=replay_local(tmp_path/'private',tmp_path/'replay',data_root=tmp_path,temp_root=tmp_path)
        assert replay['scientific_members']=='pass' and replay['field_acceptance']=='unresolved'
        verified=verify_local(tmp_path/'private/result',tmp_path/'cold-verification',temp_root=tmp_path)
        assert verified['selected_model_recomputation']=='pass'
    with pytest.raises(core.SurveyError):
        export_result(worker/'result',tmp_path/'private',scope='private',temp_root=tmp_path)
    for change in ('count','epoch','fit_count','axis','height','residual','overall','false_gates','edge','aux_rights'):
        wrong=deepcopy(result)
        if change=='count':
            wrong['inventory']['retained']-=1
        elif change=='epoch':
            wrong['policy_epoch']='resolution_v2'
        elif change=='fit_count':
            wrong['fit']['fit_count']=24
        elif change=='axis':
            wrong['grid'][0]['easting_axis']['ordered_ids_sha256']='0'*64
        elif change=='height':
            wrong['grid'][1]['config']['plane_upward_m']-=1.
        elif change=='residual':
            wrong['evaluation']['rmse_nT']+=1.
        elif change=='overall':
            wrong['verdict']['overall']='pass'
        elif change=='false_gates':
            wrong['verdict']['overall']='pass'
            for gate in wrong['verdict']['gates']:
                gate['verdict']='pass'
        elif change=='edge':
            wrong['channels'][1]['state'][-1]['output_channel_sha256']='0'*64
        elif change=='aux_rights':
            wrong['input']['auxiliary_identities'][0]['rights']['raw_mirroring']='allowed' if raw_mirroring=='denied' else 'denied'
        with pytest.raises(core.SurveyError):
            results.verify_result(worker/'result',wrong,temp_root=tmp_path,allow_uncommitted=True)
