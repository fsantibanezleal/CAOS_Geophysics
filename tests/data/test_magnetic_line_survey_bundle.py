"""Actual original S1 geometry preparation, explicitly NOT a field/fit pass."""
from copy import deepcopy
from hashlib import sha256
import os
from pathlib import Path
import struct
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'data-pipeline'))
import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_bundle as bundle
import magnetic_line_survey_io as io
import magnetic_line_survey_runtime as runtime
from magnetic_line_survey_result import _refs
from test_magnetic_line_survey_diagnostic import plan as original_plan


def entry(path):
    # Bounded fixture originals only; production does not read whole originals.
    body = path.read_bytes()
    return dict(path=str(path), bytes=len(body), sha256=sha256(body).hexdigest())


def write_bundle(path, members):
    with path.open('xb') as stream:
        stream.write(b'M03AUX1\n'+struct.pack('<I', len(members)))
        for name, payload in sorted(members):
            encoded = name.encode('ascii')
            stream.write(struct.pack('<H', len(encoded))+encoded+struct.pack('<Q', len(payload)))
            stream.write(sha256(payload).digest()+payload)
        stream.flush(); os.fsync(stream.fileno())


def fixture(root, *, extra=()):
    root.mkdir()
    original = base.strict_json(original_plan(root).read_bytes())
    metadata = original['metadata']; request = original['request']
    known = {}
    for directory, value in [(original['geometry_root'], metadata), (original['request_root'], request)]:
        reader = io.Reader(directory)
        for ref in _refs(value):
            for _ in reader.chunks(ref): pass
        for name in reader.known:
            payload = (Path(directory)/name).read_bytes()
            assert name not in known or known[name] == payload
            known[name] = payload
    members = list(known.items())+list(extra)
    container = root/'auxiliary-original.bin'; write_bundle(container, members)
    meta, req = root/'metadata-original.json', root/'request-original.json'
    meta.write_bytes(base.canonical_bytes(metadata)); req.write_bytes(base.canonical_bytes(request))
    return dict(schema='m03-owner-preparation-plan/1', original=entry(Path(original['csv_path'])),
        metadata=entry(meta), request=entry(req), bundles=[entry(container)])


def test_exact_closure_and_unknown_alias_refusal(tmp_path):
    plan = fixture(tmp_path/'positive')
    workspace = tmp_path/'prepared'; workspace.mkdir()
    result = bundle._prepare(plan, workspace)
    assert result['rows'] == 363 and result['semantic_closure'] == 'schema_recognized_encoded_bytes'
    assert result['scientific_result'] == result['field_eligibility'] == 'not_established'
    assert result['capacity']['full_job_admission'] == 'not_established'
    assert result['physical_members'] > result['logical_members']
    for number, (name, payload) in enumerate([('not-authorized.py', b'print(1)'), ('Array-row_id.json', b'{}')]):
        wrong = fixture(tmp_path/f'unknown-{number}', extra=[(name, payload)])
        output = tmp_path/f'refused-{number}'; output.mkdir()
        with pytest.raises(core.SurveyError): bundle._prepare(wrong, output)
        assert (output/'bundle-index.sqlite3').exists()
        assert not (output/'preparation.json').exists()
    # Across two individually valid containers, repeated/case-aliased members
    # refuse BEFORE any extracted member is allocated.
    for number, name in enumerate(['array-row_id.json', 'Array-row_id.json']):
        second = tmp_path/f'duplicate-{number}.bin'
        write_bundle(second, [(name, b'{}')])
        wrong = deepcopy(plan); wrong['bundles'].append(entry(second))
        output = tmp_path/f'duplicate-refused-{number}'; output.mkdir()
        with pytest.raises(core.SurveyError): bundle._prepare(wrong, output)
        assert not (output/'auxiliary').exists()


def test_geometry_mismatch_preserves_failure(tmp_path):
    plan = fixture(tmp_path/'inputs')
    meta = base.strict_json(Path(plan['metadata']['path']).read_bytes())
    # The entire typed bundle stays valid. Change ONLY a fixture original
    # geometry coordinate and honestly bind its new raw identity; independently
    # reconstructed geometry must disagree with the unchanged supplied arrays.
    csv = Path(plan['original']['path'])
    records = csv.read_text().splitlines()
    cells = records[1].split(',')
    column = base.CSV_COLUMNS.index('easting_m')
    cells[column] = str(float(cells[column])+1.)
    records[1] = ','.join(cells)
    csv.write_bytes(('\n'.join(records)+'\n').encode('ascii'))
    plan['original'] = entry(csv)
    meta['original']['csv_sha256'] = plan['original']['sha256']
    meta['original']['csv_bytes'] = plan['original']['bytes']
    Path(plan['metadata']['path']).write_bytes(base.canonical_bytes(meta))
    plan['metadata'] = entry(Path(plan['metadata']['path']))
    request_path = Path(plan['request']['path'])
    request = base.strict_json(request_path.read_bytes())
    request['dataset_version_sha256'] = base.dataset_identity(meta['original']['csv_sha256'], base.digest(meta))
    request_path.write_bytes(base.canonical_bytes(request)); plan['request'] = entry(request_path)
    output = tmp_path/'failed'; output.mkdir()
    with pytest.raises(core.SurveyError): bundle._prepare(plan, output)
    assert (output/'auxiliary').exists() and (output/'bundle-index.sqlite3').exists()
    assert (output/'geometry'/'inspection.json').exists()
    assert not (output/'preparation.json').exists()
    assert runtime.owned_bytes(output) > 0


def test_preallocation_capacity_and_actual_containment_refusals(tmp_path):
    proof = bundle.preparation_capacity(8201, 1000000)
    assert proof['original_rows'] == 8201  # Arithmetic ONLY, no acquired field claim.
    assert proof['scratch_bound_bytes'] == 1000000+4294967296+65536*8201+134217728
    for rows, count in [(True, 1), (8000000, 1), (363, True), (363, 4294967297)]:
        with pytest.raises(core.SurveyError): bundle.preparation_capacity(rows, count)
    with pytest.raises(core.SurveyError): bundle.run_preparation_plan({}, tmp_path, 0)
    assert not list(tmp_path.iterdir())


@pytest.mark.skipif(sys.platform != 'win32', reason='Actual Windows Job required')
@pytest.mark.parametrize('opaque_measurements', [False, True])
def test_native_full_geometry_without_measurement_decode(tmp_path, monkeypatch, opaque_measurements):
    plan = fixture(tmp_path/'inputs')
    # Independent corruption of opaque original measurements. Geometry and raw
    # custody are updated honestly; no synthetic field/source metadata is added.
    csv = Path(plan['original']['path'])
    records = csv.read_text().splitlines()
    magnetic = base.CSV_COLUMNS.index('magnetic_nT')
    changed = [records[0]]
    for record in records[1:]:
        cells = record.split(','); cells[magnetic] = 'SEALED_NOT_A_NUMBER'
        changed.append(','.join(cells))
    if opaque_measurements:
        csv.write_bytes(('\n'.join(changed)+'\n').encode('ascii'))
    plan['original'] = entry(csv)
    meta_path = Path(plan['metadata']['path'])
    metadata = base.strict_json(meta_path.read_bytes())
    metadata['original']['csv_bytes'] = plan['original']['bytes']
    metadata['original']['csv_sha256'] = plan['original']['sha256']
    meta_path.write_bytes(base.canonical_bytes(metadata)); plan['metadata'] = entry(meta_path)
    request_path = Path(plan['request']['path'])
    request = base.strict_json(request_path.read_bytes())
    request['dataset_version_sha256'] = base.dataset_identity(metadata['original']['csv_sha256'], base.digest(metadata))
    request_path.write_bytes(base.canonical_bytes(request)); plan['request'] = entry(request_path)
    # Local oracle ensures no general array cells decoder is used in preparation.
    def unopened(*args, **kwargs): raise AssertionError('Measurement cells must remain unopened')
    monkeypatch.setattr(io.Reader, 'cells', unopened)
    oracle = tmp_path/'encoded-oracle'; oracle.mkdir()
    assert bundle._prepare(plan, oracle)['value_access'] == 'not_opened'
    workspace = tmp_path/'native'; workspace.mkdir()
    path = workspace/'plan.json'; path.write_bytes(base.canonical_bytes(plan))
    lifetime = runtime.run_worker(Path(sys.base_prefix)/'python.exe',
        Path(os.environ['GEOPHYSICS_EXISTING_PACKAGE_ROOT']), workspace, path)
    assert lifetime['verdict'] == 'component_pass', (lifetime, (workspace/'stderr.log').read_text(), (workspace/'stdout.log').read_text())
    result = base.strict_json((workspace/'preparation.json').read_bytes())
    assert result['rows'] == 363 and result['geometry']['value_access'] == result['value_access'] == 'not_opened'
    assert lifetime['total_processes'] == 1 and lifetime['active_processes'] == 0
    assert lifetime['scratch_bytes'] == runtime.owned_bytes(workspace)
    assert 'magnetic_line_survey_bundle.py' in lifetime['source_sha256']
    assert not list(workspace.rglob('*coefficients*')) and not (workspace/'result').exists()
