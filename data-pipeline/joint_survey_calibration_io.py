"""Closed26-fit ledger export and independent actual-state/selection replay."""
from copy import deepcopy

import numpy as np

import joint_survey_evaluation as evaluation
import joint_survey_files as files
import joint_survey_objective as objective
import joint_survey_optimizer as optimizer
import joint_survey_plan as planner


_KEYS=('schema','plan_sha256','development_sha256','optimizer_binding','source_inventory','allocation_plan',
       'status','reason','candidates','selected_baselines','selection','calibration_sha256')
_CANDIDATE=('stage','modality','weights','start_kind','identity','result','physical_trace','terms_trace',
            'validation_wrms','stationarity_verified','eligible')
_RESULT=('status','reason','q','phi_d','phi_m','phi_engine','kkt_normalized','iterations','trace','failed_trial')
_STATES=('models_q','phi_d','phi_m','phi_engine','kkt_normalized')
_STEPS=('relative_changes','branches','active_counts','binding_counts','cg_counts','cg_abs_residuals',
        'cg_relative_residuals','line_search_counts','line_search_alphas','projected_slopes','armijo_margins','cg_residuals_available')
_INT=('branches','active_counts','binding_counts','cg_counts','line_search_counts')


def _grammar(ledger,problem,*,serialized=False):
    planner._keys(ledger,_KEYS,'calibration')
    planner._enum(ledger['schema'],('joint-survey-calibration-1',),'calibration.schema')
    for key in ('plan_sha256','development_sha256','calibration_sha256'): objective._sha(ledger[key],key)
    if ledger['plan_sha256']!=problem.plan['plan_sha256'] or ledger['development_sha256']!=problem.development_sha256:
        raise ValueError('calibration: original inputs drift')
    planner._enum(ledger['status'],('selected','failed'),'calibration.status')
    planner._enum(ledger['reason'],('no_stationary_separate_baseline','validated_coupled_selection','no_validated_coupling_benefit'),'calibration.reason')
    candidates=ledger['candidates']
    if type(candidates) is not (list if serialized else tuple) or len(candidates) not in (16,26):
        raise ValueError('calibration: fixed ordered16/26 actual attempts')
    if (ledger['status']=='selected')!=(len(candidates)==26): raise ValueError('calibration: attempt/status mismatch')
    for stage,c in enumerate(candidates):
        planner._keys(c,_CANDIDATE,'candidate')
        if type(c['stage']) is not int or c['stage']!=stage: raise ValueError('calibration: ordered unique stages')
        modality='gravity' if stage<8 else 'magnetic' if stage<16 else None
        if c['modality']!=modality or (c['modality'] is not None and type(c['modality']) is not str):
            raise ValueError('calibration: exact modality schedule')
        planner._enum(c['start_kind'],('submitted' if stage<16 or stage%2==0 else 'baseline',),'candidate start')
        for key in ('stationarity_verified','eligible'):
            if type(c[key]) is not bool: raise ValueError('calibration: exact boolean claims')
        planner._keys(c['result'],_RESULT,'optimizer result')
        r=c['result'];planner._enum(r['status'],('converged','failed','nonconverged'),'result.status')
        planner._enum(r['reason'],('kkt','iteration_cap','wall_cap','state_mismatch','nonfinite','engine_error',
            'cg_cap','zero_free_direction','line_search_failed'),'result.reason')
        expected_status='converged' if r['reason']=='kkt' else 'failed' if r['reason'] in (
            'state_mismatch','nonfinite','engine_error') else 'nonconverged'
        if r['status']!=expected_status: raise ValueError('calibration: exact terminal status/reason')
        if type(r['iterations']) is not int or not 0<=r['iterations']<=250: raise ValueError('calibration: literal iterations')
        if r['status']=='converged':
            if r['failed_trial'] is not None: raise ValueError('calibration: converged failed-trial fabrication')
        else:
            planner._keys(r['failed_trial'],('iteration','reason'),'failed trial')
            if (type(r['failed_trial']['iteration']) is not int or r['failed_trial']['iteration']!=r['iterations']
                    or type(r['failed_trial']['reason']) is not str or r['failed_trial']['reason']!=r['reason']):
                raise ValueError('calibration: actual failed-trial identity')
        planner._keys(r['trace'],_STATES+_STEPS,'trace')
    files.metadata_budget(ledger,max_array_bytes=planner.MAX_EXPORT_BYTES)


def verify_joint_calibration(ledger,problem,budget,*,frozen=None):
    _grammar(ledger,problem)
    inventory=optimizer.reviewed_source_inventory();allocation=optimizer.allocation_plan(problem)
    if ledger['source_inventory']!=inventory or ledger['allocation_plan']!=allocation:
        raise ValueError('calibration: reviewed source/allocation drift')
    binding={'accepted_export':'physical_nonlinear_optimizer.solve_bounded_nonlinear',
        'optimizer_source_sha256':optimizer.SOLVER_SHA,'vendor_source_sha256':optimizer.VENDOR_SHA,
        'source_inventory_sha256':planner._digest(inventory),'runtime_epoch':optimizer.solver.RUNTIME_EPOCH,
        'policy':optimizer.solver.POLICY}
    if ledger['optimizer_binding']!=binding: raise ValueError('calibration: public optimizer binding drift')
    candidates=ledger['candidates'];selected={}
    for stage,c in enumerate(candidates):
        budget.checkpoint();m=c['modality'];sl=slice(0,problem.n) if m=='gravity' else slice(problem.n,2*problem.n) if m=='magnetic' else slice(None)
        if stage<16:
            beta=objective.BETAS[stage%8];weights={'beta_gravity':beta if m=='gravity' else .0001,
                'beta_magnetic':beta if m=='magnetic' else .0001,'coupling':0.};start=problem.start[sl]
        else:
            pair=np.r_[candidates[selected['gravity']]['result']['q'],candidates[selected['magnetic']]['result']['q']]
            weights={'beta_gravity':candidates[selected['gravity']]['weights']['beta_gravity'],
                'beta_magnetic':candidates[selected['magnetic']]['weights']['beta_magnetic'],'coupling':objective.LAMBDAS[1+(stage-16)//2]}
            start=problem.start if stage%2==0 else pair
        if c['weights']!=weights: raise ValueError('calibration: frozen weights drift')
        adapter=optimizer.JointOptimizerObjective(problem,weights,start,stage,inventory,allocation,budget,m)
        if c['identity']!=adapter.identity(): raise ValueError('calibration: actual objective identity drift')
        r=c['result'];trace=r['trace'];n=adapter.n;states=trace['models_q']
        if type(states) is not np.ndarray or states.dtype!=np.float64 or states.ndim!=2 or states.shape[1]!=n or len(states)>251:
            raise ValueError('calibration: actual bounded state matrix')
        count=len(states);steps=max(0,count-1)
        if r['iterations']!=steps: raise ValueError('calibration: trace iteration count drift')
        for name in _STATES[1:]+_STEPS:
            size=count if name in _STATES else steps
            dtype=np.bool_ if name=='cg_residuals_available' else np.int64 if name in _INT else np.float64
            value=trace[name]
            if type(value) is not np.ndarray or value.dtype!=np.dtype(dtype) or value.shape!=(size,):
                raise ValueError('calibration: exact typed trace columns')
        if c['physical_trace'].shape!=(count,n) or c['terms_trace'].shape!=(count,5): raise ValueError('calibration: physical trace shapes')
        if count and not np.array_equal(states[0],start): raise ValueError('calibration: original start drift')
        initial=adapter.evaluate(start,True)[1];norm=max(1.,float(np.linalg.norm(initial,np.inf)))
        for i,q in enumerate(states):
            components=adapter.components(q);phi,g=adapter.evaluate(q,True)
            kkt=evaluation.projected_kkt(q,g,problem.lower[sl],problem.upper[sl])/norm
            actual=(components['phi_d'],components['phi_m'],phi,kkt)
            if actual!=tuple(trace[key][i] for key in _STATES[1:]): raise ValueError('calibration: actual F/KKT replay drift')
            values=tuple(adapter.terms(q)[key] for key in ('data_gravity','data_magnetic','regularization_gravity','regularization_magnetic','coupling'))
            if not np.array_equal(c['terms_trace'][i],values) or not np.array_equal(c['physical_trace'][i],q*problem.scales[sl]):
                raise ValueError('calibration: actual physical/five-term replay drift')
            if i:
                previous=states[i-1];previous_phi,previous_g=adapter.evaluate(previous,True)
                active=(previous==problem.lower[sl])|(previous==problem.upper[sl])
                binding=((previous==problem.lower[sl])&(previous_g>=0.))|((previous==problem.upper[sl])&(previous_g<=0.))
                branch=0 if np.any(active&~binding) else 1
                if (trace['active_counts'][i-1]!=int(active.sum()) or trace['binding_counts'][i-1]!=int(binding.sum())
                        or trace['branches'][i-1]!=branch):
                    raise ValueError('calibration: exact native face/branch replay drift')
                if trace['line_search_alphas'][i-1]!=.5**(int(trace['line_search_counts'][i-1])-1):
                    raise ValueError('calibration: literal projected line-search alpha')
                slope=float(np.inner(previous_g,q-previous));margin=(phi-previous_phi)-1e-4*slope
                if slope!=trace['projected_slopes'][i-1] or margin!=trace['armijo_margins'][i-1] or not slope<0. or not margin<=0.:
                    raise ValueError('calibration: actual projected Armijo replay drift')
        if (np.any((trace['branches']<0)|(trace['branches']>1)) or np.any((trace['line_search_counts']<1)|(trace['line_search_counts']>30))
                or np.any((trace['cg_counts']<0)|(trace['cg_counts']>512))
                or np.any(trace['cg_abs_residuals']<0.) or np.any(trace['cg_relative_residuals']<0.)):
            raise ValueError('calibration: literal branch/search caps')
        if not np.array_equal(trace['cg_residuals_available'],trace['branches']==1): raise ValueError('calibration: actual CG availability')
        unused=~trace['cg_residuals_available']
        if np.any(trace['cg_counts'][unused]!=0) or np.any(trace['cg_abs_residuals'][unused]!=0.) or np.any(trace['cg_relative_residuals'][unused]!=0.):
            raise ValueError('calibration: unused CG quantities are not measurements')
        if np.any(trace['cg_relative_residuals'][trace['cg_residuals_available']]>1e-6): raise ValueError('calibration: actual CG residual cap')
        if not np.array_equal(trace['relative_changes'],np.abs(np.diff(trace['phi_engine']))/np.maximum(1.,np.abs(trace['phi_engine'][:-1]))):
            raise ValueError('calibration: trace changes drift')
        stationary=count>0 and r['status']=='converged' and r['reason']=='kkt' and trace['kkt_normalized'][-1]<=1e-5
        if c['stationarity_verified']!=stationary: raise ValueError('calibration: stationarity claim drift')
        if count:
            if not np.array_equal(r['q'],states[-1]) or tuple(r[k] for k in _STATES[1:])!=tuple(trace[k][-1] for k in _STATES[1:]):
                raise ValueError('calibration: terminal state drift')
            full=problem.start.copy();full[sl]=r['q'];metrics=optimizer.validation_wrms(problem,full,m)
            if metrics!=c['validation_wrms']: raise ValueError('calibration: real validation predictions drift')
        elif r['q'] is not None or c['validation_wrms']!={}: raise ValueError('calibration: empty-trace terminal fabrication')
        if stage in (7,15):
            modality='gravity' if stage==7 else 'magnetic'
            feasible=[entry for entry in candidates[:stage+1] if entry['modality']==modality and entry['stationarity_verified']]
            if feasible: selected[modality]=min(feasible,key=lambda entry:(entry['validation_wrms'][modality],-entry['weights']['beta_'+modality],entry['stage']))['stage']
        if stage>=16:
            baseline=optimizer.validation_wrms(problem,pair)
            eligible=stationary and all(c['validation_wrms'][modal]<=1.05*baseline[modal] for modal in evaluation.MODALITIES)
            if eligible!=c['eligible']: raise ValueError('calibration: eligibility drift')
        elif c['eligible']: raise ValueError('calibration: baseline is not a positive coupling candidate')
    if selected!=ledger['selected_baselines']: raise ValueError('calibration: exact independent baseline selection drift')
    if ledger['status']=='selected':
        pair=np.r_[candidates[selected['gravity']]['result']['q'],candidates[selected['magnetic']]['result']['q']]
        positive=[c for c in candidates[16:] if c['eligible']]
        choice=min(positive,key=lambda c:(sum(c['validation_wrms'][m]**2 for m in evaluation.MODALITIES)/2,
            c['weights']['coupling'],0 if c['start_kind']=='baseline' else 1,c['stage'])) if positive else None
        q=pair if choice is None else choice['result']['q'];stage=None if choice is None else choice['stage']
        weights={'beta_gravity':candidates[selected['gravity']]['weights']['beta_gravity'],
            'beta_magnetic':candidates[selected['magnetic']]['weights']['beta_magnetic'],'coupling':0.} if choice is None else choice['weights']
        wanted={'q':q,'weights':weights,'stage':stage,'baseline_validation_wrms':optimizer.validation_wrms(problem,pair),
            'validation_wrms':optimizer.validation_wrms(problem,q),'refit':False,'lambda0_refitted':False}
        if planner._digest(wanted)!=planner._digest(ledger['selection']): raise ValueError('calibration: frozen selection drift')
        reason='no_validated_coupling_benefit' if choice is None else 'validated_coupled_selection'
        if ledger['reason']!=reason: raise ValueError('calibration: coupling benefit claim drift')
    elif len(selected)==2 or ledger['selection'] is not None: raise ValueError('calibration: failed selection drift')
    if ledger['calibration_sha256']!=planner._digest({k:v for k,v in ledger.items() if k!='calibration_sha256'}):
        raise ValueError('calibration: full state commitment drift')
    if frozen is not None:
        evaluation.verify_frozen_model(frozen,problem)
        if ledger['status']!='selected' or frozen['origin']!='optimized_selection' or frozen['selection_sha256']!=ledger['calibration_sha256']:
            raise ValueError('calibration: frozen actual solve identity drift')
        if not np.array_equal(frozen['q'],ledger['selection']['q']) or frozen['weights']!=ledger['selection']['weights']:
            raise ValueError('calibration: frozen models/weights drift')
    return {'calibration_verified':True,'inverse_completed':ledger['status']=='selected','field_eligible':False}


def _encode(ledger):
    payload=deepcopy(ledger);arrays={}
    def bind(node,key,name):
        arrays[name]=node[key];node[key]={'array':name}
    for c in payload['candidates']:
        prefix=f"c{c['stage']:02d}_";r=c['result']
        for key in ('physical_trace','terms_trace'): bind(c,key,prefix+key)
        if r['q'] is not None: bind(r,'q',prefix+'q')
        for key in _STATES+_STEPS: bind(r['trace'],key,prefix+key)
    if payload['selection'] is not None: bind(payload['selection'],'q','selection_q')
    return payload,arrays


def write_joint_calibration(directory,ledger,problem,budget):
    verify_joint_calibration(ledger,problem,budget)
    payload,arrays=_encode(ledger)
    return files.write_arrays(directory,'calibration.json','joint-survey-calibration-file-1',payload,arrays,
        max_array_bytes=planner.MAX_EXPORT_BYTES)


def load_joint_calibration(directory,problem,budget):
    # Bounded original JSON obtains exact state COUNTS, never reads trace values
    # or arbitrary descriptor-defined filenames to discover a schema.
    from joint_survey_serialization import _external
    import joint_survey_intake as intake
    root=_external(directory,existing=True)
    document=intake._parse_json(intake._read_bounded(root/'calibration.json',planner.MAX_METADATA_BYTES))
    planner._keys(document,('schema','payload','arrays'),'calibration file')
    ledger=document['payload'];_grammar(ledger,problem,serialized=True)
    specs={}
    def spec(node,key,name,dtype,shape):
        planner._keys(node[key],('array',),'calibration reference')
        if type(node[key]['array']) is not str or node[key]['array']!=name: raise ValueError('calibration: fixed array binding')
        specs[name]=(dtype,shape)
    for c in ledger['candidates']:
        prefix=f"c{c['stage']:02d}_";r=c['result'];n=problem.n if c['modality'] else 2*problem.n
        count=r['iterations']+1 if r['q'] is not None else 0;steps=max(0,count-1)
        spec(c,'physical_trace',prefix+'physical_trace','<f8',(count,n));spec(c,'terms_trace',prefix+'terms_trace','<f8',(count,5))
        if r['q'] is not None: spec(r,'q',prefix+'q','<f8',(n,))
        for key in _STATES+_STEPS:
            shape=(count,n) if key=='models_q' else (count,) if key in _STATES else (steps,)
            dtype='|b1' if key=='cg_residuals_available' else '<i8' if key in _INT else '<f8'
            spec(r['trace'],key,prefix+key,dtype,shape)
    if ledger['selection'] is not None: spec(ledger['selection'],'q','selection_q','<f8',(2*problem.n,))
    def validate_payload(value):
        _grammar(value,problem,serialized=True)
        if value!=ledger: raise ValueError('calibration: original metadata drift')
    payload,arrays,_=files.read_arrays(directory,'calibration.json','joint-survey-calibration-file-1',specs,validate_payload,
        max_array_bytes=planner.MAX_EXPORT_BYTES)
    def materialize(node):
        if type(node) is dict:
            if set(node)=={'array'}: return arrays[node['array']]
            return {k:materialize(v) for k,v in node.items()}
        if type(node) is list: return tuple(materialize(v) for v in node)
        return node
    result=materialize(payload);verify_joint_calibration(result,problem,budget)
    return result


def write_aborted_calibration(directory,failure,problem,*,frozen_selection_created=False,sealed_values_read_started=False):
    """Strict actual failure snapshot, not a selected/replayed calibration."""
    if type(failure) is not optimizer.JointCalibrationFailure: raise TypeError('aborted: trusted driver failure required')
    if type(frozen_selection_created) is not bool or type(sealed_values_read_started) is not bool:
        raise TypeError('aborted: exact driver phase flags required')
    arrays={};payload={'schema':'joint-survey-aborted-calibration-1','plan_sha256':problem.plan['plan_sha256'],
        'development_sha256':problem.development_sha256,'reason':failure.reason,
        'source_inventory':failure.source_inventory,'optimizer_binding':failure.optimizer_binding,
        'verified_candidates':deepcopy(failure.verified_candidates),'last_attempt':deepcopy(failure.last_attempt),
        'inverse_completed':False,'sealed_values_read_started':sealed_values_read_started,'frozen_selection_created':frozen_selection_created,
        'scientific_replay_completed':False,'field_eligible':False}
    def bind(node,key,name):
        arrays[name]=node[key];node[key]={'array':name}
    for c in payload['verified_candidates']:
        prefix=f"c{c['stage']:02d}_";r=c['result']
        for key in ('physical_trace','terms_trace'): bind(c,key,prefix+key)
        if r['q'] is not None: bind(r,'q',prefix+'q')
        for key in _STATES+_STEPS: bind(r['trace'],key,prefix+key)
    last=payload['last_attempt']
    if last is not None:
        r=last['result']
        if r['q'] is not None: bind(r,'q','last_q')
        for key in _STATES+_STEPS: bind(r['trace'],key,'last_'+key)
    return files.write_arrays(directory,'aborted.json','joint-survey-aborted-calibration-file-1',payload,arrays,
        max_array_bytes=planner.MAX_EXPORT_BYTES)
