"""Fast stdlib-only committed-artifact contract; no computation or dependencies in CI."""
from pathlib import Path
import hashlib
import json
import math
import argparse

ROOT=Path(__file__).resolve().parents[1]/"data/derived/v2"


def finite(obj):
    if isinstance(obj,float):
        assert math.isfinite(obj),"non-finite number"
    elif isinstance(obj,dict):
        for v in obj.values(): finite(v)
    elif isinstance(obj,list):
        for v in obj: finite(v)


def validate():
    catalog=json.loads((ROOT/"catalog.json").read_text(encoding="utf-8"))
    assert catalog["schema"]=="inverse-earth.catalog/v2"
    assert len(catalog["cases"])==20
    geometries=set();runs=0;cells=0
    for case in catalog["cases"]:
        assert len(case["variants"])==6
        assert {v["id"] for v in case["variants"]}=={"reference","contrast","noise","acquisition","coverage","regularization"}
        for variant in case["variants"]:
            path=(ROOT/variant["path"]).resolve()
            assert path.is_relative_to(ROOT.resolve()),"unsafe artifact path"
            raw=path.read_bytes()
            assert len(raw)==variant["bytes"] and hashlib.sha256(raw).hexdigest()==variant["sha256"],str(path)
            run=json.loads(raw)
            finite(run)
            assert run["schema"]=="inverse-earth/v2" and run["id"]==case["id"] and run["variant"]==variant["id"]
            assert run["provenance"]["synthetic"] and run["methods"]
            assert set(run["methods"])==set(variant["methods"])
            if variant["id"]=="reference":
                fingerprint=hashlib.sha256(json.dumps(run["truth"]).encode()).hexdigest()
                assert fingerprint not in geometries,"Repeated geological truth"
                geometries.add(fingerprint)
            for key,method in run["methods"].items():
                assert method["model"] and method["history"] and method["metrics"]
                assert method["metrics"]==variant["methods"][key]["metrics"]
                assert method['evaluation']['status'] in ('recovered','unresolved','failed','negative-control')
                assert method['evaluation']==variant['methods'][key]['evaluation']
                assert method['target'] and method['state_identity']['predictions']=='final-model'
                if method['frames']:assert method['frames'][-1]==method['model'],'Last replay state differs from final model'
                cells+=1
            runs+=1
    training=json.loads((ROOT/"models/training.json").read_text())
    assert len(set(training["seeds"]))==3 and training["split_counts"]==[800,160,160]
    for model in training["models"].values():
        assert hashlib.sha256((ROOT/model["checkpoint"]).read_bytes()).hexdigest()==model["sha256"]
    release=json.loads((ROOT/"release.json").read_text())
    assert release['complete'] and catalog['complete']
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
    assert training['comparison']['noisy_test_sha256'] and training['novelty_evaluation']
    print(f"PASS: {len(geometries)} distinct truths / {runs} experiments / {cells} method results; all SHA-256 and sizes match")
    return dict(cases=len(geometries),runs=runs,method_results=cells)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument('--data',type=Path,default=ROOT)
    ROOT=parser.parse_args().data.resolve();validate()
