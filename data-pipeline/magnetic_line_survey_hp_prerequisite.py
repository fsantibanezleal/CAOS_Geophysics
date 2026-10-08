"""Fail-first, ONCE, historical candidate39; no outer-value decoding or score."""
from hashlib import sha256
from pathlib import Path
import struct

import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_io as io
import magnetic_line_survey_representation as representation
import magnetic_line_survey_capacity_hp as capacity_hp
import magnetic_line_survey_hp as hp

HISTORICAL_PLAN_SHA = 'dd9d3d4a820c1d2ba23c50f8d368570220ed6a5ca1ad2b992a2ac9621f9d0748'
HISTORICAL_FAILURE_SHA = '8c1d2c370cb59dea8fd546cc1c5dbc1bdce8ba927d6be3e42a05e013e84dff17'
HISTORICAL_CORRECTIONS_SHA = '683c05fbbd97d087a6d0e8271195d4430b828f41da5eff7ac66df78d50ca3b64'


def _document(root, name):
    path = core._plain_path(Path(root)/name)
    return base.strict_json(base.read_bounded(path, 2097152))


def selected_cells(reader, ref, indexes):
    """Custody hashes encoded chunks; unpack ONLY declared training positions.

    No frombuffer/memmap/cells of the complete magnetic/sigma channel. Byte
    hashes are custody, as for pre-value original CSV hashing, not outer scores.
    """
    width = io.WIDTHS[ref['dtype']]*(ref['shape'][1] if len(ref['shape']) == 2 else 1)
    fmt = io.FORMATS[ref['dtype']]
    count, cursor, result = 0, 0, []
    for payload in reader.chunks(ref):
        stop = count+len(payload)//width
        while cursor < len(indexes) and indexes[cursor] < stop:
            pos = indexes[cursor]
            if pos < count:
                raise core.SurveyError('custody_mismatch', 'fit')
            if len(ref['shape']) == 1:
                result.append(struct.unpack_from(fmt, payload, (pos-count)*width)[0])
            else:
                result.append(tuple(struct.unpack_from(fmt, payload, (pos-count)*width+i*io.WIDTHS[ref['dtype']])[0]
                    for i in range(ref['shape'][1])))
            cursor += 1
        count = stop
    if cursor != len(indexes):
        raise core.SurveyError('custody_mismatch', 'fit')
    return result


def _capacity(geometry, proof):
    refs = {ref['array_id']: ref for ref in geometry['arrays']}
    training = [refs[f'f{f}-train']['shape'][0] for f in range(4)]
    validation = [refs[f'f{f}-validation']['shape'][0] for f in range(4)]
    old, reserved = proof['capacity'], proof['proof']
    return capacity_hp.plan_capacity(geometry['rows'], training, validation, geometry['source_counts_by_geometry'],
        **{key: old[key] for key in ('auxiliary_rows', 'crossover_candidates', 'exported_cells', 'fft_cells',
            'raw_bytes', 'auxiliary_bytes')},
        **{key: reserved[key] for key in ('retained_member_bytes', 'retained_index_bytes',
            'logical_members', 'arrays', 'dictionaries')})


def run_prerequisite(plan, root, job_handle):
    from magnetic_line_survey_runtime import require_job
    from magnetic_line_survey_resolution_geometry import seal_resolution_geometry, verify_resolution_geometry
    require_job(job_handle)
    core._closed(plan, 'schema retained_root oracle_receipt oracle_receipt_sha256', 'seal')
    if plan['schema'] != 'm03-hp-prerequisite-plan/1':
        raise core.SurveyError('invalid_contract', 'seal')
    root, retained = io.external_path(root), io.external_path(plan['retained_root'])
    oracle_bytes = base.read_bounded(core._plain_path(plan['oracle_receipt']), 2097152)
    oracle = base.strict_json(oracle_bytes)
    if sha256(oracle_bytes).hexdigest() != plan['oracle_receipt_sha256'] or \
       oracle['verdict'] != 'pass' or oracle['policy_epoch'] != hp.EPOCH or \
       oracle['source_sha256'] != {name: sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
           for name in oracle['source_sha256']}:
        raise core.SurveyError('custody_mismatch', 'seal')
    original_plan_bytes = base.read_bounded(core._plain_path(retained/'worker/plan.json'), 2097152)
    if sha256(original_plan_bytes).hexdigest() != HISTORICAL_PLAN_SHA:
        raise core.SurveyError('custody_mismatch', 'seal')
    original_plan = base.strict_json(original_plan_bytes)
    failure = base.read_bounded(core._plain_path(retained/'worker/fit/physical-fit-failure.json'), 2097152)
    if sha256(failure).hexdigest() != HISTORICAL_FAILURE_SHA:
        raise core.SurveyError('custody_mismatch', 'seal')
    old_geometry = _document(retained/'worker/sealed', 'geometry-seal.json')
    old_proof = _document(retained/'worker/sealed', 'resolution-capacity-proof.json')
    # Complete resource proof BEFORE fresh geometry construction/native imports.
    planned, proof = _capacity(old_geometry, old_proof)
    core._write_member(root, 'hp-prospective-capacity.json', base.canonical_bytes(dict(
        schema='m03-hp-prospective-capacity/1', policy_epoch=hp.EPOCH,
        capacity=planned, proof=proof, value_access='not_opened')))
    sealed = seal_resolution_geometry(original_plan['geometry_root'], original_plan['inspection'],
        original_plan['metadata'], original_plan['request'], original_plan['request_root'], root/'sealed',
        temp_root=root, navigation_root=original_plan['navigation_root'])
    checked = verify_resolution_geometry(original_plan['geometry_root'], original_plan['inspection'],
        original_plan['metadata'], original_plan['request'], original_plan['request_root'], root/'sealed', sealed,
        temp_root=root, navigation_root=original_plan['navigation_root'])
    geometry = sealed['geometry']
    new_proof = _document(root/'sealed', 'resolution-capacity-proof.json')
    if geometry != old_geometry or _capacity(geometry, new_proof) != (planned, proof):
        raise core.SurveyError('custody_mismatch', 'seal')
    # Bind ALL16 rebuilt maps and NEW policy, not a renamed frozen-v2 seal.
    seal = dict(schema='m03-hp-prerequisite-seal/1', policy_epoch=hp.EPOCH,
        geometry_sha256=base.digest(geometry), capacity_sha256=base.digest(dict(capacity=planned, proof=proof)),
        source_maps=geometry['source_maps'], request_sha256=base.digest(original_plan['request']),
        original=geometry['original'], candidate=dict(number=39, source_geometry_index=1,
            fold_id='C', depth_m=500., damping=.0001, rows=249, sources=127),
        original_geometry_verification=checked, oracle_receipt_sha256=plan['oracle_receipt_sha256'],
        value_access='not_opened', outer_evaluation_count=0)
    core._write_member(root, 'hp-prevalue-seal.json', base.canonical_bytes(seal))
    if _document(root, 'hp-prevalue-seal.json') != seal:
        raise core.SurveyError('custody_mismatch', 'seal')
    reader = representation.Reader(root/'sealed')
    source_map = next(item for item in geometry['source_maps']
        if item['source_geometry_index'] == 1 and item['fold_id'] == 'C')
    train = list(reader.cells(source_map['training']))
    if len(train) != 249 or train != sorted(set(train)) or source_map['sources']['shape'] != [127, 3]:
        raise core.SurveyError('custody_mismatch', 'fit')
    xyz_ref = sealed['navigation']['coordinates']
    xyz_values = selected_cells(reader, xyz_ref, train)
    source_values = selected_cells(reader, source_map['sources'], list(range(127)))
    correction_bytes = base.read_bounded(core._plain_path(retained/'worker/corrected/instrument-corrections.json'), 2097152)
    if sha256(correction_bytes).hexdigest() != HISTORICAL_CORRECTIONS_SHA:
        raise core.SurveyError('custody_mismatch', 'fit')
    corrected = base.strict_json(correction_bytes)
    if corrected['geometry_sha256'] != base.digest(geometry) or \
       corrected['request_sha256'] != base.digest(original_plan['request']) or \
       corrected['channels'][-1]['kind'] != 'scalar_total_field_anomaly':
        raise core.SurveyError('custody_mismatch', 'fit')
    correction_reader = io.Reader(retained/'worker/corrected')
    values = selected_cells(correction_reader, corrected['channels'][-1]['data'], train)
    flags = selected_cells(correction_reader, corrected['masks'][-1], train)
    if any(flags):
        raise core.SurveyError('metadata_ineligible', 'fit')
    # Historical candidate is explicitly UNWEIGHTED; do not open sigma/outer.
    if original_plan['request']['equivalent_sources']['weights_policy'] != 'unweighted':
        raise core.SurveyError('custody_mismatch', 'fit')
    np, _ = core.engines()
    xyz, sources, y = (np.ascontiguousarray(v, dtype='<f8') for v in (xyz_values, source_values, values))
    sources[:, 2] = min(float(v) for v in xyz[:, 2])-500.
    for array in (xyz, sources, y): array.flags.writeable = False
    inputs = dict(schema='m03-hp-training-input/1', training_positions_sha256=base.digest(train),
        geometry_sha256=hp.content_sha256(xyz), sources_sha256=hp.content_sha256(sources),
        corrected_training_values_sha256=hp.content_sha256(y), rows=249, sources=127,
        response_access='declared_fold_C_training_only', sigma_access='not_opened_unweighted',
        outer_evaluation_count=0, original_sha256=geometry['original']['csv_sha256'])
    core._write_member(root, 'hp-training-input.json', base.canonical_bytes(inputs))
    model = core.GlobalOperator(xyz, sources, job_handle=job_handle)
    error = None
    try:
        state = hp.solve_hp(model, y, .0001)
    except core.SurveyError as failed:
        error, state = failed.error, model.hp_failure_state
    for key in ('scaled_coefficients', 'coefficients'):
        core._write_member(root, f'hp-{key}.bin', memoryview(state[key]).cast('B').tobytes())
    # Independent native reconstruction of P and original coordinates, not just
    # a receipt hash. These passes are in the additional verification proof.
    rebuilt = core.GlobalOperator(xyz, sources, job_handle=job_handle)
    p = hp.preconditioner(rebuilt, .0001)
    if hp.content_sha256(p) != state['receipt']['preconditioner_sha256'] or \
       hp.original_diagnostics(rebuilt, y, .0001, state['scaled_coefficients']) != state['receipt']['original_diagnostics']:
        raise core.SurveyError('custody_mismatch', 'replay')
    result = dict(schema='m03-hp-prerequisite-result/1', policy_epoch=hp.EPOCH,
        prevalue_seal_sha256=base.digest(seal), input_sha256=base.digest(inputs), solve=state['receipt'], error=error,
        preconditioner_reconstruction='pass', outer_evaluation_count=0,
        full97_status='not_executed', historical_v2_status='fail_unchanged', field8201='not_verified')
    core._write_member(root, 'hp-prerequisite-result.json', base.canonical_bytes(result))
    return 2 if error else 0
