"""Explicit private operator lock initialization, never normal startup repair.

Creates only two fixed locks exclusively in an existing verified private root.
No migration, account, runtime authority, service or deletion is created here.
"""

import os
import stat

from app.physical_contract import require
from app.physical_posix import PrivateFiles


def initialize_private_locks(root):
    files = PrivateFiles(root)
    try:
        records = {}
        for name, marker in (('.physical-writers.lock', b'\0'), ('.processing-worker.lock', b'0')):
            created = False
            try:
                fd = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
                             0o600, dir_fd=files.fd)
                created = True
            except FileExistsError:
                fd = os.open(name, os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
                             dir_fd=files.fd)
            try:
                if created:
                    require(os.write(fd, marker) == 1, 'physical_bootstrap_short_write')
                    os.fsync(fd)
                    os.fsync(files.fd)
                info = os.fstat(fd)
                current = os.stat(name, dir_fd=files.fd, follow_symlinks=False)
                require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size == 1
                        and stat.S_IMODE(info.st_mode) == 0o600 and info.st_uid == os.geteuid()
                        and info.st_dev == files.identity[0]
                        and (info.st_dev, info.st_ino) == (current.st_dev, current.st_ino)
                        and os.pread(fd, 2, 0) == marker and not os.get_inheritable(fd),
                        'physical_bootstrap_existing_lock_refused')
                records[name] = dict(device=info.st_dev, inode=info.st_ino, uid=info.st_uid)
            finally:
                os.close(fd)
        files.check_root()
        return records
    finally:
        files.close()
