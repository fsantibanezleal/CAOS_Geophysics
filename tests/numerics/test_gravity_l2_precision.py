"""cpu-4 test-first certified predicates, never a replacement production oracle."""
from decimal import Decimal, getcontext, ROUND_UP
from fractions import Fraction as F
import importlib
import json
from threading import Event, Thread
from time import monotonic
from types import SimpleNamespace

import numpy as np
import pytest
import scipy.sparse as sp
import choclo
import psutil

import gravity_l2 as l2
from test_gravity_l2 import six_cell_control, tiny, noise, assert_six_cell_optimum


def evaluator(problem, lower, upper, deadline=None):
    return importlib.import_module('gravity_l2_precision')._CertifiedDelta(
        problem, np.array(lower, dtype=np.float64), np.array(upper, dtype=np.float64),
        l2.monotonic()+120. if deadline is None else deadline)


def toy(g=((1.,),), target=(0.,), reference=(0.,), alpha=0., beta=1., w=None, d=None):
    g = np.array(g, dtype=np.float64)
    a = len(g[0])
    component = SimpleNamespace(W=sp.eye(a, format='csr'),
                                f_m_deriv=lambda q: sp.eye(a, format='csr') if d is None else sp.csr_matrix(d))
    return {'simulation': SimpleNamespace(G=g),
            'misfit': SimpleNamespace(W=sp.eye(len(g), format='csr') if w is None else sp.csr_matrix(w),
                                      data=SimpleNamespace(dobs=np.array(target, dtype=np.float64))),
            'regularization': SimpleNamespace(multipliers=(alpha,), objfcts=(component,)),
            'reference_q': np.array(reference, dtype=np.float64), 'beta_engine': beta}


def evaluate(engine, q, qt, gradient, phi=1., phit=.5):
    return engine.evaluate(np.array(q, dtype=np.float64), np.array(qt, dtype=np.float64),
                           np.array(gradient, dtype=np.float64), 0, 0, phi, phit)


def interval_contains(pair, exact):
    assert pair is not None
    assert F(Decimal(pair[0])) <= exact <= F(Decimal(pair[1]))


def rational_nested_objective(problem, q):
    """Tiny test-only independent exact assembly; never imported by product."""
    x = [F.from_float(float(v)) for v in q]
    def mat(matrix,vector):
        dense = matrix.toarray() if sp.issparse(matrix) else matrix
        return [sum((F.from_float(float(c))*v for c,v in zip(row,vector)),F(0)) for row in dense]
    misfit = problem['misfit']
    residual = mat(misfit.W,[v-F.from_float(float(d)) for v,d in zip(mat(problem['simulation'].G,x),misfit.data.dobs)])
    total = sum((v*v for v in residual),F(0))
    delta = [v-F.from_float(float(ref)) for v,ref in zip(x,problem['reference_q'])]
    regularizer = problem['regularization']
    for alpha,component in zip(regularizer.multipliers,regularizer.objfcts):
        if alpha==0: continue
        model = mat(component.W,mat(component.f_m_deriv(problem['reference_q']),delta))
        total += F.from_float(float(alpha))*F.from_float(problem['beta_engine'])*sum((v*v for v in model),F(0))
    return total


def test_certified_delta_native_six_cell_full_chord(monkeypatch):
    states = []
    original = l2._RecordedProjectedGNCG._record
    def observe(optimizer):
        outcome = original(optimizer)
        states.append((optimizer.xc.copy(),optimizer.g.copy()))
        return outcome
    monkeypatch.setattr(l2._RecordedProjectedGNCG,'_record',observe)
    req, observed, spec, prior, _, _, _ = six_cell_control('diagonal_sd', 1500., 'upper_lower')
    problem = l2._build_problem(req, observed, spec, prior, np.arange(5, dtype=np.int64), .01)
    result = l2._solve_partition(problem, prior)
    assert result['status'] == 'converged' and result['reason'] == 'absolute_stationary'
    assert result['iterations'] <= 200
    records = problem['optimizer_evidence']['precision_trials']
    assert records and all(r['passes'] <= 3 for r in records)
    assert any(r['decision'] == 'certified_accept' and r['native_phi_trial'] > r['native_phi_current'] for r in records)
    assert len(result['trace']['models_kg_m3']) == result['iterations']+1
    for record in records:
        if record['decision']!='certified_accept': continue
        # Exact q is native accepted state, not an oracle-manufactured step.
        q,gradient = states[record['iteration']]
        qt = states[record['iteration']+1][0]
        delta = rational_nested_objective(problem,qt)-rational_nested_objective(problem,q)
        slope = sum((F.from_float(float(g))*(F.from_float(float(y))-F.from_float(float(x)))
                     for g,x,y in zip(gradient,q,qt)),F(0))
        interval_contains(record['delta_interval'],delta)
        interval_contains(record['slope_interval'],slope)
        interval_contains(record['armijo_margin_interval'],delta-F.from_float(1e-4)*slope)
    assert l2.RUNTIME_EPOCH == 'm02-survey-l2-cpu-4'
    assert l2.OPTIMIZER_POLICY == 'projected-gncg-binding-release-certified-delta-1'


@pytest.mark.parametrize('kind', ['noop', 'zero_slope', 'rounded_zero'])
def test_certified_delta_no_fake_progress(kind):
    q, qt, grad = [1.], [0.], [0.]
    if kind == 'noop': qt, grad = q, [2.]
    if kind == 'rounded_zero': q, qt, grad = [1.], [1.+1e-30], [2.]
    r = evaluate(evaluator(toy(), [-2.], [2.]), q, qt, grad)
    assert r['decision'] != 'certified_accept'
    assert r['cause'] == ('non_descent' if kind == 'zero_slope' else 'zero_displacement')
    assert r['passes'] == (1 if kind == 'zero_slope' else 0)


@pytest.mark.parametrize('ascent', [False, True])
def test_certified_delta_rounding_reversal(ascent):
    q, qt, grad = ([0.], [1.], [-2.]) if ascent else ([1.], [0.], [2.])
    # Adversarial rounded scalar cannot authorize an ascent or forbid real descent.
    r = evaluate(evaluator(toy(), [-2.], [2.]), q, qt, grad, phi=1., phit=0. if ascent else 2.)
    assert r['decision'] == ('certified_reject' if ascent else 'certified_accept')
    interval_contains(r['delta_interval'], F(1 if ascent else -1))


def test_certified_delta_frozen_slope():
    engine = evaluator(toy(), [-2.], [2.])
    good = evaluate(engine, [1.], [0.], [2.])
    wrong = evaluate(engine, [1.], [0.], [-2.])
    assert good['decision'] == 'certified_accept' and wrong['cause'] == 'non_descent'
    interval_contains(good['slope_interval'], F(-2))
    interval_contains(wrong['slope_interval'], F(2))


def test_certified_delta_interval_inclusion():
    q, qt, g, coefficient, target = .7, .6, 3., .3, .2
    r = evaluate(evaluator(toy(((coefficient,),), (target,)), [-2.], [2.]), [q], [qt], [g])
    x, y, b, c, gn = map(F.from_float, [q, qt, coefficient, target, g])
    delta = (b*y-c)**2-(b*x-c)**2
    slope = gn*(y-x)
    interval_contains(r['delta_interval'], delta)
    interval_contains(r['slope_interval'], slope)
    interval_contains(r['armijo_margin_interval'], delta-F.from_float(1e-4)*slope)
    assert r['passes'] == 1 and r['precision_digits'] == 34
    # Exactly zero margin: three passes, never manufacture strict acceptance.
    boundary = evaluate(evaluator(toy(((0.,),), alpha=1e-4), [-2.], [2.]), [1.], [0.], [1.])
    assert boundary['decision'] == 'unresolved' and boundary['cause'] == 'precision_limit'
    assert boundary['passes'] == 3 and boundary['precision_digits'] == 80
    interval_contains(boundary['armijo_margin_interval'], F(0))


def test_certified_delta_source_identity():
    w, d, alpha, beta = .7, .3, .2, .6
    ref, target, q, qt = .1, .2, .7, .6
    engine = evaluator(toy(((.3,),), (target,), (ref,), alpha, beta, [[w]], [[d]]), [-2.], [2.])
    r = evaluate(engine, [q], [qt], [3.])
    x,y,rr,dd,ww,aa,bb,tt,j = map(F.from_float, [q,qt,ref,d,w,alpha,beta,target,.3])
    exact = ww**2*((j*y-tt)**2-(j*x-tt)**2)+aa*bb*dd**2*((y-rr)**2-(x-rr)**2)
    interval_contains(r['delta_interval'], exact)
    assert r['arithmetic_domain'] == 'fixed_native_operand_quadratic'
    assert r['slope_domain'] == 'recorded_native_gradient'


def test_certified_delta_nested_matrix_and_stored_dobs():
    # Deliberately non-diagonal W/D; compare the nested exact factors, not
    # a pre-rounded matrix product. dobs is the already rounded native datum.
    g = np.array([[.1,.3],[.7,-.2]])
    w = np.array([[.6,.4],[.4,.8]])
    d = np.array([[.3,-.7],[.2,.4]])
    target = np.array([.7-.6,.3-.2])
    q, qt, ref, grad = [.7,-.2], [.6,-.1], [.1,-.3], [3.,-2.]
    engine = evaluator(toy(g,target,ref,.2,.6,w,d),[-2.,-2.],[2.,2.])
    r = evaluate(engine,q,qt,grad)
    def mat(matrix, values):
        return [sum((F.from_float(float(c))*v for c,v in zip(row,values)),F(0)) for row in matrix]
    def objective(values):
        x = list(map(F.from_float,values))
        residual = mat(w,[v-F.from_float(float(t)) for v,t in zip(mat(g,x),target)])
        model = mat(d,[v-F.from_float(t) for v,t in zip(x,ref)])
        return sum((v*v for v in residual),F(0))+F.from_float(.2)*F.from_float(.6)*sum((v*v for v in model),F(0))
    delta = objective(qt)-objective(q)
    slope = sum((F.from_float(gg)*(F.from_float(y)-F.from_float(x)) for gg,x,y in zip(grad,q,qt)),F(0))
    interval_contains(r['delta_interval'],delta)
    interval_contains(r['slope_interval'],slope)
    interval_contains(r['armijo_margin_interval'],delta-F.from_float(1e-4)*slope)


def test_certified_delta_platform_precision():
    original = getcontext().copy()
    try:
        getcontext().prec, getcontext().rounding = 2, ROUND_UP
        engine = evaluator(toy(), [-2.], [2.])
        r = evaluate(engine, [1.], [0.], [2.])
        assert r['decision'] == 'certified_accept'
        assert getcontext().prec == 2 and getcontext().rounding == ROUND_UP
    finally:
        import decimal
        decimal.setcontext(original)
    assert np.finfo(np.longdouble).nmant+1 == 53  # pinned Windows runtime, no fictitious extended precision


@pytest.mark.parametrize('fault', ['model', 'gradient', 'phi', 'trial_phi', 'operator'])
def test_certified_delta_native_failures(fault):
    p = toy()
    if fault == 'operator': p['simulation'].G[0,0] = np.inf
    if fault == 'operator':
        with pytest.raises(ValueError): evaluator(p, [-2.], [2.])
        return
    args = dict(q=[1.], qt=[0.], gradient=[2.], phi=1., phit=0.)
    args[{'model':'qt','gradient':'gradient','phi':'phi','trial_phi':'phit'}[fault]] = (
        [np.nan] if fault in ('model','gradient') else np.nan)
    r = evaluate(evaluator(p, [-2.], [2.]), **args)
    assert r['decision'] == 'not_run' and r['cause'] == 'native_failure'
    assert r['slope_interval'] is r['delta_interval'] is r['armijo_margin_interval'] is None


def test_certified_delta_precision_deadline_caps():
    r = evaluate(evaluator(toy(), [-2.], [2.], deadline=-1.), [1.], [0.], [2.])
    assert r['cause'] == 'wall_cap' and r['decision'] == 'not_run' and r['passes'] == 0
    engine = evaluator(toy(), [-2.], [2.])
    with pytest.raises(ValueError): engine.evaluate(np.ones(1), np.zeros(1), np.ones(1), 200, 0, 1., 0.)
    with pytest.raises(ValueError): engine.evaluate(np.ones(1), np.zeros(1), np.ones(1), 0, 20, 1., 0.)


@pytest.mark.parametrize('cut', [2,7,12])
def test_certified_delta_midstream_deadline_discards_partial_output(monkeypatch,cut):
    module = importlib.import_module('gravity_l2_precision')
    engine = evaluator(toy(alpha=1.),[-2.],[2.],deadline=10.)
    clock_calls = []
    def clock():
        clock_calls.append(None)
        return 11. if len(clock_calls)>=cut else 0.
    monkeypatch.setattr(module,'monotonic',clock)
    r = evaluate(engine,[1.],[0.],[4.])
    assert len(clock_calls)==cut and r['decision']=='not_run' and r['cause']=='wall_cap'
    assert r['passes']==0 and r['precision_digits'] is None
    assert r['slope_interval'] is r['delta_interval'] is r['armijo_margin_interval'] is None


def test_certified_delta_decimal_failure_discards_partial_output(monkeypatch):
    from decimal import InvalidOperation
    module = importlib.import_module('gravity_l2_precision')
    engine = evaluator(toy(alpha=1.),[-2.],[2.])
    calls = []
    original = module._Intervals.matrix
    def broken(arithmetic,matrix,vector):
        calls.append(None)
        if len(calls)==3: raise InvalidOperation('incomplete interval arithmetic')
        return original(arithmetic,matrix,vector)
    monkeypatch.setattr(module._Intervals,'matrix',broken)
    r = evaluate(engine,[1.],[0.],[4.])
    assert len(calls)==3 and r['decision']=='not_run' and r['cause']=='range_unsupported'
    assert r['passes']==0 and r['precision_digits'] is None
    assert r['slope_interval'] is r['delta_interval'] is r['armijo_margin_interval'] is None


def test_certified_delta_exact_diagnostic_keys():
    module = importlib.import_module('gravity_l2_precision')
    r = evaluate(evaluator(toy(), [-2.], [2.]), [1.], [0.], [2.])
    assert len(r) == 14
    module._validate_record(r)
    for change in ({'extra':0}, {'slope_interval':('NaN','0')}, {'passes':True},
                   {'precision_digits':17}, {'decision':'finite_precision_stagnation'},
                   {'armijo_margin_interval':('0','-1')}, {'delta_interval':('0'*193,'1')},
                   {'native_phi_trial':None}):
        bad = dict(r, **change)
        with pytest.raises(ValueError): module._validate_record(bad)


@pytest.mark.parametrize('subnormal', [False, True])
def test_certified_delta_null_bound_faces(subnormal):
    tiny_value = np.nextafter(0., 1.) if subnormal else 0.
    r = evaluate(evaluator(toy(), [0.], [1.]), [tiny_value], [0.], [tiny_value])
    assert r['decision'] == ('certified_accept' if subnormal else 'not_run')
    rejected = evaluate(evaluator(toy(), [0.], [1.]), [1.], [-1.], [2.])
    assert rejected['decision'] != 'certified_accept'


@pytest.mark.parametrize('kind', ['diagonal_sd','full_covariance'])
@pytest.mark.parametrize('bound', [75.,1500.])
@pytest.mark.parametrize('start', ['zero','all_lower','all_upper','lower_upper','upper_lower','lower_reference','upper_reference'])
def test_certified_delta_unchanged_controls(kind,bound,start):
    # Reuse every unchanged independent numerical comparison, not a weaker proxy.
    assert_six_cell_optimum(kind,bound,start)


def test_certified_delta_streaming_resources():
    # Exact cap-edge pure evaluator, not a claim of full native workflow resources.
    n, a = 2048, 4096
    p = toy(g=np.zeros((n,a)), target=np.zeros(n), reference=np.zeros(a))
    p['simulation'].G[0,0] = 1.
    engine = evaluator(p, [-2.]*a, [2.]*a)
    q, qt, g = np.zeros(a), np.zeros(a), np.zeros(a)
    q[0], g[0] = 1., 2.
    r = evaluate(engine, q, qt, g)
    assert r['decision'] == 'certified_accept'
    assert not any(type(x) is list and len(x) >= n*a for x in vars(engine).values())
    for dimension in ('rows', 'cells'):
        oversized = toy(g=np.zeros((2049,1) if dimension=='rows' else (1,4097)),
                        target=np.zeros(2049 if dimension=='rows' else 1),
                        reference=np.zeros(1 if dimension=='rows' else 4097))
        with pytest.raises(ValueError): evaluator(oversized, [-2.]*len(oversized['reference_q']), [2.]*len(oversized['reference_q']))


def test_certified_delta_real_cap_resource_measurement(record_property):
    """Actual dense native G at both frozen caps, never a sparse toy substitute.

    Unsealed resource control: independent off-grid prism, fixed beta .01,
    no geometry/candidate/stopping selection from the measured outcome. This
    is not the locked24 workflow or the20 nominal-repeat resource gate.
    """
    req, _, prior, _, _ = tiny()
    n,a = 2048,4096
    points = np.array([[-3150.+100.*i,-1550.+100.*j,100.] for j in range(32) for i in range(64)])
    req['mesh'] = {'origin_m':np.array([-800.,-800.,-1600.]),
                   'hx_m':np.full(16,100.),'hy_m':np.full(16,100.),'hz_m':np.full(16,100.),
                   'active':np.ones(a,dtype=bool)}
    req['stations']['receivers_m'] = points
    req['background_mgal'] = np.zeros(n)
    observed = np.array([choclo.prism.gravity_u(*point,-85.,45.,-75.,35.,-135.,-45.,450.)*1e5 for point in points])
    for key,value in [('lower_kg_m3',-1500.),('upper_kg_m3',1500.),('start_kg_m3',0.),('reference_kg_m3',0.)]:
        prior[key] = np.full(a,value)
    prior['lengths_m'] = np.full(3,100.)
    spec = {'kind':'diagonal_sd','values':np.full(n,.005)}
    rows = np.arange(n,dtype=np.int64)
    from gravity_survey_l2 import _digest
    spec_sha = _digest({'request':req,'prior':prior,'noise':spec,'observations':observed,'beta':.01})
    process, done = psutil.Process(), Event()
    samples = [process.memory_info().rss]
    def monitor():
        while not done.wait(.01): samples.append(process.memory_info().rss)
    watcher = Thread(target=monitor,daemon=True)
    started = monotonic()
    watcher.start()
    try:
        problem = l2._build_problem(req,observed,spec,prior,rows,.01)
        built = monotonic()
        result = l2._solve_partition(problem,prior)
        # Separate performance diagnostic, NEVER a fallback/accepted solver
        # state after CG failure. Both models are dense and use real operands.
        q,qt = np.full(a,.01),np.full(a,.009)
        native_gradient = problem['misfit'].deriv(q)+problem['beta_engine']*problem['regularization'].deriv(q)
        phi = float(problem['misfit'](q)+problem['beta_engine']*problem['regularization'](q))
        phit = float(problem['misfit'](qt)+problem['beta_engine']*problem['regularization'](qt))
        proof_started = monotonic()
        engine = evaluator(problem,prior['lower_kg_m3']/1000.,prior['upper_kg_m3']/1000.)
        performance_certificate = evaluate(engine,q,qt,native_gradient,phi,phit)
        proof_seconds = monotonic()-proof_started
    finally:
        done.set()
        watcher.join()
        samples.append(process.memory_info().rss)
    measurements = {'control':'unsealed_real_cap_2048_4096_diagonal_prism','spec_sha256':spec_sha,
                    'n':n,'a':a,'G_bytes':problem['simulation'].G.nbytes,
                    'G_nonzero':int(np.count_nonzero(problem['simulation'].G)),
                    'base_rss_bytes':samples[0],'peak_rss_bytes':max(samples),
                    'rss_samples':len(samples),'build_seconds':built-started,'total_seconds':monotonic()-started,
                    'solve_seconds':result['wall_seconds'],'status':result['status'],'reason':result['reason'],
                    'iterations':result['iterations'],'kkt_normalized':result['kkt_normalized'],
                    'precision_trials':len(problem['optimizer_evidence']['precision_trials']),
                    'last_precision':problem['optimizer_evidence']['precision_trials'][-1] if problem['optimizer_evidence']['precision_trials'] else None,
                    'result_sha256':_digest(result),'runtime_epoch':l2.RUNTIME_EPOCH,
                    'diagnostic_chord_not_solver_direction':True,'diagnostic_seconds':proof_seconds,
                    'diagnostic_certificate':performance_certificate,
                    'full_workflow_resource_acceptance':False}
    record_property('actual_resource_measurements',json.dumps(measurements,sort_keys=True,allow_nan=False))
    assert problem['simulation'].G.nbytes==64*1024**2 and measurements['G_nonzero']==n*a
    assert max(samples)<=2*1024**3
    assert result['status']=='converged', measurements


def test_stagnation_verdict_closed():
    req, _, prior, _, _ = tiny()
    prior['reference_kg_m3'][:] = prior['start_kg_m3'][:] = 0.
    p = l2._build_problem(req, req['background_mgal'], noise(), prior, np.arange(4,dtype=np.int64), .01)
    result = l2._solve_partition(p, prior)
    assert result['reason'] == 'absolute_stationary' and result['iterations'] == 0
    assert p['optimizer_evidence']['precision_trials'] == ()
    assert 'finite_precision_stagnation' not in result['reason']


@pytest.mark.parametrize('width', [1,7,37,4096])
@pytest.mark.parametrize('sparse', [False,True])
def test_NI01_outward_row_matches_independent_rational_corners(width,sparse):
    module = importlib.import_module('gravity_l2_precision')
    arithmetic = module._Intervals(34,monotonic()+30.)
    # Test the actual new enclosure, not the old Decimal implementation alone.
    assert hasattr(arithmetic,'_enclosed_row')
    generator = np.random.Generator(np.random.PCG64(104729+width))
    coefficients = generator.normal(size=width)*.3
    centers = generator.normal(size=width)
    radii = np.abs(generator.normal(size=width))*2.**-35
    vector = [arithmetic.sub(arithmetic.exact(z),arithmetic.exact(r))[0:1]+
              arithmetic.add(arithmetic.exact(z),arithmetic.exact(r))[1:2]
              for z,r in zip(centers,radii)]
    matrix = coefficients.reshape(1,-1)
    if sparse: matrix = sp.csr_matrix(matrix)
    bounds = arithmetic.matrix(matrix,vector)[0]
    lo = sum((F.from_float(float(c))*F(x[0] if c>=0 else x[1]) for c,x in zip(coefficients,vector)),F(0))
    hi = sum((F.from_float(float(c))*F(x[1] if c>=0 else x[0]) for c,x in zip(coefficients,vector)),F(0))
    assert F(bounds[0])<=lo<=hi<=F(bounds[1])


@pytest.mark.parametrize('fault',['coefficient','center','radius','overflow'])
def test_NI02_unsupported_row_uses_original_decimal(monkeypatch,fault):
    module = importlib.import_module('gravity_l2_precision')
    arithmetic = module._Intervals(34,monotonic()+30.)
    coefficient,vector = 1.,[(Decimal(1),Decimal(1))]
    if fault=='coefficient': coefficient=np.nextafter(0.,1.)
    if fault=='center': vector=[(Decimal('1E-330'),Decimal('2E-330'))]
    if fault=='radius': vector=[(Decimal(1),Decimal('1.'+'0'*329+'1'))]
    if fault=='overflow': coefficient,vector=1e300,[(Decimal('1E100'),Decimal('1E100'))]
    calls=[]
    original=arithmetic.dot
    def observe(*args):
        calls.append(None)
        return original(*args)
    monkeypatch.setattr(arithmetic,'dot',observe)
    bounds=arithmetic.matrix(np.array([[coefficient]]),vector)[0]
    assert calls  # Unsupported fast native domain must not silently accept it.
    exact_lo=F.from_float(float(coefficient))*F(vector[0][0])
    exact_hi=F.from_float(float(coefficient))*F(vector[0][1])
    assert F(bounds[0])<=exact_lo<=exact_hi<=F(bounds[1])


def test_NI03_exact_gamma_products_and_absolute_reduction():
    module = importlib.import_module('gravity_l2_precision')
    arithmetic=module._Intervals(34,monotonic()+30.)
    for k in (1,7,4096,8192):
        gamma,denominator,loss=arithmetic._reduction_bound(k)
        u=F(1,2**52)
        exact_gamma=2*k*u/(1-2*k*u)
        assert F(gamma)>=exact_gamma
        assert 0<F(denominator)<=1-F(gamma)
        assert F(loss)>=2*k*F.from_float(float(np.finfo(np.float64).tiny))*(1+F(gamma))
    with pytest.raises(ValueError): arithmetic._reduction_bound(2**52)


@pytest.mark.parametrize('digits',[34,50,80])
def test_NI04_cancellation_zero_and_context_isolation(digits):
    module=importlib.import_module('gravity_l2_precision')
    arithmetic=module._Intervals(digits,monotonic()+30.)
    row=np.array([[1e150,-1e150,1.]])
    bounds=arithmetic.matrix(row,[(Decimal(1),Decimal(1))]*3)[0]
    assert F(bounds[0])<=F(1)<=F(bounds[1])
    zero=arithmetic.matrix(np.zeros((1,3)),[(Decimal(1),Decimal(1))]*3)[0]
    assert zero==(Decimal(0),Decimal(0))


@pytest.mark.parametrize('seed',range(8))
def test_NI05_complete_nested_margin_rational_inclusion(seed):
    generator=np.random.Generator(np.random.PCG64(20261004+seed))
    g=generator.normal(size=(5,3))*.3
    w=generator.normal(size=(5,5))*.2+np.eye(5)
    derivative=generator.normal(size=(3,3))*.1
    q=generator.normal(size=3)*.1
    qt=q*.6
    grad=q*10.
    problem=toy(g,generator.normal(size=5)*.01,alpha=.2,beta=.6,w=w,d=derivative,
                reference=generator.normal(size=3)*.01)
    r=evaluate(evaluator(problem,[-2.]*3,[2.]*3),q,qt,grad)
    exact=rational_nested_objective(problem,qt)-rational_nested_objective(problem,q)
    slope=sum((F.from_float(float(gg))*(F.from_float(float(y))-F.from_float(float(x)))
               for gg,x,y in zip(grad,q,qt)),F(0))
    interval_contains(r['delta_interval'],exact)
    interval_contains(r['armijo_margin_interval'],exact-F.from_float(1e-4)*slope)


def test_NI06_original_decimal_context_used_when_fast_sign_unresolved(monkeypatch):
    module=importlib.import_module('gravity_l2_precision')
    contexts=[]
    original=module._Intervals.__init__
    def observe(arithmetic,*args,**kwargs):
        original(arithmetic,*args,**kwargs)
        contexts.append(arithmetic)
    monkeypatch.setattr(module._Intervals,'__init__',observe)
    boundary=evaluate(evaluator(toy(((0.,),),alpha=1e-4),[-2.],[2.]),[1.],[0.],[1.])
    assert boundary['decision']=='unresolved' and boundary['passes']==3
    assert any(getattr(context,'_use_native_rows',None) is False for context in contexts)
