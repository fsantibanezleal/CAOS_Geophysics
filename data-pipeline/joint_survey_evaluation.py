"""Actual physical frozen-model evaluation; sealed values cannot enter calibration."""
import hashlib
import math

import numpy as np
import scipy.linalg as la

import gravity_forward
import magnetic_forward
import joint_survey_files as files
import joint_survey_objective as objective
import joint_survey_plan as planner
from joint_survey_serialization import _manifest


MODALITIES=('gravity','magnetic')
PARTITIONS=('training','validation','sealed')
EPOCHS={'gravity':gravity_forward.ENGINE,'magnetic':magnetic_forward.ENGINE}
_FROZEN_KEYS=('schema','plan_sha256','development_sha256','physical_epochs','weights','origin',
              'selection_sha256','q','frozen_sha256')


def projected_kkt(q,g,lower,upper):
    """Exact feasible-bound signs; no epsilon-active or near-bound substitution."""
    residual=g.copy()
    residual[q==lower]=np.minimum(g[q==lower],0.)
    residual[q==upper]=np.maximum(g[q==upper],0.)
    return float(np.linalg.norm(residual,np.inf))


def freeze_joint_model(problem,q,weights,*,origin='supplied_model',selection_sha256=None):
    problem._admit_state(q,weights)
    planner._enum(origin,('supplied_model','optimized_selection'),'origin')
    if origin=='supplied_model':
        if selection_sha256 is not None: raise ValueError('freeze: supplied model cannot claim calibration')
    else: objective._sha(selection_sha256,'selection_sha256')
    result={'schema':'joint-survey-frozen-model-1','plan_sha256':problem.plan['plan_sha256'],
        'development_sha256':problem.development_sha256,'physical_epochs':dict(EPOCHS),'weights':dict(weights),
        'origin':origin,'selection_sha256':selection_sha256,'q':planner._snapshot(q)}
    result['frozen_sha256']=planner._digest(result)
    return result


def _frozen_metadata(value,problem,*,has_q=True):
    planner._keys(value,_FROZEN_KEYS if has_q else tuple(k for k in _FROZEN_KEYS if k!='q'),'freeze')
    planner._enum(value['schema'],('joint-survey-frozen-model-1',),'freeze.schema')
    for key in ('plan_sha256','development_sha256','frozen_sha256'): objective._sha(value[key],key)
    if (value['plan_sha256']!=problem.plan['plan_sha256'] or value['development_sha256']!=problem.development_sha256):
        raise ValueError('freeze: input identity drift')
    planner._keys(value['physical_epochs'],EPOCHS,'physical_epochs')
    for key,epoch in EPOCHS.items(): planner._enum(value['physical_epochs'][key],(epoch,),'physical epoch')
    planner._enum(value['origin'],('supplied_model','optimized_selection'),'freeze.origin')
    if value['origin']=='supplied_model':
        if value['selection_sha256'] is not None: raise ValueError('freeze: supplied model cannot claim calibration')
    else: objective._sha(value['selection_sha256'],'selection_sha256')
    planner._keys(value['weights'],('beta_gravity','beta_magnetic','coupling'),'freeze.weights')
    for key,v in value['weights'].items():
        planner._float(v,0.,1000.,key)
        if v not in (objective.LAMBDAS if key=='coupling' else objective.BETAS):
            raise ValueError('freeze: frozen weight required')
    if has_q: planner._array(value['q'],(2*problem.n,),'freeze.q')
    files.metadata_budget(value)


def verify_frozen_model(value,problem):
    _frozen_metadata(value,problem)
    problem._admit_state(value['q'],value['weights'])
    expected=planner._digest({k:v for k,v in value.items() if k!='frozen_sha256'})
    if expected!=value['frozen_sha256']: raise ValueError('freeze: model commitment drift')


def write_frozen_model(directory,value,problem):
    verify_frozen_model(value,problem)
    return files.write_arrays(directory,'frozen.json','joint-survey-frozen-model-file-1',
        {k:v for k,v in value.items() if k!='q'},{'q':value['q']})


def load_frozen_model(directory,problem):
    payload,arrays,_=files.read_arrays(directory,'frozen.json','joint-survey-frozen-model-file-1',
        {'q':('<f8',(2*problem.n,))},lambda p:_frozen_metadata(p,problem,has_q=False))
    result={**payload,'q':arrays['q']};verify_frozen_model(result,problem)
    return result


def _sealed_specs(plan):
    result={}
    for m in MODALITIES:
        n=len(plan[m]['sealed_rows'])
        result[m+'_rows']=('<i8',(n,));result[m+'_observed']=('<f8',(n,))
        result[m+'_noise']=('<f8',(n,n) if plan[m]['noise']['kind']=='full_covariance' else (n,))
    return result


def _noise(survey,noise):
    if survey['noise']['kind']=='diagonal_sd':
        if np.any(noise<=0.): raise ValueError('sealed: positive SD required, no floor')
        return ('diagonal',noise)
    if not np.array_equal(noise,noise.T): raise ValueError('sealed: exact covariance symmetry required')
    return ('cholesky',la.cholesky(noise,lower=True,check_finite=False))


def write_joint_sealed(directory,plan,data):
    """Separate authored/import stage, before fitting; never a fitting argument."""
    specs=_sealed_specs(plan);planner._keys(data,specs,'sealed arrays')
    for name,(dtype,shape) in specs.items():
        if name.endswith('_rows'):
            if type(data[name]) is not np.ndarray or data[name].dtype.str!=dtype or data[name].shape!=shape:
                raise ValueError('sealed: exact int64 row vector')
        else: planner._array(data[name],shape,name)
    planner._metadata_budget(data);planner._finite(data)
    for m in MODALITIES:
        if not np.array_equal(data[m+'_rows'],plan[m]['sealed_rows']): raise ValueError('sealed: exact row IDs')
        _noise(plan[m],data[m+'_noise'])
    written=files.write_arrays(directory,'sealed.json','joint-survey-sealed-input-1',
        {'plan_sha256':plan['plan_sha256']},data)
    manifest={'schema':'joint-survey-sealed-manifest-1'}
    for m in MODALITIES:
        manifest[m]={'rows_sha256':hashlib.sha256(data[m+'_rows'].tobytes(order='C')).hexdigest(),
            'observations_file_sha256':written['arrays'][m+'_observed']['file_sha256'],
            'noise_file_sha256':written['arrays'][m+'_noise']['file_sha256'],
            'count':len(data[m+'_rows']),'noise_kind':plan[m]['noise']['kind']}
    return manifest


def load_joint_sealed(directory,problem,frozen,manifest):
    # Freeze and commitment admission BEFORE inventory or any sealed byte is opened.
    verify_frozen_model(frozen,problem);_manifest(manifest,problem.plan)
    def payload(p):
        planner._keys(p,('plan_sha256',),'sealed payload');objective._sha(p['plan_sha256'],'plan_sha256')
        if p['plan_sha256']!=frozen['plan_sha256']: raise ValueError('sealed: stale plan')
    def descriptors(values):
        for m in MODALITIES:
            for suffix,key in (('_observed','observations_file_sha256'),('_noise','noise_file_sha256')):
                if values[m+suffix]['file_sha256']!=manifest[m][key]:
                    raise ValueError('sealed: development commitment mismatch')
    payload_value,arrays,bindings=files.read_arrays(directory,'sealed.json','joint-survey-sealed-input-1',
        _sealed_specs(problem.plan),payload,descriptors)
    for m in MODALITIES:
        if not np.array_equal(arrays[m+'_rows'],problem.plan[m]['sealed_rows']): raise ValueError('sealed: row identity drift')
        for suffix,key in (('_observed','observations_file_sha256'),('_noise','noise_file_sha256')):
            if bindings['arrays'][m+suffix]['file_sha256']!=manifest[m][key]:
                raise ValueError('sealed: development commitment mismatch')
        _noise(problem.plan[m],arrays[m+'_noise'])
    return {'schema':'joint-survey-sealed-values-1','frozen_sha256':frozen['frozen_sha256'],
        'plan_sha256':payload_value['plan_sha256'],'arrays':arrays,'bindings':bindings}


def _partition(problem,m,label,prediction,sealed):
    survey=problem.plan[m]
    if label=='sealed':
        rows=sealed['arrays'][m+'_rows'];observed=sealed['arrays'][m+'_observed'];noise=sealed['arrays'][m+'_noise']
    else:
        train=len(survey['training_rows']);dev=problem.development[m]
        sl=slice(0,train) if label=='training' else slice(train,None)
        rows=dev['rows'][sl];observed=dev['observed'][sl]
        noise=dev['noise_values'][sl,sl] if survey['noise']['kind']=='full_covariance' else dev['noise_values'][sl]
    predicted=prediction[rows];residual=predicted-observed
    whitened=objective._whiten(_noise(survey,noise),residual)
    chi_square=float(whitened@whitened)
    metrics={'count':len(rows),'unit':survey['unit'],'rmse_physical':float(np.sqrt(np.mean(residual**2))),
        'wrms':math.sqrt(chi_square/len(rows)),'chi_square':chi_square}
    arrays={'rows':rows,'observed':observed,'predicted':predicted,'signed_residual':residual,'whitened_residual':whitened}
    return metrics,{key:planner._snapshot(value) for key,value in arrays.items()}


def evaluate_frozen_joint(problem,frozen,sealed):
    verify_frozen_model(frozen,problem)
    planner._keys(sealed,('schema','frozen_sha256','plan_sha256','arrays','bindings'),'sealed values')
    planner._enum(sealed['schema'],('joint-survey-sealed-values-1',),'sealed.schema')
    if sealed['frozen_sha256']!=frozen['frozen_sha256'] or sealed['plan_sha256']!=problem.plan['plan_sha256']:
        raise ValueError('evaluation: stale frozen sealed channel')
    specs=_sealed_specs(problem.plan);planner._keys(sealed['arrays'],specs,'sealed arrays')
    planner._keys(sealed['bindings'],('manifest_sha256','arrays'),'sealed bindings')
    objective._sha(sealed['bindings']['manifest_sha256'],'sealed manifest hash')
    planner._keys(sealed['bindings']['arrays'],specs,'sealed binding arrays')
    for name,(dtype,shape) in specs.items():
        value=sealed['arrays'][name]
        if type(value) is not np.ndarray or value.dtype.str!=dtype or value.shape!=shape:
            raise ValueError('evaluation: sealed native dtype/shape')
    files.metadata_budget(sealed);planner._finite(sealed['arrays'])
    # Bind the in-memory marginal values too; a modified writable copy is not
    # excused merely because the original directory once passed intake.
    _,descriptors,_=files._descriptors(sealed['arrays'])
    if descriptors!=sealed['bindings']['arrays']: raise ValueError('evaluation: sealed data binding drift')
    for m in MODALITIES:
        if not np.array_equal(sealed['arrays'][m+'_rows'],problem.plan[m]['sealed_rows']):
            raise ValueError('evaluation: sealed row identity drift')
    q=frozen['q'];state=problem.state(q,frozen['weights']);predicted=problem.predict(q)
    metrics={};arrays={'q':q}
    for m in MODALITIES:
        metrics[m]={}
        for label in PARTITIONS:
            metrics[m][label],values=_partition(problem,m,label,predicted[m],sealed)
            arrays.update({m+'_'+label+'_'+key:value for key,value in values.items()})
    kkt=projected_kkt(q,state['gradient_normalized'],problem.lower,problem.upper)
    warnings={'cross_partition_dependence':{m:problem.plan[m]['noise']['cross_partition'] for m in MODALITIES},
        'rights_verified':False,'correction_science_verified':False,'field_eligible':False,
        'global_optimum_verified':False,'recovery_verified':False,'public_redistribution':False,
        'inverse_completed':False,'calibration_identity_declared':frozen['origin']=='optimized_selection'}
    payload={'schema':'joint-survey-evaluation-1','frozen_sha256':frozen['frozen_sha256'],
        'origin':frozen['origin'],'selection_sha256':frozen['selection_sha256'],
        'plan_sha256':problem.plan['plan_sha256'],'development_sha256':problem.development_sha256,
        'physical_epochs':dict(EPOCHS),'weights':dict(frozen['weights']),
        'sealed_bindings':sealed['bindings'],'objective':state['objective'],'terms':state['terms'],
        'exact_bound_kkt_inf':kkt,'metrics':metrics,'claims':warnings}
    files.metadata_budget({'payload':payload,'arrays':arrays});planner._finite({'payload':payload,'arrays':arrays})
    return {'payload':payload,'arrays':planner._snapshot(arrays)}


def write_joint_result(directory,result):
    planner._keys(result,('payload','arrays'),'result')
    return files.write_arrays(directory,'result.json','joint-survey-result-file-1',result['payload'],result['arrays'])


def validate_joint_result(directory,problem,frozen,sealed):
    expected=evaluate_frozen_joint(problem,frozen,sealed)
    specs={key:(value.dtype.str,value.shape) for key,value in expected['arrays'].items()}
    def payload(value):
        # Closed native expected grammar, not a permissive imported summary.
        if planner._digest(value)!=planner._digest(expected['payload']):
            raise ValueError('result: recomputed scientific metadata drift')
    actual,arrays,bindings=files.read_arrays(directory,'result.json','joint-survey-result-file-1',specs,payload)
    if planner._digest({'payload':actual,'arrays':arrays})!=planner._digest(expected):
        raise ValueError('result: actual physical replay drift')
    return {'validated':True,'frozen_sha256':frozen['frozen_sha256'],'result_manifest_sha256':bindings['manifest_sha256'],
        'inverse_completed':expected['payload']['claims']['inverse_completed'],'field_eligible':False}
