"""Lossless shallow typed pools for corrected actual IRLS evidence, not pickle.

Original logical partition and whole encoded wrapper limits both apply. No
optimizer/admission or hash-only physics acceptance; numerical replay is separate.
"""
import hashlib
from pathlib import Path

import numpy as np

import gravity_l2 as l2
import gravity_survey_l2 as survey


SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
_DTYPES = (np.dtype('float64'), np.dtype('int64'), np.dtype('bool'))
_KEYS = ('schema', 'node_count', 'nodes', 'edge_count', 'edges', 'strings',
         'float_count', 'floats', 'int_count', 'ints', 'bool_count', 'bools', 'raw_sha256', 'pool_sha256')


def _grid(value):
    length = len(value)
    width = min(4096, max(1, length))
    rows = (length+width-1)//width
    if rows > 4096:
        raise ValueError('IRLS pool: unchanged native grid shape cap')
    result = np.zeros((rows, width), dtype=value.dtype)
    result.flat[:length] = value
    return survey._readonly(result)


def encode(value):
    l2._result_native_metadata(value)
    survey._finite(value)
    nodes, edges, strings = [], [], []
    words, parts, counts = {}, [[], [], []], [0, 0, 0]
    def word(v):
        if v not in words:
            words[v] = len(strings)
            strings.append(v)
        return words[v]
    def bank(v, kind):
        offset = counts[kind]
        flat = v.ravel(order='C')
        parts[kind].append(flat)
        counts[kind] += len(flat)
        return offset
    def visit(v):
        kind = type(v)
        ndim, d0, d1, count, offset = 0, 0, 0, 0, 0
        if v is None:
            tag = 0
        elif kind in (bool, int, float):
            tag, dtype = {bool:(1, 2), int:(2, 1), float:(3, 0)}[kind]
            offset, count = bank(np.array([v], dtype=_DTYPES[dtype]), dtype), 1
        elif kind is str:
            tag, offset = 4, word(v)
        elif kind is np.ndarray:
            tag = 5
            dtype = _DTYPES.index(v.dtype)
            offset, count = bank(v, dtype), v.size
            ndim, d0, d1 = v.ndim, v.shape[0], v.shape[1] if v.ndim == 2 else dtype
            # dtype occupies the high bits; literal original rank remains low.
            ndim += 4*dtype
        elif kind is dict:
            children = [(word(k), visit(v[k])) for k in sorted(v)]
            tag, offset, count = 6, len(edges), len(children)
            edges.extend(x for pair in children for x in pair)
        elif kind is tuple:
            children = [visit(x) for x in v]
            tag, offset, count = 7, len(edges), len(children)
            edges.extend(children)
        else:
            raise TypeError('IRLS pool: exact original native values only')
        if len(nodes) >= 65536:
            raise ValueError('IRLS pool: original logical node cap')
        nodes.append((tag, offset, count, ndim, d0, d1))
        return len(nodes)-1
    visit(value)
    result = dict(schema='gravity-irls-typed-pool-1', node_count=len(nodes),
        nodes=_grid(np.array(nodes, dtype=np.int64).ravel()), edge_count=len(edges),
        edges=_grid(np.array(edges, dtype=np.int64)), strings=tuple(strings),
        raw_sha256=survey._digest(value))
    for index, name in enumerate(('floats', 'ints', 'bools')):
        flat = np.concatenate(parts[index]) if parts[index] else np.empty(0, dtype=_DTYPES[index])
        result[name] = _grid(flat)
        result[('float_count', 'int_count', 'bool_count')[index]] = counts[index]
    l2._result_native_metadata(result)
    result['pool_sha256'] = survey._digest(result)
    l2._result_native_metadata(result)
    return result


def decode(pool):
    # COMPLETE external pool guard BEFORE value/hash scans/views/allocations.
    l2._result_native_metadata(pool)
    survey._keys(pool, _KEYS, 'IRLS typed pool')
    survey._enum(pool['schema'], 'gravity-irls-typed-pool-1', 'IRLS typed pool epoch')
    if (type(pool['node_count']) is not int or not 1 <= pool['node_count'] <= 65536
        or type(pool['edge_count']) is not int or not 0 <= pool['edge_count'] <= 2*65536
        or type(pool['strings']) is not tuple or len(pool['strings']) > 32768
        or any(type(s) is not str or len(s) > 1024 for s in pool['strings'])):
        raise ValueError('IRLS pool: bounded closed header')
    specifications = [('nodes', np.int64, 6*pool['node_count']), ('edges', np.int64, pool['edge_count'])]
    for name, count_name, dtype in (('floats', 'float_count', np.float64),
        ('ints', 'int_count', np.int64), ('bools', 'bool_count', np.bool_)):
        if type(pool[count_name]) is not int or not 0 <= pool[count_name] <= 256*1024**2//np.dtype(dtype).itemsize:
            raise ValueError('IRLS pool: original byte/count cap')
        specifications.append((name, dtype, pool[count_name]))
    for name, dtype, length in specifications:
        v = pool[name]
        if (type(v) is not np.ndarray or v.dtype != np.dtype(dtype) or v.ndim != 2
            or any(d > 4096 for d in v.shape) or v.size < length or v.size-length >= max(1, v.shape[1])):
            raise ValueError('IRLS pool: exact bounded bank/table metadata')
    survey._finite(pool)
    if len(set(pool['strings'])) != len(pool['strings']):
        raise ValueError('IRLS pool: unique bounded strings')
    if pool['pool_sha256'] != survey._digest({k:v for k,v in pool.items() if k != 'pool_sha256'}):
        raise ValueError('IRLS pool: exact whole pool hash')
    for name, _, length in specifications:
        if np.any(pool[name].ravel()[length:]):
            raise ValueError('IRLS pool: no hidden bank padding')
    nodes = pool['nodes'].ravel()[:6*pool['node_count']].reshape(-1, 6)
    edges = pool['edges'].ravel()[:pool['edge_count']]
    banks = [pool[k].ravel()[:pool[c]] for k, c in (('floats', 'float_count'), ('ints', 'int_count'), ('bools', 'bool_count'))]
    seen, used_words, consumed, used_edges = set(), set(), [0, 0, 0], set()
    logical = [0, 0]  # ORIGINAL per-partition logical occurrence byte/scalar caps.
    def word(index):
        if not 0 <= index < len(pool['strings']):
            raise ValueError('IRLS pool: string index')
        used_words.add(index)
        return pool['strings'][index]
    def take(bank, offset, count):
        if offset != consumed[bank] or count < 0 or offset+count > len(banks[bank]):
            raise ValueError('IRLS pool: exact ordered bank lineage')
        consumed[bank] += count
        return banks[bank][offset:offset+count]
    def visit(index, depth):
        if not 0 <= index < len(nodes) or index in seen or depth > 8:
            raise ValueError('IRLS pool: original tree/depth/no-alias cap')
        seen.add(index)
        tag, offset, count, ndim, d0, d1 = map(int, nodes[index])
        if tag == 5:
            bank, rank = divmod(ndim, 4)
            if not 0 <= bank <= 2 or rank not in (1, 2) or not 0 <= d0 <= 4096:
                raise ValueError('IRLS pool: original native array metadata')
            shape = (d0,) if rank == 1 else (d0, d1)
            if (rank == 2 and not 0 <= d1 <= 4096 or rank == 1 and d1 != bank
                or count != int(np.prod(shape))):
                raise ValueError('IRLS pool: original array count/shape')
            logical[0] += count*_DTYPES[bank].itemsize
            if logical[0] > 256*1024**2:
                raise ValueError('IRLS pool: original logical occurrence storage cap')
            result = take(bank, offset, count).reshape(shape)
            result.setflags(write=False)
            return result
        if ndim or d0 or d1 or tag not in range(8):
            raise ValueError('IRLS pool: canonical native node')
        if tag in (6, 7):
            length = count*(2 if tag == 6 else 1)
            if count < 0 or count > 32768 or offset < 0 or offset+length > len(edges):
                raise ValueError('IRLS pool: original container count')
            span = range(offset, offset+length)
            if any(i in used_edges for i in span):
                raise ValueError('IRLS pool: no shared container span')
            used_edges.update(span)
            child = edges[offset:offset+length]
            indices = child[1::2] if tag == 6 else child
            if np.any(indices < 0) or np.any(indices >= index):
                raise ValueError('IRLS pool: original postorder DAG, no cycles')
            if tag == 6:
                keys = [word(int(k)) for k in child[::2]]
                logical[1] += len(keys)
                if keys != sorted(set(keys)):
                    raise ValueError('IRLS pool: canonical unique original keys')
                result = {key: visit(int(i), depth+1) for key, i in zip(keys, indices)}
            else:
                result = tuple(visit(int(i), depth+1) for i in indices)
            return result
        logical[1] += 1
        if logical[1] > 32768:
            raise ValueError('IRLS pool: original scalar expansion cap')
        if tag == 0:
            if count or offset:
                raise ValueError('IRLS pool: canonical None')
            return None
        if tag == 4:
            if count:
                raise ValueError('IRLS pool: canonical string')
            return word(offset)
        if count != 1:
            raise ValueError('IRLS pool: canonical scalar')
        bank = {1:2, 2:1, 3:0}[tag]
        return {1:bool, 2:int, 3:float}[tag](take(bank, offset, 1)[0])
    result = visit(len(nodes)-1, 0)
    if (len(seen) != len(nodes) or len(used_edges) != len(edges) or len(used_words) != len(pool['strings'])
        or consumed != [len(b) for b in banks]):
        raise ValueError('IRLS pool: no unused/unreachable payload')
    l2._result_native_metadata(result)
    if pool['raw_sha256'] != survey._digest(result):
        raise ValueError('IRLS pool: exact original logical hash')
    return result
