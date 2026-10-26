"""Complete pinned field-byte inspection; missing physics never becomes datum.

Streaming archive inspection is not a magnetic inverse or a subset substitute
for the complete acquisition. No provider scripts/saved models are executed.
"""

import csv
import hashlib
import io
import math
from pathlib import PurePosixPath
import stat
import zipfile

from magnetic_local_paths import external_path
from magnetic_survey_json import fail

ORIGINAL_CAP = 128*1024**2
ROWS_CAP = 2048


def inspect_clear_lake(archive, source_record):
    path = external_path(archive)
    expected = source_record['archive_contract']['selected_members']['data/aeromagnetic_data.csv']
    sha, size = hashlib.sha256(), 0
    if path.stat().st_size != source_record['expected_bytes'] or path.stat().st_size > ORIGINAL_CAP:
        fail('bytes', '$/field/original', 'Actual complete field original exceeds bounded inverse cap or differs from receipt')
    with path.open('rb') as stream:
        while raw := stream.read(1024**2):
            size += len(raw)
            if size > ORIGINAL_CAP:
                fail('bytes', '$/field/original', 'Complete original grew beyond cap')
            sha.update(raw)
    if sha.hexdigest() != source_record['sha256']:
        fail('hash', '$/field/original', 'Complete pinned field archive hash mismatch')
    with zipfile.ZipFile(path) as zipped:
        inventory = zipped.infolist()
        if len(inventory) != 40 or sum(item.file_size for item in inventory) != 299907397:
            fail('count', '$/field/archive', 'Complete pinned archive inventory changed')
        names = set()
        for item in inventory:
            parts = PurePosixPath(item.filename).parts
            mode = (item.external_attr >> 16)&0xffff
            if (not parts or item.filename.startswith('/') or '\\' in item.filename or '..' in parts
                    or item.filename in names or stat.S_ISLNK(mode)):
                fail('durability', '$/field/archive', 'Unsafe or duplicate field archive member')
            names.add(item.filename)
        info = zipped.getinfo('data/aeromagnetic_data.csv')
        if info.file_size != expected['bytes'] or info.file_size > 32*1024**2:
            fail('bytes', '$/field/member', 'Pinned complete magnetic member size mismatch/cap')
        identity, count = hashlib.sha256(), 0
        with zipped.open(info) as stream:
            while raw := stream.read(65536):
                count += len(raw)
                if count > info.file_size:
                    fail('bytes', '$/field/member', 'Complete magnetic member exceeds exact receipt')
                identity.update(raw)
        if count != expected['bytes'] or identity.hexdigest() != expected['sha256']:
            fail('hash', '$/field/member', 'Complete magnetic member hash mismatch')
        with zipped.open(info) as binary:
            reader = csv.DictReader(io.TextIOWrapper(binary, encoding='utf-8-sig', newline=''), strict=True)
            headers = reader.fieldnames
            if not headers or len(headers) > 64 or len(set(headers)) != len(headers):
                fail('type', '$/field/csv', 'Bounded unique original magnetic CSV fields required')
            missing = {key: 0 for key in headers}
            nonnumeric = {key: 0 for key in headers}
            rows = 0
            for row in reader:
                rows += 1
                if rows > 2_000_000 or None in row or any(value is None or len(value) > 2048 for value in row.values()):
                    fail('count', '$/field/csv', 'Complete field stream parser bound or columns failed')
                for key, value in row.items():
                    if not value.strip():
                        missing[key] += 1
                        continue
                    try:
                        number = float(value)
                    except ValueError:
                        nonnumeric[key] += 1
                    else:
                        if not math.isfinite(number):
                            missing[key] += 1
    reasons = ['compiled_grid_not_original_flight_lines', 'unresolved_acquisition_height_and_vertical_datum',
               'no_supplied_measurement_uncertainty', 'unresolved_upstream_correction_lineage']
    if rows > ROWS_CAP:
        reasons.append('complete_acquisition_rows_exceed_bounded_inverse_cap')
    return dict(schema='magnetic-field-evaluation-1', source_id=source_record['source_id'],
        original_bytes=size, original_sha256=sha.hexdigest(), complete_archive_members=len(inventory),
        complete_archive_expanded_bytes=299907397, magnetic_member=info.filename,
        magnetic_member_bytes=count, magnetic_member_sha256=identity.hexdigest(), original_headers=headers,
        original_rows=rows, missing_or_nonfinite=missing, nonnumeric=nonnumeric,
        retained_all_rows=True, subset_used=False, rights=source_record['rights_statement'],
        attribution=source_record['citation'], original_cap_bytes=ORIGINAL_CAP, original_row_cap=ROWS_CAP,
        modelling_eligible=False, scientific_verdict='ineligible_no_invented_datum_or_errors', reasons=reasons,
        heldout_evaluated=False, model_truth=None, field_source_verified=False, online_admitted=False)
