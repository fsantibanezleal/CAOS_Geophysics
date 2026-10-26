"""Actual original S3 cold DAG/global25 fits/full grid, no field substitution."""
from copy import deepcopy
from hashlib import sha256
import math
import os
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'data-pipeline'))
sys.path.insert(0,str(Path(__file__).parent))
import magnetic_line_contract as base
import magnetic_line_survey_contract_v2 as schema
import magnetic_line_survey_io as io
import magnetic_line_survey_representation as representation
import magnetic_line_survey_runtime as runtime
from test_magnetic_line_survey_corrections import full_case


def test_actual_original_s3_global_grids_and_height(tmp_path):
    metadata,_,inspection,_,request,_,_,roots,definitions=full_case(tmp_path)
    worker=tmp_path/'worker'
    worker.mkdir()
    plan=dict(schema='m03-physical-grid-plan/1',csv_path=str(tmp_path/'s3-original.csv'),
        geometry_root=str(tmp_path/'geometry'),inspection=inspection,metadata=metadata,request=request,
        request_root=str(tmp_path/'request'),navigation_root=str(tmp_path/'navigation'),
        auxiliary_roots={key:str(value) for key,value in roots.items()},reference_definitions=definitions)
    path=worker/'plan.json'
    path.write_bytes(base.canonical_bytes(plan))
    receipt=runtime.run_worker(Path(sys.base_prefix)/'python.exe',Path(os.environ['GEOPHYSICS_EXISTING_PACKAGE_ROOT']),worker,path)
    assert receipt['verdict']=='component_pass',(receipt,(worker/'stderr.log').read_text(),(worker/'stdout.log').read_text())
    assert receipt['active_processes']==0 and receipt['total_processes']==1
    ready=base.strict_json((worker/'physical-grid-ready.json').read_bytes())
    fitted=base.strict_json((worker/'fit/physical-fit.json').read_bytes())
    result=base.strict_json((worker/'grids/grid-workflow.json').read_bytes())
    assert ready['rows']==363 and ready['grid_count']==2 and ready['result_sha256']==base.digest(result)
    assert fitted['fit']['fit_count']==25 and fitted['evaluation_count']==1
    assert result['full_result']=='not_assembled' and result['field_acceptance']=='unresolved'
    assert result['original']==metadata['original'] and result['request_sha256']==base.digest(request)
    assert sha256((tmp_path/'s3-original.csv').read_bytes()).hexdigest()==metadata['original']['csv_sha256']
    fr=io.Reader(worker/'fit')
    source_values=list(fr.cells(fitted['fit']['sources']))
    sources=list(zip(source_values[::3],source_values[1::3],source_values[2::3],strict=True))
    strengths=list(fr.cells(fitted['fit']['coefficients']))
    reader=representation.Reader(worker/'grids')
    for index,grid in enumerate(result['grid']):
        schema.validate('SurveyGridReceipt',grid)
        east=list(reader.cells(grid['easting_axis']))
        north=list(reader.cells(grid['northing_axis']))
        values=list(reader.cells(grid['values']))
        masks=list(io.Reader(worker/'sealed').cells(grid['support_mask']))
        config=grid['config']
        assert len(values)==3185 and all(mask==4096 for mask in masks)
        assert east==[config['origin_e_m']+i*config['spacing_e_m'] for i in range(config['nx'])]
        assert north==[config['origin_n_m']+i*config['spacing_n_m'] for i in range(config['ny'])]
        # Independent original 1/r metric formula, ALL cells/ALL sources. No
        # fit truth or outer scoring enters this identity check.
        expected=[math.fsum(q/math.hypot(e-x,n-y,config['plane_upward_m']-z)
                  for (x,y,z),q in zip(sources,strengths,strict=True)) for n in north for e in east]
        assert values==pytest.approx(expected,rel=1e-12,abs=1e-12)
        assert grid['role']==('fitted_plane' if index==0 else 'continued_plane')
        for key in ('easting_axis','northing_axis','values'):
            reader.verify(grid[key])
    assert result['grid'][1]['config']['plane_upward_m']==request['grid']['plane_upward_m']+100.
    assert result['fft_continuation']['verdict']=='eligible'
    # Eligibility and comparison are not a parity PASS on a finite boundary.
    assert result['fft_continuation']['maximum_direct_difference_nT']>=0
    reader.reject_unknown(extra=('grid-workflow.json',))
    wrong=deepcopy(result['grid'][0])
    wrong['easting_axis']['role']='grid_coordinate'
    with pytest.raises(ValueError):
        schema.validate('SurveyGridReceipt',wrong)
