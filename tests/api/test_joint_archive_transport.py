"""Real ZIP/backpressure/ASGI cancellation, without SQL or a scientific fit."""
import asyncio
import hashlib
import io
import threading
import zipfile

import pytest

from app.joint_archive import ArchivePipe, CHUNK, JointArchiveResponse


def test_actual_stored_zip_stream_exact_count_and_backpressure():
    body = bytes(range(256)) * 8192
    def produce(output):
        with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_STORED) as archive:
            with archive.open('calibration/original.npy', 'w', force_zip64=True) as member:
                member.write(body[:CHUNK]); member.write(body[CHUNK:])
    count = len(body) + 120 + 2 * len('calibration/original.npy') + 22
    pipe = ArchivePipe(produce, byte_count=count, cap=count)
    pipe.start()
    try:
        actual = bytearray()
        while (chunk := pipe.read()) is not None:
            assert len(chunk) <= CHUNK and pipe.queue.qsize() <= 1
            actual.extend(chunk)
        assert len(actual) == count
        with zipfile.ZipFile(io.BytesIO(actual)) as archive:
            assert archive.namelist() == ['calibration/original.npy']
            assert hashlib.sha256(archive.read(archive.namelist()[0])).digest() == hashlib.sha256(body).digest()
    finally:
        pipe.stop.set(); pipe.join()
    assert not pipe.thread.is_alive()


@pytest.mark.parametrize('count,cap', [(0, 1), (2, 1), (True, 1)])
def test_cap_refusal_precedes_actual_producer(count, cap):
    with pytest.raises(ValueError, match='whole_cap'):
        ArchivePipe(lambda _: pytest.fail('producer must not start'), byte_count=count, cap=cap)


def test_producer_exception_propagates_and_drains():
    def produce(output):
        output.write(b'original')
        raise RuntimeError('actual_writer_refusal')
    pipe = ArchivePipe(produce, byte_count=8, cap=8); pipe.start()
    try:
        with pytest.raises(RuntimeError, match='actual_writer_refusal'):
            pipe.read()
    finally:
        pipe.stop.set(); pipe.join()
    assert not pipe.thread.is_alive()


def test_post_zip_verification_failure_withholds_the_actual_end_record():
    def produce(output):
        with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_STORED) as archive:
            archive.writestr('original.json', b'original private bytes')
        raise RuntimeError('final_original_inventory_changed')
    pipe = ArchivePipe(produce, byte_count=1024, cap=1024); pipe.start()
    actual = bytearray()
    try:
        with pytest.raises(RuntimeError, match='final_original_inventory_changed'):
            while (chunk := pipe.read()) is not None:
                actual.extend(chunk)
        assert b'PK\x05\x06' not in actual
        with pytest.raises(zipfile.BadZipFile):
            zipfile.ZipFile(io.BytesIO(actual))
    finally:
        pipe.stop.set(); pipe.join()


def test_repeated_asgi_cancellation_does_not_release_a_held_producer():
    entered, release, exited = threading.Event(), threading.Event(), threading.Event()
    def produce(output):
        output.write(b'x'); output.write(b'y'); entered.set(); assert release.wait(5); exited.set()
        output.write(b'z')
    pipe = ArchivePipe(produce, byte_count=3, cap=3)
    response = JointArchiveResponse(pipe, job_id='fixture')
    assert pipe.thread is None  # Constructing a response acquires no producer.
    async def execute():
        sending = asyncio.Event()
        async def send(message):
            if message['type'] == 'http.response.body' and message.get('body'):
                sending.set(); await asyncio.Event().wait()
        async def receive():
            await asyncio.Event().wait()
        task = asyncio.create_task(response({'type': 'http', 'asgi': {'spec_version': '2.4'}}, receive, send))
        await asyncio.wait_for(sending.wait(), 5)
        assert entered.is_set()
        task.cancel(); await asyncio.sleep(.02); task.cancel(); await asyncio.sleep(.02)
        assert not task.done() and not exited.is_set()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert exited.is_set() and not pipe.thread.is_alive()
    asyncio.run(execute())


def test_actual_asgi_disconnect_drains_before_response_return():
    entered, release, exited = threading.Event(), threading.Event(), threading.Event()
    def produce(output):
        output.write(b'x'); output.write(b'y'); entered.set(); assert release.wait(5)
        exited.set(); output.write(b'z')
    pipe = ArchivePipe(produce, byte_count=3, cap=3)
    response = JointArchiveResponse(pipe, job_id='fixture')
    async def execute():
        sending = asyncio.Event()
        async def send(message):
            if message['type'] == 'http.response.body' and message.get('body'):
                sending.set(); await asyncio.Event().wait()
        async def receive():
            await sending.wait()
            return {'type': 'http.disconnect'}
        task = asyncio.create_task(response({'type': 'http', 'asgi': {'spec_version': '2.3'}}, receive, send))
        await asyncio.wait_for(sending.wait(), 5)
        assert entered.is_set()
        await asyncio.sleep(.05)
        assert not task.done() and not exited.is_set()
        release.set(); await asyncio.wait_for(task, 5)
        assert exited.is_set() and not pipe.thread.is_alive()
    asyncio.run(execute())


@pytest.mark.parametrize('actual,count', [(b'too large', 1), (b'x', 2)])
def test_actual_transport_overrun_and_underrun_never_release_final_bytes(actual, count):
    pipe = ArchivePipe(lambda output: output.write(actual), byte_count=count, cap=count); pipe.start()
    try:
        with pytest.raises(ValueError, match='whole_cap|byte_count'):
            pipe.read()
    finally:
        pipe.stop.set(); pipe.join()
    assert not pipe.thread.is_alive()
