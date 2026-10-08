"""Deterministic bounded numeric ZIP export/reimport, never raw field mirroring."""

import hashlib
import io
import os
import re
import zipfile

from magnetic_local_paths import external_path
from magnetic_result_bundle import read_bundle, _read_regular, MAX_BYTES, MAX_MANIFEST
from magnetic_survey_json import fail, _Lexer

NAME = re.compile(r'(?:manifest\.json|[A-Za-z0-9_-]{1,80}\.npy)\Z', re.ASCII)


def export_zip(bundle, destination):
    root, output = external_path(bundle), external_path(destination)
    imported = read_bundle(root)
    manifest_raw = _read_regular(root/'manifest.json', MAX_MANIFEST)
    manifest = _Lexer(manifest_raw, max_bytes=MAX_MANIFEST, max_tokens=500000, max_strings=MAX_MANIFEST, defer=False).document()
    entries = {entry['name']: entry for entry in manifest['members']}
    if output.exists():
        fail('durability', '$/export', 'Fresh external numeric ZIP required')
    created = False
    try:
        with output.open('xb') as stream:
            created = True
            with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED, allowZip64=False) as zipped:
                for path in sorted(root.iterdir(), key=lambda p: p.name):
                    if NAME.fullmatch(path.name) is None:
                        fail('durability', '$/export', 'Only verified manifest and numeric members permitted')
                    raw = _read_regular(path, MAX_MANIFEST if path.name == 'manifest.json' else MAX_BYTES)
                    if path.name == 'manifest.json':
                        if raw != manifest_raw:
                            fail('hash', '$/export', 'Pinned manifest changed during export')
                    elif (path.name not in entries or len(raw) != entries[path.name]['bytes']
                            or hashlib.sha256(raw).hexdigest() != entries[path.name]['sha256']):
                        fail('hash', '$/export', 'Pinned native member changed during export')
                    info = zipfile.ZipInfo(path.name, date_time=(1980,1,1,0,0,0))
                    info.compress_type, info.create_system, info.external_attr = zipfile.ZIP_STORED, 3, 0o100600 << 16
                    zipped.writestr(info, raw)
            stream.flush()
            os.fsync(stream.fileno())
        if read_bundle(root) != imported:
            fail('hash', '$/export', 'Original immutable generation changed during export')
        raw = _read_regular(output, MAX_BYTES)
        return dict(schema='magnetic-numeric-zip-receipt-1', bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                    generation_sha256=imported['generation_sha256'], raw_original_included=False)
    except BaseException:
        if created:
            output.unlink(missing_ok=True)
        raise


def import_zip(archive, destination):
    archive, root = external_path(archive), external_path(destination)
    if root.exists():
        fail('durability', '$/import', 'Fresh external generation required; no overwrite')
    # Pin the bounded complete archive bytes once. Reopening a mutable path after
    # its cap check would let a replacement central directory bypass that cap.
    archive_raw = _read_regular(archive, MAX_BYTES)
    created = []
    root.mkdir()
    try:
        with zipfile.ZipFile(io.BytesIO(archive_raw)) as zipped:
            members = zipped.infolist()
            names = [m.filename for m in members]
            if (not 1 <= len(names) <= 65 or len(names) != len(set(names)) or 'manifest.json' not in names
                    or sum(m.file_size for m in members) > MAX_BYTES):
                fail('resource', '$/import', 'Complete bounded unique numeric ZIP members required')
            for m in members:
                maximum = MAX_MANIFEST if m.filename == 'manifest.json' else MAX_BYTES
                if (NAME.fullmatch(m.filename) is None or m.is_dir() or m.compress_type != zipfile.ZIP_STORED
                        or m.compress_size != m.file_size or m.file_size > maximum
                        or m.flag_bits & 1 or (m.external_attr >> 16) & 0o170000 not in (0,0o100000)):
                    fail('durability', '$/import', 'No paths, links, encryption, compression or unbounded numeric members')
            # Manifest closes last. No partial generation is read-successful.
            for m in sorted(members, key=lambda m: (m.filename == 'manifest.json', m.filename)):
                path = root/m.filename
                with path.open('xb') as stream:
                    created.append(path)
                    with zipped.open(m) as source:
                        count = 0
                        while chunk := source.read(65536):
                            count += len(chunk)
                            if count > m.file_size:
                                fail('resource', '$/import', 'Member grew beyond complete receipt')
                            stream.write(chunk)
                    if count != m.file_size:
                        fail('hash', '$/import', 'Truncated complete numeric member')
                    stream.flush()
                    os.fsync(stream.fileno())
        return read_bundle(root)
    except BaseException:
        # Only this fresh explicitly checked directory and our created members.
        for path in created:
            path.unlink(missing_ok=True)
        root.rmdir()
        raise
