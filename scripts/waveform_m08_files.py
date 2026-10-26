"""Ordinary bounded held-file I/O; no process/job/cgroup/resource controller."""

import hashlib
import os
from pathlib import Path
import re
import stat

from waveform_input import fail


def validate_path(value):
    if type(value) not in (str, type(Path())):
        fail("waveform_type")
    text = str(value)
    if (
        not 0 < len(text) <= 4096
        or any(ord(c) < 32 for c in text)
        or any(c in text for c in "*?\0")
        or "://" in text
        or text.startswith(("\\\\", "//"))
    ):
        fail("waveform_contract")
    if os.name == "nt" and (not re.match(r"[A-Za-z]:[\\/]", text) or ":" in text[2:]):
        fail("waveform_contract")
    parts = re.split(r"[\\/]", text)
    if any(part in (".", "..") for part in parts) or len(parts) > 128:
        fail("waveform_contract")
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
    if any(p and (p.endswith((" ", ".")) or p.split(".")[0].upper() in reserved) for p in parts[1:]):
        fail("waveform_contract")
    path = Path(text)
    if not path.is_absolute():
        fail("waveform_contract")
    return path


def _win_api():
    import ctypes

    class FileTime(ctypes.Structure):
        _fields_ = [("low", ctypes.c_uint32), ("high", ctypes.c_uint32)]

    class FileInfo(ctypes.Structure):
        _fields_ = [
            ("attributes", ctypes.c_uint32),
            ("created", FileTime),
            ("accessed", FileTime),
            ("written", FileTime),
            ("volume", ctypes.c_uint32),
            ("size_high", ctypes.c_uint32),
            ("size_low", ctypes.c_uint32),
            ("links", ctypes.c_uint32),
            ("index_high", ctypes.c_uint32),
            ("index_low", ctypes.c_uint32),
        ]

    if ctypes.sizeof(FileInfo) != 52:
        fail("waveform_contract")
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.CreateFileW.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    ]
    api.CreateFileW.restype = ctypes.c_void_p
    api.GetFileInformationByHandle.argtypes = [ctypes.c_void_p, ctypes.POINTER(FileInfo)]
    api.GetFileInformationByHandle.restype = ctypes.c_int32
    api.GetFileType.argtypes = [ctypes.c_void_p]
    api.GetFileType.restype = ctypes.c_uint32
    api.CloseHandle.argtypes = [ctypes.c_void_p]
    api.CloseHandle.restype = ctypes.c_int32
    return api, FileInfo


def _info(fd):
    if os.name != "nt":
        s = os.fstat(fd)
        return (s.st_dev, s.st_ino), s.st_size, s.st_nlink, stat.S_ISDIR(s.st_mode), s.st_mtime_ns
    import msvcrt

    api, Info = _win_api()
    value = Info()
    handle = msvcrt.get_osfhandle(fd)
    if api.GetFileType(handle) != 1 or not api.GetFileInformationByHandle(handle, value) or value.attributes & 0x400:
        fail("waveform_contract")
    return (
        (value.volume, value.index_high, value.index_low),
        (value.size_high << 32) | value.size_low,
        value.links,
        bool(value.attributes & 0x10),
        (value.written.high << 32) | value.written.low,
    )


def _open_fd(path, *, directory=False, create=False, parent_fd=None):
    failure = False
    fd = None
    try:
        if os.name == "nt":
            import ctypes
            import msvcrt

            api, Info = _win_api()
            access = 0x80 if directory else 0xC0000000 if create else 0x80000000
            handle = api.CreateFileW(
                str(path), access, 1, None, 1 if create else 3, 0x00200000 | (0x02000000 if directory else 0), None
            )
            if handle == ctypes.c_void_p(-1).value:
                raise OSError("File open failed")
            try:
                fd = msvcrt.open_osfhandle(
                    handle, os.O_BINARY | os.O_NOINHERIT | (os.O_RDWR if create else os.O_RDONLY)
                )
            except BaseException:
                api.CloseHandle(handle)
                raise
        else:
            if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
                fail("waveform_contract")
            flags = (
                os.O_NOFOLLOW
                | os.O_CLOEXEC
                | (
                    os.O_DIRECTORY | os.O_RDONLY
                    if directory
                    else os.O_CREAT | os.O_EXCL | os.O_RDWR
                    if create
                    else os.O_RDONLY
                )
            )
            fd = os.open(path.name if parent_fd is not None else path, flags, 0o600, dir_fd=parent_fd)
        info = _info(fd)
        if info[3] != directory or not directory and (info[2] != 1 or not stat.S_ISREG(os.fstat(fd).st_mode)):
            failure = True
    except OSError:
        failure = True
    except BaseException:
        if fd is not None:
            os.close(fd)
        raise
    if failure:
        if fd is not None:
            os.close(fd)
        fail("waveform_contract")
    return fd


def _lease(path):
    held = []
    try:
        for item in (*reversed(path.parents), path):
            fd = _open_fd(item, directory=True, parent_fd=held[-1] if held and os.name != "nt" else None)
            held.append(fd)
        return held
    except BaseException:
        for fd in reversed(held):
            os.close(fd)
        raise


class InputHandle:
    def __init__(self, path, cap):
        if type(cap) is not int or not 0 < cap <= 16777216:
            fail("waveform_limit")
        self.path = validate_path(path)
        self.held = _lease(self.path.parent)
        self.fd = None
        try:
            self.fd = _open_fd(self.path, parent_fd=self.held[-1])
            self.initial = _info(self.fd)
            if not 0 < self.initial[1] <= cap:
                fail("waveform_limit")
            self.handle = os.fdopen(self.fd, "rb", buffering=0)
            self.cap, self.used, self.sha256 = cap, False, None
        except BaseException:
            if self.fd is not None:
                os.close(self.fd)
            for fd in reversed(self.held):
                os.close(fd)
            raise

    def read_bytes(self):
        if self.used:
            fail("waveform_contract")
        self.used = True
        raw = self.handle.read(self.cap + 1)
        if len(raw) != self.initial[1] or _info(self.fd) != self.initial:
            fail("waveform_contract")
        self.sha256 = hashlib.sha256(raw).hexdigest()
        return raw

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.handle.close()
        for fd in reversed(self.held):
            os.close(fd)


def open_input(path, cap):
    return InputHandle(path, cap)


class OwnedDirectory:
    def __init__(self, path, held, *, readonly=False):
        self.path, self.held = path, held
        self.fd, self.identity = held[-1], _info(held[-1])[0]
        self.closed = False
        self.readonly = readonly

    def check_identity(self):
        if self.closed or _info(self.fd)[0] != self.identity:
            fail("waveform_contract")
        fresh = _open_fd(self.path, directory=True)
        try:
            if _info(fresh)[0] != self.identity:
                fail("waveform_contract")
        finally:
            os.close(fresh)

    def names(self, cap):
        self.check_identity()
        if type(cap) is not int or not 0 < cap <= 55:
            fail("waveform_limit")
        names = []
        with os.scandir(self.path) as entries:
            for item in entries:
                if (
                    len(names) >= cap
                    or item.is_symlink()
                    or getattr(item.stat(follow_symlinks=False), "st_file_attributes", 0) & 0x400
                ):
                    fail("waveform_contract")
                names.append(item.name)
        self.check_identity()
        return sorted(names)

    def _regular(self, name, create):
        from waveform_m08_export import _name

        _name(name)
        self.check_identity()
        fd = _open_fd(self.path / name, create=create, parent_fd=self.fd)
        return os.fdopen(fd, "w+b" if create else "rb", buffering=0)

    def create_regular(self, name):
        if self.readonly:
            fail("waveform_contract")
        return self._regular(name, True)

    def open_regular(self, name):
        return self._regular(name, False)

    @staticmethod
    def file_size(handle):
        return _info(handle.fileno())[1]

    @staticmethod
    def flush_file(handle):
        handle.flush()
        os.fsync(handle.fileno())

    def publish_pending(self):
        if self.readonly:
            fail("waveform_contract")
        self.check_identity()
        failed = False
        try:
            if os.name == "nt":
                os.rename(self.path / "manifest.pending", self.path / "manifest.json")
            else:
                os.link(
                    "manifest.pending", "manifest.json", src_dir_fd=self.fd, dst_dir_fd=self.fd, follow_symlinks=False
                )
                os.unlink("manifest.pending", dir_fd=self.fd)
                os.fsync(self.fd)
        except OSError:
            failed = True
        if failed:
            fail("waveform_contract")
        self.check_identity()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if not self.closed:
            self.closed = True
            for fd in reversed(self.held):
                os.close(fd)


def create_output(path, *, trusted_parent):
    path, parent = validate_path(path), validate_path(trusted_parent)
    if path.parent != parent:
        fail("waveform_contract")
    held = _lease(parent)
    failed = False
    try:
        if os.name == "nt":
            os.mkdir(path, 0o700)
        else:
            os.mkdir(path.name, 0o700, dir_fd=held[-1])
        held.append(_open_fd(path, directory=True, parent_fd=held[-1]))
    except OSError:
        failed = True
    except BaseException:
        for fd in reversed(held):
            os.close(fd)
        raise
    if failed:
        for fd in reversed(held):
            os.close(fd)
        fail("waveform_contract")
    return OwnedDirectory(path, held)


def open_output(path):
    """Read-only lease for an existing export; no creation, reuse or repair."""
    path = validate_path(path)
    return OwnedDirectory(path, _lease(path), readonly=True)
