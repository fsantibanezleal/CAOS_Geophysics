"""Independent exact-file cancellation/recovery boundaries, no numerical fit."""
import asyncio
import hashlib
import os
from pathlib import Path
import shutil
import threading

import pytest

from app import joint_result as result
from app.errors import ApiError


def original():
    root = Path(os.environ['GEOPHYSICS_JOINT_INSTRUMENT_FIXTURE'])
    return next((root / 'calibration').glob('*.npy'))


def test_cancelled_writer_is_drained_before_caller_releases_guard(tmp_path):
    source = original(); target = tmp_path / 'retained.npy'
    body = source.read_bytes(); binding = {'byte_count': len(body), 'sha256': hashlib.sha256(body).hexdigest()}
    entered, release, exited = threading.Event(), threading.Event(), threading.Event()
    def held_copy():
        entered.set(); assert release.wait(5)
        result._copy(source, target, binding); exited.set()
    async def execute():
        task = asyncio.create_task(result._drained_io(held_copy))
        for _ in range(100):
            if entered.is_set(): break
            await asyncio.sleep(.01)
        assert entered.is_set(); task.cancel(); await asyncio.sleep(.02)
        assert not task.done() and not exited.is_set()
        task.cancel(); await asyncio.sleep(.02)
        assert not task.done()
        release.set()
        with pytest.raises(asyncio.CancelledError): await task
        assert exited.is_set() and target.read_bytes() == body
    asyncio.run(execute())


def test_directory_drift_during_hash_refuses_without_hash_reuse(tmp_path, monkeypatch):
    root = tmp_path / 'native'; (root / 'calibration').mkdir(parents=True)
    source = original(); shutil.copyfile(source, root / 'calibration' / source.name)
    real = result._hash; calls = []
    def mutate(path, *args, **kwargs):
        calls.append(path); value = real(path, *args, **kwargs)
        (root / 'foreign-directory').mkdir()
        return value
    monkeypatch.setattr(result, '_hash', mutate)
    with pytest.raises(ApiError): result.inventory(root)
    assert len(calls) == 1 and (root / 'calibration' / source.name).read_bytes() == source.read_bytes()


def test_read_only_recovery_measures_unknown_missing_changed_and_empty_dirs(tmp_path):
    root = tmp_path / 'retained'; (root / 'calibration').mkdir(parents=True)
    source = original(); target = root / 'calibration' / source.name
    shutil.copyfile(source, target); expected = result.inventory(root)
    with target.open('ab') as stream: stream.write(b'actual retained drift')
    with (root / 'unknown.bin').open('xb') as stream: stream.write(b'actual unknown private bytes')
    (root / 'unknown-empty').mkdir()
    report = result.recovery_report(root, expected)
    assert report['changed'] == list(expected) and report['unknown'] == ['unknown.bin']
    assert report['unknown_directories'] == ['unknown-empty'] and report['reconciled'] is False
    assert report['observed_bytes'] == target.stat().st_size + (root / 'unknown.bin').stat().st_size
    target.rename(root / 'retained-missing.bin')
    assert result.recovery_report(root, expected)['missing'] == list(expected)
