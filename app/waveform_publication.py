"""Finite descriptor-held Linux export adoption, never overwrite or copy fallback."""
from __future__ import annotations

import ctypes
import errno
import os
import stat
import sys
from uuid import UUID

from app.errors import ApiError


def _identity(info):
    return dict(device=info.st_dev,inode=info.st_ino)


def verify_adopted_path(path, export_fd):
    """Bind the generated publication name back to the held export before commit."""
    from scripts.waveform_m08_installation import directory_fd
    current = None
    try:
        current = directory_fd(path)
        if _identity(os.fstat(current)) != _identity(os.fstat(export_fd)):
            raise ValueError()
    except (OSError,ValueError,TypeError):
        raise ApiError(409,"waveform_stage_changed","Waveform installed destination changed; bytes retained") from None
    finally:
        if current is not None:
            os.close(current)


def _rename_noreplace(source_parent, target_parent, identifier):
    libc = ctypes.CDLL(None,use_errno=True)
    try:
        rename = libc.renameat2
    except AttributeError:
        raise OSError(errno.ENOSYS,"waveform atomic installation unavailable") from None
    rename.argtypes = [ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(source_parent,b"export",target_parent,identifier.encode("ascii"),1) != 0:
        raise OSError(ctypes.get_errno(),"waveform atomic installation refused")


def adopt_export(stage_fd, export_fd, target_parent_fd, identifier, stage_identity):
    """Caller retains all descriptors and independently verifies the scientific seal.

    No deletion on any failure, including a successful rename with failed readback.
    Destination is one generated UUID leaf under a separately held parent.
    """
    try:
        if (sys.platform != "linux" or type(identifier) is not str or str(UUID(identifier)) != identifier
                or any(type(fd) is not int or fd < 0 for fd in (stage_fd,export_fd,target_parent_fd))
                or type(stage_identity) is not dict or set(stage_identity) != {"device","inode"}
                or any(type(value) is not int or value < 0 for value in stage_identity.values())):
            raise ValueError()
        stage,export,target = (os.fstat(fd) for fd in (stage_fd,export_fd,target_parent_fd))
        if (not all(stat.S_ISDIR(info.st_mode) for info in (stage,export,target))
                or _identity(stage) != stage_identity
                or not stage.st_dev == export.st_dev == target.st_dev):
            raise ValueError()
        source_entry = os.stat("export",dir_fd=stage_fd,follow_symlinks=False)
        if not stat.S_ISDIR(source_entry.st_mode) or _identity(source_entry) != _identity(export):
            raise ValueError()
        os.fsync(export_fd)
        _rename_noreplace(stage_fd,target_parent_fd,identifier)
        installed = os.stat(identifier,dir_fd=target_parent_fd,follow_symlinks=False)
        if not stat.S_ISDIR(installed.st_mode) or _identity(installed) != _identity(export):
            raise ValueError()
        try:
            os.stat("export",dir_fd=stage_fd,follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise ValueError()
        if _identity(os.fstat(stage_fd)) != stage_identity or _identity(os.fstat(export_fd)) != _identity(export):
            raise ValueError()
        os.fsync(target_parent_fd)
        os.fsync(stage_fd)
    except OSError as error:
        code = "waveform_publication_conflict" if error.errno == errno.EEXIST else "waveform_storage_unavailable"
        raise ApiError(409 if error.errno == errno.EEXIST else 503,code,
                       "Waveform export installation refused; owned bytes retained") from None
    except (ValueError,TypeError,AttributeError,UnicodeError):
        raise ApiError(409,"waveform_stage_changed","Waveform held publication identity changed; bytes retained") from None
