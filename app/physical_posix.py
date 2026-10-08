"""Descriptor-relative POSIX file and directory barriers.

Only the measured Linux-local platform can qualify these mechanisms. Windows
is explicitly unsupported here. Callers retain the physical writer lease for
the whole operation; this class does not replace all-writer exclusion.
"""

import hashlib
import os
from pathlib import Path
import stat

from app.physical_contract import integer, require, sha


class PrivateFiles:
    def __init__(self, root):
        require(os.name == "posix" and hasattr(os, "O_NOFOLLOW"), "physical_posix_required")
        path = Path(root)
        require(path.is_absolute() and path != Path(path.anchor), "physical_external_root_required")
        # Walk from the filesystem root without following any directory link.
        descriptor = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        chain = []
        descriptors = [descriptor]
        try:
            for part in path.parts[1:]:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=descriptor)
                descriptors.append(child)
                chain.append((descriptor, part, self._identity(os.fstat(child))))
                descriptor = child
                try:
                    marker = os.stat(".git", dir_fd=descriptor, follow_symlinks=False)
                except FileNotFoundError:
                    marker = None
                require(marker is None, "physical_external_root_required")
            self.fd = descriptor
            self.chain = chain
            self.descriptors = descriptors
            info = os.fstat(descriptor)
            require(info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) == 0o700,
                    "physical_private_root_owner_mode")
            self.pid = os.getpid()
            self.identity = self._identity(os.fstat(self.fd))
        except BaseException:
            for opened in reversed(descriptors):
                os.close(opened)
            raise

    @staticmethod
    def _identity(value):
        return value.st_dev, value.st_ino

    @staticmethod
    def _parts(key):
        require(type(key) is str and 0 < len(key.encode()) <= 512 and "\\" not in key and "\0" not in key,
                "physical_file_key")
        parts = key.split("/")
        require(all(p and p not in (".", "..") for p in parts) and len(parts) <= 8, "physical_file_key")
        return parts

    def _parent(self, key):
        self.check_root()
        parts = self._parts(key)
        descriptor = os.dup(self.fd)
        os.set_inheritable(descriptor, False)
        try:
            for part in parts[:-1]:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=descriptor)
                if os.fstat(child).st_dev != self.identity[0]:
                    os.close(child)
                    require(False, "physical_cross_device")
                os.close(descriptor)
                descriptor = child
            return descriptor, parts[-1]
        except BaseException:
            os.close(descriptor)
            raise

    def check_root(self):
        require(self.fd is not None and os.getpid() == self.pid
                and self._identity(os.fstat(self.fd)) == self.identity, "physical_root_identity")
        for parent, name, identity in self.chain:
            info = os.stat(name, dir_fd=parent, follow_symlinks=False)
            require(stat.S_ISDIR(info.st_mode) and self._identity(info) == identity, "physical_root_replaced")

    def _open(self, parent, name):
        descriptor = os.open(name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            info = os.fstat(descriptor)
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_dev == self.identity[0],
                    "physical_file_identity")
            return descriptor
        except BaseException:
            os.close(descriptor)
            raise

    def _read(self, descriptor, cap):
        integer(cap, 1, 1073741824)
        before = os.fstat(descriptor)
        require(before.st_size <= cap, "physical_file_limit")
        pieces, total, hasher = [], 0, hashlib.sha256()
        while True:
            piece = os.read(descriptor, min(65536, cap + 1 - total))
            if not piece:
                break
            total += len(piece)
            require(total <= cap, "physical_file_limit")
            hasher.update(piece)
            pieces.append(piece)
        after = os.fstat(descriptor)
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns, before.st_nlink) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns, after.st_nlink),
                "physical_file_changed")
        require(total == before.st_size, "physical_file_changed")
        return b"".join(pieces), hasher.hexdigest(), before

    def read(self, key, *, cap, expected_bytes=None, expected_sha256=None):
        parent, name = self._parent(key)
        descriptor = None
        try:
            descriptor = self._open(parent, name)
            body, digest, info = self._read(descriptor, cap)
            if expected_bytes is not None:
                integer(expected_bytes, 0, cap)
                require(len(body) == expected_bytes, "physical_file_bytes")
            if expected_sha256 is not None:
                sha(expected_sha256)
                require(digest == expected_sha256, "physical_file_hash")
            require(self._identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) == self._identity(info),
                    "physical_file_replaced")
            return body
        finally:
            if descriptor is not None:
                os.close(descriptor)
            os.close(parent)

    def verify_directory(self, key, *, expected_files, expected_directories=()):
        """Exact closed namespace check, not a recursive cleanup/sweep."""
        require(type(expected_files) in (list, tuple, set) and type(expected_directories) in (list, tuple, set),
                "physical_directory_declaration")
        parent, name = self._parent(key)
        descriptor = None
        try:
            descriptor = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=parent)
            require(set(os.listdir(descriptor)) == set(expected_files) | set(expected_directories), "physical_directory_inventory")
            for leaf in expected_files:
                require(len(self._parts(leaf)) == 1, "physical_directory_leaf")
                child = self._open(descriptor, leaf)
                os.close(child)
            for leaf in expected_directories:
                require(len(self._parts(leaf)) == 1, "physical_directory_leaf")
                info = os.stat(leaf, dir_fd=descriptor, follow_symlinks=False)
                require(stat.S_ISDIR(info.st_mode) and info.st_dev == self.identity[0], "physical_directory_identity")
            self.check_root()
        finally:
            if descriptor is not None:
                os.close(descriptor)
            os.close(parent)

    def install(self, source, target, *, cap, expected_bytes, expected_sha256, failure_cut=None):
        """Exclusive independent copy, then file fsync, then directory fsync.

        A partially written/existing destination is NEVER unlinked in finally.
        It remains an inconsistent or prepared charged copy for fresh recovery.
        """
        body = self.read(source, cap=cap, expected_bytes=expected_bytes, expected_sha256=expected_sha256)
        parent, name = self._parent(target)
        descriptor = None
        try:
            descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600, dir_fd=parent)
            view = memoryview(body)
            while view:
                count = os.write(descriptor, view[:65536])
                require(count > 0, "physical_short_write")
                view = view[count:]
            if failure_cut:
                failure_cut("copy")
            os.fsync(descriptor)
            if failure_cut:
                failure_cut("file_sync")
            os.fsync(parent)
            if failure_cut:
                failure_cut("directory_sync")
        finally:
            if descriptor is not None:
                os.close(descriptor)
            os.close(parent)

    def remove(self, key, *, cap, expected_bytes, expected_sha256, failure_cut=None):
        """Delete exactly one verified ordinary file and sync its directory.

        Absence before this operation is a refusal, NOT a removal receipt. If
        directory fsync/SQL acknowledgement is uncertain, retain the charge.
        """
        parent, name = self._parent(key)
        descriptor = None
        try:
            descriptor = self._open(parent, name)
            body, digest, info = self._read(descriptor, cap)
            integer(expected_bytes, 0, cap)
            sha(expected_sha256)
            require(len(body) == expected_bytes and digest == expected_sha256, "physical_remove_identity")
            require(self._identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) == self._identity(info),
                    "physical_file_replaced")
            os.unlink(name, dir_fd=parent)
            if failure_cut:
                failure_cut("unlink")
            os.fsync(parent)
            if failure_cut:
                failure_cut("directory_sync")
        finally:
            if descriptor is not None:
                os.close(descriptor)
            os.close(parent)

    def close(self):
        if self.fd is not None:
            for descriptor in reversed(self.descriptors):
                os.close(descriptor)
            self.fd = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
