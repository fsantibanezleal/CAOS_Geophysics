"""Predeclared log17/floor3 and actual official frozen Sparse-stage controls."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from time import monotonic

import numpy as np
import pytest
from scipy.optimize import lsq_linear

import gravity_irls as irls
import gravity_l2 as l2


def policy():
    return {'norms':(1.,2.,2.,2.),'gradient_type':'components','irls_scaled':True,
        'epsilon_floor':(.001,.00001,.00001,.00001),
        'epsilon_units':('g/cc','g/cc/m','g/cc/m','g/cc/m'),
        'epsilon_initialization':'max_submitted_floor_and_fit_L2_kernel_max',
        'epsilon_continuation':{'name':'log17_floor3_1','floor_update':17,'max_updates':20,
                              'rounding':'native_log_exp_clamp_endpoints'},
        'beta_transition':'fixed_initial_beta_every_stage','max_weight_updates':20,
        'overall_stop_policy':'saturated_floor_three_stage_fixed_point_1'}


def native_problem(null=True, sparse=False):
    spec=importlib.util.spec_from_file_location('_irls_actual_controls',
        Path(__file__).with_name('test_gravity_l2.py'))
    controls=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(controls)
    req,data,prior,_,_=controls.tiny()
    if not sparse:
        req['mesh']['active'][:]=True
        for key,value in [('lower_kg_m3',-1500.),('upper_kg_m3',1500.),
                          ('start_kg_m3',0.),('reference_kg_m3',0.)]:
            prior[key]=np.full(12,value)
    if null:
        data=req['background_mgal'].copy()
        prior['reference_kg_m3'][:]=0.
    problem=l2._build_problem(req,data,controls.noise(),prior,np.arange(4,dtype=np.int64),.01)
    return problem,prior


@pytest.mark.parametrize('initial,floor',[(1.,1.),(.1,.001),(1.,.001),
    (np.finfo(np.float64).max,np.nextafter(0.,1.)),(1e-300,1e-310)])
def test_IR_C01_exact_log17_endpoints_monotonic_no_ratio(initial,floor):
    values=[irls._epsilon(float(initial),float(floor),k) for k in range(21)]
    assert values[0].hex()==float(initial).hex()
    assert all(v.hex()==float(floor).hex() for v in values[17:])
    assert all(np.isfinite(v) and floor<=v<=initial for v in values)
    assert all(left>=right for left,right in zip(values,values[1:]))
    if initial>floor:
        for k in (1,8,16):
            assert values[k]==min(initial,max(floor,float(np.exp(
                np.log(initial)+(float(k)/17.)*(np.log(floor)-np.log(initial))))))


@pytest.mark.parametrize('initial,floor,k',[(0.,.001,1),(1.,0.,1),(float('inf'),.1,1),
    (1.,float('nan'),1),(.001,.1,1),(1.,.1,True),(1.,.1,-1),(1.,.1,21)])
def test_IR_C02_invalid_log_domain_no_floor_guess(initial,floor,k):
    with pytest.raises(ValueError): irls._epsilon(initial,floor,k)


@pytest.mark.parametrize('fault',['old_cooling','floor_null','floor_zero','wrong_units',
    'norm','gradient_spelling','max_bool','continuation_extra','scaled_false'])
def test_I_T01_exact_policy_no_legacy_recipe(fault):
    value=policy()
    if fault=='old_cooling': value['epsilon_cooling_factor']=1.2
    if fault=='floor_null': value['epsilon_floor']=None
    if fault=='floor_zero': value['epsilon_floor']=(0.,.1,.1,.1)
    if fault=='wrong_units': value['epsilon_units']=('kg/m3',)*4
    if fault=='norm': value['norms']=(0.,2.,2.,2.)
    if fault=='gradient_spelling': value['gradient_type']='component'
    if fault=='max_bool': value['max_weight_updates']=True
    if fault=='continuation_extra': value['epsilon_continuation']['extra']=0
    if fault=='scaled_false': value['irls_scaled']=False
    before=deepcopy(value)
    with pytest.raises(ValueError): irls._validate_policy(value)
    assert value==before


def test_I_T03_real_Sparse_p1_scaled_and_p2_unity_with_frozen_identity():
    problem,prior=native_problem()
    q=np.linspace(-.013,.011,12)
    initial=(.013,.001,.001,.001)
    stage=irls._build_stage(problem,q,policy(),0,initial)
    assert type(stage['problem']['regularization']) is l2.regularization.Sparse
    weights=stage['weights']
    expected=np.sqrt(.013**2+.013**2)/np.sqrt(q**2+.013**2)
    np.testing.assert_allclose(weights[0],expected,rtol=1e-14,atol=0.)
    assert all(np.array_equal(w,np.ones_like(w)) for w in weights[1:])
    assert all(not w.flags.writeable for w in weights)
    reg=stage['problem']['regularization']
    trial=q+np.linspace(-.01,.01,12)
    before=[reg(trial),reg.deriv(trial).copy(),reg.deriv2(trial,np.ones(12))]
    for component in reg.objfcts:
        assert np.isfinite(component.irls_threshold) and component.irls_threshold>0
    # Merely evaluating several models MUST NOT update this fixed surrogate.
    reg(np.zeros(12))
    reg.deriv(np.zeros(12))
    np.testing.assert_array_equal(before[1],reg.deriv(trial))
    np.testing.assert_array_equal(before[2],reg.deriv2(trial,np.ones(12)))
    assert before[0]==reg(trial)
    assert stage['problem']['beta_engine']==problem['beta_engine']


def test_I_T02_original_sparse5_empty_orientation_remains_unsupported():
    problem,prior=native_problem(sparse=True)
    with pytest.raises(ValueError,match='unsupported_sparse_empty_face'):
        irls._build_stage(problem,np.zeros(5),policy(),0,(.001,.00001,.00001,.00001))


def test_IR_C03_actual_null_all21_stages_floor_and_three_real_observations(record_property):
    problem,prior=native_problem()
    value=policy()
    result=irls._solve_partition(problem,prior,value,monotonic()+120.)
    assert result['irls_terminal']['status']=='converged',result['irls_terminal']
    assert result['irls_terminal']['reason']=='irls_stationary_null'
    assert result['l2_initialization']['status']=='converged'
    assert result['l2_initialization']['iterations']==0
    assert len(result['stages'])==21 and result['irls_terminal']['weight_updates']==20
    assert result['irls_terminal']['epsilon_saturated'] is True
    assert len(result['irls_terminal']['stage_changes'])==20
    assert all(s['status']=='converged' and s['accepted_start']==s['accepted_stop']==0
               for s in result['stages'])
    assert all(s['epsilon']==value['epsilon_floor'] for s in result['stages'][17:])
    assert result['iterations']==0
    np.testing.assert_array_equal(result['model_kg_m3'],np.zeros(12))
    record_property('native_outcome','CONVERGED/IRLS_STATIONARY_NULL')
    record_property('accepted_steps',0)
    record_property('actual_fixed_stage_observations',21)


def test_IR_C04_expired_or_zero_shared_ledger_cannot_waive_nonnull_initialization():
    problem,prior=native_problem(null=False)
    result=irls._solve_partition(problem,prior,policy(),monotonic()-1.)
    assert result['irls_terminal']['status']=='nonconverged'
    assert result['irls_terminal']['reason']=='wall_cap'
    assert result['stages']==() and result['iterations']==0


def test_IR_C03_fixed_floor_alone_does_not_mean_fixed_point():
    changes=tuple({'model_relative':0.,'weights_relative':0.} for _ in range(20))
    assert irls._fixed_point(20,True,changes)
    assert not irls._fixed_point(19,True,changes[:-1])
    assert not irls._fixed_point(20,False,changes)
    changed=list(changes)
    changed[-1]={'model_relative':2e-6,'weights_relative':0.}
    assert not irls._fixed_point(20,True,tuple(changed))
    changed[-1]={'model_relative':0.,'weights_relative':None}
    assert not irls._fixed_point(20,True,tuple(changed))


def test_I_T04_actual_fixed_Sparse_quadratic_native_solution_independent_bound_oracle(record_property):
    problem,prior=native_problem(null=False)
    q=np.linspace(-.013,.011,12)
    stage=irls._build_stage(problem,q,policy(),0,(.013,.001,.001,.001))
    lower,upper=prior['lower_kg_m3']/1000.,prior['upper_kg_m3']/1000.
    obj=irls._StageObjective(stage,0,lower,upper,'b'*64)
    p=stage['problem']
    blocks=[p['misfit'].W@p['simulation'].G]
    targets=[p['misfit'].W@p['misfit'].data.dobs]
    for alpha,component in zip(p['regularization'].multipliers,p['regularization'].objfcts):
        block=np.sqrt(p['beta_engine']*alpha)*(component.W@component.f_m_deriv(p['reference_q'])).toarray()
        blocks.append(block)
        targets.append(block@p['reference_q'])
    oracle=lsq_linear(np.vstack(blocks),np.concatenate(targets),bounds=(lower,upper),
                     method='bvls',tol=1e-12,max_iter=1000)
    assert oracle.success
    binding=irls.optimizer.OptimizerBinding('physical_optimizer.solve_bounded_physical',
        irls.optimizer.SOURCE_SHA256,irls._SOURCES[Path(irls.precision.__file__).name],
        irls._INVENTORY,irls.optimizer.RUNTIME_EPOCH,irls.optimizer.POLICY)
    budget=irls.optimizer.OptimizerBudget(monotonic()+120.,200,2*1024**3,16*1024**2,'b'*64)
    result=irls.optimizer.solve_bounded_physical(obj,lower,upper,q,budget=budget,binding=binding)
    assert result['status']=='converged',result
    np.testing.assert_allclose(result['q'],oracle.x,rtol=1e-7,atol=1e-8)
    assert result['iterations']>0
    record_property('native_outcome',result['status'].upper()+'/'+result['reason'].upper())


def test_I_T04_mutated_stage_factors_rejected_before_initial_binding():
    problem,prior=native_problem()
    stage=irls._build_stage(problem,np.zeros(12),policy(),0,(.001,.00001,.00001,.00001))
    obj=irls._StageObjective(stage,0,prior['lower_kg_m3']/1000.,prior['upper_kg_m3']/1000.,'b'*64)
    stage['problem']['regularization'].objfcts[0].irls_threshold=.002
    with pytest.raises(ValueError,match='stage'):
        obj.identity()


@pytest.mark.parametrize('factor',['reference','norm','scale','mapping'])
def test_I_T04_actual_component_semantics_bound_not_just_weight_array(factor):
    problem,prior=native_problem()
    stage=irls._build_stage(problem,np.zeros(12),policy(),0,(.001,.00001,.00001,.00001))
    obj=irls._StageObjective(stage,0,prior['lower_kg_m3']/1000.,prior['upper_kg_m3']/1000.,'b'*64)
    component=stage['problem']['regularization'].objfcts[0]
    before=obj.identity()
    if factor=='reference': component.reference_model=np.full(12,.1)
    if factor=='norm': component.norm=0.
    if factor=='scale': component.irls_scaled=False
    if factor=='mapping': component.mapping=l2.maps.IdentityMap(nP=12)*l2.maps.IdentityMap(nP=12)
    # Even an equal-valued foreign mapping is outside this frozen ordinary
    # identity-map recipe. No caller-selected computation gets a new seal.
    with pytest.raises(ValueError,match='stage'):
        obj.identity()
    assert len(before['objective_sha256'])==64


def test_I_T01_structural_checks_precede_foreign_equality():
    class Foreign:
        def __eq__(self,other): raise AssertionError('foreign equality executed')
    for field in ('norms','gradient_type','epsilon_units','epsilon_initialization'):
        value=policy()
        value[field]=(Foreign(),2.,2.,2.) if field=='norms' else (
            (Foreign(),'g/cc/m','g/cc/m','g/cc/m') if field=='epsilon_units' else Foreign())
        with pytest.raises(ValueError): irls._validate_policy(value)


def test_IR_C06_nonnull_actual_fixed_floor_stages_shared_budget_no_step_fabrication(monkeypatch,record_property):
    problem,prior=native_problem(null=False)
    actual=[]
    native=irls.optimizer.solve_bounded_physical
    def record(objective,*args,**kwargs):
        result=native(objective,*args,**kwargs)
        actual.append((kwargs['budget'].remaining_steps,result['iterations'],
                       result['status'],result['reason']))
        return result
    monkeypatch.setattr(irls.optimizer,'solve_bounded_physical',record)
    result=irls._solve_partition(problem,prior,policy(),monotonic()+120.)
    terminal=result['irls_terminal']
    record_property('native_outcome',terminal['status'].upper()+'/'+terminal['reason'].upper())
    record_property('actual_stage_outcomes',repr(actual))
    record_property('actual_accepted_steps',result['iterations'])
    record_property('actual_stage_changes',json.dumps(terminal['stage_changes'],allow_nan=False))
    record_property('actual_stage_epsilon',json.dumps([s['epsilon'] for s in result['stages']],allow_nan=False))
    assert result['iterations']==result['l2_initialization']['iterations']+sum(a[1] for a in actual)
    assert result['iterations']<=200
    assert len(actual)==21 and terminal['weight_updates']==20
    assert len(result['trace']['models_kg_m3'])==result['iterations']+1
    for i,(remaining,accepted,status,reason) in enumerate(actual):
        assert remaining==200-result['l2_initialization']['iterations']-sum(a[1] for a in actual[:i])
        assert result['stages'][i]['accepted_stop']-result['stages'][i]['accepted_start']==accepted
        assert status=='converged' and reason in ('absolute_stationary','kkt_stable')
    # This actual positive scientific expectation remains a FAILURE when the
    # prescribed three final transitions do not converge. Never mark it xfail.
    assert terminal['status']=='converged',terminal
    assert terminal['reason']=='irls_fixed_point'


def _book_fixture():
    """Typed serialization fixture only; never a scientific solve receipt."""
    weights=np.array([1.,2.,3.])
    trace={'models_kg_m3':np.array([[0.,0.,0.],[1.,2.,3.]]),
           'stage_indices':np.array([-1,0],dtype=np.int64)}
    metrics={name:None if name.endswith('_initial') else 0.
             for name in irls._BOOK_METRICS}
    rows=({'index':0,'accepted_start':0,'accepted_stop':1,
        'model_row_start':0,'model_row_stop':1,'beta_engine':2.,
        'epsilon':(.001,.00001,.00001,.00001),'epsilon_units':policy()['epsilon_units'],
        'norms':policy()['norms'],'weight_sha256':(irls.survey._digest(weights),)+('f'*64,)*3,
        'smallness_weights':weights,'operator_sha256':('8'*64,)*4,
        'status':'converged','reason':'absolute_stationary','metrics':metrics},)
    args={'parameter_count':3,'beta_engine':2.,'initial_epsilon':policy()['epsilon_floor'],
          'policy':policy()}
    return rows,trace,args


def test_SB02_signed_words_exact_bits_no_float_roundtrip():
    for digest in ('0'*64,'f'*64,'8'*64,'0123456789abcdef'*4):
        words=irls._hash_words(digest)
        assert words.dtype==np.int64 and words.shape==(4,)
        assert irls._words_hash(words)==digest
    assert np.all(irls._hash_words('f'*64)==-1)
    for digest in ('F'*64,'a'*63,False):
        with pytest.raises((TypeError,ValueError)): irls._hash_words(digest)


def test_SB03_lossless_fifteen_key_digest_null_and_trace_binding():
    rows,trace,args=_book_fixture()
    book=irls.encode_stage_book(rows,trace,**args)
    assert len(book)==19 and book['schema']=='gravity-survey-irls-stage-book-1'
    assert book['logical_stage_sha256']==irls.survey._digest(rows)
    decoded=irls.decode_stage_book(book,trace,**args)
    assert irls.survey._digest(decoded)==irls.survey._digest(rows)
    assert decoded[0]['metrics']['phi_d_initial'] is None
    assert decoded[0]['metrics']['phi_d_final']==0.
    assert not decoded[0]['smallness_weights'].flags.writeable
    assert all(not v.flags.writeable for v in book.values() if type(v) is np.ndarray)
    assert all(not v.flags.writeable for v in book['metrics'].values() if type(v) is np.ndarray)


@pytest.mark.parametrize('fault',['extra','unknown_status','unknown_reason','status_reason',
    'duplicate_metric','gap_metric','unknown_metric_column','weight_digest','span_gap',
    'epsilon','beta','nonfinite','array_type','logical_digest','book_digest'])
def test_SB04_rehashed_inconsistent_book_never_decodes(fault):
    rows,trace,args=_book_fixture()
    book=deepcopy(irls.encode_stage_book(rows,trace,**args))
    for item in book.values():
        if type(item) is np.ndarray: item.flags.writeable=True
    for item in book['metrics'].values():
        if type(item) is np.ndarray: item.flags.writeable=True
    if fault=='extra': book['extra']=0
    if fault=='unknown_status': book['status'][0]=7
    if fault=='unknown_reason': book['reason'][0]=99
    if fault=='status_reason': book['status'][0]=1
    if fault=='duplicate_metric': book['metrics']['index'][0,3]=0
    if fault=='gap_metric': book['metrics']['index'][0,4]=1
    if fault=='unknown_metric_column': book['metrics']['columns']=('wrong',)+book['metrics']['columns'][1:]
    if fault=='weight_digest': book['weight_sha256_words'][0,0]^=1
    if fault=='span_gap': book['accepted_span'][0,0]=1
    if fault=='epsilon': book['epsilon'][0,0]=.002
    if fault=='beta': book['beta_engine'][0]=3.
    if fault=='nonfinite': book['smallness_weights'][0,0]=float('nan')
    if fault=='array_type': book['index']=np.array([0],dtype=np.int32)
    if fault=='logical_digest': book['logical_stage_sha256']='a'*64
    if fault=='book_digest': book['book_sha256']='a'*64
    else: book['book_sha256']=irls.survey._digest({k:v for k,v in book.items() if k!='book_sha256'})
    with pytest.raises((TypeError,ValueError)): irls.decode_stage_book(book,trace,**args)


def test_SB01_complete_metadata_admission_before_hash_or_copy(monkeypatch):
    rows,trace,args=_book_fixture()
    book=irls.encode_stage_book(rows,trace,**args)
    book['untrusted_oversize']='a'*262145
    def denied(*a,**k): raise AssertionError('hash/copy before metadata admission')
    monkeypatch.setattr(irls.survey,'_digest',denied)
    monkeypatch.setattr(irls.survey,'_readonly',denied)
    with pytest.raises((TypeError,ValueError)): irls.decode_stage_book(book,trace,**args)


def test_SB04_trace_changes_and_unaccounted_rows_rejected():
    rows,trace,args=_book_fixture()
    book=irls.encode_stage_book(rows,trace,**args)
    for key in ('models_kg_m3','stage_indices'):
        changed=deepcopy(trace)
        changed[key].flat[-1]+=1
        with pytest.raises(ValueError): irls.decode_stage_book(book,changed,**args)
    bad=deepcopy(rows)
    bad[0]['accepted_stop']=0
    with pytest.raises(ValueError): irls.encode_stage_book(bad,trace,**args)


def test_SB03_actual_native_null21_book_preserves_every_stage(record_property):
    problem,prior=native_problem()
    result=irls._solve_partition(problem,prior,policy(),monotonic()+120.)
    args={'parameter_count':12,'beta_engine':float(problem['beta_engine']),
          'initial_epsilon':policy()['epsilon_floor'],'policy':policy()}
    book=irls.encode_stage_book(result['stages'],result['trace'],**args)
    decoded=irls.decode_stage_book(book,result['trace'],**args)
    assert len(decoded)==21
    assert irls.survey._digest(decoded)==irls.survey._digest(result['stages'])
    record_property('native_outcome','CONVERGED/IRLS_STATIONARY_NULL')
    record_property('logical_stage_sha256',book['logical_stage_sha256'])


@pytest.mark.parametrize('field',['norms','epsilon_units'])
def test_SB04_empty_book_still_rejects_foreign_semantics(field):
    _,trace,args=_book_fixture()
    trace={'models_kg_m3':trace['models_kg_m3'][:1],
           'stage_indices':trace['stage_indices'][:1]}
    book=irls.encode_stage_book((),trace,**args)
    book[field]=('wrong',)*4
    book['book_sha256']=irls.survey._digest({k:v for k,v in book.items() if k!='book_sha256'})
    with pytest.raises(ValueError): irls.decode_stage_book(book,trace,**args)


def test_SB03_no_stage_or_initial_threshold_after_failed_initialization():
    _,_,args=_book_fixture()
    args['initial_epsilon']=None
    trace={'models_kg_m3':np.empty((0,3)), 'stage_indices':np.empty(0,dtype=np.int64)}
    book=irls.encode_stage_book((),trace,**args)
    assert irls.decode_stage_book(book,trace,**args)==()


def test_SB05_actual25_books_fit_whole_guard_without_list_digest_waiver():
    problem,prior=native_problem()
    result=irls._solve_partition(problem,prior,policy(),monotonic()+120.)
    args={'parameter_count':12,'beta_engine':float(problem['beta_engine']),
          'initial_epsilon':policy()['epsilon_floor'],'policy':policy()}
    book=irls.encode_stage_book(result['stages'],result['trace'],**args)
    # Repeated aliases are charged at EVERY logical occurrence, not deduped.
    envelope={'candidates':tuple({'folds':tuple({'solve':{'stages':book,
        'trace':result['trace'],'l2_initialization':result['l2_initialization']}}
        for _ in range(3))} for _ in range(8)),
        'final_solve':{'stages':book,'trace':result['trace'],
                       'l2_initialization':result['l2_initialization']}}
    # The preserved proposal's metrics.columns scalar children reach depth9.
    # Never increase the literal depth8 guard to accept this representation.
    with pytest.raises(ValueError,match='eight container levels'):
        l2._result_native_metadata(envelope)
    legacy=deepcopy(envelope)
    for candidate in legacy['candidates']:
        for fold in candidate['folds']: fold['solve']['stages']=result['stages']
    legacy['final_solve']['stages']=result['stages']
    with pytest.raises(ValueError): l2._result_native_metadata(legacy)
    pool={'stage_books':tuple(book for _ in range(25)),
          'candidates':tuple({'folds':tuple({'solve':{'stages':3*i+j,
              'trace':result['trace'],'l2_initialization':result['l2_initialization']}}
              for j in range(3))} for i in range(8)),
          'final_solve':{'stages':24,'trace':result['trace'],
                         'l2_initialization':result['l2_initialization']}}
    l2._result_native_metadata(pool)


def test_SB03_actual_nonnull_cap_outcome_lossless_not_promoted(record_property):
    problem,prior=native_problem(null=False)
    result=irls._solve_partition(problem,prior,policy(),monotonic()+120.)
    kernels=[c.f_m(result['l2_initialization']['model_kg_m3']/1000.)
        for alpha,c in zip(problem['regularization'].multipliers,
                           problem['regularization'].objfcts) if alpha>0.]
    initial=tuple(max(f,float(np.max(np.abs(k)))) for f,k in zip(policy()['epsilon_floor'],kernels))
    args={'parameter_count':12,'beta_engine':float(problem['beta_engine']),
          'initial_epsilon':initial,'policy':policy()}
    book=irls.encode_stage_book(result['stages'],result['trace'],**args)
    decoded=irls.decode_stage_book(book,result['trace'],**args)
    assert irls.survey._digest(decoded)==irls.survey._digest(result['stages'])
    assert result['irls_terminal']['status']=='nonconverged'
    assert result['irls_terminal']['reason']=='irls_iteration_cap'
    record_property('native_outcome','NONCONVERGED/IRLS_ITERATION_CAP')


def test_SB05_unchanged_array_limit_counts_duplicate_logical_occurrences():
    values=np.zeros((4096,4096),dtype=np.float64)
    # Two references are256MiB exactly; a third remains refused.
    l2._result_native_metadata((values,values))
    with pytest.raises(ValueError): l2._result_native_metadata((values,values,values))


def test_SB01_foreign_hook_rejected_without_comparison():
    class Foreign:
        def __eq__(self,other): raise AssertionError('foreign comparison')
    rows,trace,args=_book_fixture()
    book=irls.encode_stage_book(rows,trace,**args)
    book['count']=Foreign()
    with pytest.raises(TypeError): irls.decode_stage_book(book,trace,**args)
