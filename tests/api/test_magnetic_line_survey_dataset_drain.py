"""Deterministic running-thread drain controls, not scientific/host receipts."""
import asyncio
import threading

import pytest

from app import magnetic_line_survey_dataset as dataset


class BoundedOperation:
    def __init__(self,action):
        self.started=threading.Event();self.release=threading.Event()
        self.finished=threading.Event();self.action=action

    def run(self,*args):
        self.started.set()
        try:
            assert self.release.wait(3),'bounded test operation was not released'
            return self.action()
        finally:
            self.finished.set()


async def started(operation):
    assert await asyncio.to_thread(operation.started.wait,2)


@pytest.mark.parametrize('marker_failure',[False,True])
def test_repeated_cancel_waits_for_actual_thread_and_retains_once(tmp_path,monkeypatch,marker_failure):
    token=object();operation=BoundedOperation(lambda:token)
    marker_done=threading.Event();original=dataset._publish_cancel

    def marker(root):
        try:
            if marker_failure:raise OSError('independent marker publication failure')
            original(root)
        finally:marker_done.set()

    monkeypatch.setattr(dataset,'_publish_cancel',marker)

    class Controller:
        run=operation.run

    async def scenario():
        receipts=[]
        owner=asyncio.create_task(dataset._run_phase(Controller(),None,None,tmp_path,{},receipts))
        await started(operation)
        owner.cancel()
        assert await asyncio.to_thread(marker_done.wait,2)
        for _ in range(3):
            owner.cancel();await asyncio.sleep(0)
            assert not owner.done() and not operation.finished.is_set() and receipts==[]
        operation.release.set()
        with pytest.raises(asyncio.CancelledError) as failure:await owner
        assert operation.finished.is_set() and receipts==[token]
        if marker_failure:
            assert isinstance(failure.value.__cause__,OSError)
            assert not (tmp_path/'cancel.request').exists()
        else:
            assert (tmp_path/'cancel.request').read_bytes()==b'm03-owner-cancel/1\n'
            assert not (tmp_path/'cancel.request.pending').exists()

    asyncio.run(scenario())


def test_uncancelled_phase_retains_exact_thread_value_once(tmp_path):
    token=object();operation=BoundedOperation(lambda:token)

    class Controller:
        run=operation.run

    async def scenario():
        receipts=[]
        owner=asyncio.create_task(dataset._run_phase(Controller(),None,None,tmp_path,{},receipts))
        await started(operation);operation.release.set()
        assert await owner is token and receipts==[token] and operation.finished.is_set()
        assert not (tmp_path/'cancel.request').exists()

    asyncio.run(scenario())


def test_settlement_preserves_actual_thread_exception():
    def fail():raise ValueError('actual bounded-operation exception')
    operation=BoundedOperation(fail)

    async def scenario():
        work=asyncio.create_task(asyncio.to_thread(operation.run))
        owner=asyncio.create_task(dataset._settle(work))
        await started(operation);owner.cancel();await asyncio.sleep(0)
        assert not owner.done();operation.release.set()
        with pytest.raises(ValueError,match='actual bounded-operation exception'):await owner
        assert operation.finished.is_set()

    asyncio.run(scenario())


def test_repeated_cancel_cannot_skip_actual_persistence_settlement(tmp_path):
    path=tmp_path/'durable-debt';operation=BoundedOperation(lambda:dataset._write(path,b'charged\n'))

    async def scenario():
        work=asyncio.create_task(asyncio.to_thread(operation.run))
        owner=asyncio.create_task(dataset._settle(work))
        await started(operation)
        for _ in range(3):
            owner.cancel();await asyncio.sleep(0)
            assert not owner.done() and not path.exists()
        operation.release.set();assert await owner is None
        assert operation.finished.is_set() and path.read_bytes()==b'charged\n'

    asyncio.run(scenario())


def test_cancelled_operation_is_not_looped_or_called_a_receipt():
    async def scenario():
        work=asyncio.create_task(asyncio.sleep(1));work.cancel()
        with pytest.raises(asyncio.CancelledError):await dataset._settle(work)
        assert work.cancelled()

    asyncio.run(scenario())
