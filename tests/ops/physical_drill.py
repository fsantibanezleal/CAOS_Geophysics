"""Actual isolated Linux mechanism drill, never a live target/admission tool."""

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

from app.physical_leases import WriterLeases
from app.physical_posix import PrivateFiles


SOURCE_ID = "2026-03-13 10:38:09 737ae4a34738ffa0c3ff7f9bb18df914dd1cad163f28fd6b6e114a344fe6d618"


def digest(body):
    return hashlib.sha256(body).hexdigest()


def refused(callback):
    try:
        callback()
    except (ValueError, OSError):
        return
    raise AssertionError("unsafe operation admitted")


async def lease_drill(root):
    lock = root / ".physical-writers.lock"
    with lock.open("xb") as stream:
        stream.write(b"\0")
        stream.flush()
        os.fsync(stream.fileno())
    lock.chmod(0o600)
    info = lock.stat()
    manager = WriterLeases(root, device=info.st_dev, inode=info.st_ino, uid=os.geteuid())
    try:
        async with manager.acquire():
            async with manager.acquire():
                pass
            async def blocked():
                try:
                    async with manager.acquire(exclusive=True, timeout=0.05):
                        raise AssertionError("exclusive bypassed live shared writer")
                except ValueError as error:
                    assert str(error) == "physical_writer_busy"
            await asyncio.create_task(blocked())
            async def second_shared():
                async with manager.acquire(timeout=0):
                    pass
            await asyncio.create_task(second_shared())
            try:
                async with manager.acquire(exclusive=True, timeout=0):
                    raise AssertionError("upgrade")
            except ValueError as error:
                assert str(error) == "physical_lease_upgrade_or_reentry"
            # The exec child must not inherit ANY descriptor to the lock inode.
            child = subprocess.run([sys.executable, "-B", "-c",
                "import json,os,sys; identity=tuple(json.loads(sys.argv[1])); "
                "hits=[]\nfor name in os.listdir('/proc/self/fd'):\n"
                " try:\n  s=os.fstat(int(name)); hits.append(name) if (s.st_dev,s.st_ino)==identity else None\n"
                " except OSError: pass\nassert not hits, hits", json.dumps((info.st_dev, info.st_ino))],
                close_fds=True, capture_output=True, timeout=5)
            assert child.returncode == 0, child.stderr
        async with manager.acquire(exclusive=True, timeout=0):
            pass
        # Same-name replacement never silently reinitializes the lease.
        lock.rename(root / "old-lock")
        with lock.open("xb") as stream:
            stream.write(b"\0")
        lock.chmod(0o600)
        try:
            async with manager.acquire(timeout=0):
                raise AssertionError("replacement")
        except ValueError as error:
            assert str(error) == "physical_lock_identity"
    finally:
        manager.close()
    return dict(shared_nested=True, concurrent_shared=True, exclusive_blocked=True,
                no_upgrade=True, exec_noninheritance=True, identity_replacement_refused=True)


def file_drill(root):
    body = b'{"actual":"independent native copies"}'
    (root / "stage").mkdir(mode=0o700)
    (root / "derived").mkdir(mode=0o700)
    with (root / "stage/input.json").open("xb") as stream:
        stream.write(body)
        stream.flush()
        os.fsync(stream.fileno())
    expected = dict(cap=4096, expected_bytes=len(body), expected_sha256=digest(body))
    with PrivateFiles(root) as files:
        files.install("stage/input.json", "derived/output.json", **expected)
        assert files.read("derived/output.json", **expected) == body
        source, target = (root / "stage/input.json").stat(), (root / "derived/output.json").stat()
        assert (source.st_dev, source.st_ino) != (target.st_dev, target.st_ino)
        assert source.st_nlink == target.st_nlink == 1
        refused(lambda: files.install("stage/input.json", "derived/output.json", **expected))
        os.link(root / "stage/input.json", root / "stage/alias.json")
        refused(lambda: files.read("stage/input.json", **expected))
        (root / "stage/alias.json").unlink()
        (root / "stage/link.json").symlink_to("input.json")
        refused(lambda: files.read("stage/link.json", **expected))
        refused(lambda: files.read("../outside", **expected))
        files.remove("derived/output.json", **expected)
        refused(lambda: files.remove("derived/output.json", **expected))
        def cut(point):
            if point == "file_sync":
                raise RuntimeError("after_file_sync")
        try:
            files.install("stage/input.json", "derived/uncertain.json", **expected, failure_cut=cut)
        except RuntimeError:
            pass
        assert files.read("derived/uncertain.json", **expected) == body
        uncertain = root / "derived/uncertain.json"
        def unlink_cut(point):
            if point == "unlink":
                raise RuntimeError("before_directory_sync")
        try:
            files.remove("derived/uncertain.json", **expected, failure_cut=unlink_cut)
        except RuntimeError:
            pass
        assert not uncertain.exists()
        refused(lambda: files.remove("derived/uncertain.json", **expected))
    # Root pathname replacement while old descriptor is alive refuses.
    alternate = root / "identity"
    alternate.mkdir(mode=0o700)
    with PrivateFiles(alternate) as files:
        alternate.rename(root / "old-identity")
        alternate.mkdir(mode=0o700)
        refused(lambda: files.check_root())
    return dict(independent_copy=True, file_directory_sync=True, destination_exclusive=True,
                hardlink_symlink_traversal_refused=True, absence_not_removal_authority=True,
                uncertain_copy_retained=True, root_replacement_refused=True,
                power_loss_tested=False)


def wal_drill(root):
    # Explicit isolated tooling context. Never use this observation to admit a
    # production target; exact loaded build is independently captured outside.
    with sqlite3.connect(":memory:") as memory:
        identity = memory.execute("SELECT sqlite_version(),sqlite_source_id()").fetchone()
    assert identity == ("3.51.3", SOURCE_ID), identity
    db = root / "fixture.sqlite"
    assert not db.exists()
    connection = sqlite3.connect(db, autocommit=sqlite3.LEGACY_TRANSACTION_CONTROL, isolation_level=None, timeout=30)
    try:
        assert connection.execute("PRAGMA journal_mode=WAL").fetchone() == ("wal",)
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA wal_autocheckpoint=0")
        connection.execute("CREATE TABLE evidence(id INTEGER PRIMARY KEY,value TEXT NOT NULL)")
        connection.execute("INSERT INTO evidence VALUES(1,'before')")
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        # Retain an actual stale main-file copy before a child commits to WAL.
        stale = root / "stale.sqlite"
        with stale.open("xb") as stream:
            stream.write(db.read_bytes())
            stream.flush()
            os.fsync(stream.fileno())
        program = "import os,sqlite3,sys; c=sqlite3.connect(sys.argv[1],isolation_level=None); c.execute('PRAGMA synchronous=FULL'); c.execute('PRAGMA wal_autocheckpoint=0'); c.execute('BEGIN IMMEDIATE'); c.execute(\"UPDATE evidence SET value='wal-committed'\"); c.execute('COMMIT'); os._exit(0)"
        child = subprocess.run([sys.executable, "-B", "-c", program, str(db)], close_fds=True, capture_output=True, timeout=5)
        assert child.returncode == 0 and (root / "fixture.sqlite-wal").stat().st_size > 0, child.stderr
        fresh = sqlite3.connect(db.as_uri() + "?mode=rw&cache=private", uri=True,
                               autocommit=sqlite3.LEGACY_TRANSACTION_CONTROL, isolation_level=None, timeout=30)
        try:
            for name, value in (("foreign_keys", 1), ("synchronous", 2), ("trusted_schema", 0),
                                ("busy_timeout", 30000), ("read_uncommitted", 0)):
                fresh.execute(f"PRAGMA {name}={value}")
                assert fresh.execute(f"PRAGMA {name}").fetchone() == (value,)
            assert fresh.execute("PRAGMA journal_mode").fetchone() == ("wal",)
            fresh.execute("BEGIN IMMEDIATE")
            assert fresh.execute("SELECT value FROM evidence").fetchone() == ("wal-committed",)
            assert fresh.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
            assert fresh.execute("PRAGMA foreign_key_check").fetchall() == []
            fresh.execute("ROLLBACK")
        finally:
            fresh.close()
        with sqlite3.connect(stale.as_uri() + "?mode=ro", uri=True) as old:
            assert old.execute("SELECT value FROM evidence").fetchone() == ("before",)
        program = "import os,sqlite3,sys; c=sqlite3.connect(sys.argv[1],isolation_level=None); c.execute('BEGIN IMMEDIATE'); c.execute(\"UPDATE evidence SET value='uncommitted'\"); os._exit(9)"
        child = subprocess.run([sys.executable, "-B", "-c", program, str(db)], close_fds=True, capture_output=True, timeout=5)
        assert child.returncode == 9
        assert connection.execute("SELECT value FROM evidence").fetchone() == ("wal-committed",)
    finally:
        connection.close()
    return dict(sqlite_version=identity[0], sqlite_source_id=identity[1], actual_child_wal_commit=True,
                fresh_normal_sees_wal=True, stale_main_is_not_authority=True,
                interrupted_transaction_not_adopted=True, pragma_readbacks=True,
                power_loss_tested=False, production_activated=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    options = parser.parse_args()
    root = Path(options.root)
    assert root.is_absolute() and root.is_dir() and not any(root.iterdir())
    assert os.name == "posix" and os.geteuid() != 0
    with PrivateFiles(root):
        pass
    result = dict(schema="geophysics.physical-native-drill/v1", uid=os.geteuid(),
                  python=sys.version, production_activated=False,
                  files=file_drill(root), lease=asyncio.run(lease_drill(root)), wal=wal_drill(root))
    loaded = sorted({line.split()[-1] for line in Path("/proc/self/maps").read_text().splitlines()
                     if line.split()[-1].startswith("/") and
                     (Path(line.split()[-1]).name == "libsqlite3.so.0" or
                      Path(line.split()[-1]).name.startswith("_sqlite3."))})
    result["loaded_sqlite_binaries"] = [dict(path=name, bytes=Path(name).stat().st_size,
                                             sha256=digest(Path(name).read_bytes())) for name in loaded]
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
