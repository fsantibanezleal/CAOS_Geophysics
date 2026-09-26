"""Fast stdlib-only committed-artifact contract; no computation or dependencies in CI."""
from pathlib import Path
import hashlib
import json
import math
import argparse
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'data-pipeline'))
from provenance import generator_fingerprint

ROOT=Path(__file__).resolve().parents[1]/"data/derived/v2"
EXPECTED_CASE_FAMILY={
    'GRAVITY_INTRUSION':'gravity', 'GRAVITY_DEEP_BODY':'gravity',
    'GRAVITY_NOISY':'gravity', 'GRAVITY_TILTED':'gravity',
    'MAGNETIC_DYKE':'magnetics', 'MAGNETIC_REMANENCE':'magnetics',
    'MAGNETIC_DEEP':'magnetics', 'MAGNETIC_NOISY':'magnetics',
    'MT_RESISTIVE':'mt', 'MT_CONDUCTIVE':'mt', 'MT_MIXED':'mt', 'MT_NOISY':'mt',
    'FWI_LAYERED':'seismic', 'FWI_FAULT':'seismic',
    'FWI_CYCLE_SKIP':'seismic', 'FWI_NOISY':'seismic',
    'JOINT_SHARED':'joint', 'JOINT_CONFLICT':'joint',
    'LEARNED_CNN':'learned', 'LEARNED_AUTOENCODER':'learned',
}
EXPECTED_METHODS={
    'gravity':{'l2','irls'},
    'magnetics':{'l2','irls','vector'},
    'mt':{'mt-lm','mt-adam','mt-neural'},
    'seismic':{'fwi-l2','fwi-multiscale'},
    'joint':{'l2','irls','joint-uncoupled','joint','pgi'},
    'learned':{'l2','irls','cnn','autoencoder'},
}
EXPECTED_VARIANTS={'reference','contrast','noise','acquisition','coverage','regularization'}


def assert_method_matrix(family, run_methods, catalog_methods):
    expected=EXPECTED_METHODS[family]
    assert set(run_methods)==expected, f'{family}: missing or unexpected run methods: {set(run_methods)^expected}'
    assert set(catalog_methods)==expected, f'{family}: missing or unexpected catalogue methods: {set(catalog_methods)^expected}'


def finite(obj):
    if isinstance(obj,float):
        assert math.isfinite(obj),"non-finite number"
    elif isinstance(obj,dict):
        for v in obj.values(): finite(v)
    elif isinstance(obj,list):
        for v in obj: finite(v)


def numbers(obj):
    if isinstance(obj,list):
        for value in obj:yield from numbers(value)
    elif isinstance(obj,(int,float)):
        yield float(obj)


def validate():
    catalog=json.loads((ROOT/"catalog.json").read_text(encoding="utf-8"))
    assert catalog["schema"]=="inverse-earth.catalog/v2"
    assert len(catalog["cases"])==20
    assert len({case['id'] for case in catalog['cases']})==20,'Duplicate case id'
    assert {case['id']:case['family'] for case in catalog['cases']}==EXPECTED_CASE_FAMILY,'Missing, extra or relabelled case'
    geometries=set();runs=0;cells=0
    for case in catalog["cases"]:
        assert len(case["variants"])==6
        assert {v["id"] for v in case["variants"]}==EXPECTED_VARIANTS
        for variant in case["variants"]:
            assert variant['path']==f"{case['id']}/{variant['id']}.json",'Unexpected experiment path'
            path=(ROOT/variant["path"]).resolve()
            assert path.is_relative_to(ROOT.resolve()),"unsafe artifact path"
            raw=path.read_bytes()
            assert len(raw)==variant["bytes"] and hashlib.sha256(raw).hexdigest()==variant["sha256"],str(path)
            run=json.loads(raw)
            finite(run)
            assert run["schema"]=="inverse-earth/v2" and run["id"]==case["id"] and run["variant"]==variant["id"]
            assert run['family']==case['family'] and run['geometry']==case['geometry'] and run['seed']==case['seed'],'Case identity mismatch'
            if case['family'] in ('gravity','magnetics','joint'):
                assert 0<case['survey_max_abs']<math.inf
                assert max(abs(v) for v in run['survey']['observed'])<=case['survey_max_abs']*(1+1e-12)
                assert 'volume' in case['display_scales']
                lo,hi=case['display_scales']['volume']['range']
                assert lo<=min(numbers(run['truth'])) and max(numbers(run['truth']))<=hi
                if case['family']=='joint':
                    lo,hi=case['display_scales']['secondary']['range']
                    assert lo<=min(numbers(run['secondary_truth'])) and max(numbers(run['secondary_truth']))<=hi
            if case['family']=='seismic':
                assert run.get('export_precision_significant_digits')==10,'FWI model export must round-trip float32 forward states'
            run_version=run['provenance']['version']
            assert run_version in {catalog['version'],'0.04.000'},'Unexpected run version'
            assert run['provenance']['generator_fingerprint']==generator_fingerprint(case['family'],version=run_version),'Stale scientific source/settings'
            assert run["provenance"]["synthetic"] and run["methods"]
            assert_method_matrix(case['family'],run['methods'],variant['methods'])
            if variant["id"]=="reference":
                fingerprint=hashlib.sha256(json.dumps(run["truth"]).encode()).hexdigest()
                assert fingerprint not in geometries,"Repeated geological truth"
                geometries.add(fingerprint)
            for key,method in run["methods"].items():
                assert method["model"] and method["history"] and method["metrics"]
                assert method["metrics"]==variant["methods"][key]["metrics"]
                assert method['evaluation']['status'] in ('recovered','unresolved','failed','negative-control')
                assert method['evaluation']==variant['methods'][key]['evaluation']
                if case['family'] in ('gravity','magnetics','joint'):
                    group='vector-amplitude' if key=='vector' else 'volume'
                    scale=case['display_scales'][group]
                    lo,hi=scale['range']
                    assert scale['maximum']>0 and math.isfinite(scale['maximum'])
                    assert lo<=min(numbers(method['model'])) and max(numbers(method['model']))<=hi
                    for frame in method['frames']:
                        assert lo<=min(numbers(frame)) and max(numbers(frame))<=hi
                    if case['family']=='joint' and method.get('magnetic_model'):
                        lo,hi=case['display_scales']['secondary']['range']
                        assert lo<=min(numbers(method['magnetic_model'])) and max(numbers(method['magnetic_model']))<=hi
                assert method['target'] and method['state_identity']['predictions']=='final-model'
                if method['frames']:assert method['frames'][-1]==method['model'],'Last replay state differs from final model'
                if key=='autoencoder':
                    assert method['evaluation']==dict(status='unresolved',reason_codes=['case-score-not-calibrated-as-geology'])
                    assert len(method['network_input'])==len(method['predicted'])==len(method['residual'])==256
                if case['family']=='seismic':
                    metrics=method['metrics'];status=method['evaluation']['status']
                    if case['geometry']=='salt':assert status=='negative-control'
                    if status=='recovered':
                        assert metrics['model_rmse_ratio']<1 and metrics['active_relative_mse']<metrics['initial_active_relative_mse']
                        assert metrics['withheld_relative_mse']<metrics['initial_withheld_relative_mse']
                        assert metrics['active_wrms']<=2 and metrics['withheld_wrms']<=2
                if case['family']=='joint' and key in ('joint','pgi'):
                    baseline=run['methods']['joint-uncoupled']['metrics']
                    metrics=method['metrics']
                    assert math.isclose(metrics['independent_model_rmse'],baseline['model_rmse'],rel_tol=2e-5)
                    assert math.isclose(metrics['independent_magnetic_model_rmse'],baseline['magnetic_model_rmse'],rel_tol=2e-5)
                    if case['geometry']=='conflict':assert method['evaluation']['status']=='negative-control'
                cells+=1
            runs+=1
    training=json.loads((ROOT/"models/training.json").read_text())
    assert len(set(training["seeds"]))==3 and training["split_counts"]==[800,160,160]
    for model in training["models"].values():
        assert hashlib.sha256((ROOT/model["checkpoint"]).read_bytes()).hexdigest()==model["sha256"]
    release=json.loads((ROOT/"release.json").read_text())
    assert release['complete'] and catalog['complete']
    assert release['version']==catalog['version'],'Catalogue/release version mismatch'
    assert (runs,cells)==(release["runs"],release["methods"])
    edi=json.loads((ROOT/'edi/manifest.json').read_text())
    assert len(edi['fixtures'])==3 and len(edi['calibration'])==2
    for entry in edi['fixtures']+edi['calibration']:
        path=(ROOT/'edi'/entry['artifact']).resolve()
        assert path.is_relative_to((ROOT/'edi').resolve())
        assert hashlib.sha256(path.read_bytes()).hexdigest()==entry['artifact_sha256']
        if 'source' in entry:
            source=(ROOT/'edi'/entry['source']).resolve()
            assert source.is_relative_to((ROOT/'edi').resolve())
            assert hashlib.sha256(source.read_bytes()).hexdigest()==entry['source_sha256']
    field_screens=edi.get('field_screens',[])
    assert len(field_screens)==1 and field_screens[0]['id']=='cl061'
    field=field_screens[0]
    field_path=(ROOT/'edi'/field['artifact']).resolve()
    assert field_path.is_relative_to((ROOT/'edi').resolve())
    raw=field_path.read_bytes()
    assert len(raw)==field['artifact_bytes'] and hashlib.sha256(raw).hexdigest()==field['artifact_sha256']
    assert field['parser_source_sha256']==hashlib.sha256((Path(__file__).resolve().parents[1]/'data-pipeline/edi.py').read_bytes()).hexdigest()
    screened=json.loads(raw)
    assert screened['schema']=='inverse-earth/edi-screen/v1' and screened['id']=='cl061'
    assert screened['source_kind']=='measured EDI transfer functions' and screened['provenance']['synthetic'] is False
    assert screened['truth'] is None and not screened['methods'] and screened['inversion_performed'] is False
    assert len(screened['frequencies_hz'])==field['observed_frequencies']==42
    assert screened['provenance']['source_sha256']==field['source_sha256']
    assert not screened['one_d_inversion_eligible'] and not screened['compatibility']['passes_screen']
    assert all(screened['compatibility'][key]>screened['compatibility']['threshold'] for key in
               ('xx_component_wrms','yy_component_wrms','antisymmetry_conservative_wrms'))
    assert training['comparison']['noisy_test_sha256'] and training['novelty_evaluation']
    print(f"PASS: {len(geometries)} distinct truths / {runs} experiments / {cells} method results; all SHA-256 and sizes match")
    return dict(cases=len(geometries),runs=runs,method_results=cells)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument('--data',type=Path,default=ROOT)
    ROOT=parser.parse_args().data.resolve();validate()
