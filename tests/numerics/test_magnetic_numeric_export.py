"""Actual fitted numeric ZIP durability/negative controls, not field acceptance."""

from time import monotonic
import zipfile

import pytest

from magnetic_calibration import calibrate
from magnetic_result_bundle import write_bundle
from magnetic_result_export import export_zip, import_zip
from magnetic_survey_json import canonical, InputError
from test_magnetic_full_calibration import small_request


@pytest.fixture(scope='module')
def fitted(tmp_path_factory):
    root = tmp_path_factory.mktemp('numeric-zip-control')
    doc, binding = small_request()
    result = calibrate(canonical(doc), binding=binding, source_inventory_sha256='a'*64, deadline=monotonic()+120.)
    assert result['status'] == 'complete'
    write_bundle(root/'generation', result, doc)
    return root


def test_deterministic_actual_export_exact_reimport_and_no_raw(fitted):
    a, b = fitted/'first.zip', fitted/'second.zip'
    first, second = export_zip(fitted/'generation', a), export_zip(fitted/'generation', b)
    assert a.read_bytes() == b.read_bytes() and first == second
    imported = import_zip(a, fitted/'reimported')
    assert imported['generation_sha256'] == first['generation_sha256']
    assert not first['raw_original_included']
    with pytest.raises(InputError, match='Fresh'):
        export_zip(fitted/'generation', a)
    assert a.read_bytes() == b.read_bytes()


@pytest.mark.parametrize('name', ['../outside.npy', '/outside.npy', 'raw.csv', 'nested/model.npy'])
def test_actual_path_raw_member_rejection_preserves_old_generation(fitted, tmp_path, name):
    malformed = tmp_path/'wrong.zip'
    with zipfile.ZipFile(malformed, 'w') as zipped:
        zipped.writestr('manifest.json', (fitted/'generation'/'manifest.json').read_bytes())
        zipped.writestr(name, b'no numeric member')
    before = {p.name: p.read_bytes() for p in (fitted/'generation').iterdir()}
    with pytest.raises(InputError):
        import_zip(malformed, tmp_path/'new')
    assert not (tmp_path/'new').exists()
    assert before == {p.name: p.read_bytes() for p in (fitted/'generation').iterdir()}


def test_corrupted_native_member_rejects(fitted, tmp_path):
    archive = tmp_path/'corrupted.zip'
    with zipfile.ZipFile(fitted/'first.zip') as original, zipfile.ZipFile(archive, 'w') as writer:
        for info in original.infolist():
            raw = original.read(info)
            if info.filename.endswith('.npy'):
                raw = raw[:-1]+bytes([raw[-1]^1])
            writer.writestr(info, raw)
    with pytest.raises(InputError, match='hash'):
        import_zip(archive, tmp_path/'new')
    assert not (tmp_path/'new').exists()


def test_compression_rejects_before_extraction(fitted, tmp_path):
    archive = tmp_path/'compressed.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as zipped:
        zipped.writestr('manifest.json', (fitted/'generation'/'manifest.json').read_bytes())
    with pytest.raises(InputError, match='compression'):
        import_zip(archive, tmp_path/'new')
    assert not (tmp_path/'new').exists()


def test_archive_path_replacement_cannot_change_pinned_import(fitted, tmp_path, monkeypatch):
    import magnetic_result_export
    archive = tmp_path/'replace-after-check.zip'
    archive.write_bytes((fitted/'first.zip').read_bytes())
    original_reader = magnetic_result_export._read_regular
    replaced = False
    def pinned_reader(path, cap):
        nonlocal replaced
        raw = original_reader(path, cap)
        if path == archive:
            archive.write_bytes(b'Not the bounded verified ZIP that was read')
            replaced = True
        return raw
    monkeypatch.setattr(magnetic_result_export, '_read_regular', pinned_reader)
    imported = import_zip(archive, tmp_path/'new')
    assert replaced
    assert imported['generation_sha256'] == export_zip(fitted/'generation', tmp_path/'fresh.zip')['generation_sha256']


def test_actual_export_io_failure_does_not_damage_existing_generation(fitted, tmp_path, monkeypatch):
    import magnetic_result_export
    before = {p.name: p.read_bytes() for p in (fitted/'generation').iterdir()}
    def failed(*args):
        raise OSError('Injected fsync failure')
    monkeypatch.setattr(magnetic_result_export.os, 'fsync', failed)
    with pytest.raises(OSError, match='fsync'):
        export_zip(fitted/'generation', tmp_path/'failed.zip')
    assert not (tmp_path/'failed.zip').exists()
    assert before == {p.name: p.read_bytes() for p in (fitted/'generation').iterdir()}
