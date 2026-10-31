"""Bounded private stream publication used by large native originals."""
from __future__ import annotations

import hashlib
import io
import os
import stat

import pytest

from app.physical_posix import PrivateFiles


@pytest.mark.skipif(os.name != "posix", reason="the production physical store is POSIX-only")
def test_private_stream_write_hashes_fsyncs_and_refuses_changed_or_overlong_source(tmp_path):
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    os.chmod(root, 0o700)
    files = PrivateFiles(root)
    try:
        files.create_directory("projects")
        body = bytes(range(256)) * 1024
        digest = hashlib.sha256(body).hexdigest()
        written = files.write_new_stream("projects/good", io.BytesIO(body), cap=len(body),
            expected_bytes=len(body), expected_sha256=digest)
        assert written == {"bytes": len(body), "sha256": digest}
        assert files.read("projects/good", cap=len(body), expected_bytes=len(body),
            expected_sha256=digest) == body
        info = (root / "projects/good").stat()
        assert stat.S_IMODE(info.st_mode) == 0o600

        with pytest.raises(ValueError, match="physical_new_file_digest"):
            files.write_new_stream("projects/wrong-hash", io.BytesIO(body), cap=len(body),
                expected_bytes=len(body), expected_sha256="0" * 64)
        # Partial files remain visible to the enclosing custody census; callers
        # must make their transactional cleanup decision explicitly.
        assert (root / "projects/wrong-hash").read_bytes() == body

        with pytest.raises(ValueError, match="physical_new_file_limit"):
            files.write_new_stream("projects/too-long", io.BytesIO(body + b"x"), cap=len(body) + 1,
                expected_bytes=len(body), expected_sha256=digest)
        assert (root / "projects/too-long").read_bytes() == body
    finally:
        files.close()
