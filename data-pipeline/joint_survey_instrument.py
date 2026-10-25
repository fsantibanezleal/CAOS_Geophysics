"""Exclusive post-freeze native state export. No fitting or browser physics."""
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy import sparse

import joint_survey_calibration_io as calibration
import joint_survey_evaluation as evaluation
import joint_survey_files as files
import joint_survey_intake as intake
import joint_survey_objective as objective
import joint_survey_plan as planner
import joint_survey_resources as resources
import joint_survey_workflow as workflow
from joint_survey_serialization import _external, local_joint_data_root

SCHEMA='joint-survey-state-instrument-1'
ENVELOPE='joint-survey-state-instrument-file-1'
GRAM=('gram_density','gram_susceptibility','gram_product','face_contribution')
RESPONSE=('predicted','signed_residual','whitened_residual','metrics')
SOURCES=('joint_survey_instrument.py','joint_survey_calibration_io.py',
    'joint_survey_evaluation.py','joint_survey_files.py','joint_survey_intake.py',
    'joint_survey_model_export.py','joint_survey_resources.py','joint_survey_workflow.py')


def source_inventory():
    return {name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in SOURCES}


def exact_face_gram(problem,q):
    """Public installed face operators, NOT vector-first cross-gradient diagnostic."""
    problem._admit_state(q,{'beta_gravity':.0001,'beta_magnetic':.0001,'coupling':0.})
    reg=problem.cross_exact.regularization_mesh
    G=reg.cell_gradient;B=sparse.diags(np.sqrt(reg.vol))@reg.average_face_to_cell
    with np.errstate(over='raise',invalid='raise',divide='raise'):
        a=G@q[:problem.n];b=G@q[problem.n:]
        p=B@(a*a);t=B@(b*b);h=B@(a*b)
        contribution=problem.factor*(p*t-h*h)
        actual=problem.factor*float(problem.cross_exact(q))
    if (not all(np.isfinite(v).all() for v in (p,t,h,contribution))
            or not np.isclose(np.sum(contribution),actual,atol=1e-10,rtol=1e-9)):
        raise RuntimeError('instrument: actual face Gram/scalar mismatch')
    # Negative roundoff is a measured value, never clipped to imply agreement.
    return dict(zip(GRAM,(p,t,h,contribution)))


def _inventory(root):
    result={};total=0
    for child in sorted(root.iterdir()):
        if child.name=='workflow.json': members=[child]
        elif child.name in ('calibration','frozen','models','result'):
            intake._ordinary(child,directory=True);members=sorted(child.iterdir())
        else: raise ValueError('instrument: exact original workflow inventory')
        for path in members:
            size=intake._ordinary(path).st_size;total+=size
            if total>planner.MAX_EXPORT_BYTES: raise ValueError('instrument: original byte cap')
            result[path.relative_to(root).as_posix()]=intake._file_sha(path)
    return result,total


def _entries(ledger):
    result=[]
    if ledger:
        for c in ledger['candidates']:
            result.append({'key':f"c{c['stage']:02d}",'kind':'candidate','stage':c['stage'],
                'modality':c['modality'],'state_count':len(c['result']['trace']['models_q']),
                'weights':dict(c['weights'])})
        baselines=ledger['selected_baselines']
        result.append({'key':'baseline','kind':'independently_optimized_pair','stage':None,
            'modality':None,'state_count':1,'weights':{
                'beta_gravity':ledger['candidates'][baselines['gravity']]['weights']['beta_gravity'],
                'beta_magnetic':ledger['candidates'][baselines['magnetic']]['weights']['beta_magnetic'],'coupling':0.}})
    return result


def _specs(problem,entries):
    specs={}
    for e in entries:
        count=e['state_count']
        for m in evaluation.MODALITIES if e['modality'] is None else (e['modality'],):
            for part in evaluation.PARTITIONS:
                rows=len(problem.plan[m][part+'_rows'])
                for name in RESPONSE:
                    specs[e['key']+'_'+m+'_'+part+'_'+name]=('<f8',(count,3 if name=='metrics' else rows))
        if e['modality'] is None:
            for name in GRAM: specs[e['key']+'_'+name]=('<f8',(count,problem.n))
    return specs


def _admit_projection(specs,payload,original_bytes):
    # Counts/shapes charged before allocations, historic predictions or mkdir.
    logical=0;descriptors={}
    for name,(dtype,shape) in specs.items():
        if dtype!='<f8' or len(shape)!=2 or not 0<=shape[0]<=251 or not 1<=shape[1]<=8192:
            raise ValueError('instrument: literal state/row shapes')
        size=int(np.prod(shape))*8;logical+=size
        if original_bytes+logical>planner.MAX_EXPORT_BYTES: raise ValueError('instrument: projected whole byte cap')
        descriptors[name]={'dtype':dtype,'shape':list(shape),'file_bytes':128+size,
            'file_sha256':'0'*64,'data_sha256':'0'*64}
    content={'schema':ENVELOPE,'payload':payload,'arrays':descriptors}
    files.metadata_budget(content)
    if (len(files._content(content))>planner.MAX_METADATA_BYTES
            or original_bytes+sum(d['file_bytes'] for d in descriptors.values())+len(files._content(content))>planner.MAX_EXPORT_BYTES
            or len(payload['original_file_sha256'])+len(specs)+1>1100):
        raise ValueError('instrument: projected native transport cap')


def _expected(problem,frozen,sealed,ledger,original_hashes,original_bytes,budget):
    entries=_entries(ledger)+[{'key':'selected','kind':'frozen_selection','stage':None,
        'modality':None,'state_count':1,'weights':dict(frozen['weights'])}]
    payload={'schema':SCHEMA,'plan_sha256':problem.plan['plan_sha256'],
        'development_sha256':problem.development_sha256,'frozen_sha256':frozen['frozen_sha256'],
        'calibration_sha256':None if ledger is None else ledger['calibration_sha256'],
        'original_file_sha256':original_hashes,'exporter_source_inventory':source_inventory(),
        'physical_epochs':dict(evaluation.EPOCHS),'entries':entries,
        'coupling_method':'active-face-averaged-squared-product-gram',
        'coupling_length_m':problem.plan['prior']['coupling_length_m'],
        'coupling_factor':problem.factor,'metric_columns':['rmse_physical','wrms','chi_square'],
        'residual_convention':'predicted_minus_observed','historical_sealed_use':'post_freeze_diagnostic_only',
        'refit':False,'scientific_acceptance_verified':False,'field_eligible':False,
        'recovery_verified':False,'global_optimum_verified':False,'public_activation':False,
        'public_redistribution':False,'archive_authenticated':False}
    specs=_specs(problem,entries);_admit_projection(specs,payload,original_bytes)
    arrays={name:np.empty(shape,dtype=dtype) for name,(dtype,shape) in specs.items()}
    for e in entries:
        if e['key']=='selected': states=frozen['q'][None,:]
        elif e['key']=='baseline':
            states=np.concatenate([ledger['candidates'][ledger['selected_baselines'][m]]['result']['q']
                for m in evaluation.MODALITIES])[None,:]
        else: states=ledger['candidates'][e['stage']]['result']['trace']['models_q']
        for i,state in enumerate(states):
            budget.checkpoint()
            q=state
            if e['modality'] is not None:
                q=problem.start.copy();sl=slice(0,problem.n) if e['modality']=='gravity' else slice(problem.n,2*problem.n)
                q[sl]=state
            predictions=problem.predict(q)
            for m in evaluation.MODALITIES if e['modality'] is None else (e['modality'],):
                for part in evaluation.PARTITIONS:
                    metric,values=evaluation._partition(problem,m,part,predictions[m],sealed)
                    prefix=e['key']+'_'+m+'_'+part+'_'
                    for name in RESPONSE:
                        arrays[prefix+name][i]=[metric[k] for k in payload['metric_columns']] if name=='metrics' else values[name]
            if e['modality'] is None:
                values=exact_face_gram(problem,q)
                for name in GRAM: arrays[e['key']+'_'+name][i]=values[name]
    return payload,arrays,specs


def _paths(data_root,development,sealed,original,output,scratch,*,existing):
    root=local_joint_data_root(data_root)
    paths={k:workflow._under(root,v,existing=k!='output' or existing) for k,v in (
        ('development',development),('sealed',sealed),('original',original),('output',output))}
    paths['scratch']=_external(scratch,existing=True)
    for i,(k,left) in enumerate(paths.items()):
        for right in list(paths.values())[i+1:]:
            if left==right or left.is_relative_to(right) or right.is_relative_to(left):
                raise ValueError('instrument: disjoint external directories required')
    if not existing and paths['output'].exists(): raise FileExistsError('instrument: exclusive output')
    intake._ordinary(paths['output'].parent,directory=True)
    return root,paths


def _load(root,paths,budget):
    # Outer absolute resource clock includes original replay, even though the
    # original validator also retains its independently measured replay receipt.
    workflow.validate_joint_workflow(data_root=str(root),development=str(paths['development']),
        sealed=str(paths['sealed']),output=str(paths['original']),scratch=str(paths['scratch']))
    budget.checkpoint();admitted,problem=workflow._compile(paths['development'])
    frozen=evaluation.load_frozen_model(str(paths['original']/'frozen'),problem)
    ledger=None
    if (paths['original']/'calibration').exists():
        ledger=calibration.load_joint_calibration(str(paths['original']/'calibration'),problem,budget)
        calibration.verify_joint_calibration(ledger,problem,budget,frozen=frozen)
    # These diagnostics open AFTER original durable freeze/selection verification.
    sealed=evaluation.load_joint_sealed(str(paths['sealed']),problem,frozen,admitted['sealed_manifest'])
    hashes,size=_inventory(paths['original'])
    return problem,frozen,sealed,ledger,hashes,size


def state_instrument_workflow(*,data_root,development,sealed,original,output,scratch,validate=False):
    root,paths=_paths(data_root,development,sealed,original,output,scratch,existing=validate)
    with resources.JointResourceBudget(str(paths['scratch'])) as budget:
        problem,frozen,values,ledger,hashes,size=_load(root,paths,budget)
        payload,arrays,specs=_expected(problem,frozen,values,ledger,hashes,size,budget)
        if not validate:
            paths['output'].mkdir(mode=0o700)
            for relative,digest in hashes.items():
                budget.checkpoint();source=paths['original']/relative;before=intake._ordinary(source)
                # Individual original bytes also guarded against concurrent change.
                content=intake._read_bounded(source,planner.MAX_EXPORT_BYTES)
                intake._unchanged(source,before)
                if hashlib.sha256(content).hexdigest()!=digest: raise ValueError('instrument: original byte drift')
                target=paths['output']/relative
                if not target.parent.exists(): target.parent.mkdir(mode=0o700)
                with target.open('xb') as stream: stream.write(content)
            files.write_arrays(str(paths['output']/'instrument'),'instrument.json',ENVELOPE,payload,arrays,
                max_array_bytes=planner.MAX_EXPORT_BYTES)
        expected_dirs={'workflow.json','frozen','models','result','instrument'}|({'calibration'} if ledger else set())
        if {p.name for p in paths['output'].iterdir()}!=expected_dirs: raise ValueError('instrument: exact bundle inventory')
        for relative,digest in hashes.items():
            if intake._file_sha(paths['output']/relative)!=digest: raise ValueError('instrument: original copy drift')
        for directory in ('calibration','frozen','models','result'):
            expected={r.split('/')[1] for r in hashes if r.startswith(directory+'/')}
            if expected and {p.name for p in (paths['output']/directory).iterdir()}!=expected:
                raise ValueError('instrument: exact original member inventory')
        def metadata(value):
            if value!=payload: raise ValueError('instrument: source/input/frame metadata drift')
        actual,loaded,bindings=files.read_arrays(str(paths['output']/'instrument'),'instrument.json',ENVELOPE,
            specs,metadata,max_array_bytes=planner.MAX_EXPORT_BYTES)
        if any(not np.array_equal(loaded[k],arrays[k]) for k in arrays):
            raise ValueError('instrument: actual historical physics drift')
        if resources.scratch_bytes(paths['output'])>planner.MAX_EXPORT_BYTES: raise ValueError('instrument: whole output byte cap')
        if _inventory(paths['original'])[0]!=hashes: raise ValueError('instrument: concurrent original drift')
        budget.checkpoint()
        return {'schema':'joint-survey-state-instrument-receipt-1','validated':True,
            'frozen_sha256':actual['frozen_sha256'],'refit':False,'public_activation':False,
            'instrument_manifest_sha256':bindings['manifest_sha256'],'exporter_source_inventory':source_inventory(),
            'scientific_acceptance_verified':False,'resources':budget.receipt(workflow_completed=True)}


def main(argv=None):
    import argparse
    parser=argparse.ArgumentParser(description='Private post-freeze joint state instrument export',allow_abbrev=False)
    parser.add_argument('command',choices=('export','validate'))
    parser.add_argument('--data-root');parser.add_argument('--development',required=True)
    parser.add_argument('--sealed',required=True);parser.add_argument('--original',required=True)
    parser.add_argument('--output',required=True);parser.add_argument('--scratch-root',required=True)
    args=vars(parser.parse_args(argv));args['validate']=args.pop('command')=='validate'
    args['scratch']=args.pop('scratch_root')
    try:
        print(json.dumps(state_instrument_workflow(**args),sort_keys=True,allow_nan=False));return 0
    except (ValueError,TypeError,RuntimeError,OSError,ImportError):
        print(json.dumps({'schema':'joint-survey-state-instrument-error-1','validated':False,
            'refit':False,'scientific_acceptance_verified':False,'public_activation':False},sort_keys=True));return 1
