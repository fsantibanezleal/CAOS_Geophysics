"""Assemble a release only from source-matched solved artifacts; no computation."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from geology import registry,VARIANTS
from rebuild import generator_fingerprint,save,RELEASE_VERSION,REUSABLE_VERSIONS


def update_extrema(stats, values):
    if isinstance(values, list):
        for value in values:
            update_extrema(stats, value)
    elif values is not None:
        value=float(values)
        if not math.isfinite(value):raise ValueError('Non-finite display-scale value')
        stats[0]=min(stats[0],value);stats[1]=max(stats[1],value)


def display_scale(extrema):
    lo,hi=extrema
    # One part per million keeps the serialized seven-digit range inclusive.
    maximum=max(abs(lo),abs(hi))*(1+1e-6) or 1.
    signed=lo<0
    return dict(range=[-maximum,maximum] if signed else [0,maximum],maximum=maximum,signed=signed)


def absolute_percentile(values, fraction=0.9):
    ordered=sorted(abs(float(value)) for value in values)
    if not ordered or not all(math.isfinite(value) for value in ordered):
        raise ValueError('Invalid inverse model for display threshold')
    return ordered[int((len(ordered)-1)*fraction)]


def assemble(root,allow_partial=False):
    cases=[];missing=[]
    for case in registry():
        entry={**case,'variants':[]}
        volume_stats=[0.,0.];vector_stats=[0.,0.];secondary_stats=[0.,0.];survey_max_abs=0.
        for vid,name,name_es in VARIANTS:
            path=root/case['id']/f'{vid}.json'
            if not path.exists():
                missing.append(f"{case['id']}/{vid}");continue
            raw=path.read_bytes();run=json.loads(raw)
            provenance=run.get('provenance',{})
            version=provenance.get('version')
            if version not in REUSABLE_VERSIONS or provenance.get('generator_fingerprint')!=generator_fingerprint(case['family'],version=version):
                raise ValueError(f'Stale scientific source/settings: {path}')
            if (run['id'],run['variant'])!=(case['id'],vid):raise ValueError('Identity mismatch')
            if case['family'] in ('gravity','magnetics','joint'):
                if vid=='reference':
                    # Only the recovered reference models set the display
                    # threshold; truth never enters this presentation choice.
                    entry['default_thresholds']={'volume':absolute_percentile(run['methods']['irls']['model'])}
                    if case['family']=='magnetics':
                        entry['default_thresholds']['vector-amplitude']=absolute_percentile(run['methods']['vector']['model'])
                update_extrema(volume_stats,run['truth'])
                if case['family']=='joint':update_extrema(secondary_stats,run['secondary_truth'])
                survey_max_abs=max(survey_max_abs,*(abs(v) for v in run['survey']['observed']))
                for method_id,method in run['methods'].items():
                    stats=vector_stats if method_id=='vector' else volume_stats
                    update_extrema(stats,method['model'])
                    for frame in method.get('frames',[]):update_extrema(stats,frame)
                    if method.get('uncertainty'):
                        update_extrema(stats,method['uncertainty']['lower'])
                        update_extrema(stats,method['uncertainty']['upper'])
                    if method_id=='vector' and method.get('vector_truth'):
                        update_extrema(stats,[math.hypot(*components) for components in method['vector_truth']])
                    if case['family']=='joint':
                        update_extrema(secondary_stats,method.get('magnetic_model',method.get('secondary_model')))
            if case['family']=='seismic' and vid=='contrast':name,name_es='Velocity contrast ×1.15','Contraste de velocidad ×1,15'
            entry['variants'].append(dict(id=vid,name=name,name_es=name_es,path=f"{case['id']}/{vid}.json",
                sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),runtime_seconds=run['runtime_seconds'],
                methods={k:{name:v.get(name) for name in ('name','name_es','metrics','evaluation','target','applicability')} for k,v in run['methods'].items()}))
        if case['family'] in ('gravity','magnetics','joint') and entry['variants']:
            entry['display_scales']={'volume':display_scale(volume_stats)}
            if case['family']=='magnetics':entry['display_scales']['vector-amplitude']=display_scale(vector_stats)
            if case['family']=='joint':entry['display_scales']['secondary']=display_scale(secondary_stats)
            entry['survey_max_abs']=survey_max_abs*(1+1e-6)
        if entry['variants']:cases.append(entry)
    if missing and not allow_partial:raise ValueError('Incomplete matrix: '+', '.join(missing))
    # FWI run metrics are exported at ten digits for float32 replay; the catalog
    # must preserve those exact values for its run-to-summary identity contract.
    save(root/'catalog.json',dict(schema='inverse-earth.catalog/v2',version=RELEASE_VERSION,complete=not missing,cases=cases),significant_digits=10)
    save(root/'release.json',dict(schema='inverse-earth.release/v2',version=RELEASE_VERSION,complete=not missing,cases=len(cases),
        runs=sum(len(c['variants']) for c in cases),methods=sum(len(v['methods']) for c in cases for v in c['variants']),synthetic=True,
        engines=['SimPEG 0.25.2','SciPy 1.15.2','PyTorch 2.14.0+cu126','Deepwave 0.0.27','mt-metadata 1.0.10']))
    print(f'ASSEMBLED {len(cases)} cases; missing {len(missing)} conditions',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--allow-partial',action='store_true')
    args=parser.parse_args();assemble(args.root,args.allow_partial)
