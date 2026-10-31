"""Original same-task predicates and actual SQL accounting, portable lock IO."""

import asyncio
from contextlib import asynccontextmanager
import os
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from app.physical_assembly import run_forever_participating
from app.physical_leases import WriterLeases, _held
from app.physical_participation import WorkerExclusion, _worker_held
from app.processing_storage import account_derived_usage
from tests.api.test_physical_assembly import bound_fixture
from tests.api.test_physical_deleted_inventory import case
from tests.api.test_physical_roots import root_case as root_case
from tests.api.test_physical_successor import successor as successor
from tests.api.test_physical_wire import survey as survey


def strict_transport(physical):
    """Only descriptor IO is a fixture. Both native authority predicates run."""
    leases, worker = physical.leases, physical.worker
    trace = []
    leases.pid = os.getpid()

    def lease_check(fd):
        assert fd == 101

    def worker_check(fd):
        assert fd == 102

    leases._check, worker._check = lease_check, worker_check
    leases.require_held = WriterLeases.require_held.__get__(leases)
    worker.require_held = WorkerExclusion.require_held.__get__(worker)
    worker.require_processing_held = WorkerExclusion.require_processing_held.__get__(worker)

    @asynccontextmanager
    async def acquire(*, exclusive=False):
        task = asyncio.current_task()
        assert not leases.held
        leases.held = True
        token = _held.set((task, leases, 101, exclusive))
        trace.append(('lease-enter', task, exclusive))
        try:
            yield
        finally:
            leases.require_held(exclusive=exclusive)
            trace.append(('lease-exit', task, exclusive))
            _held.reset(token)
            leases.held = False

    @asynccontextmanager
    async def singleton(*, exclusive=False):
        leases.require_held(exclusive=exclusive)
        task = asyncio.current_task()
        assert not worker.held
        worker.held = True
        token = _worker_held.set((task, worker, 102))
        trace.append(('worker-enter', task, exclusive))
        try:
            yield
        finally:
            worker.require_processing_held()
            trace.append(('worker-exit', task, exclusive))
            _worker_held.reset(token)
            worker.held = False

    leases.acquire = acquire
    worker.acquire_processing = singleton
    worker.acquire = lambda: singleton(exclusive=True)
    return trace


def test_drained_cycle_owns_native_predicates_and_real_accounting_through_repeated_stop(root_case, monkeypatch):
    case(root_case)
    settings, physical = bound_fixture(root_case, monkeypatch)
    trace = strict_transport(physical)

    async def run():
        entered, release = asyncio.Event(), asyncio.Event()
        cycle_tasks = []
        charges = []

        async def claim(sessions, identifier):
            physical.leases.require_held()
            physical.worker.require_processing_held()
            cycle_tasks.append(asyncio.current_task())
            return SimpleNamespace(id='only-lifetime-transport')

        async def executor(settings, sessions, job, interval):
            physical.leases.require_held()
            physical.worker.require_processing_held()
            async with sessions() as session:
                await session.execute(text('BEGIN IMMEDIATE'))
                # No accounting stub: bound session -> derived_charge ->
                # actual native WAL transaction -> exact stored copies/debt.
                charges.append(await account_derived_usage(session, root_case[2]['owner_id']))
                await session.rollback()
            entered.set()
            await release.wait()  # explicit EOF/final-cleanup boundary transport
            physical.leases.require_held()
            physical.worker.require_processing_held()
            trace.append(('cleanup', asyncio.current_task(), False))

        monkeypatch.setattr('app.worker._claim', claim)
        monkeypatch.setattr('app.worker._execute', executor)
        parent = asyncio.create_task(run_forever_participating(settings, physical, poll_interval=.01))
        try:
            await asyncio.wait_for(entered.wait(), 10)
            assert cycle_tasks and cycle_tasks[0] is not parent
            parent.cancel()
            await asyncio.sleep(.01)
            parent.cancel()
            await asyncio.sleep(.01)
            assert not parent.done() and physical.leases.held and physical.worker.held
        finally:
            release.set()
        with pytest.raises(asyncio.CancelledError):
            await parent
        assert charges == [len(root_case[4]) + 2*len(root_case[3])]
        cycle = cycle_tasks[0]
        events = [kind for kind, task, exclusive in trace if task is cycle]
        assert events == ['lease-enter', 'worker-enter', 'cleanup', 'worker-exit', 'lease-exit']
        assert not physical.leases.held and not physical.worker.held
    asyncio.run(run())


def test_inherited_context_never_grants_processing_or_original_ex_authority(root_case, monkeypatch):
    settings, physical = bound_fixture(root_case, monkeypatch)
    strict_transport(physical)

    async def run():
        async with physical.leases.acquire():
            async with physical.worker.acquire_processing():
                physical.leases.require_held()
                physical.worker.require_processing_held()
                with pytest.raises(ValueError, match='physical_writer_lease_required'):
                    physical.worker.require_held()  # unchanged EX requirement
                async def inherited():
                    for check in (physical.leases.require_held, physical.worker.require_processing_held,
                                  physical.worker.require_held):
                        with pytest.raises(ValueError, match='physical_writer_lease_required'):
                            check()
                await asyncio.create_task(inherited())
        assert not physical.leases.held and not physical.worker.held
    asyncio.run(run())
