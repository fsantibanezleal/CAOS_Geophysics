"""Bounded saved native selected-final arrays, never a new solve or geology."""
import hashlib
import math
import os
from pathlib import Path
import stat

from magnetic_survey_json import _Lexer, canonical, fail, keys


MAX_LINE = 16*1024**2
MAX_AUDIT = 64*1024**2
MAX_STATE_BYTES = 8*1024**2
MAX_STATES = 201
_AUDIT_KEYS = 'schema source_inventory_sha256 candidate fold solve actual_result field_accepted online_admitted'


def _q(values, parameters, request):
    """Count/type/bounds checks precede numerical array materialization."""
    if (type(values) is not list or len(values) != parameters
            or any(type(v) not in (float, int) or not math.isfinite(v) for v in values)):
        fail('count', '$/model_states', 'Complete actual finite q-model required')
    lower, upper = request['prior']['lower_si']['data'], request['prior']['upper_si']['data']
    if any(not lo <= .01*q <= hi for lo, q, hi in zip(lower, values, upper)):
        fail('physical_metadata', '$/model_states', 'Actual model outside original physical bounds')
    import numpy as np
    array = np.asarray(values, dtype='<f8')
    return array, hashlib.sha256(array.tobytes()).hexdigest()


def from_closed_audit(path, result, request, inventory_sha256):
    """Read only a completed driver's existing audit after fitting has stopped.

    The caller supplies its original binding inventory, not request authority.
    This is replay provenance, not independent numerical or native admission.
    """
    from magnetic_result_bundle import validate_result, _hash
    from magnetic_local_paths import external_path
    validate_result(result, request)
    if result['schema'] != 'magnetic-survey-result-1' or result['status'] != 'complete':
        fail('convergence', '$/model_states', 'Only a complete original result may gain saved states')
    _hash(inventory_sha256, '$/model_states')
    path = external_path(Path(path))
    if not path.is_absolute() or path.is_symlink() or path.is_junction():
        fail('durability', '$/model_states', 'Explicit regular closed audit required')
    parameters = len(result['model']['chi_si']['data'])
    if not 1 <= parameters <= 2048:
        fail('resource', '$/model_states', 'Original active model capacity required')
    history = [(i, h) for i, h in enumerate(result['history'])
        if h['candidate'] == result['selected'] and h['fold'] == -1 and h['phase'] != 'irls_fixed']
    saved, indices = [], []
    cursor = used = records = moves = 0
    audit_sha = hashlib.sha256()
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= MAX_AUDIT:
            fail('resource', '$/model_states', 'Complete bounded closed audit required')
        while raw := stream.readline(MAX_LINE+1):
            used += len(raw)
            if len(raw) > MAX_LINE or used > MAX_AUDIT or not raw.endswith(b'\n') or records >= 4096:
                fail('resource', '$/model_states', 'Complete bounded audit lines required')
            audit_sha.update(raw)
            record = _Lexer(raw, max_bytes=MAX_LINE, max_tokens=2000000,
                max_strings=MAX_LINE, defer=False).document()
            keys(record, _AUDIT_KEYS, '$/model_states/audit')
            if (record['schema'] != 'magnetic-conditioned-solve-audit-1'
                    or record['source_inventory_sha256'] != inventory_sha256
                    or type(record['solve']) is not int or record['solve'] != records
                    or record['field_accepted'] is not False or record['online_admitted'] is not False):
                fail('hash', '$/model_states', 'Complete original source/order/claims audit binding required')
            records += 1
            if record['candidate'] != result['selected'] or record['fold'] is not None:
                continue
            native = record['actual_result']
            if (type(native) is not dict or native.get('status') != 'converged'
                    or native.get('runtime_epoch') != result['identity']['engine_epoch']
                    or type(native.get('source_binding')) is not dict
                    or native['source_binding'].get('optimizer') != result['identity']['optimizer_source']
                    or type(native.get('iterations')) is not int or not 0 <= native['iterations'] <= 200
                    or type(native.get('trace')) is not dict
                    or type(native['trace'].get('models_q')) is not list
                    or len(native['trace']['models_q']) != native['iterations']+1
                    or not native.get('terminal_audits')):
                fail('convergence', '$/model_states', 'Actual complete selected-final native trace required')
            check = native['terminal_audits'][-1].get('check')
            if type(check) is not dict or check.get('passed') is not True or check.get('disposed') is not True:
                fail('convergence', '$/model_states', 'Selected-final native terminal must pass and dispose')
            models = native['trace']['models_q']
            if any(type(native['trace'].get(k)) is not list or len(native['trace'][k]) != len(models)
                    for k in ('phi_d', 'phi_m', 'phi_engine')):
                fail('count', '$/model_states', 'Complete actual native objective records required')
            moves += native['iterations']
            if moves > 200 or len(saved)+(len(models) if not saved else len(models)-1) > MAX_STATES:
                fail('resource', '$/model_states', 'Original complete accepted200/state201 cap exceeded')
            capacity = (len(saved)+(len(models) if not saved else len(models)-1))*(16*parameters+8)
            if capacity > MAX_STATE_BYTES:
                fail('resource', '$/model_states', 'Complete saved q/SI/index payload capacity exceeded')
            for inner, values in enumerate(models):
                if cursor >= len(history):
                    fail('count', '$/model_states', 'No trace without exact selected history record')
                index, h = history[cursor]
                cursor += 1
                q, sha = _q(values, parameters, request)
                if (h['inner_iteration'] != inner or h['model_sha256'] != sha or h['status'] == 'failed'
                        or h['phi_d'] != native['trace']['phi_d'][inner]
                        or h['phi_regularizer'] != native['trace']['phi_m'][inner]
                        or h['objective'] != native['trace']['phi_engine'][inner]):
                    fail('hash', '$/model_states', 'Exact selected-final model/history association required')
                if inner == 0 and saved:
                    import numpy as np
                    if not np.array_equal(saved[-1], q):
                        fail('hash', '$/model_states', 'Actual stage-entry model continuity required')
                    continue
                saved.append(q)
                indices.append(index)
        after = os.fstat(stream.fileno())
        if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                or used != before.st_size):
            fail('durability', '$/model_states', 'Closed audit changed during bounded read')
    if not saved or cursor != len(history):
        fail('count', '$/model_states', 'Complete selected-final trace/history inventory required')
    import numpy as np
    from magnetic_calibration import descriptor
    q = np.vstack(saved)
    states = dict(schema='magnetic-selected-final-model-states-1', candidate=result['selected'],
        fold=-1, source_inventory_sha256=inventory_sha256, audit_sha256=audit_sha.hexdigest(),
        q_unit='chi_over_0.01', physical_unit='SI', physical_scale=.01,
        q_models=descriptor(q), chi_si=descriptor(.01*q),
        history_indices=descriptor(np.array(indices, dtype=np.int64)))
    validate(states, result, request)
    return states


def validate(states, result, request):
    from magnetic_result_bundle import _descriptor, _hash
    import numpy as np
    keys(states, 'schema candidate fold source_inventory_sha256 audit_sha256 q_unit '
        'physical_unit physical_scale q_models chi_si history_indices', '$/model_states')
    if (states['schema'] != 'magnetic-selected-final-model-states-1'
            or states['candidate'] != result['selected'] or type(states['fold']) is not int or states['fold'] != -1
            or states['q_unit'] != 'chi_over_0.01' or states['physical_unit'] != 'SI'
            or type(states['physical_scale']) is not float or states['physical_scale'] != .01):
        fail('type', '$/model_states', 'Closed selected-final units/mapping required')
    for name in ('source_inventory_sha256', 'audit_sha256'):
        _hash(states[name], '$/model_states')
    shape = states['q_models'].get('shape') if type(states['q_models']) is dict else None
    parameters = len(result['model']['chi_si']['data'])
    if (type(shape) is not list or len(shape) != 2
            or any(type(n) is not int for n in shape) or not 1 <= shape[0] <= MAX_STATES
            or shape[1] != parameters or not 1 <= parameters <= 2048
            or shape[0]*(16*parameters+8) > MAX_STATE_BYTES):
        fail('resource', '$/model_states', 'Complete bounded actual model-state shape required')
    count = shape[0]
    _descriptor(states['q_models'], 'float64', [count, parameters], '$/model_states/q_models')
    _descriptor(states['chi_si'], 'float64', [count, parameters], '$/model_states/chi_si')
    _descriptor(states['history_indices'], 'int64', [count], '$/model_states/history_indices')
    indices = states['history_indices']['data']
    if (indices != sorted(set(indices)) or any(not 0 <= i < len(result['history']) for i in indices)):
        fail('count', '$/model_states', 'Strict original history order required')
    q = np.asarray(states['q_models']['data'], dtype='<f8').reshape(count, parameters)
    chi = np.asarray(states['chi_si']['data'], dtype='<f8').reshape(count, parameters)
    if not np.array_equal(.01*q, chi) or not np.array_equal(chi[-1], result['model']['chi_si']['data']):
        fail('hash', '$/model_states', 'Native physical conversion/final model mismatch')
    for model, index in zip(q, indices):
        h = result['history'][index]
        _, sha = _q(model.tolist(), parameters, request)
        if (h['candidate'] != states['candidate'] or h['fold'] != -1 or h['phase'] not in ('l2', 'irls_surrogate')
                or h['status'] == 'failed' or h['model_sha256'] != sha):
            fail('hash', '$/model_states', 'Saved model must match exact selected-final history')
    if canonical(result['model']['chi_si']['data']) != canonical(chi[-1].tolist()):
        fail('hash', '$/model_states', 'Exact final physical payload required')
    return states
