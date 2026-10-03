"""Strict native local-survey planning, not upload/HTTP/field admission.

All error contexts are private. Snapshot callers must own their input buffers.
No file/network I/O, user hooks, random retries or observation values are used.
"""

from hashlib import sha256
import json
import math
import re

import numpy as np
from scipy.spatial import cKDTree

from gravity_forward import ENGINE, FRAME, forward_gravity


PLAN_KEYS = ("schema", "source", "frame", "mesh", "stations", "background_mgal", "split", "engine")
SOURCE_KEYS = ("source_id", "source_kind", "raw_sha256", "raw_bytes", "citation", "rights", "processing_sha256",
               "processing_kind", "quantity", "reference_description", "original_acceleration_unit",
               "original_vertical_positive", "normalization_sha256", "horizontal_reference", "vertical_reference",
               "transform_sha256", "geometry_uncertainty")
STATION_KEYS = ("station_ids", "partition_group_ids", "receivers_m", "excluded", "exclusion_reasons")
SPLIT_KEYS = ("policy", "block_origin_m", "block_size_m", "buffer_m", "seed")
GEOMETRY_KEYS = ("shape_xyz", "flattening", "active_cell_indices", "active_cell_bounds_m", "active_cell_centres_m",
                 "active_cell_volumes_m3", "receivers_m", "density_kg_m3")
RESULT_KEYS = ("schema", "request", "plan_sha256", "development_rows", "outer_rows", "embargo_rows", "folds",
               "geometry", "scope")
MAX_ARRAY_BYTES = 96 * 1024**2
MAX_METADATA_BYTES = 256 * 1024
MAX_SCALARS = 32768


def _keys(value, keys, field):
    if type(value) is not dict:
        raise TypeError(f"{field}: exact dict required")
    if any(type(key) is not str for key in value) or set(value) != set(keys):
        raise ValueError(f"{field}: exact keys required")


def _enum(value, choices, field):
    if type(value) is not str:
        raise TypeError(f"{field}: exact string required")
    if value not in choices:
        raise ValueError(f"{field}: unsupported value")


def _text(value, field, identifier=False, empty=False):
    if type(value) is not str:
        raise TypeError(f"{field}: exact string required")
    if len(value) > (128 if identifier else 1024) or (not empty and not value.strip()):
        raise ValueError(f"{field}: empty or oversized text")
    if identifier and re.fullmatch(r"[A-Za-z0-9_.:-]+", value) is None:
        raise ValueError(f"{field}: invalid identifier")


def _sha(value, field):
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{field}: lowercase SHA256 required")


def _float(value, field, positive=False):
    if type(value) is not float:
        raise TypeError(f"{field}: exact float required")
    if not math.isfinite(value) or (positive and value <= 0):
        raise ValueError(f"{field}: finite positive float required" if positive else f"{field}: finite float required")


def _array(value, shape, field, dtype=np.float64):
    if type(value) is not np.ndarray or value.dtype != np.dtype(dtype):
        raise TypeError(f"{field}: exact native {np.dtype(dtype)} ndarray required")
    if value.ndim != len(shape) or any(s is not None and s != n for s, n in zip(shape, value.shape)):
        raise ValueError(f"{field}: wrong shape")


def _native_metadata(value):
    """Walk exact container/array metadata only. Never traverse array values."""
    totals = [0, 0, 0]
    def visit(item, depth):
        if depth > 8:
            raise ValueError("request: exceeds eight container levels")
        kind = type(item)
        if kind is np.ndarray:
            if item.dtype not in (np.dtype('float64'), np.dtype('int64'), np.dtype('bool')):
                raise TypeError("array: exact native float64/int64/bool required")
            if item.ndim not in (1, 2) or any(n > 4096 for n in item.shape):
                raise ValueError("array: dimensions exceed ordinary metadata envelope")
            totals[0] += item.nbytes
        elif kind is dict:
            if len(item) > MAX_SCALARS or any(type(key) is not str for key in item):
                raise TypeError("metadata: exact bounded string keys required")
            for key, child in item.items():
                visit(key, depth + 1)
                visit(child, depth + 1)
        elif kind is tuple:
            if len(item) > MAX_SCALARS:
                raise ValueError("metadata: tuple count exceeds cap")
            for child in item:
                visit(child, depth + 1)
        elif kind in (str, int, float, bool, type(None)):
            totals[2] += 1
            if kind is str:
                if len(item) > 1024:
                    raise ValueError("metadata: string exceeds 1024 code points")
                totals[1] += len(item.encode('utf-8'))
            else:
                if kind is int and item.bit_length() > 64:
                    raise ValueError("metadata: oversized integer")
                totals[1] += 24
        else:
            raise TypeError("metadata: custom types, hooks and array subclasses forbidden")
        if totals[0] > MAX_ARRAY_BYTES or totals[1] > MAX_METADATA_BYTES or totals[2] > MAX_SCALARS:
            raise ValueError("request: native array/metadata storage or scalar-count cap exceeded")
    visit(value, 0)


def _finite(value):
    if type(value) is np.ndarray:
        if not np.isfinite(value).all():
            raise ValueError("array: nonfinite values")
    elif type(value) is dict:
        for child in value.values(): _finite(child)
    elif type(value) is tuple:
        for child in value: _finite(child)
    elif type(value) is float and not math.isfinite(value):
        raise ValueError("metadata: nonfinite scalar")


def _readonly(value, dtype=None):
    result = np.array(value, dtype=dtype, copy=True, order='C')
    result.flags.writeable = False
    return result


def _snapshot(value):
    if type(value) is np.ndarray: return _readonly(value)
    if type(value) is dict: return {key: _snapshot(child) for key, child in value.items()}
    if type(value) is tuple: return tuple(_snapshot(child) for child in value)
    return value


def _digest(value):
    """Private encoder, used only AFTER exact metadata/value admission."""
    def encode(item):
        if type(item) is np.ndarray:
            dtype = {'f': '<f8', 'i': '<i8', 'b': '|b1'}[item.dtype.kind]
            array = np.asarray(item, dtype=dtype, order='C')
            return {'dtype': dtype, 'shape': list(item.shape), 'sha256': sha256(array.tobytes(order='C')).hexdigest()}
        if type(item) is dict: return {key: encode(child) for key, child in item.items()}
        if type(item) is tuple: return [encode(child) for child in item]
        if type(item) is float and item == 0: return 0.0
        return item
    encoded = json.dumps(encode(value), sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    return sha256(encoded.encode('utf-8')).hexdigest()


def _planning_metadata(req):
    _keys(req, PLAN_KEYS, 'request')
    _enum(req['schema'], ('gravity-survey-l2-plan-request-1',), 'schema')
    _enum(req['engine'], (ENGINE,), 'engine')
    _keys(req['frame'], FRAME, 'frame')
    for key in ('kind', 'length_unit', 'vertical_positive'):
        _enum(req['frame'][key], (FRAME[key],), 'frame.' + key)
    if type(req['frame']['axes']) is not tuple or req['frame']['axes'] != FRAME['axes']:
        raise ValueError('frame.axes: east,north,up required')
    mesh = req['mesh']
    _keys(mesh, ('origin_m', 'hx_m', 'hy_m', 'hz_m', 'active'), 'mesh')
    _array(mesh['origin_m'], (3,), 'origin_m')
    widths = [mesh[key] for key in ('hx_m', 'hy_m', 'hz_m')]
    for width in widths:
        _array(width, (None,), 'width')
        if not 1 <= len(width) <= 4096: raise ValueError('mesh: axis count outside 1..4096')
    count = math.prod(len(width) for width in widths)
    if not 1 <= count <= 4096: raise ValueError('mesh: full-cell count outside 1..4096')
    _array(mesh['active'], (count,), 'active', np.bool_)
    stations = req['stations']
    _keys(stations, STATION_KEYS, 'stations')
    _array(stations['receivers_m'], (None, 3), 'receivers_m')
    n = len(stations['receivers_m'])
    if not 1 <= n <= 2048: raise ValueError('stations: row count outside 1..2048')
    _array(stations['excluded'], (n,), 'excluded', np.bool_)
    for key in ('station_ids', 'partition_group_ids', 'exclusion_reasons'):
        if type(stations[key]) is not tuple or len(stations[key]) != n:
            raise ValueError('stations: exact aligned tuples required')
        for item in stations[key]: _text(item, key, identifier=key != 'exclusion_reasons', empty=key == 'exclusion_reasons')
    _array(req['background_mgal'], (n,), 'background_mgal')
    split = req['split']
    _keys(split, SPLIT_KEYS, 'split')
    _array(split['block_origin_m'], (2,), 'block_origin_m')
    _array(split['block_size_m'], (2,), 'block_size_m')
    _enum(split['policy'], ('blocked-hash-3fold-sealed-1',), 'split.policy')
    _float(split['buffer_m'], 'buffer_m', positive=True)
    if type(split['seed']) is not int or split['seed'] != 104729:
        raise ValueError('split.seed: exact 104729 required')
    source = req['source']
    _keys(source, SOURCE_KEYS, 'source')
    _text(source['source_id'], 'source_id', identifier=True)
    for key in ('citation', 'reference_description', 'horizontal_reference', 'vertical_reference'):
        _text(source[key], key)
        if source[key].strip().lower() in ('unknown', 'unspecified', 'none'):
            raise ValueError('source: unknown reference/citation not admissible')
    for key in ('raw_sha256', 'processing_sha256', 'normalization_sha256'): _sha(source[key], key)
    if source['transform_sha256'] is not None: _sha(source['transform_sha256'], 'transform_sha256')
    if type(source['raw_bytes']) is not int or not 1 <= source['raw_bytes'] <= 1073741824:
        raise ValueError('raw_bytes: exact positive bounded integer required')
    _enum(source['source_kind'], ('synthetic_control', 'user_upload', 'field'), 'source_kind')
    _enum(source['rights'], ('private_only', 'derivative_only', 'redistributable_declared'), 'rights')
    _enum(source['processing_kind'], ('synthetic_anomaly', 'm01_declared_derivative', 'provider_declared_derivative'),
          'processing_kind')
    if (source['source_kind'] == 'synthetic_control') != (source['processing_kind'] == 'synthetic_anomaly'):
        raise ValueError('source: derivative/source-kind mismatch')
    _enum(source['quantity'], ('processed_gravity_anomaly',), 'quantity')
    _enum(source['original_acceleration_unit'], ('mGal', 'microGal', 'm/s2'), 'original_acceleration_unit')
    _enum(source['original_vertical_positive'], ('up', 'down'), 'original_vertical_positive')
    _enum(source['geometry_uncertainty'], ('conditional_fixed_geometry',), 'geometry_uncertainty')
    return count, n


def _coverage(xy):
    centred = xy - np.mean(xy, axis=0)
    values = np.linalg.svd(centred, compute_uv=False)
    threshold = max(len(xy), 2) * np.finfo(np.float64).eps * values[0]
    if not np.isfinite(values).all() or np.count_nonzero(values > threshold) != 2 or np.any(np.ptp(xy, axis=0) <= 0):
        raise ValueError('split: fit coordinate rank/extent insufficient')


def _partition(req):
    stations, split = req['stations'], req['split']
    xy = stations['receivers_m'][:, :2]
    with np.errstate(over='ignore', invalid='ignore', divide='ignore'):
        floating = np.floor((xy - split['block_origin_m']) / split['block_size_m'])
    # int64 max rounds up as float64. The upper bound must be exclusive 2**63.
    if not np.isfinite(floating).all() or np.any(floating < -2**63) or np.any(floating >= 2**63):
        raise ValueError('split: block indices outside representable int64')
    blocks = floating.astype(np.int64)
    eligible = np.flatnonzero(~stations['excluded'])
    parent = {int(i): int(i) for i in eligible}
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    seen_block, seen_group = {}, {}
    for raw in eligible:
        i = int(raw)
        for seen, key in ((seen_block, tuple(int(x) for x in blocks[i])),
                          (seen_group, stations['partition_group_ids'][i])):
            if key in seen:
                parent[find(i)] = find(seen[key])
            else: seen[key] = i
    grouped = {}
    for raw in eligible:
        i = int(raw)
        grouped.setdefault(find(i), []).append(i)
    if len(seen_block) < 12 or len(grouped) < 12:
        raise ValueError('split: at least twelve occupied blocks and union units required')
    ordered = []
    for indices in grouped.values():
        ids = tuple(sorted(stations['station_ids'][i] for i in indices))
        ordered.append((_digest({'seed': 104729, 'station_ids': ids}), ids, indices))
    ordered.sort(key=lambda value: (value[0], value[1]))
    n_outer = math.ceil(len(ordered) / 5)
    outer = np.array(sorted(i for item in ordered[:n_outer] for i in item[2]), dtype=np.int64)
    units = [np.array(item[2], dtype=np.int64) for item in ordered[n_outer:]]
    if len(outer) < 10: raise ValueError('split: outer needs ten rows')
    # Stable bounded nearest distances, no dense n*n pair expansion.
    distance = cKDTree(xy[outer]).query(xy, k=1, workers=1)[0]
    if not np.isfinite(distance).all(): raise ValueError('split: nonfinite distance')
    embargo = np.array(sorted(int(i) for unit in units for i in unit if distance[i] <= split['buffer_m']), dtype=np.int64)
    surviving = [unit[distance[unit] > split['buffer_m']] for unit in units]
    development = np.array(sorted(int(i) for unit in surviving for i in unit), dtype=np.int64)
    if len(development) < 50 or sum(len(unit) > 0 for unit in surviving) < 6:
        raise ValueError('split: development needs fifty rows and six surviving units')
    _coverage(xy[development])
    folds = []
    for index in range(3):
        validation = np.array(sorted(int(i) for unit in surviving[index::3] for i in unit), dtype=np.int64)
        if len(validation) < 10: raise ValueError('split: each validation needs ten rows')
        possible = development[~np.isin(development, validation)]
        near = cKDTree(xy[validation]).query(xy[possible], k=1, workers=1)[0]
        if not np.isfinite(near).all(): raise ValueError('split: nonfinite buffer distance')
        fit = possible[near > split['buffer_m']]
        if len(fit) < 40: raise ValueError('split: each buffered fit needs forty rows')
        _coverage(xy[fit])
        folds.append({'fold': index, 'fit_rows': _readonly(fit), 'validation_rows': _readonly(validation),
                      'buffer_rows': _readonly(possible[near <= split['buffer_m']])})
    return development, outer, embargo, tuple(folds)


def plan_gravity_l2(request: dict) -> dict:
    """Freeze geometry-only partitions under the reviewed exact native protocol."""
    _native_metadata(request)
    _, n = _planning_metadata(request)
    _finite(request)
    mesh, stations = request['mesh'], request['stations']
    active_count = int(np.count_nonzero(mesh['active']))
    if active_count == 0: raise ValueError('mesh: at least one active cell required')
    if np.any(request['split']['block_size_m'] <= 0): raise ValueError('split: positive block sizes required')
    if len(set(stations['station_ids'])) != n: raise ValueError('stations: duplicate identity')
    if len(set(tuple(row) for row in stations['receivers_m'])) != n: raise ValueError('stations: duplicate XYZ')
    for excluded, reason in zip(stations['excluded'], stations['exclusion_reasons']):
        if bool(excluded) != bool(reason.strip()): raise ValueError('stations: mask/reason mismatch')
    req = _snapshot(request)
    development, outer, embargo, folds = _partition(req)
    forward = forward_gravity({'schema': 'gravity-prism-forward-request-1', 'frame': req['frame'], 'mesh': req['mesh'],
                               'receivers_m': req['stations']['receivers_m'], 'density_kg_m3': np.zeros(active_count),
                               'engine': req['engine']})
    result = {'schema': 'gravity-survey-l2-plan-1', 'request': req, 'development_rows': _readonly(development),
              'outer_rows': _readonly(outer), 'embargo_rows': _readonly(embargo), 'folds': folds,
              'geometry': forward['geometry'], 'scope': 'ordinary_local_conditional_not_field'}
    result['plan_sha256'] = _digest(result)
    return result


def _plan_result_metadata(plan):
    _keys(plan, RESULT_KEYS, 'plan')
    _, n = _planning_metadata(plan['request'])
    _enum(plan['schema'], ('gravity-survey-l2-plan-1',), 'plan.schema')
    _enum(plan['scope'], ('ordinary_local_conditional_not_field',), 'plan.scope')
    _sha(plan['plan_sha256'], 'plan_sha256')
    for key in ('development_rows', 'outer_rows', 'embargo_rows'):
        _array(plan[key], (None,), key, np.int64)
        if len(plan[key]) > n: raise ValueError('plan: oversized row vector')
    if type(plan['folds']) is not tuple or len(plan['folds']) != 3: raise ValueError('plan: exactly three folds required')
    for i, fold in enumerate(plan['folds']):
        _keys(fold, ('fold', 'fit_rows', 'validation_rows', 'buffer_rows'), 'fold')
        if type(fold['fold']) is not int or fold['fold'] != i: raise ValueError('plan: ordered folds required')
        for key in ('fit_rows', 'validation_rows', 'buffer_rows'):
            _array(fold[key], (None,), key, np.int64)
            if len(fold[key]) > n: raise ValueError('plan: oversized fold vector')
    geometry = plan['geometry']
    _keys(geometry, GEOMETRY_KEYS, 'geometry')
    _array(geometry['active_cell_indices'], (None,), 'indices', np.int64)
    a = len(geometry['active_cell_indices'])
    if not 1 <= a <= 4096: raise ValueError('geometry: active count')
    for key, shape in (('active_cell_bounds_m', (a, 6)), ('active_cell_centres_m', (a, 3)),
                       ('active_cell_volumes_m3', (a,)), ('density_kg_m3', (a,)), ('receivers_m', (n, 3))):
        _array(geometry[key], shape, key)
    if type(geometry['shape_xyz']) is not tuple or len(geometry['shape_xyz']) != 3:
        raise ValueError('geometry: exact three-axis shape required')
    if any(type(x) is not int or not 1 <= x <= 4096 for x in geometry['shape_xyz']):
        raise ValueError('geometry: shape counts')
    _enum(geometry['flattening'], ('x-fast',), 'flattening')


def _validate_plan(plan):
    """Recompute geometry/splits, not just trust a caller-replaced digest."""
    _native_metadata(plan)
    _plan_result_metadata(plan)
    _finite(plan)
    body = {key: value for key, value in plan.items() if key != 'plan_sha256'}
    if _digest(body) != plan['plan_sha256']: raise ValueError('plan: content hash mismatch')
    expected = plan_gravity_l2(plan['request'])
    if expected['plan_sha256'] != plan['plan_sha256']: raise ValueError('plan: recomputed geometry/partition mismatch')
    return expected
