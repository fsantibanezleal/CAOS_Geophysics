"""Build v2 scientific artifacts. Invoke by path; never run in CI/CD."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
import numpy as np

from geology import registry, VARIANTS
import potential

RELEASE_VERSION = '0.04.000'


def generator_fingerprint(family, iterations=28, epochs=180):
    """Resume only artifacts produced by the same scientific source/settings."""
    modules=['geology.py']
    if family=='seismic':modules+=['seismic.py']
    elif family=='mt':modules+=['electromagnetics.py']
    else:
        modules+=['potential.py','spatial_inverse.py','evaluation.py']
        if family=='joint':modules+=['joint.py','petrophysics.py']
        if family=='learned':modules+=['learning.py']
    digest=hashlib.sha256()
    for name in sorted(modules):
        digest.update(name.encode());digest.update((Path(__file__).parent/name).read_bytes())
    digest.update(json.dumps(dict(version=RELEASE_VERSION,iterations=iterations if family=='seismic' else None,
                                  epochs=epochs if family=='learned' else None),sort_keys=True).encode())
    return digest.hexdigest()


def annotate(result, case, runtime, iterations=28, epochs=180):
    result['runtime_seconds']=runtime
    result['provenance']={**result.get('provenance',{}),'source':'Original geological constructors','license':'CC-BY-4.0',
                          'seed':case['seed'],'version':RELEASE_VERSION,'synthetic':True,
                          'generator_fingerprint':generator_fingerprint(case['family'],iterations,epochs)}
    result['stages']=['construct geological model','configure survey','forward solve','seed noise and mask coverage',
                      'invert without target truth','evaluate data fit and model recovery separately','export']
    return result


def jsonable(value):
    if isinstance(value,np.ndarray):
        return jsonable(value.tolist())
    if isinstance(value,dict):
        return {k:jsonable(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value,(float,np.floating)):
        if not np.isfinite(value):
            raise ValueError("Non-finite scientific artifact")
        return float(f"{value:.7g}")
    if isinstance(value,np.integer):
        return int(value)
    return value


def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(jsonable(obj),ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    return dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=Path(__file__).resolve().parents[1]/"data/derived/v2")
    parser.add_argument("--cases",nargs="*")
    parser.add_argument("--variants",nargs="*")
    parser.add_argument("--iterations",type=int,default=28)
    parser.add_argument("--epochs",type=int,default=180)
    parser.add_argument("--resume",action="store_true")
    args=parser.parse_args()
    if (args.cases or args.variants) and args.output.resolve()==(Path(__file__).resolve().parents[1]/"data/derived/v2").resolve():
        parser.error('Filtered runs require --output to a separate experiment directory; canonical catalogue must remain complete.')
    out=args.output
    out.mkdir(parents=True,exist_ok=True)
    cache={};learned=None
    cases=registry()
    catalog=[]
    for case in cases:
        if args.cases and case["id"] not in args.cases:
            continue
        entry={**case,"variants":[]}
        for vid,label,label_es in VARIANTS:
            if vid=="contrast" and case["family"]=="seismic":
                label,label_es="Velocity contrast ×1.15","Contraste de velocidad ×1,15"
            if args.variants and vid not in args.variants:
                continue
            path=out/case["id"]/f"{vid}.json"
            start=time.perf_counter()
            print(f"SOLVE {case['id']} / {vid}",flush=True)
            existing=json.loads(path.read_text(encoding='utf-8')) if args.resume and path.exists() else None
            if existing and existing.get('provenance',{}).get('generator_fingerprint')==generator_fingerprint(case['family'],args.iterations,args.epochs):
                result=existing
            else:
                if case["family"]=="mt":
                    from electromagnetics import solve_case
                    result=solve_case(case,vid)
                elif case["family"]=="seismic":
                    from seismic import solve_case
                    result=solve_case(case,vid,args.iterations)
                else:
                    result=potential.solve_case(case,vid,cache)
                    if case["family"]=="joint":
                        from joint import attach
                        result=attach(result,cache)
                    if case["family"]=="learned":
                        from learning import train,attach
                        if learned is None:
                            print("TRAIN CNN + autoencoder on disjoint realizations",flush=True)
                            learned=train(cache[60][0],cache[60][2],out/"models",args.epochs)
                        result=attach(result,learned)
                annotate(result,case,time.perf_counter()-start,args.iterations,args.epochs)
                save(path,result)
            entry["variants"].append(dict(id=vid,name=label,name_es=label_es,path=f"{case['id']}/{vid}.json",sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size,
                methods={k:{"name":v["name"],"name_es":v["name_es"],"metrics":v["metrics"],"evaluation":v.get('evaluation'),"target":v.get('target'),"applicability":v.get('applicability')} for k,v in result["methods"].items()},runtime_seconds=result["runtime_seconds"]))
            print(f"OK {path.name} {path.stat().st_size//1024} KiB {time.perf_counter()-start:.1f}s",flush=True)
        catalog.append(entry)
    complete=len(catalog)==20 and all(len(c['variants'])==6 for c in catalog)
    save(out/"catalog.json",dict(schema="inverse-earth.catalog/v2",version=RELEASE_VERSION,complete=complete,cases=catalog))
    save(out/"release.json",dict(schema="inverse-earth.release/v2",version=RELEASE_VERSION,complete=complete,cases=len(catalog),runs=sum(len(c["variants"]) for c in catalog),methods=sum(len(v["methods"]) for c in catalog for v in c["variants"]),synthetic=True,engines=["SimPEG 0.25.2","SciPy 1.15.2","PyTorch 2.14.0+cu126","Deepwave 0.0.27","mt-metadata 1.0.10"]))


if __name__=="__main__":
    main()
