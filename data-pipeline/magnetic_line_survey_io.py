"""Streamed typed custody and explicit external storage for M03."""
from __future__ import annotations

from hashlib import sha256
import math
import os
from pathlib import Path
import struct
import sys
import tempfile

import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_contract as schema


WIDTHS = dict(float64=8, uint8=1, uint32=4, uint64=8, int64=8, ascii64=64, ascii30=30)
FORMATS = dict(float64='<d', uint8='<B', uint32='<I', uint64='<Q', int64='<q')


def external_path(path, *, directory=True):
    """Resolve actual ancestors; reject repository/system-temp destinations."""
    if not Path(path).is_absolute():
        raise core.SurveyError('invalid_contract', 'export')
    target = Path(os.path.abspath(path))
    for ancestor in (target, *target.parents):
        if (ancestor / '.git').exists():
            raise core.SurveyError('invalid_contract', 'export')
    system_temp = [os.environ.get(k) for k in ('TEMP', 'TMP', 'TMPDIR')]
    for value in system_temp:
        if value:
            candidate = Path(value).resolve()
            if target == candidate or candidate in target.parents:
                raise core.SurveyError('invalid_contract', 'export')
    core._plain_path(target if target.exists() else target.parent,
                     directory=directory if target.exists() else True)
    return target


def local_root(root=None, *, temporary=False):
    key = 'GEOPHYSICS_LOCAL_TEMP_ROOT' if temporary else 'GEOPHYSICS_LOCAL_DATA_ROOT'
    value = root if root is not None else os.environ.get(key)
    if value is None or not str(value).strip():
        raise core.SurveyError('invalid_contract', 'ingest')
    return external_path(value)


def encoded_cell(value, dtype):
    if type(value) not in (int, float, str):
        # Only exact native NumPy scalar classes from an already loaded engine.
        # Do not invoke an arbitrary object's item/array/conversion hook.
        np = sys.modules.get('numpy')
        if np is None or type(value) not in (np.float64, np.int64, np.uint64, np.int32, np.uint32, np.uint8):
            raise core.SurveyError('invalid_contract', 'export')
        value = value.item()
    if dtype.startswith('ascii'):
        if type(value) is not str:
            raise core.SurveyError('invalid_contract', 'export')
        data = value.encode('ascii')
        if b'\0' in data or len(data) > WIDTHS[dtype]:
            raise core.SurveyError('invalid_contract', 'export')
        return data.ljust(WIDTHS[dtype], b'\0')
    if dtype == 'float64':
        if type(value) not in (int, float) or not math.isfinite(value):
            raise core.SurveyError('invalid_contract', 'export')
    elif type(value) is not int:
        raise core.SurveyError('invalid_contract', 'export')
    try:
        return struct.pack(FORMATS[dtype], value)
    except (struct.error, OverflowError):
        raise core.SurveyError('invalid_contract', 'export') from None


class Writer(core._ChunkWriter):
    """One immutable typed array/table, bounded pages and binary records."""
    def __init__(self, root, identifier, *, role=None, row_schema=None, shape=None,
                 dtype=None, unit=None, mask_array_id=None):
        root = external_path(root)
        # Preflight descriptor metadata before creating even a chunk/page.
        if role:
            schema.validate('ArrayRef', dict(array_id=identifier,role=role,shape=shape,dtype=dtype,unit=unit,
                chunk_rows=1,manifest=dict(name=f'array-{identifier}.json',bytes=1,sha256='0'*64),
                ordered_ids_sha256='0'*64,mask_array_id=mask_array_id))
        else:
            schema.validate('TableRef', dict(table_id=identifier,row_schema=row_schema,rows=1,
                manifest=dict(name=f'table-{identifier}.json',bytes=1,sha256='0'*64)))
        super().__init__(root, identifier, role=role, row_schema=row_schema)
        self.shape, self.dtype, self.unit, self.mask = shape, dtype, unit, mask_array_id
        if role:
            width = WIDTHS[dtype] * (shape[1] if len(shape) == 2 else 1)
            self.chunk_rows = min(4096, 8388608 // width)
            if self.chunk_rows < 1:
                raise core.SurveyError('resource_refused', 'export')
        else:
            self.chunk_rows = 4096

    def append(self, payload, identity_payload=None):
        if self.role:
            expected = WIDTHS[self.dtype]*(self.shape[1] if len(self.shape) == 2 else 1)
            if len(payload) != expected:
                raise core.SurveyError('invalid_contract', 'export')
        if len(self.buffer) + len(payload) > 8388608:
            self.flush()
        self.buffer.extend(payload)
        self.content.update(payload if identity_payload is None else identity_payload)
        self.rows += 1
        if self.rows - self.chunk_first == self.chunk_rows:
            self.flush()

    def finish(self, ordered_ids_sha256=None):
        self.flush()
        self._page()
        if self.role:
            if self.rows != self.shape[0]:
                raise core.SurveyError('invalid_contract', 'export')
            value = dict(schema='magnetic-line-array-manifest/1', array_id=self.identifier,
                shape=self.shape, dtype=self.dtype, unit=self.unit, pages=self.pages, content_sha256=self.content.hexdigest())
        else:
            value = dict(schema='magnetic-line-table-manifest/1', table_id=self.identifier,
                row_schema=self.row_schema, rows=self.rows, pages=self.pages, content_sha256=self.content.hexdigest())
        schema.validate('ArrayManifest' if self.role else 'TableManifest', value)
        member = core._write_member(self.root, f'{self.prefix}-{self.identifier}.json', base.canonical_bytes(value))
        if self.role:
            ref = dict(array_id=self.identifier, role=self.role, shape=self.shape, dtype=self.dtype, unit=self.unit,
                chunk_rows=self.chunk_rows, manifest=member, ordered_ids_sha256=ordered_ids_sha256, mask_array_id=self.mask)
        else:
            ref = dict(table_id=self.identifier, row_schema=self.row_schema, rows=self.rows, manifest=member)
        return schema.validate('ArrayRef' if self.role else 'TableRef', ref)


def write_array(root, identifier, role, values, shape, dtype, unit, ordered_ids_sha256, mask=None):
    writer = Writer(root, identifier, role=role, shape=shape, dtype=dtype, unit=unit, mask_array_id=mask)
    for value in values:
        cells = value if len(shape) == 2 else (value,)
        writer.append(b''.join(encoded_cell(x, dtype) for x in cells))
    return writer.finish(ordered_ids_sha256)


def write_table(root, identifier, row_schema, rows):
    writer = Writer(root, identifier, row_schema=row_schema)
    for row in rows:
        row = schema.validate(schema.TABLE_TYPES[row_schema], row)
        encoded = base.canonical_bytes(row)
        writer.append(encoded+b'\n', struct.pack('<Q', len(encoded))+encoded)
    return writer.finish()


class Reader:
    """Independently verify every byte, page, dtype and order before use."""
    def __init__(self, root):
        self.root = external_path(root)
        self.known = {}

    def member(self, identity, limit=4194304):
        schema.validate('FileIdentity', identity)
        self._case_identity(identity)
        previous = self.known.get(identity['name'])
        if previous is not None and previous != identity:
            raise core.SurveyError('custody_mismatch', 'replay')
        data = core._verified_member(self.root, identity, set(), limit)
        self.known[identity['name']] = identity
        return data

    def _case_identity(self, identity):
        if any(name.casefold() == identity['name'].casefold() and name != identity['name']
               for name in self.known):
            raise core.SurveyError('custody_mismatch', 'replay')

    def chunks(self, ref):
        array = 'array_id' in ref
        schema.validate('ArrayRef' if array else 'TableRef', ref)
        kind = 'array' if array else 'table'
        identifier = ref[kind+'_id']
        manifest = schema.validate('ArrayManifest' if array else 'TableManifest', base.strict_json(self.member(ref['manifest'], 2097152)))
        for key in (('array_id', 'shape', 'dtype', 'unit') if array else ('table_id', 'row_schema', 'rows')):
            if manifest[key] != ref[key]:
                raise core.SurveyError('custody_mismatch', 'replay')
        rows = ref['shape'][0] if array else ref['rows']
        count = sequence = 0
        digest = sha256()
        if (rows == 0) != (len(manifest['pages']) == 0):
            raise core.SurveyError('custody_mismatch', 'replay')
        for number, page in enumerate(manifest['pages']):
            if page['sequence'] != number or page['first_row'] != count or \
               page['file']['name'] != f'{kind}-{identifier}-page-{number:06d}.json':
                raise core.SurveyError('custody_mismatch', 'replay')
            body = schema.validate('ManifestPage', base.strict_json(self.member(page['file'])))
            if body['owner_id'] != identifier or body['sequence'] != number:
                raise core.SurveyError('custody_mismatch', 'replay')
            start = count
            for entry in body['entries']:
                if entry['sequence'] != sequence or entry['first_row'] != count or \
                   entry['name'] != f'{kind}-{identifier}-{sequence:08d}.' + ('bin' if array else 'jsonl'):
                    raise core.SurveyError('custody_mismatch', 'replay')
                # ChunkIdentity allows 8 MiB; FileIdentity roots allow 4 MiB.
                identity = {k: entry[k] for k in ('name', 'bytes', 'sha256')}
                self._case_identity(identity)
                previous = self.known.get(identity['name'])
                if previous is not None and previous != identity:
                    raise core.SurveyError('custody_mismatch', 'replay')
                payload = core._verified_member(self.root, identity, set(), 8388608)
                self.known[identity['name']] = identity
                if array:
                    width = WIDTHS[ref['dtype']] * (ref['shape'][1] if len(ref['shape']) == 2 else 1)
                    if entry['rows'] > ref['chunk_rows'] or len(payload) != entry['rows']*width:
                        raise core.SurveyError('custody_mismatch', 'replay')
                    digest.update(payload)
                    yield payload
                else:
                    lines = payload.splitlines()
                    if len(lines) != entry['rows'] or not payload.endswith(b'\n'):
                        raise core.SurveyError('custody_mismatch', 'replay')
                    decoded = []
                    for encoded in lines:
                        row = schema.validate(schema.TABLE_TYPES[ref['row_schema']], base.strict_json(encoded))
                        if base.canonical_bytes(row) != encoded:
                            raise core.SurveyError('custody_mismatch', 'replay')
                        digest.update(struct.pack('<Q', len(encoded))+encoded)
                        decoded.append(row)
                    yield decoded
                count += entry['rows']
                sequence += 1
            if page['rows'] != count-start:
                raise core.SurveyError('custody_mismatch', 'replay')
        if count != rows or digest.hexdigest() != manifest['content_sha256'] or \
           (array and ref['role'] == 'row_id' and digest.hexdigest() != ref['ordered_ids_sha256']):
            raise core.SurveyError('custody_mismatch', 'replay')

    def cells(self, ref):
        dtype = ref['dtype']
        for payload in self.chunks(ref):
            if dtype.startswith('ascii'):
                width = WIDTHS[dtype]
                for pos in range(0, len(payload), width):
                    token = payload[pos:pos+width].rstrip(b'\0')
                    if b'\0' in token:
                        raise core.SurveyError('custody_mismatch', 'replay')
                    try:
                        decoded = token.decode('ascii')
                    except UnicodeError:
                        raise core.SurveyError('custody_mismatch', 'replay') from None
                    if ref['role'] == 'row_id' and not base.ID_PATTERN.fullmatch(decoded):
                        raise core.SurveyError('custody_mismatch', 'replay')
                    if ref['role'] == 'utc' and (decoded or ref['mask_array_id'] is None):
                        try:
                            base.utc_key(decoded)
                        except base.MagneticContractError:
                            raise core.SurveyError('custody_mismatch', 'replay') from None
                    yield decoded
            else:
                for (value,) in struct.iter_unpack(FORMATS[dtype], payload):
                    if dtype == 'float64' and not math.isfinite(value):
                        raise core.SurveyError('custody_mismatch', 'replay')
                    yield value

    def table(self, ref):
        for chunk in self.chunks(ref):
            yield from chunk

    def verify(self, ref):
        for _ in (self.cells(ref) if 'array_id' in ref else self.table(ref)):
            pass

    def reject_unknown(self, extra=()):
        if {p.name for p in self.root.iterdir()} != set(self.known) | set(extra):
            raise core.SurveyError('custody_mismatch', 'replay')


def scratch_directory(temp_root):
    return tempfile.TemporaryDirectory(prefix='m03-', dir=local_root(temp_root, temporary=True))
