"""Assemble a release only from source-matched solved artifacts; no computation."""
import argparse
import hashlib
import json
from pathlib import Path
from geology import registry,VARIANTS
from rebuild import generator_fingerprint,save,RELEASE_VERSION


def assemble(root,allow_partial=False):
    cases=[];missing=[]
    for case in registry():
        entry={**case,'variants':[]}
        for vid,name,name_es in VARIANTS:
            path=root/case['id']/f'{vid}.json'
            if not path.exists():
                missing.append(f"{case['id']}/{vid}");continue
            raw=path.read_bytes();run=json.loads(raw)
            if run.get('provenance',{}).get('generator_fingerprint')!=generator_fingerprint(case['family']):
                raise ValueError(f'Stale scientific source/settings: {path}')
            if (run['id'],run['variant'])!=(case['id'],vid):raise ValueError('Identity mismatch')
            if case['family']=='seismic' and vid=='contrast':name,name_es='Velocity contrast ×1.15','Contraste de velocidad ×1,15'
            entry['variants'].append(dict(id=vid,name=name,name_es=name_es,path=f"{case['id']}/{vid}.json",
                sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),runtime_seconds=run['runtime_seconds'],
                methods={k:{name:v.get(name) for name in ('name','name_es','metrics','evaluation','target','applicability')} for k,v in run['methods'].items()}))
        if entry['variants']:cases.append(entry)
    if missing and not allow_partial:raise ValueError('Incomplete matrix: '+', '.join(missing))
    save(root/'catalog.json',dict(schema='inverse-earth.catalog/v2',version=RELEASE_VERSION,complete=not missing,cases=cases))
    save(root/'release.json',dict(schema='inverse-earth.release/v2',version=RELEASE_VERSION,complete=not missing,cases=len(cases),
        runs=sum(len(c['variants']) for c in cases),methods=sum(len(v['methods']) for c in cases for v in c['variants']),synthetic=True,
        engines=['SimPEG 0.25.2','SciPy 1.15.2','PyTorch 2.14.0+cu126','Deepwave 0.0.27','mt-metadata 1.0.10']))
    print(f'ASSEMBLED {len(cases)} cases; missing {len(missing)} conditions',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--allow-partial',action='store_true')
    args=parser.parse_args();assemble(args.root,args.allow_partial)
