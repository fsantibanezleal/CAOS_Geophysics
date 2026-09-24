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
            if args.resume and path.exists():
                result=json.loads(path.read_text(encoding="utf-8"))
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
                result["runtime_seconds"]=time.perf_counter()-start
                result["provenance"]={"source":"Original geological constructors","license":"CC-BY-4.0","seed":case["seed"],"version":"0.03.000","synthetic":True}
                result["stages"]=["construct geological model","configure survey","forward solve","seed noise and mask coverage","invert","evaluate against known truth","export"]
                save(path,result)
            entry["variants"].append(dict(id=vid,name=label,name_es=label_es,path=f"{case['id']}/{vid}.json",sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size,
                methods={k:{"name":v["name"],"name_es":v["name_es"],"metrics":v["metrics"]} for k,v in result["methods"].items()},runtime_seconds=result["runtime_seconds"]))
            print(f"OK {path.name} {path.stat().st_size//1024} KiB {time.perf_counter()-start:.1f}s",flush=True)
        catalog.append(entry)
    save(out/"catalog.json",dict(schema="inverse-earth.catalog/v2",version="0.03.000",cases=catalog))
    save(out/"release.json",dict(schema="inverse-earth.release/v2",version="0.03.000",cases=len(catalog),runs=sum(len(c["variants"]) for c in catalog),methods=sum(len(v["methods"]) for c in catalog for v in c["variants"]),synthetic=True,engines=["SimPEG 0.25.2","SciPy 1.15.2","PyTorch 2.14.0+cu126","Deepwave 0.0.27"]))


if __name__=="__main__":
    main()
