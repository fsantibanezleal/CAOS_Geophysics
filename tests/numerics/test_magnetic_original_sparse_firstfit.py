"""ONE original nonzero full528 sparse firstfit; stop dependent matrices on fail."""
import hashlib
import importlib.util
from pathlib import Path
from time import monotonic
import numpy as np

from magnetic_calibration import fit_partition, mesh_from_metadata
from magnetic_conditioned_adapter import OptimizerAudit
from magnetic_inverse import build_operator
from magnetic_likelihood import SealedLikelihood
from magnetic_original_adapter import allocation, binding_for_sources, PUBLIC_SOURCES
from magnetic_optimizer_adapter import EPSILONS
from magnetic_survey_json import canonical, digest
from run_magnetic_survey import source_inventory


def test_original_A_full528_complete_sparse_firstfit(tmp_path):
    sources = source_inventory(original=True)
    inventory = digest(sources)
    binding = binding_for_sources(sources, inventory)
    spec = importlib.util.spec_from_file_location('unchanged_sparse_firstfit_s2',
        Path(__file__).parents[1]/'fixtures'/'magnetic_survey'/'full_request.py')
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    doc, original, evaluator = generator.generate('A', 'secondary_enu_nT', binding)
    raw = canonical(doc)
    reader = SealedLikelihood(raw)
    reader.validate_noise()
    rows = tuple(reader.plan['partition']['folds'][0]['fit_rows']['data'])
    assert len(rows) == 144 and reader.plan['preflight']['active_cells'] == 528
    assert not set(rows)&set(reader.plan['partition']['outer_rows']['data'])
    observed, noise = reader.read(rows, role='fit', fold=0)
    plan = allocation(864, 432, 528, False, reader.plan['preflight']['conservative_bytes'], 3)
    operator = build_operator(raw, rows, deadline=monotonic()+120.)
    audit = OptimizerAudit(tmp_path/'sparse-firstfit-optimizer.jsonl', inventory)
    native = []
    def observe(solved):
        audit.append('b00-sparse', 0, solved)
        # Observer metadata only; do not retain extra native operand/factor
        # owners or re-enter the source terminal after its original deadline.
        native.append(dict(start=np.array(solved['trace']['models_q'][0], copy=True),
            status=solved['status'], iterations=solved['iterations'],
            conditioning=solved['conditioning_attempts'], trials=solved['line_search_trials'],
            terminal=solved['terminal_audits'][-1]['check'] if solved['terminal_audits'] else None,
            domains=solved['magnetic_domain_checks']))
    started = monotonic()
    try:
        result = fit_partition(operator, mesh_from_metadata(reader.metadata), doc['prior'],
            observed, noise, doc['policy']['betas'][0], 'sparse_smallness', binding=binding,
            deadline=started+120., admitted_bytes=plan['admitted_bytes'], allocation_sha256=digest(plan),
            source_inventory_sha256=inventory, source_components=864, reduced_plan=plan,
            optimizer_audit=observe)
    finally:
        audit.close()
    fit_seconds = monotonic()-started  # stop scientific clock BEFORE independent observer
    record = dict(schema='magnetic-original-sparse-firstfit-prerequisite-1', sources=sources,
        source_inventory_sha256=inventory, request_sha256=hashlib.sha256(raw).hexdigest(),
        original_sha256=hashlib.sha256(original).hexdigest(), evaluator=evaluator, plan=plan,
        allocation_sha256=digest(plan), beta=doc['policy']['betas'][0], rows=list(rows),
        status=result['status'], reason=result['reason'], fit_wall_s=fit_seconds,
        kkt_inf=result['kkt_inf'], history=result['history'], full_matrix_run=False,
        full_method_accepted=False, field_accepted=False, native_security_admitted=False)
    (tmp_path/'sparse-firstfit-prerequisite.json').write_bytes(canonical(record))
    assert result['status'] == 'converged', result['reason']
    assert fit_seconds <= 120. and sum(row['iterations'] for row in native) <= 200
    assert all(row['status'] == 'converged' and row['terminal']['passed'] and row['terminal']['disposed'] for row in native)
    assert all(row['terminal']['allocation']['maximum'] <= plan['admitted_bytes'] for row in native)
    assert all(check['passed'] for row in native for check in row['domains'])
    assert all(trial['trial'] < 20 for row in native for trial in row['trials'])
    for row in native:
        phases = {}
        for phase in row['conditioning']:
            assert phase['failure'] is None and phase['true_relative_residual'] <= 1e-6
            phases[phase['iteration']] = phases.get(phase['iteration'], 0)+phase['iterations']
        assert max(phases.values(), default=0) <= 200
    fixed = [row for row in result['history'] if row['phase'] == 'irls_fixed' and row['status'] == 'converged']
    assert tuple(dict.fromkeys(row['epsilon_q'] for row in fixed)) == EPSILONS
    starts = [row for row in result['history'] if row['inner_iteration'] == 0 and row['phase'] in ('l2', 'irls_surrogate')]
    assert len(starts) == len(native)
    index = next(i for i, row in enumerate(starts) if row['phase'] == 'irls_surrogate'
                 and row['epsilon_q'] == EPSILONS[-1] and row['outer_iteration'] == 0)
    spec = importlib.util.spec_from_file_location('independent_final_precision',
        Path(__file__).parents[1]/'fixtures/magnetic_survey/final_precision.py')
    precision = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(precision)
    kernel, fractions = precision.independent_kernel(doc, rows)
    reference, lower, upper = [np.array(doc['prior'][key]['data'], dtype=float)/.01
        for key in ('reference_si', 'lower_si', 'upper_si')]
    independent = precision.compare_final(kernel, observed, noise, result['objective'].regularizer.terms(),
        fractions, reference, lower, upper, result['q'], native[index]['start'],
        doc['policy']['betas'][0], EPSILONS[-1])
    record['independent_precision'] = independent
    (tmp_path/'sparse-firstfit-prerequisite.json').write_bytes(canonical(record))
    assert independent['model_inf_q'] <= 1e-6
    assert independent['objective_relative'] <= 1e-8
    assert independent['prediction_rms_nT'] <= 1e-6
    assert independent['normalized_kkt_inf'] <= 1e-7
    qualification = dict(schema='magnetic-public-original-nonzero-qualification-1', case='S2-A',
        quantity='secondary_enu_nT', active_cells=528, source_components=864, fit_components=432, epsilon_stages=8,
        caps=dict(wall_s=120, accepted=200, cg_per_direction=200, line_search=20, admitted_bytes=805306368),
        sources={name: sources[name] for name in PUBLIC_SOURCES}, status='passed', fit_wall_s=fit_seconds,
        independent_precision=independent)
    (tmp_path/'public-nonzero-qualification.json').write_bytes(canonical(qualification))
    assert reader.frozen() is None
