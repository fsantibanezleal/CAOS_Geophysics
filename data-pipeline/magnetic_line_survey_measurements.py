"""Second-pass typed raw channels: no inferred sigma or numerical admission."""
from __future__ import annotations

from decimal import Decimal
from hashlib import sha256
import math
import os
from pathlib import Path
import struct

import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_io as io


def _number(token):
    if not token:
        return None
    if len(token) > 128 or not base.CSV_NUMBER.fullmatch(token):
        raise core.SurveyError('metadata_ineligible', 'ingest')
    value = float(token)
    if not math.isfinite(value) or value == 0 and Decimal(token) != 0:
        raise core.SurveyError('metadata_ineligible', 'ingest')
    return value


def _verify_original(stream, source, original):
    before = os.fstat(stream.fileno())
    digest, total = sha256(), 0
    while True:
        block = stream.read(min(1048576, original['csv_bytes']-total+1))
        if not block:
            break
        digest.update(block)
        total += len(block)
        if total > original['csv_bytes']:
            raise core.SurveyError('custody_mismatch', 'ingest')
    after = os.fstat(stream.fileno())
    if total != original['csv_bytes'] or digest.hexdigest() != original['csv_sha256'] or \
       core._file_key(before) != core._file_key(after) or before.st_ctime_ns != after.st_ctime_ns or \
       core._file_key(after) != core._file_key(source.stat()):
        raise core.SurveyError('custody_mismatch', 'ingest')
    return after


def decode_measurements(csv_path, geometry_root, inspection, output_root):
    """Recheck original and geometry; stream every row into immutable channels.

    This internal raw decoder is deliberately NOT a physical eligibility seal
    or SurveyResult. The full owner must commit its partitions/source/crossing
    geometry before calling it for a new scientific request. Existing ingestion
    negatives are permitted to reach this independent refusal boundary.
    """
    core.verify_geometry_inspection(io.external_path(geometry_root), inspection)
    source = io.external_path(csv_path, directory=False)
    root = io.external_path(output_root)
    if root.exists():
        raise core.SurveyError('custody_mismatch', 'export')
    original = inspection['original']
    with source.open('rb') as stream:
        before = _verify_original(stream, source, original)
        stream.seek(0)
        root.mkdir()
        writers = [io.Writer(root, 'measurement-'+role, role=role, shape=[inspection['rows']],
                            dtype=dtype, unit=unit, mask_array_id='measurement-missing' if role != 'missing_mask' else None)
                   for role, dtype, unit in [('magnetic','float64','nT'), ('uncertainty','float64','nT'), ('missing_mask','uint32','identity')]]
        # Producer ID, not the role name, is the actual mask-array reference.
        writers[2].identifier = 'measurement-missing'
        original_hash, geometry_hash, ids_hash = sha256(), sha256(), sha256()
        count = total = 0
        header = True
        for raw in iter(lambda: stream.readline(4097), b''):
            total += len(raw)
            if len(raw) > 4096 or total > original['csv_bytes']:
                raise core.SurveyError('custody_mismatch', 'ingest')
            original_hash.update(raw)
            try:
                text = raw.decode('utf-8-sig' if header else 'utf-8')
            except UnicodeError:
                raise core.SurveyError('invalid_contract', 'ingest') from None
            text = text[:-2] if text.endswith('\r\n') else text[:-1] if text.endswith('\n') else text
            if header:
                if text != ','.join(base.CSV_COLUMNS):
                    raise core.SurveyError('custody_mismatch', 'ingest')
                header = False
                continue
            tokens = text.split(',')
            record = core._geometry_record(tokens, base)
            encoded = base.canonical_bytes(record)
            geometry_hash.update(struct.pack('<Q', len(encoded))+encoded)
            ids_hash.update(record['row_id'].encode('ascii').ljust(64, b'\0'))
            magnetic, sigma = _number(tokens[11]), _number(tokens[12])
            if sigma is not None and sigma <= 0:
                raise core.SurveyError('metadata_ineligible', 'ingest')
            mask = record['missing_mask'] | (16 if magnetic is None else 0) | (32 if sigma is None else 0)
            for writer, value in zip(writers, (magnetic, sigma, mask), strict=True):
                writer.append(io.encoded_cell(0. if value is None else value, writer.dtype))
            count += 1
            if count > inspection['rows']:
                raise core.SurveyError('custody_mismatch', 'ingest')
        after = os.fstat(stream.fileno())
        if count != inspection['rows'] or total != original['csv_bytes'] or original_hash.hexdigest() != original['csv_sha256'] or \
           geometry_hash.hexdigest() != inspection['geometry_sha256'] or core._file_key(before) != core._file_key(after) or \
           before.st_ctime_ns != after.st_ctime_ns or core._file_key(after) != core._file_key(source.stat()):
            raise core.SurveyError('custody_mismatch', 'ingest')
        result = dict(schema='m03-measurement-pass/1', original=original, rows=count,
                      geometry_sha256=inspection['geometry_sha256'], arrays=[w.finish(ids_hash.hexdigest()) for w in writers],
                      numerical_admission='not_established')
        core._write_member(root, 'measurement-pass.json', base.canonical_bytes(result))
        reader = io.Reader(root)
        for ref in result['arrays']:
            reader.verify(ref)
        reader.reject_unknown(extra=('measurement-pass.json',))
        return result
