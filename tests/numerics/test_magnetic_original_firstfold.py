"""Original full528 firstfold prerequisites, no dependent matrix or retry."""
import hashlib
import importlib.util
from pathlib import Path
from time import monotonic

import choclo
from choclo.constants import VACUUM_MAGNETIC_PERMEABILITY as MU0
import numpy as np
from scipy.optimize import lsq_linear

import magnetic_original_adapter as adapter
from magnetic_calibration import mesh_from_metadata
from magnetic_inverse import build_operator
from magnetic_likelihood import SealedLikelihood
from magnetic_optimizer_adapter import MagneticObjective, MagneticRegularizer
from magnetic_survey_json import canonical, digest
from run_magnetic_survey import source_inventory
import physical_original_optimizer as core


def test_original_A_full528_firstfold_strong_accuracy(tmp_path):
    quantity = 'secondary_enu_nT'
    sources = source_inventory(original=True)
    inventory = digest(sources)
    binding = adapter.binding_for_sources(sources, inventory)
    location = Path(__file__).parents[1]/'fixtures'/'magnetic_survey'/'full_request.py'
    spec = importlib.util.spec_from_file_location('unchanged_firstfold_s2', location)
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    doc, original, evaluator = generator.generate('A', quantity, binding)
    raw = canonical(doc)
    assert hashlib.sha256(original).hexdigest() == doc['source']['original_sha256']
    reader = SealedLikelihood(raw)
    reader.validate_noise()
    rows = tuple(reader.plan['partition']['folds'][0]['fit_rows']['data'])
    assert len(rows) == 144 and reader.plan['preflight']['active_cells'] == 528
    assert not set(rows)&set(reader.plan['partition']['outer_rows']['data'])
    observed, noise = reader.read(rows, role='fit', fold=0)
    components = 3 if quantity == 'secondary_enu_nT' else 1
    # Every quantity retains the complete three-component physical source
    # kernel; only the principal likelihood component count is scalar.
    plan = adapter.allocation(864, 144*components, 528, False,
        reader.plan['preflight']['conservative_bytes'], components)
    # Allocation gate above precedes the original full physical kernel.
    operator = build_operator(raw, rows, deadline=monotonic()+120.)
    mesh, prior = mesh_from_metadata(reader.metadata), doc['prior']
    reference, lower, upper, start = [np.array(prior[k]['data'], dtype=np.float64)/.01
        for k in ('reference_si', 'lower_si', 'upper_si', 'start_si')]
    beta = float(doc['policy']['betas'][0])
    started, deadline = monotonic(), monotonic()+120.
    reg = MagneticRegularizer(mesh, reference, np.array(prior['lengths_m']['data'], dtype=np.float64),
        'l2', 0., start)
    physical = MagneticObjective(operator, reg, observed, noise, lower, upper, beta, inventory, digest(plan), 0)
    objective = physical
    budget = core.ConditionedBudget(deadline, 200, adapter.LIMIT, plan['admitted_bytes'], digest(plan))
    result = adapter.solve_original(objective, lower, upper, start, budget=budget, binding=binding, plan=plan)
    seconds = monotonic()-started
    record = dict(schema='magnetic-original-firstfold-prerequisite-1', sources=sources,
        source_inventory_sha256=inventory, request_sha256=hashlib.sha256(raw).hexdigest(),
        original_sha256=hashlib.sha256(original).hexdigest(), evaluator=evaluator,
        plan=plan, allocation_sha256=digest(plan), rows=list(rows), beta=beta, status=result['status'],
        reason=result['reason'], actual_accepted=result['iterations'], fit_wall_s=seconds,
        actual_CG_phases=len(result['conditioning_attempts']), full_matrix_run=False,
        independent_precision=None, full_method_accepted=False, field_accepted=False)
    (tmp_path/'firstfold-prerequisite.json').write_bytes(canonical(record))
    # Preserve complete native diagnostics even on an original failure.
    from magnetic_conditioned_adapter import OptimizerAudit
    audit = OptimizerAudit(tmp_path/'firstfold-optimizer.jsonl', inventory)
    try:
        audit.append('b00-l2', 0, result)
    finally:
        audit.close()
    assert result['status'] == 'converged', result['reason']
    terminal = result['terminal_audits'][-1]['check']
    assert terminal['passed'] and terminal['disposed']
    assert terminal['allocation']['maximum'] <= adapter.LIMIT
    assert all(row['passed'] for row in result['magnetic_domain_checks'])
    assert seconds <= 120. and result['iterations'] <= 200
    assert result['trace']['models_q'].shape[0] == result['iterations']+1
    assert all(p['cumulative_CG'] <= 200 and p['true_relative_residual'] <= 1e-6
        for p in result['conditioning_attempts'] if p['branch'] == 'cg')

    # TEST ONLY independent physical Choclo kernel, x-fast explicit cell bounds.
    widths = [mesh[k] for k in ('hx_m', 'hy_m', 'hz_m')]
    edges = [o+np.r_[0., np.cumsum(h)] for o, h in zip(mesh['origin_m'], widths)]
    indices = np.unravel_index(np.flatnonzero(mesh['active']), tuple(map(len, widths)), order='F')
    bounds = np.column_stack([e[i+j] for e, i in zip(edges, indices) for j in (0, 1)])
    xyz = np.array(doc['geometry']['receivers_m']['data']).reshape(288, 3)[list(rows)]
    _, background, _, _, _ = operator.operand_snapshot()
    magnetization = background*1e-9/MU0
    vector = np.array([[[fun(*receiver, *cell, *magnetization)*1e9
        for cell in bounds] for fun in (choclo.prism.magnetic_e, choclo.prism.magnetic_n,
        choclo.prism.magnetic_u)] for receiver in xyz])*.01
    independent = (vector.reshape(432, 528) if components == 3 else
        np.einsum('rck,c->rk', vector, background/np.linalg.norm(background)))
    native = operator.evaluate(start)['jacobian_nT_per_q']
    np.testing.assert_allclose(native, independent, rtol=2e-8, atol=1e-7)
    sd = noise['values'].ravel()
    terms = [np.sqrt(beta*t['alpha'])*t['weights'][:, None]*t['derivative'].toarray()
        for t in reg.terms()]
    matrix = np.vstack([independent/sd[:, None], *terms])
    rhs = np.r_[observed.ravel()/sd, *(t@reference for t in terms)]
    oracle = lsq_linear(matrix, rhs, bounds=(lower, upper), method='bvls', tol=1e-12, max_iter=10000)
    assert oracle.success
    optimum = float(np.linalg.norm(matrix@oracle.x-rhs)**2)
    gap = abs(result['phi_engine']-optimum)/max(1., optimum)
    prediction_error = float(np.sqrt(np.mean((native@result['q']-independent@oracle.x)**2)))
    np.testing.assert_allclose(result['q'], oracle.x, rtol=0., atol=1e-6)
    record['independent_precision'] = dict(model_max=float(np.max(abs(result['q']-oracle.x))), oracle='TEST_ONLY_Choclo_BVLS', oracle_success=bool(oracle.success),
        objective_gap=gap, prediction_rms_nT=prediction_error, objective_limit=1e-8, prediction_limit_nT=1e-6)
    (tmp_path/'firstfold-prerequisite.json').write_bytes(canonical(record))
    assert gap <= 1e-8 and prediction_error <= 1e-6
    assert reader.frozen() is None  # No refit/outer evaluation in this prerequisite.
