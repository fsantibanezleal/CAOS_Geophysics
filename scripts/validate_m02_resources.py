"""Actual serial original-cap and complete nominal runs, with external custody.

This harness imports fixed repository-owned controls, never request-selected
code. Observed process RSS is evidence, not a native allocation upper proof.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

import psutil

ROOT=Path(__file__).resolve().parents[1]


def external_path(path):
    if not path.is_absolute(): raise ValueError('absolute external output path required')
    for ancestor in (path,*path.parents):
        if ancestor.is_symlink() or (hasattr(ancestor,'is_junction') and ancestor.is_junction()):
            raise ValueError('QA output: reparse ancestor forbidden')
        if (ancestor/'.git').exists(): raise ValueError('QA output must be outside repositories')
    return path.resolve()


def _write(target,value):
    with target.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,sort_keys=True,allow_nan=False,indent=2)
        stream.write('\n')


def child(kind,out):
    out=external_path(out)
    sys.path.insert(0,str(ROOT/'data-pipeline'))
    sys.path.insert(0,str(ROOT/'tests/numerics'))
    name='test_gravity_l2_precision' if kind=='cap' else 'test_gravity_l2_selection'
    path=ROOT/'tests/numerics'/f'{name}.py'
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    properties={}
    started=time.monotonic()
    result={'status':'failed','properties':properties}
    try:
        if kind=='cap': module.test_certified_delta_real_cap_resource_measurement(properties.__setitem__)
        else: module.test_complete_locked_l2_control_matrix(0,0,properties.__setitem__)
        result['status']='passed'
    except Exception as error:
        result['error_type']=type(error).__name__
        result['error']=str(error)
    result['wall_seconds']=time.monotonic()-started
    result['source_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
        (path,Path(__file__).resolve(),ROOT/'tests/numerics/test_gravity_l2_selection.py',
         ROOT/'tests/data/test_gravity_survey_l2.py',
         *(ROOT/'data-pipeline'/n for n in ('gravity_forward.py','gravity_l2.py','gravity_l2_metric.py','gravity_l2_precision.py','gravity_survey_l2.py')))}
    _write(out,result)
    return 0 if result['status']=='passed' else 1


def _completed(prefix,kind,index):
    resource=prefix.with_suffix('.resource.json')
    science=prefix.with_suffix('.json')
    if not resource.exists(): return None
    with resource.open(encoding='utf-8') as stream: record=json.load(stream)
    with science.open(encoding='utf-8') as stream: result=json.load(stream)
    if (record.get('kind')!=kind or type(record.get('index')) is not int or record['index']!=index
        or type(record.get('exit_code')) is not int or record['exit_code'] not in (0,1)
        or type(record.get('hard_timeout')) is not bool or record['hard_timeout'] and record['exit_code']==0
        or type(record.get('sampled_process_tree_peak_rss_bytes')) is not int
        or record['sampled_process_tree_peak_rss_bytes']<=0
        or type(record.get('wall_seconds')) not in (int,float) or not math.isfinite(record['wall_seconds'])
        or record['wall_seconds']<0.
        or (record['exit_code']==0)!=(result.get('status')=='passed')):
        raise ValueError('QA resume: literal completed science/resource receipt required')
    if 'sampling_complete' in record and (type(record['sampling_complete']) is not bool
        or type(record.get('sampling_errors')) is not list
        or record['sampling_complete']!= (not record['sampling_errors'])):
        raise ValueError('QA resume: actual sampling error/availability pairing')
    # The sampler may evolve without changing the original scientific control.
    # Every recorded science source (not this orchestration harness) is pinned.
    for name,digest in result['source_sha256'].items():
        if name==Path(__file__).name: continue
        candidates=(ROOT/'data-pipeline'/name,ROOT/'tests/numerics'/name,ROOT/'tests/data'/name)
        found=[p for p in candidates if p.is_file()]
        if len(found)!=1 or hashlib.sha256(found[0].read_bytes()).hexdigest()!=digest:
            raise ValueError('QA resume: scientific source changed')
    return record


def _resume_attempt(out,kind,index):
    """Reuse complete sampling only; retain every failed/incomplete attempt."""
    prefix=out/f'{kind}-{index:02d}'
    attempt=0
    while True:
        completed=_completed(prefix,kind,index)
        if completed is not None and completed.get('sampling_complete',True):
            return prefix,completed
        if not any(prefix.with_suffix(suffix).exists() for suffix in ('.log','.json','.resource.json')):
            return prefix,None
        attempt+=1
        prefix=out/f'{kind}-{index:02d}-retry-{attempt}'


def _summary_target(out):
    target=out/'summary.json'
    attempt=0
    while target.exists():
        attempt+=1
        target=out/f'summary-retry-{attempt}.json'
    return target


def run(out,count,resume=False):
    out=external_path(out)
    if out==ROOT or ROOT in out.parents or any((p/'.git').exists() for p in (out,*out.parents)):
        raise ValueError('QA output must be outside repositories')
    out.mkdir(parents=True,exist_ok=resume)
    for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'): os.environ[key]='1'
    os.environ['PYTHONDONTWRITEBYTECODE']='1'
    os.environ['TEMP']=os.environ['TMP']=str(out)
    measurements=[]
    for kind in ('cap','nominal'):
        for index in range(count):
            prefix=out/f'{kind}-{index:02d}'
            if resume:
                prefix,completed=_resume_attempt(out,kind,index)
                if completed is not None:
                    measurements.append(completed)
                    continue
            with prefix.with_suffix('.log').open('xb') as log:
                process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),
                    '--child',kind,'--output',str(prefix.with_suffix('.json'))],
                    cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
                sampled=psutil.Process(process.pid)
                peak=0
                started=time.monotonic()
                killed=False
                sampling_errors=[]
                while process.poll() is None:
                    try:
                        tree=(sampled,*sampled.children(recursive=True))
                        peak=max(peak,sum(p.memory_info().rss for p in tree if p.is_running()))
                    except psutil.NoSuchProcess: pass
                    except OSError as error:
                        sampling_errors.append({'type':type(error).__name__,'winerror':getattr(error,'winerror',None)})
                    if time.monotonic()-started>1900.:
                        # This exact child was created here; terminate its owned
                        # descendants too, not just Windows' venv launcher.
                        for owned in reversed(sampled.children(recursive=True)):
                            try: owned.kill()
                            except psutil.NoSuchProcess: pass
                        process.kill()
                        killed=True
                        break
                    time.sleep(.05)
                code=process.wait()
            record={'kind':kind,'index':index,'exit_code':code,'hard_timeout':killed,
                'sampled_process_tree_peak_rss_bytes':peak,'wall_seconds':time.monotonic()-started,
                'sampling_complete':not sampling_errors,'sampling_errors':tuple(sampling_errors)}
            _write(prefix.with_suffix('.resource.json'),record)
            measurements.append(record)
            print(json.dumps(record,sort_keys=True),flush=True)
    import numpy as np
    groups={}
    for kind in ('cap','nominal'):
        actual=[r for r in measurements if r['kind']==kind]
        groups[kind]={'count':len(actual),'passed':sum(r['exit_code']==0 for r in actual),
            'sampling_complete_count':sum(r.get('sampling_complete',True) for r in actual),
            'sampled_process_tree_peak_rss_p95_bytes':float(np.percentile([r['sampled_process_tree_peak_rss_bytes'] for r in actual],95)),
            'total_wall_p95_seconds':float(np.percentile([r['wall_seconds'] for r in actual],95)),
            'resource_upper_proof':False,'host_accepted':False}
    summary=_summary_target(out)
    _write(summary,groups)
    print(json.dumps({'summary':str(summary)},sort_keys=True),flush=True)
    return 0 if all(r['exit_code']==0 and r.get('sampling_complete',True) for r in measurements) else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--count',type=int,default=20,choices=(20,))
    parser.add_argument('--child',choices=('cap','nominal'),help=argparse.SUPPRESS)
    parser.add_argument('--resume',action='store_true',help='verify completed source-pinned receipts; retain interrupted attempts')
    args=parser.parse_args()
    return child(args.child,args.output) if args.child else run(args.output,args.count,args.resume)


if __name__=='__main__': raise SystemExit(main())
