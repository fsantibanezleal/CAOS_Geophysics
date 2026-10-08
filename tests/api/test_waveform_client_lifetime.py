"""Real ordinary process/pipe/singleton lifetime; not root/native science proof."""
import asyncio
import os
from pathlib import Path
import sys

import pytest

from app.waveform_linux_worker import mandatory_helper_drain, _capture
from app.worker import _worker_lock


def native_python():
    return os.environ.get("M08_TEST_NATIVE_PYTHON",sys.executable)


@pytest.mark.parametrize("mutation",["normal","cancel","repeated","creation","overflow-out","overflow-err"])
def test_exact_helper_reap_eof_precede_singleton_release(tmp_path,mutation):
    async def run():
        output = "stdout" if mutation == "overflow-out" else "stderr"
        payload = "x" if mutation.startswith("overflow") else "bounded"
        count = 2*1024**2 if mutation.startswith("overflow") else len(payload)
        command = [native_python(),"-I","-B","-c",
            "import sys,time;from pathlib import Path;sys.stdin.buffer.read();deadline=time.monotonic()+4;"
            "exec('while not Path(\"allow-reap\").exists() and time.monotonic()<deadline: time.sleep(.01)');"
            f"sys.{output}.buffer.write(b'{payload}'*{count});sys.{output}.flush()"]
        released = asyncio.Event()
        adopting = asyncio.Event()
        readers = []
        processes = []
        async def spawn():
            process = await asyncio.create_subprocess_exec(*command,stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,cwd=tmp_path)
            processes.append(process)
            adopting.set()
            if mutation == "creation":
                await asyncio.sleep(.15)
            return process
        creation = asyncio.create_task(spawn())
        async def owner():
            with _worker_lock(tmp_path):
                try:
                    if mutation != "creation":
                        await asyncio.shield(creation)
                    await asyncio.sleep(.01)
                finally:
                    cancelled = await mandatory_helper_drain(creation,readers)
                    if cancelled:
                        raise asyncio.CancelledError()
            released.set()
        owner_task = asyncio.create_task(owner())
        await adopting.wait()
        if mutation in ("cancel","repeated","creation"):
            owner_task.cancel()
            await asyncio.sleep(.03)
            if mutation == "repeated":
                owner_task.cancel()
        # In a different interpreter, acquisition really fails until helper EOF.
        lock_path = str(Path(tmp_path)/".processing-worker.lock")
        peer = ("import sys;f=open(sys.argv[1],'r+b');"
                + ("import msvcrt;msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)"
                   if os.name == "nt" else "import fcntl;fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)"))
        async def lock_peer():
            p = await asyncio.create_subprocess_exec(native_python(),"-I","-B","-c",peer,lock_path,
                stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL)
            return await p.wait()
        assert await lock_peer() != 0
        assert not released.is_set()
        assert processes[0].returncode is None
        (tmp_path/"allow-reap").write_bytes(b"ordinary external test control")
        with pytest.raises(asyncio.CancelledError) if mutation in ("cancel","repeated","creation") else _no_error():
            await asyncio.wait_for(owner_task,5)
        assert processes[0].returncode == 0
        assert processes[0].stdout.at_eof() and processes[0].stderr.at_eof()
        assert all(reader.done() for reader in readers)
        assert await lock_peer() == 0
    asyncio.run(run())


def _no_error():
    from contextlib import nullcontext
    return nullcontext()


def test_parent_exit_does_not_release_lease_while_descendant_holds_pipe(tmp_path):
    async def run():
        descendant = ("from pathlib import Path;import time,sys;"
            "Path('descendant-ready').write_bytes(b'ready');deadline=time.monotonic()+4;"
            "exec('while not Path(\"allow-reap\").exists() and time.monotonic()<deadline: time.sleep(.01)');"
            "sys.stdout.write('retained pipe');sys.stdout.flush()")
        parent = ("import sys,subprocess;subprocess.Popen([sys.executable,'-I','-B','-c',"
                  +repr(descendant)+"],stdin=subprocess.DEVNULL,stdout=sys.stdout,stderr=sys.stderr)")
        readers = []
        process = None
        held = asyncio.Event()
        async def owner():
            nonlocal process
            with _worker_lock(tmp_path):
                spawn = asyncio.create_task(asyncio.create_subprocess_exec(native_python(),"-I","-B","-c",parent,
                    cwd=tmp_path,stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE))
                process = await asyncio.shield(spawn)
                held.set()
                await mandatory_helper_drain(spawn,readers)
        task = asyncio.create_task(owner())
        await held.wait()
        deadline = asyncio.get_running_loop().time()+3
        while not (tmp_path/"descendant-ready").exists() or process.returncode is None:
            assert asyncio.get_running_loop().time() < deadline
            await asyncio.sleep(.01)
        assert process.returncode == 0 and not task.done()
        assert not process.stdout.at_eof()
        peer = ("import sys;f=open(sys.argv[1],'r+b');"
                + ("import msvcrt;msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)"
                   if os.name == "nt" else "import fcntl;fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)"))
        p = await asyncio.create_subprocess_exec(native_python(),"-I","-B","-c",peer,
            str(tmp_path/".processing-worker.lock"),stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL)
        assert await p.wait() != 0
        task.cancel()
        (tmp_path/"allow-reap").write_bytes(b"ordinary external descendant barrier")
        await asyncio.wait_for(task,5)
        assert process.stdout.at_eof() and process.stderr.at_eof()
        assert all(reader.done() for reader in readers)
    asyncio.run(run())


def test_invalid_frame_signals_before_eof_but_keeps_draining():
    async def run():
        stream = asyncio.StreamReader()
        first = asyncio.get_running_loop().create_future()
        reader = asyncio.create_task(_capture(stream,65544,first))
        stream.feed_data(b'{"duplicate":1,"duplicate":2}\n')
        await asyncio.sleep(0)
        assert first.done() and isinstance(first.exception(),ValueError)
        assert not reader.done()
        stream.feed_data(b"x"*100000)
        stream.feed_eof()
        with pytest.raises(ValueError):
            await reader
        assert stream.at_eof()
    asyncio.run(run())
