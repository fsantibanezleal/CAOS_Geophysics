"""Real files and authored allocation cuts, not an OS memory admission."""
import hashlib
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2]/'scripts/validate_local.py'
spec = importlib.util.spec_from_file_location('validation_hash_memory', SCRIPT)
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)


class Stream:
    def __init__(self, underlying, fail=False):
        self.underlying = underlying
        self.fail = fail
        self.buffers = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return self.underlying.__exit__(*args)

    def fileno(self):
        return self.underlying.fileno()

    def read(self, *args):
        raise AssertionError('Hashing must reuse readinto buffer')

    def readinto(self, buffer):
        self.buffers.append((id(buffer), len(buffer)))
        if self.fail:
            raise MemoryError('Authored allocation failure')
        return self.underlying.readinto(buffer)


def instrument(monkeypatch, path, fail=False):
    original = Path.open
    opened = []

    def open_file(selected, *args, **kwargs):
        real = original(selected, *args, **kwargs)
        if selected == path:
            stream = Stream(real, fail)
            opened.append(stream)
            return stream
        return real

    monkeypatch.setattr(Path, 'open', open_file)
    return opened


@pytest.mark.parametrize('size', [0, 1, 65535, 65536, 65537, 3*1048576])
def test_exact_streamed_record_uses_one_bounded_buffer(tmp_path, monkeypatch, size):
    path = tmp_path/'original.bin'
    raw = (bytes(range(256))*((size+255)//256))[:size]
    path.write_bytes(raw)
    opened = instrument(monkeypatch, path)
    record = harness.file_record(path)
    assert record == dict(path=str(path), bytes=size, sha256=hashlib.sha256(raw).hexdigest())
    assert len(opened) == 1 and opened[0].underlying.closed
    assert len(set(opened[0].buffers)) == 1 and opened[0].buffers[0][1] == 65536


def test_hash_allocation_failure_closes_stream_without_retry(tmp_path, monkeypatch):
    path = tmp_path/'original.bin'
    path.write_bytes(b'original unchanged bytes')
    opened = instrument(monkeypatch, path, fail=True)
    with pytest.raises(harness.Refusal, match='^input hashing allocation unavailable$'):
        harness.file_record(path)
    assert len(opened) == 1 and len(opened[0].buffers) == 1 and opened[0].underlying.closed


def test_buffer_allocation_failure_never_opens_source(tmp_path, monkeypatch):
    path = tmp_path/'original.bin'
    path.write_bytes(b'original')
    opened = instrument(monkeypatch, path)

    def unavailable(*args):
        raise MemoryError('Authored buffer allocation failure')

    monkeypatch.setattr(harness, 'bytearray', unavailable, raising=False)
    with pytest.raises(harness.Refusal, match='^input hashing allocation unavailable$'):
        harness.file_record(path)
    assert opened == []


def test_top_level_allocation_refuses_without_traceback(monkeypatch, capsys):
    calls = []

    def unavailable(*args):
        calls.append(args)
        raise MemoryError('Authored private diagnostic must not leak')

    monkeypatch.setattr(harness, 'run', unavailable)
    status = harness.main(['--config', 'x', '--device-root', 'y', '--cache-root', 'z', '--report-root', 'r'])
    assert status == 2 and len(calls) == 1
    captured = capsys.readouterr()
    assert captured.out == '' and captured.err == 'REFUSED: validation allocation unavailable\n'
