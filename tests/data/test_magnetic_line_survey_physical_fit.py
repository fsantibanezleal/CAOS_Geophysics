"""Actual cold original-S3 physical correction plus frozen global 25-fit execution."""
from pathlib import Path
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'data-pipeline'))
sys.path.insert(0, str(Path(__file__).parent))
import magnetic_line_contract as base
import magnetic_line_survey_io as io
import magnetic_line_survey_runtime as runtime
from test_magnetic_line_survey_corrections import full_case


def test_actual_original_s3_physical_global_fits(tmp_path):
    metadata, _, inspection, _, request, _, _, roots, definitions = full_case(tmp_path)
    worker = tmp_path/'worker'
    worker.mkdir()
    plan = dict(schema='m03-physical-fit-plan/1', csv_path=str(tmp_path/'s3-original.csv'),
        geometry_root=str(tmp_path/'geometry'), inspection=inspection, metadata=metadata, request=request,
        request_root=str(tmp_path/'request'), navigation_root=str(tmp_path/'navigation'),
        auxiliary_roots={key:str(value) for key,value in roots.items()}, reference_definitions=definitions)
    path = worker/'plan.json'
    path.write_bytes(base.canonical_bytes(plan))
    receipt = runtime.run_worker(Path(sys.base_prefix)/'python.exe', Path(os.environ['GEOPHYSICS_EXISTING_PACKAGE_ROOT']), worker, path)
    assert receipt['verdict']=='component_pass', (receipt, (worker/'stderr.log').read_text(), (worker/'stdout.log').read_text())
    assert receipt['total_processes']==1 and receipt['active_processes']==0
    ready = base.strict_json((worker/'physical-fit-ready.json').read_bytes())
    fitted = base.strict_json((worker/'fit/physical-fit.json').read_bytes())
    assert ready['rows']==363 and ready['fit_count']==25 and ready['evaluation_count']==1
    assert ready['result_sha256']==base.digest(fitted) and ready['full_result']=='not_assembled'
    assert fitted['original']==metadata['original'] and fitted['field_acceptance']=='unresolved'
    assert fitted['predictive_acceptance']=='not_established'
    reader = io.Reader(worker/'fit')
    candidates = list(reader.table(fitted['fit']['candidates']))
    assert len(candidates)==24 and all(candidate['solve']['verdict']=='pass' for candidate in candidates)
    assert fitted['fit']['solve']['stationarity_relative']<=1e-9
    observed, predicted, residual = [list(reader.cells(ref)) for ref in fitted['outer_arrays']]
    assert all(actual==value-prediction for value,prediction,actual in zip(observed,predicted,residual,strict=True))
    assert sum(line['scored'] for line in reader.table(fitted['per_line']))==fitted['scored']
    assert sum(line['excluded'] for line in reader.table(fitted['per_line']))==fitted['excluded']
    for ref in [fitted['fit'][key] for key in ('sources','column_scales','coefficients','candidates')] + \
               fitted['outer_arrays']+[fitted['outer_positions'],fitted['per_line']]:
        reader.verify(ref)
    reader.reject_unknown(extra=('physical-fit.json',))
