"""Fast stdlib-only committed-artifact contract; no computation or dependencies in CI."""
from pathlib import Path
import hashlib
import json
import math

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
                cells+=1
            runs+=1
    training=json.loads((ROOT/"models/training.json").read_text())
    assert len(set(training["seeds"]))==3 and training["split_counts"]==[800,160,160]
    for model in training["models"].values():
        assert hashlib.sha256((ROOT/model["checkpoint"]).read_bytes()).hexdigest()==model["sha256"]
    release=json.loads((ROOT/"release.json").read_text())
    assert (runs,cells)==(release["runs"],release["methods"])
    print(f"PASS: {len(geometries)} distinct truths / {runs} experiments / {cells} method results; all SHA-256 and sizes match")
    return dict(cases=len(geometries),runs=runs,method_results=cells)


if __name__=="__main__":validate()
