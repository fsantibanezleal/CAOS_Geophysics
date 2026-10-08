"""Bounded numeric fitted generations, hashes, original identities and readback.

New explicit directory only. Manifest publication uses same-directory atomic
replacement after all numeric members are closed. Filesystem fsync limitations
are explicit; no host/crash acceptance follows from ordinary local readback.
"""

import hashlib
import io
import math
import os
from pathlib import Path
import re
import stat

from magnetic_survey_json import canonical, digest, keys, fail, parse_request, _Lexer
from magnetic_survey import plan_geometry


MAX_BYTES = 128*1024**2
MAX_MANIFEST = 1024**2
_NAME = re.compile(r'[A-Za-z0-9_-]{1,80}\.npy\Z', re.ASCII)
_CANDIDATES = tuple(f'b{i:02d}-{p}' for i in range(8) for p in ('l2', 'sparse'))
_PHASES = ('l2', 'irls_surrogate', 'irls_fixed')
_STATES = ('iterating', 'converged', 'failed')
_HASH = re.compile(r'[0-9a-f]{64}\Z', re.ASCII)


def _hash(value, route):
    if type(value) is not str or _HASH.fullmatch(value) is None:
        fail('hash', route, 'Literal complete lowercase SHA256 required')


def _real(value, route):
    if type(value) not in (float, int) or not math.isfinite(value) or value < 0:
        fail('numerical', route, 'Finite nonnegative real, not bool, required')


def _descriptor(value, dtype, shape, route):
    keys(value, 'dtype shape data sha256', route)
    if value['dtype'] != dtype or value['shape'] != shape or type(value['data']) is not list or len(value['data']) != math.prod(shape):
        fail('count', route, 'Literal typed numeric shape required')
    _hash(value['sha256'], route)
    for x in value['data']:
        if dtype == 'float64':
            if type(x) not in (float, int) or not math.isfinite(x):
                fail('numerical', route, 'Native finite numeric payload required')
        elif dtype == 'int64' and (type(x) is not int or not -(2**63) <= x < 2**63):
            fail('type', route, 'Literal bounded int64 payload required')
        elif dtype == 'bool' and type(x) is not bool:
            fail('type', route, 'Literal bool payload required')
    import numpy as np
    native = np.array(value['data'], dtype={'float64': '<f8', 'int64': '<i8', 'bool': '?'}[dtype])
    if hashlib.sha256(native.tobytes()).hexdigest() != value['sha256']:
        fail('hash', route, 'Physical descriptor payload hash mismatch')


def _metric(value, rows, components, route):
    keys(value, 'n_rows n_components phi_d rms_nT normalized_rms', route)
    if type(value['n_rows']) is not int or type(value['n_components']) is not int or value['n_rows'] != rows or value['n_components'] != rows*components:
        fail('count', route, 'Actual sealed metric component counts required')
    for field in ('phi_d', 'rms_nT', 'normalized_rms'):
        _real(value[field], route)
    if value['normalized_rms'] != math.sqrt(value['phi_d']/(rows*components)):
        fail('numerical', route, 'Actual normalized RMS mismatch')


def _unit(path):
    if any(p in path for p in ('receivers_m', 'origin_m', 'widths_', 'lengths_m', 'block_width_m')):
        return 'm'
    if any(p in path for p in ('chi_si', 'lower_si', 'upper_si', 'start_si', 'reference_si')):
        return 'SI'
    if '/noise/values' in path:
        return None  # Supplied noise kind determines nT versus nT^2.
    if any(p in path for p in ('observations/values', 'values_nT', 'residual_nT')):
        return 'nT'
    return '1'


def _array(value):
    return type(value) is dict and set(value) == {'dtype', 'shape', 'data', 'sha256'}


def _encode_history(history):
    import numpy as np
    from magnetic_calibration import descriptor
    if type(history) is not list or len(history) > 4096:
        fail('resource', '$/history', 'Complete bounded history required')
    index, numeric, hashes = [], [], []
    for record in history:
        keys(record, 'candidate fold phase outer_iteration inner_iteration beta epsilon_q phi_d phi_regularizer objective kkt_inf model_sha256 status', '$/history')
        try:
            index.append([_CANDIDATES.index(record['candidate']), record['fold'], _PHASES.index(record['phase']),
                          record['outer_iteration'], record['inner_iteration'], _STATES.index(record['status'])])
        except ValueError:
            fail('enum', '$/history', 'Closed history enum required')
        numeric.append([record[k] for k in ('beta', 'epsilon_q', 'phi_d', 'phi_regularizer', 'objective', 'kkt_inf')])
        raw = bytes.fromhex(record['model_sha256'])
        if len(raw) != 32:
            fail('hash', '$/history', 'Complete SHA256 required')
        hashes.append([int.from_bytes(raw[i:i+8], 'little', signed=True) for i in range(0, 32, 8)])
    return dict(codec='magnetic-history-table-1', index=descriptor(np.array(index, dtype=np.int64).reshape(-1, 6)),
                numeric=descriptor(np.array(numeric, dtype=np.float64).reshape(-1, 6)),
                model_hash_words=descriptor(np.array(hashes, dtype=np.int64).reshape(-1, 4)))


def _decode_history(value):
    keys(value, 'codec index numeric model_hash_words', '$/history')
    if value['codec'] != 'magnetic-history-table-1':
        fail('enum', '$/history', 'Registered lossless history codec required')
    n = value['index']['shape'][0]
    if n > 4096 or value['index']['shape'] != [n, 6] or value['numeric']['shape'] != [n, 6] or value['model_hash_words']['shape'] != [n, 4]:
        fail('count', '$/history', 'History table shapes required')
    if value['index']['dtype'] != 'int64' or value['model_hash_words']['dtype'] != 'int64' or value['numeric']['dtype'] != 'float64':
        fail('type', '$/history', 'History table native dtype required')
    out = []
    for i in range(n):
        a = value['index']['data'][6*i:6*(i+1)]
        b = value['numeric']['data'][6*i:6*(i+1)]
        h = value['model_hash_words']['data'][4*i:4*(i+1)]
        if not (0 <= a[0] < 16 and -1 <= a[1] <= 2 and 0 <= a[2] < 3 and 0 <= a[5] < 3
                and 0 <= a[3] < 20 and 0 <= a[4] <= 200):
            fail('count', '$/history', 'Closed history indices required')
        record = dict(candidate=_CANDIDATES[a[0]], fold=a[1], phase=_PHASES[a[2]], outer_iteration=a[3],
            inner_iteration=a[4], status=_STATES[a[5]],
            model_sha256=b''.join(int(word).to_bytes(8, 'little', signed=True) for word in h).hex())
        record.update(zip(('beta', 'epsilon_q', 'phi_d', 'phi_regularizer', 'objective', 'kkt_inf'), b))
        if any(not math.isfinite(x) or x < 0 for x in b):
            fail('numerical', '$/history', 'Finite nonnegative actual history required')
        out.append(record)
    return out


def validate_result(result, request):
    """Replay supplied schema, geometry, identities and actual residual sign."""
    import numpy as np
    keys(result, 'schema status identity inventory partition candidates selected model prediction metrics history diagnostics claims', '$/result')
    if result['schema'] != 'magnetic-survey-result-1' or result['status'] != 'complete':
        fail('convergence', '$/result', 'Only a complete fitted generation can be published')
    raw = canonical(request)
    plan = plan_geometry(parse_request(raw))
    from magnetic_likelihood import SealedLikelihood
    SealedLikelihood(raw).validate_noise()
    keys(result['identity'], 'seal_sha256 configuration_sha256 source_record_sha256 observations_sha256 noise_sha256 engine_epoch optimizer_source', '$/identity')
    if type(result['identity']['engine_epoch']) is not str or not result['identity']['engine_epoch'] or len(result['identity']['engine_epoch']) > 512:
        fail('type', '$/identity', 'Explicit bounded engine epoch required')
    _hash(result['identity']['optimizer_source'], '$/identity')
    binding = request['policy']['optimizer_binding']
    if binding['epoch'] != result['identity']['engine_epoch'] or binding['accepted_source'] != result['identity']['optimizer_source']:
        fail('dependency', '$/identity', 'Executed optimizer must match declared source binding')
    for key, value in plan['identity'].items():
        if result['identity'].get(key) != value:
            fail('hash', '$/identity', 'Frozen likelihood/configuration/source identity mismatch')
    if canonical(result['inventory']) != canonical(plan['inventory']) or canonical(result['partition']) != canonical(plan['partition']):
        fail('hash', '$/partition', 'Exact original inventory/seal mismatch')
    if result['claims'] != plan['claims'] or any(type(v) is not bool for v in result['claims'].values()):
        fail('type', '$/claims', 'No full method, field, geological or online claim upgrade')
    candidates = result['candidates']
    if type(candidates) is not list or len(candidates) != 16 or any(type(c) is not dict for c in candidates) or [c.get('id') for c in candidates] != list(_CANDIDATES):
        fail('count', '$/candidates', 'Complete frozen candidate inventory required')
    c = request['observations']['values']['shape'][1]
    for index, candidate in enumerate(candidates):
        keys(candidate, 'id beta penalty folds status score', '$/candidates')
        if (type(candidate['beta']) not in (float, int) or candidate['beta'] != request['policy']['betas'][index//2]
                or candidate['penalty'] != request['policy']['penalties'][index%2] or candidate['status'] not in ('complete', 'failed')):
            fail('enum', '$/candidates', 'Frozen beta/penalty/status inventory required')
        if type(candidate['folds']) is not list or len(candidate['folds']) != 3:
            fail('count', '$/candidates', 'Three literal folds required')
        for fold, metric in enumerate(candidate['folds']):
            keys(metric, 'fold status reason n_rows n_components phi_d rms_nT normalized_rms kkt_inf model_sha256', '$/fold')
            if type(metric['fold']) is not int or metric['fold'] != fold or metric['status'] not in ('converged', 'failed'):
                fail('enum', '$/fold', 'Literal fold/status required')
            n = len(plan['partition']['folds'][fold]['validation_rows']['data'])
            if type(metric['n_rows']) is not int or type(metric['n_components']) is not int or metric['n_rows'] != n or metric['n_components'] != n*c:
                fail('count', '$/fold', 'Actual validation component counts required')
            if metric['status'] == 'converged':
                if metric['reason'] is not None:
                    fail('convergence', '$/fold', 'Converged fold cannot retain failure reason')
                _metric({k: metric[k] for k in ('n_rows', 'n_components', 'phi_d', 'rms_nT', 'normalized_rms')}, n, c, '$/fold')
                _real(metric['kkt_inf'], '$/fold')
                _hash(metric['model_sha256'], '$/fold')
            elif (type(metric['reason']) is not str or not metric['reason'] or len(metric['reason']) > 512
                    or any(metric[k] is not None for k in ('phi_d', 'rms_nT', 'normalized_rms', 'kkt_inf', 'model_sha256'))):
                fail('convergence', '$/fold', 'Failure retains reason and unavailable metrics, never partial score')
        completed = all(f.get('status') == 'converged' for f in candidate['folds'])
        if (candidate['status'] == 'complete') != completed or (candidate['score'] is None) == completed:
            fail('convergence', '$/candidates', 'Failed fold cannot have a partial-average score')
        if completed:
            score = sum(f['phi_d'] for f in candidate['folds'])/sum(f['n_components'] for f in candidate['folds'])
            if candidate['score'] != score:
                fail('numerical', '$/candidates', 'Actual pooled component score mismatch')
    from magnetic_calibration import select_candidate
    if select_candidate(candidates)['id'] != result['selected']:
        fail('numerical', '$/selected', 'Frozen candidate selection mismatch')
    model = result['model']
    keys(model, 'chi_si active_indices mesh_sha256 sha256', '$/model')
    a = request['prior']['start_si']['shape'][0]
    _descriptor(model['chi_si'], 'float64', [a], '$/model/chi_si')
    _descriptor(model['active_indices'], 'int64', [a], '$/model/active_indices')
    if model['chi_si']['shape'] != [a] or model['chi_si']['dtype'] != 'float64':
        fail('count', '$/model', 'Physical active-model shape/dtype mismatch')
    chi = np.array(model['chi_si']['data'], dtype=np.float64)
    if (len(chi) != a or not np.isfinite(chi).all() or np.any(chi < request['prior']['lower_si']['data'])
            or np.any(chi > request['prior']['upper_si']['data']) or model['sha256'] != model['chi_si']['sha256']):
        fail('physical_metadata', '$/model', 'Physical model/bounds/hash mismatch')
    expected_active = np.flatnonzero(request['geometry']['mesh']['active']['data']).tolist()
    if (model['active_indices']['data'] != expected_active or model['mesh_sha256'] != digest(request['geometry']['mesh'])):
        fail('geometry', '$/model', 'Active ordering/mesh identity mismatch')
    prediction = result['prediction']
    keys(prediction, 'quantity components rows values_nT residual_nT', '$/prediction')
    expected_rows = [i for i, flag in enumerate(request['geometry']['usable']['data']) if flag]
    _descriptor(prediction['rows'], 'int64', [len(expected_rows)], '$/prediction/rows')
    if (prediction['rows']['data'] != expected_rows or prediction['quantity'] != request['processing']['quantity']
            or prediction['components'] != (['E', 'N', 'U'] if c == 3 else ['scalar'])):
        fail('geometry', '$/prediction', 'Original usable row/quantity/component ordering mismatch')
    for field in ('values_nT', 'residual_nT'):
        _descriptor(prediction[field], 'float64', [len(expected_rows), c], '$/prediction/'+field)
        if prediction[field]['shape'] != [len(expected_rows), c] or prediction[field]['dtype'] != 'float64':
            fail('count', '$/prediction', 'Exact physical prediction shape/dtype required')
    observed = np.array(request['observations']['values']['data']).reshape(-1, c)[expected_rows]
    predicted = np.array(prediction['values_nT']['data']).reshape(-1, c)
    residual = np.array(prediction['residual_nT']['data']).reshape(-1, c)
    if not np.isfinite(predicted).all() or not np.array_equal(observed-predicted, residual):
        fail('numerical', '$/prediction', 'Literal observed-minus-predicted residual mismatch')
    measures = result['metrics']
    keys(measures, 'development outer l2_baseline sparse_comparison', '$/metrics')
    _metric(measures['development'], len(plan['final_refit_rows']['data']), c, '$/metrics/development')
    _metric(measures['outer'], len(plan['partition']['outer_rows']['data']), c, '$/metrics/outer')
    from magnetic_calibration import metrics
    original_noise = np.array(request['noise']['values']['data']).reshape(request['noise']['values']['shape'])
    lookup = {row: i for i, row in enumerate(expected_rows)}
    all_observed = np.array(request['observations']['values']['data']).reshape(-1, c)
    for field, rows in (('development', plan['final_refit_rows']['data']), ('outer', plan['partition']['outer_rows']['data'])):
        ids = [i*c+j for i in rows for j in range(c)]
        principal = original_noise[np.ix_(ids, ids)] if request['noise']['kind'] == 'full_covariance' else original_noise[rows]
        replay = metrics(predicted[[lookup[i] for i in rows]], all_observed[rows], dict(kind=request['noise']['kind'], values=principal))
        if replay != measures[field]:
            fail('numerical', '$/metrics', 'Literal physical prediction/noise metric replay mismatch')
    selected = select_candidate(candidates)
    if (measures['l2_baseline'] != selected['id'][:3]+'-l2' or
            measures['sparse_comparison'] != (selected['id'] if selected['penalty'] == 'sparse_smallness' else None)):
        fail('enum', '$/metrics', 'Literal selected-beta comparison identities required')
    history = result['history']
    if type(history) is not list or not 1 <= len(history) <= 4096:
        fail('count', '$/history', 'Complete bounded actual history required')
    from magnetic_optimizer_adapter import EPSILONS
    for record in history:
        keys(record, 'candidate fold phase outer_iteration inner_iteration beta epsilon_q phi_d phi_regularizer objective kkt_inf model_sha256 status', '$/history')
        if record['candidate'] not in _CANDIDATES or record['phase'] not in _PHASES or record['status'] not in _STATES:
            fail('enum', '$/history', 'Literal history enums required')
        for field, lower, upper in (('fold', -1, 2), ('outer_iteration', 0, 19), ('inner_iteration', 0, 200)):
            if type(record[field]) is not int or not lower <= record[field] <= upper:
                fail('count', '$/history', 'Bounded actual history counters required')
        candidate = candidates[_CANDIDATES.index(record['candidate'])]
        for field in ('beta', 'epsilon_q', 'phi_d', 'phi_regularizer', 'objective', 'kkt_inf'):
            _real(record[field], '$/history')
        if (record['beta'] != candidate['beta'] or record['epsilon_q'] not in ((0.,) if record['phase'] == 'l2' else EPSILONS)
                or (record['phase'] != 'l2' and candidate['penalty'] != 'sparse_smallness')):
            fail('enum', '$/history', 'Frozen beta/epsilon/phase association required')
        if record['objective'] != record['phi_d']+record['beta']*record['phi_regularizer']:
            fail('numerical', '$/history', 'Actual objective terms mismatch')
        _hash(record['model_sha256'], '$/history')
    diagnostics = result['diagnostics']
    keys(diagnostics, 'reason resolution_kind resolution_arrays resources', '$/diagnostics')
    if diagnostics['reason'] is not None and (type(diagnostics['reason']) is not str or len(diagnostics['reason']) > 512):
        fail('type', '$/diagnostics', 'Bounded unavailable reason required')
    if diagnostics['resolution_kind'] == 'none':
        if diagnostics['resolution_arrays'] is not None:
            fail('type', '$/diagnostics', 'Unavailable resolution has no invented arrays')
    elif diagnostics['resolution_kind'] == 'local_fixed_objective':
        arrays = diagnostics['resolution_arrays']
        keys(arrays, 'free_indices selected_indices diagonal point_spread matrix singular_values', '$/resolution')
        selected_indices = np.unique([k*(a-1)//7 for k in range(8)]).tolist()
        _descriptor(arrays['selected_indices'], 'int64', [len(selected_indices)], '$/resolution/selected_indices')
        if arrays['selected_indices']['data'] != selected_indices:
            fail('geometry', '$/resolution', 'Frozen evenly spaced original columns required')
        free = [] if arrays['free_indices'] is None else arrays['free_indices']['data']
        if arrays['free_indices'] is not None:
            _descriptor(arrays['free_indices'], 'int64', [len(free)], '$/resolution/free_indices')
            if not free or any(i < 0 or i >= a for i in free) or any(i >= j for i, j in zip(free, free[1:])):
                fail('geometry', '$/resolution', 'Increasing original free column indices required')
        _descriptor(arrays['point_spread'], 'float64', [a, len(selected_indices)], '$/resolution/point_spread')
        if a <= 64:
            _descriptor(arrays['diagonal'], 'float64', [a], '$/resolution/diagonal')
            _descriptor(arrays['matrix'], 'float64', [a, a], '$/resolution/matrix')
            if free:
                _descriptor(arrays['singular_values'], 'float64', [len(free)], '$/resolution/singular_values')
                if any(x <= 0. for x in arrays['singular_values']['data']):
                    fail('numerical', '$/resolution', 'Positive stacked-system singular values required')
            elif arrays['singular_values'] is not None:
                fail('numerical', '$/resolution', 'All-bound spectrum unavailable')
            matrix = np.array(arrays['matrix']['data']).reshape(a, a)
            if not np.array_equal(matrix[:, selected_indices].ravel(), arrays['point_spread']['data']) or not np.array_equal(np.diag(matrix), arrays['diagonal']['data']):
                fail('numerical', '$/resolution', 'Literal resolution columns/diagonal mismatch')
        elif any(arrays[k] is not None for k in ('matrix', 'diagonal', 'singular_values')):
            fail('resource', '$/resolution', 'No dense resolution above 64 active cells')
        point = np.array(arrays['point_spread']['data']).reshape(a, -1)
        if np.any(point[[i for i in range(a) if i not in free]] != 0.):
            fail('numerical', '$/resolution', 'Bound-locked resolution rows must be zero')
    else:
        fail('enum', '$/diagnostics', 'Only qualified local resolution supported')
    if diagnostics['resources'] is not None:
        resources = diagnostics['resources']
        keys(resources, 'wall_s cpu_s peak_rss_bytes peak_private_bytes scratch_bytes', '$/resources')
        for field in ('wall_s', 'cpu_s'):
            _real(resources[field], '$/resources')
        for field in ('peak_rss_bytes', 'peak_private_bytes', 'scratch_bytes'):
            if type(resources[field]) is not int or resources[field] < 0:
                fail('type', '$/resources', 'Measured bounded native byte counts required')
    return result


def write_bundle(path, result, request):
    import numpy as np
    from magnetic_local_paths import external_path
    validate_result(result, request)
    root = external_path(path)
    if root.is_symlink() or root.exists():
        fail('durability', '$/output', 'Fresh explicit generation directory required')
    members, arrays = [], {}
    noise_unit = request['noise']['unit']
    def encode(value, route):
        if _array(value):
            dtype = {'float64': '<f8', 'int64': '<i8', 'bool': '?'}[value['dtype']]
            array = np.array(value['data'], dtype=dtype).reshape(value['shape'])
            if hashlib.sha256(array.tobytes()).hexdigest() != value['sha256']:
                fail('hash', route, 'Native descriptor hash mismatch')
            name = f'a{len(members):02d}.npy'
            stream = io.BytesIO()
            np.save(stream, array, allow_pickle=False)
            raw = stream.getvalue()
            unit = _unit(route)
            if value['dtype'] == 'int64':
                unit = 'index'
            elif value['dtype'] == 'bool':
                unit = 'bool'
            elif unit is None:
                unit = noise_unit
            members.append(dict(name=name, dtype=value['dtype'], shape=value['shape'], unit=unit,
                                bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
            arrays[name] = raw
            return dict(member=name)
        if type(value) is dict:
            return {key: encode(item, route+'/'+key) for key, item in value.items()}
        if type(value) is list:
            return [encode(item, route) for item in value]
        return value
    result_copy = dict(result, history=_encode_history(result['history']))
    manifest = dict(schema='magnetic-survey-bundle-1', result=encode(result_copy, '$/result'),
        request_metadata=encode(request, '$/request'), original=dict(sha256=request['source']['original_sha256'],
            bytes=request['source']['original_bytes'], scope=request['source']['scope'],
            rights=request['source']['rights'], included=False), members=members)
    manifest['generation_sha256'] = digest(manifest)
    body = canonical(manifest)
    if len(body) > MAX_MANIFEST or len(members) > 64 or len(body)+sum(len(v) for v in arrays.values()) > MAX_BYTES:
        fail('resource', '$/bundle', 'Whole fitted bundle capacities exceeded before publication')
    root.mkdir()
    written = []
    try:
        for name, raw in arrays.items():
            with (root/name).open('xb') as stream:
                written.append(root/name)
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        pending = root/'manifest.pending'
        with pending.open('xb') as stream:
            written.append(pending)
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(pending, root/'manifest.json')
        written.append(root/'manifest.json')
        imported = read_bundle(root)
        if canonical(imported['result']) != canonical(result):
            fail('durability', '$/bundle', 'Fitted generation readback mismatch')
    except BaseException:
        for member in written:
            member.unlink(missing_ok=True)
        root.rmdir()
        raise
    return manifest['generation_sha256']


def _read_regular(path, maximum):
    if path.is_symlink() or path.is_junction():
        fail('durability', '$/bundle', 'Symlink members forbidden')
    with path.open('rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
            fail('resource', '$/bundle', 'Regular bounded member required')
        raw = stream.read(maximum+1)
    if len(raw) > maximum:
        fail('resource', '$/bundle', 'Member grew beyond declared capacity')
    return raw


def read_bundle(path):
    import numpy as np
    from magnetic_calibration import descriptor
    root = Path(path)
    if root.is_symlink() or root.is_junction() or not root.is_dir():
        fail('durability', '$/bundle', 'Explicit non-symlink fitted directory required')
    body = _read_regular(root/'manifest.json', MAX_MANIFEST)
    manifest = _Lexer(body, max_bytes=MAX_MANIFEST, max_tokens=500000, max_strings=MAX_MANIFEST, defer=False).document()
    keys(manifest, 'schema result request_metadata original members generation_sha256', '$/manifest')
    if manifest['schema'] != 'magnetic-survey-bundle-1':
        fail('enum', '$/manifest', 'Registered fitted bundle schema required')
    identity = manifest['generation_sha256']
    if digest({k: v for k, v in manifest.items() if k != 'generation_sha256'}) != identity:
        fail('hash', '$/manifest', 'Fitted generation identity mismatch')
    if type(manifest['members']) is not list or not 1 <= len(manifest['members']) <= 64:
        fail('count', '$/members', 'Complete bounded member table required')
    members, total = {}, len(body)
    for entry in manifest['members']:
        keys(entry, 'name dtype shape unit bytes sha256', '$/members')
        name, shape = entry['name'], entry['shape']
        if (type(name) is not str or _NAME.fullmatch(name) is None or name in members
                or entry['dtype'] not in ('float64', 'int64', 'bool') or type(shape) is not list or not 1 <= len(shape) <= 3
                or any(type(n) is not int or n < 0 for n in shape) or math.prod(shape) > 12582912
                or type(entry['bytes']) is not int or entry['bytes'] < 10 or entry['bytes'] > MAX_BYTES):
            fail('type', '$/members', 'Closed bounded member name/shape/dtype/bytes required')
        total += entry['bytes']
        if total > MAX_BYTES:
            fail('resource', '$/members', 'Whole declared fitted capacity exceeded')
        members[name] = entry
    expected_files = set(members)|{'manifest.json'}
    if {p.name for p in root.iterdir()} != expected_files:
        fail('durability', '$/members', 'No missing, extra or partial members accepted')
    used = set()
    def decode(value, route):
        if type(value) is dict and set(value) == {'member'}:
            name = value['member']
            if type(name) is not str or name not in members or name in used:
                fail('hash', route, 'Every bounded member referenced exactly once')
            entry = members[name]
            used.add(name)
            raw = _read_regular(root/name, entry['bytes'])
            if len(raw) != entry['bytes'] or hashlib.sha256(raw).hexdigest() != entry['sha256']:
                fail('hash', route, 'Member byte/hash mismatch')
            if not raw.startswith(b'\x93NUMPY') or raw[6:8] not in (b'\x01\x00', b'\x02\x00'):
                fail('type', route, 'Bounded standard NPY header required')
            prefix = 10 if raw[6] == 1 else 12
            header = int.from_bytes(raw[8:prefix], 'little')
            size = 1 if entry['dtype'] == 'bool' else 8
            if header > 65536 or prefix+header+size*math.prod(entry['shape']) != len(raw):
                fail('resource', route, 'NPY header/payload bounds mismatch before allocation')
            # Header parsing precedes np.load so forged metadata cannot allocate.
            import ast
            try:
                info = ast.literal_eval(raw[prefix:prefix+header].decode('latin1').strip())
            except (ValueError, SyntaxError, UnicodeError):
                fail('type', route, 'Invalid bounded NPY header')
            keys(info, 'descr fortran_order shape', route)
            expected_dtype = {'float64': '<f8', 'int64': '<i8', 'bool': '|b1'}[entry['dtype']]
            if info['descr'] != expected_dtype or info['fortran_order'] is not False or tuple(entry['shape']) != info['shape']:
                fail('type', route, 'Native C-order dtype/shape mismatch, no pickle')
            expected_unit = 'index' if entry['dtype'] == 'int64' else 'bool' if entry['dtype'] == 'bool' else _unit(route)
            if expected_unit is None:
                expected_unit = manifest['request_metadata']['noise']['unit']
            if entry['unit'] != expected_unit:
                fail('physical_metadata', route, 'Position-derived physical unit mismatch')
            array = np.load(io.BytesIO(raw), allow_pickle=False, max_header_size=65536)
            if array.dtype == np.float64 and not np.isfinite(array).all():
                fail('numerical', route, 'Nonfinite numeric fitted member')
            return descriptor(array)
        if type(value) is dict:
            return {k: decode(v, route+'/'+k) for k, v in value.items()}
        if type(value) is list:
            return [decode(v, route) for v in value]
        return value
    result = decode(manifest['result'], '$/result')
    request = decode(manifest['request_metadata'], '$/request')
    if used != set(members):
        fail('hash', '$/members', 'Unused fitted member forbidden')
    result['history'] = _decode_history(result['history'])
    original = dict(sha256=request['source']['original_sha256'], bytes=request['source']['original_bytes'],
                    scope=request['source']['scope'], rights=request['source']['rights'], included=False)
    if manifest['original'] != original or manifest['original']['included'] is not False:
        fail('hash', '$/original', 'Original identity/rights/fullness mismatch; raw not bundled')
    validate_result(result, request)
    return dict(result=result, request=request, generation_sha256=identity)
