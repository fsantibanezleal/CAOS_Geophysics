"""Owned structural M11 transport admission; no numerical/native imports.

These checks establish custody/transport only. They never fit, decode held-out
values, accept physics or open a caller-supplied filesystem path.
"""
from __future__ import annotations

import ast
import hashlib
import json
import math
import re
import stat
from pathlib import Path
from uuid import UUID

METHOD_ID = 'joint.gravity-magnetic-native/v1'
MODALITY = 'joint_gravity_magnetic_native'
PARSER = 'm11-native-members/v1'
MAX_BYTES = 256 * 1024**2
MAX_JSON = 256 * 1024
MAX_HEADER = 4096
SHA = re.compile(r'[a-f0-9]{64}\Z')
DEVELOPMENT = {
    'mesh_origin', 'mesh_hx', 'mesh_hy', 'mesh_hz', 'mesh_active', 'prior_lengths',
    *(p+'_'+k for p in ('density', 'susceptibility') for k in ('lower','upper','start','reference')),
    *(m+'_'+k for m in ('gravity','magnetic') for k in ('receivers','mask','groups','partition')),
    *(m+'_development_'+k for m in ('gravity','magnetic') for k in ('rows','observed','noise')),
}
SEALED = {m+'_'+k for m in ('gravity','magnetic') for k in ('rows','observed','noise')}


def external_root(root):
    """Configured ordinary external root only; never cwd/repo/system-temp."""
    path = Path(root)
    if not path.is_absolute(): raise ValueError('joint_external_root_required')
    for parent in (path,*path.parents):
        info = parent.lstat()
        if (not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)
                or getattr(info,'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT
                or (parent/'.git').exists()):
            raise ValueError('joint_external_root_invalid')
    return path


def _keys(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError('joint_transport_keys')


def bounded_json(raw):
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_JSON:
        raise ValueError('joint_transport_metadata_cap')
    text = raw.decode('utf-8', errors='strict')
    if text.startswith('\ufeff'): raise ValueError('joint_transport_bom')
    depth = 0; quoted = False; escaped = False
    for c in text:
        if quoted:
            if escaped: escaped = False
            elif c == '\\': escaped = True
            elif c == '"': quoted = False
        elif c == '"': quoted = True
        elif c in '{[':
            depth += 1
            if depth > 8: raise ValueError('joint_transport_depth')
        elif c in '}]': depth -= 1
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise ValueError('joint_transport_duplicate_key')
            result[key] = value
        return result
    def nonfinite(_value): raise ValueError('joint_transport_nonfinite')
    value = json.loads(text, object_pairs_hook=pairs, parse_constant=nonfinite)
    def check(node):
        if type(node) is dict:
            for v in node.values(): check(v)
        elif type(node) is list:
            for v in node: check(v)
        elif type(node) is float and not math.isfinite(node): nonfinite(node)
    check(value)
    return value


def source_identity(asset, source, *, owner_id, project_id):
    """Exact application rows, independently checked for each dependency."""
    for value in (str(owner_id), project_id, asset.id, source.id): UUID(value)
    if (asset.owner_id != owner_id or source.owner_id != owner_id
            or asset.project_id != project_id or source.project_id != project_id
            or asset.source_id != source.id or asset.sha256 != source.sha256
            or source.private_storage_permission != 'attested'
            or source.rights_decision not in ('mirror','provider-link-only','derivative-only')
            or type(asset.byte_count) is not int or not 0 < asset.byte_count <= MAX_BYTES
            or type(source.version) is not int or source.version < 1
            or type(asset.sha256) is not str or not SHA.fullmatch(asset.sha256)):
        raise ValueError('joint_source_ineligible')
    return {'asset_id':asset.id, 'source_id':source.id, 'source_version':source.version,
        'raw_sha256':asset.sha256, 'raw_bytes':asset.byte_count,
        'rights_decision':source.rights_decision, 'private_storage_permission':'attested'}


def manifest(raw, role):
    """Close shape/count/byte inventory before member hashing or decoding."""
    value = bounded_json(raw)
    if role == 'development':
        _keys(value, ('schema','survey','development','arrays','sealed_manifest','raw_access'))
        if value['schema'] != 'joint-survey-intake-1': raise ValueError('joint_transport_schema')
        ids = DEVELOPMENT; main = 'request.json'
    elif role == 'sealed':
        _keys(value, ('schema','payload','arrays'))
        if value['schema'] != 'joint-survey-sealed-input-1': raise ValueError('joint_transport_schema')
        _keys(value['payload'], ('plan_sha256',))
        if type(value['payload']['plan_sha256']) is not str or not SHA.fullmatch(value['payload']['plan_sha256']):
            raise ValueError('joint_transport_plan_identity')
        ids = SEALED; main = 'sealed.json'
    else: raise ValueError('joint_transport_role')
    _keys(value['arrays'], ids)
    total = len(raw); members = {main:{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}}
    for name, d in value['arrays'].items():
        _keys(d, ('dtype','shape','file_bytes','file_sha256','data_sha256'))
        dtype = '|b1' if name.endswith(('_active','_mask')) else '<i8' if name.endswith(('_groups','_partition','_rows')) else '<f8'
        shape = d['shape']
        if (type(d['dtype']) is not str or d['dtype'] != dtype or type(shape) is not list
                or not 1 <= len(shape) <= 2 or any(type(n) is not int or not 1 <= n <= 4096 for n in shape)
                or type(d['file_bytes']) is not int):
            raise ValueError('joint_transport_shape')
        if name in ('mesh_origin','prior_lengths'):
            valid = shape == [3]
        elif name.endswith('_receivers'):
            valid = len(shape) == 2 and shape[1] == 3 and shape[0] <= 2048
        elif name.endswith('_noise'):
            valid = shape[0] <= 2048 and (len(shape) == 1 or shape[0] == shape[1])
        else:
            valid = len(shape) == 1 and (name.startswith(('mesh_','density_','susceptibility_')) or shape[0] <= 2048)
        if not valid: raise ValueError('joint_transport_shape')
        logical = math.prod(shape) * (1 if dtype == '|b1' else 8)
        if not 11 + logical <= d['file_bytes'] <= 10 + MAX_HEADER + logical:
            raise ValueError('joint_transport_native_length')
        for k in ('file_sha256','data_sha256'):
            if type(d[k]) is not str or not SHA.fullmatch(d[k]): raise ValueError('joint_transport_digest')
        total += d['file_bytes']
        if total > MAX_BYTES: raise ValueError('joint_transport_byte_cap')
        members[name+'.npy'] = {'bytes':d['file_bytes'],'sha256':d['file_sha256']}
    if role == 'development':
        _keys(value['raw_access'], ('gravity','magnetic'))
        for m in ('gravity','magnetic'):
            r = value['raw_access'][m]
            _keys(r, ('availability','raw_present','correction_present'))
            if type(r['raw_present']) is not bool or type(r['correction_present']) is not bool:
                raise ValueError('joint_transport_original_presence')
            if r != {'availability':'provider_reference_only','raw_present':False,'correction_present':False}:
                # Original raw/correction member admission is a separate service
                # step: never silently drop provided originals from the inventory.
                if r != {'availability':'provided','raw_present':True,'correction_present':True}:
                    raise ValueError('joint_transport_original_presence')
                source = value['survey'][m]['source']
                for suffix, size_key, hash_key in (('.raw','raw_bytes','raw_sha256'),('.corrections.json',None,'correction_sha256')):
                    digest = source[hash_key]
                    if type(digest) is not str or not SHA.fullmatch(digest): raise ValueError('joint_transport_digest')
                    size = source[size_key] if size_key else None
                    if size is not None and (type(size) is not int or not 0 < size <= MAX_BYTES): raise ValueError('joint_transport_original_length')
                    total += MAX_JSON if size is None else size
                    if total > MAX_BYTES: raise ValueError('joint_transport_byte_cap')
                    members[m+suffix] = {'bytes':size,'sha256':digest}
        # Correction bytes are supplied by the exact source rows, never guessed.
    return value, members


def native_header(prefix, descriptor, file_bytes):
    """Bounded NPY1 metadata only, before reading any native values."""
    _keys(descriptor, ('dtype','shape','file_bytes','file_sha256','data_sha256'))
    shape = descriptor['shape']
    if (type(descriptor['dtype']) is not str or descriptor['dtype'] not in ('<f8','<i8','|b1')
            or type(shape) is not list or not 1 <= len(shape) <= 2
            or any(type(n) is not int or not 1 <= n <= 4096 for n in shape)
            or type(descriptor['file_bytes']) is not int or not 0 < descriptor['file_bytes'] <= MAX_BYTES):
        raise ValueError('joint_transport_shape')
    if type(prefix) is not bytes or not 10 <= len(prefix) <= MAX_HEADER+10 or prefix[:8] != b'\x93NUMPY\x01\x00':
        raise ValueError('joint_transport_npy_version')
    length = int.from_bytes(prefix[8:10], 'little')
    if not 1 <= length <= MAX_HEADER or len(prefix) < 10+length:
        raise ValueError('joint_transport_npy_header_cap')
    raw = prefix[10:10+length]
    if not raw.endswith(b'\n'): raise ValueError('joint_transport_npy_header')
    try:
        tree = ast.parse(raw.decode('latin1').strip(), mode='eval')
    except (SyntaxError, RecursionError) as exc:
        raise ValueError('joint_transport_npy_literal') from exc
    nodes = list(ast.walk(tree))
    if (len(nodes) > 64 or any(type(n) not in (ast.Expression,ast.Dict,ast.Constant,ast.Tuple,ast.Load) for n in nodes)
            or type(tree.body) is not ast.Dict): raise ValueError('joint_transport_npy_literal')
    keys = [n.value if type(n) is ast.Constant else None for n in tree.body.keys]
    if len(keys) != 3 or set(keys) != {'descr','fortran_order','shape'}: raise ValueError('joint_transport_npy_keys')
    header = ast.literal_eval(tree)
    if (type(header['descr']) is not str or header['descr'] != descriptor['dtype']
            or type(header['fortran_order']) is not bool or header['fortran_order']
            or type(header['shape']) is not tuple or any(type(n) is not int for n in header['shape'])
            or list(header['shape']) != descriptor['shape']
            or type(file_bytes) is not int or file_bytes != descriptor['file_bytes']
            or file_bytes != 10+length+math.prod(header['shape'])*(1 if header['descr']=='|b1' else 8)):
        raise ValueError('joint_transport_npy_mismatch')
    return 10+length


def member_metadata(raw):
    """Dedicated ordinary-member upload grammar, before accepting any body."""
    if type(raw) is not bytes or len(raw) > 16384:
        raise ValueError('joint_member_metadata_cap')
    value = bounded_json(raw)
    _keys(value, ('role','name','source','descriptor'))
    role, name, d = value['role'], value['name'], value['descriptor']
    if type(role) is not str or role not in ('development','sealed') or type(name) is not str:
        raise ValueError('joint_member_role')
    arrays = DEVELOPMENT if role == 'development' else SEALED
    ordinary = {'request.json','gravity.raw','magnetic.raw','gravity.corrections.json',
        'magnetic.corrections.json'} if role == 'development' else {'sealed.json'}
    if name not in ordinary and name not in {n+'.npy' for n in arrays}:
        raise ValueError('joint_member_name')
    if name.endswith('.npy'):
        _keys(d, ('dtype','shape','file_bytes','file_sha256','data_sha256'))
        # Reuse the exact role/name shape inventory, not a relaxed upload dtype.
        expected = '|b1' if name[:-4].endswith(('_active','_mask')) else '<i8' if name[:-4].endswith(('_groups','_partition','_rows')) else '<f8'
        shape = d['shape']
        if (type(d['dtype']) is not str or d['dtype'] != expected or type(shape) is not list
                or not 1 <= len(shape) <= 2 or any(type(n) is not int or not 1 <= n <= 4096 for n in shape)
                or type(d['file_bytes']) is not int or not 0 < d['file_bytes'] <= MAX_BYTES
                or any(type(d[k]) is not str or not SHA.fullmatch(d[k]) for k in ('file_sha256','data_sha256'))):
            raise ValueError('joint_transport_shape')
        n = name[:-4]
        if n in ('mesh_origin','prior_lengths'): valid = shape == [3]
        elif n.endswith('_receivers'): valid = len(shape) == 2 and shape[1] == 3 and shape[0] <= 2048
        elif n.endswith('_noise'): valid = shape[0] <= 2048 and (len(shape) == 1 or shape[0] == shape[1])
        else: valid = len(shape) == 1 and (n.startswith(('mesh_','density_','susceptibility_')) or shape[0] <= 2048)
        logical = math.prod(shape)*(1 if expected == '|b1' else 8)
        if not valid or not 11+logical <= d['file_bytes'] <= 10+MAX_HEADER+logical:
            raise ValueError('joint_transport_shape')
    elif d is not None:
        raise ValueError('joint_member_unexpected_descriptor')
    source = value['source']
    if type(source) is not dict or type(source.get('expected_bytes')) is not int or not 0 < source['expected_bytes'] <= MAX_BYTES:
        raise ValueError('joint_member_source_length')
    if type(source.get('expected_sha256')) is not str or not SHA.fullmatch(source['expected_sha256']):
        raise ValueError('joint_member_source_digest')
    if d is not None and (source['expected_bytes'] != d['file_bytes'] or source['expected_sha256'] != d['file_sha256']):
        raise ValueError('joint_member_source_descriptor')
    if name.endswith('.json') and source['expected_bytes'] > MAX_JSON:
        raise ValueError('joint_member_json_cap')
    return value
