"""Installation-owned profile exec wrapper, never an uploaded executable."""
import json
import hashlib
import os
from pathlib import Path
import stat
import sys


def main():
    if os.name != "posix" or len(sys.argv) != 2:
        return 2
    path = Path(sys.argv[1])
    metadata = path.lstat()
    if (not path.is_absolute() or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1
            or metadata.st_uid != 0 or metadata.st_mode & 0o022 or not 0 < metadata.st_size <= 65536):
        return 2
    fd = os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        with os.fdopen(os.dup(fd),"rb") as stream:
            raw = stream.read(65537)
        current = os.fstat(fd)
        fields = ("st_dev","st_ino","st_mode","st_nlink","st_uid","st_gid","st_size","st_mtime_ns","st_ctime_ns")
        if any(getattr(current,key) != getattr(metadata,key) for key in fields) or len(raw) != metadata.st_size:
            return 2
    finally:
        os.close(fd)
    spec = json.loads(raw)
    if type(spec) is not dict or set(spec) != {"command","environment","stderr","inputs"}:
        return 2
    # This packet is created exclusively in the supervisor's root-owned input
    # directory, bound readonly into scratch. It is not client launch JSON.
    command, environment = spec["command"], spec["environment"]
    if (type(command) is not list or not command or any(type(v) is not str for v in command)
            or type(environment) is not dict or any(type(k) is not str or type(v) is not str for k,v in environment.items())
            or type(spec["stderr"]) is not str or spec["stderr"] != str(Path.cwd()/"stderr.txt")):
        return 2
    if type(spec["inputs"]) is not dict or set(spec["inputs"]) != {"original","dataset.json"}:
        return 2
    for name,expected in spec["inputs"].items():
        if type(expected) is not dict or set(expected) != {"device","inode","bytes","sha256"}:
            return 2
        member = path.parent/name
        fd = os.open(member,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o222
                    or info.st_nlink != 1 or not 0 < info.st_size <= 2*1024**2
                    or (info.st_dev,info.st_ino,info.st_size) != (expected["device"],expected["inode"],expected["bytes"])):
                return 2
            with os.fdopen(os.dup(fd),"rb") as stream:
                body = stream.read(2*1024**2+1)
            if len(body) != info.st_size or hashlib.sha256(body).hexdigest() != expected["sha256"]:
                return 2
        finally:
            os.close(fd)
    # Liveness supervision is installation-owned root code outside this unit.
    # No same-UID payload process is trusted to keep its own watcher alive.
    fd = os.open(spec["stderr"], os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    try:
        os.dup2(fd,2)
    finally:
        os.close(fd)
    os.execve(command[0],command,environment)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError,ValueError,TypeError,KeyError):
        raise SystemExit(2) from None
