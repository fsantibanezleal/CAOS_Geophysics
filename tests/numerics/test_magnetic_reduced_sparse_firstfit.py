"""ONE original nonzero full528 sparse firstfit; stop dependent matrices on fail."""
import hashlib
import importlib.util
from pathlib import Path
from time import monotonic

from magnetic_calibration import fit_partition, mesh_from_metadata
from magnetic_conditioned_adapter import OptimizerAudit
from magnetic_inverse import build_operator
from magnetic_likelihood import SealedLikelihood
from magnetic_reduced_adapter import allocation, binding_for_sources
from magnetic_survey_json import canonical, digest
from run_magnetic_survey import source_inventory


def test_original_A_full528_complete_sparse_firstfit(tmp_path):
    sources = source_inventory(reduced=True)
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
    plan = allocation(864, 432, 528, False, reader.plan['preflight']['conservative_bytes'])
    operator = build_operator(raw, rows, deadline=monotonic()+120.)
    audit = OptimizerAudit(tmp_path/'sparse-firstfit-optimizer.jsonl', inventory)
    started = monotonic()
    try:
        result = fit_partition(operator, mesh_from_metadata(reader.metadata), doc['prior'],
            observed, noise, doc['policy']['betas'][0], 'sparse_smallness', binding=binding,
            deadline=started+120., admitted_bytes=plan['admitted_bytes'], allocation_sha256=digest(plan),
            source_inventory_sha256=inventory, source_components=864, reduced_plan=plan,
            optimizer_audit=lambda solved: audit.append('b00-sparse', 0, solved))
    finally:
        audit.close()
    record = dict(schema='magnetic-reduced-sparse-firstfit-prerequisite-1', sources=sources,
        source_inventory_sha256=inventory, request_sha256=hashlib.sha256(raw).hexdigest(),
        original_sha256=hashlib.sha256(original).hexdigest(), evaluator=evaluator, plan=plan,
        allocation_sha256=digest(plan), beta=doc['policy']['betas'][0], rows=list(rows),
        status=result['status'], reason=result['reason'], fit_wall_s=monotonic()-started,
        kkt_inf=result['kkt_inf'], history=result['history'], full_matrix_run=False,
        full_method_accepted=False, field_accepted=False, native_security_admitted=False)
    (tmp_path/'sparse-firstfit-prerequisite.json').write_bytes(canonical(record))
    assert result['status'] == 'converged', result['reason']
    assert reader.frozen() is None
