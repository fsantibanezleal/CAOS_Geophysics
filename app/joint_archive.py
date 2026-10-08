"""Bounded ZIP response transport; no persistent export copy or numerical engine."""
import asyncio
from concurrent.futures import Future
import queue
import threading

from fastapi.responses import StreamingResponse


CHUNK = 1024 * 1024


class ExportStopped(Exception):
    """Only the cancelled private response, never a successful ZIP."""


class ArchivePipe:
    """One bounded producer, one queued chunk, owned total-byte admission."""

    def __init__(self, produce, *, byte_count, cap):
        if type(byte_count) is not int or type(cap) is not int or not 0 < byte_count <= cap:
            raise ValueError('joint_archive_whole_cap')
        self.produce = produce
        self.byte_count = byte_count
        self.position = 0
        self.queue = queue.Queue(maxsize=1)
        self.stop = threading.Event()
        self.done = Future()
        self.thread = None
        self.tail = None

    def start(self):
        if self.thread is not None:
            raise RuntimeError('joint_archive_already_started')
        self.thread = threading.Thread(target=self._run, name='joint-original-zip', daemon=True)
        self.thread.start()

    def _put(self, value):
        while not self.stop.is_set():
            try:
                self.queue.put(value, timeout=.05)
                return
            except queue.Full:
                pass
        raise ExportStopped('joint_archive_cancelled')

    def write(self, data):
        if self.stop.is_set():
            raise ExportStopped('joint_archive_cancelled')
        body = bytes(data)
        if len(body) > CHUNK or self.position + len(body) > self.byte_count:
            raise ValueError('joint_archive_whole_cap')
        if body:
            # Never release the final write (including ZIP's end record) until
            # the producer and its complete post-write predicates succeed.
            if self.tail is not None:
                self._put(self.tail)
            self.tail = body
            self.position += len(body)
        return len(body)

    def tell(self):
        return self.position

    def seek(self, *_):
        raise OSError('joint_archive_nonseekable')

    def flush(self):
        pass

    def _run(self):
        try:
            self.produce(self)
            if self.position != self.byte_count:
                raise ValueError('joint_archive_byte_count')
            if self.tail is not None:
                self._put(self.tail)
                self.tail = None
            self.done.set_result(None)
        except BaseException as error:
            self.tail = None
            self.done.set_exception(error)
        finally:
            # An ordinary consumer sees every queued byte before this sentinel.
            # On cancellation discard transport only, not stored private files.
            while True:
                try:
                    self.queue.put(None, timeout=.05)
                    break
                except queue.Full:
                    if self.stop.is_set():
                        try:
                            self.queue.get_nowait()
                        except queue.Empty:
                            pass

    def read(self):
        value = self.queue.get()
        if value is None:
            self.done.result()
        return value

    def join(self):
        if self.thread is not None:
            self.thread.join()  # No premature timeout-based guard release.


async def drain(operation):
    """Repeated cancellation cannot abandon an actual synchronous operation."""
    task = asyncio.create_task(asyncio.to_thread(operation))
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
        except BaseException:
            break
    if cancelled:
        # Retrieve the worker exception, while preserving caller cancellation.
        if not task.cancelled():
            task.exception()
        raise asyncio.CancelledError()
    return task.result()


class JointArchiveResponse(StreamingResponse):
    """Own producer lifetime across ASGI cancellation and streaming failures."""

    def __init__(self, pipe, *, job_id):
        self.pipe = pipe

        async def chunks():
            while True:
                chunk = await drain(pipe.read)
                if chunk is None:
                    return
                yield chunk

        super().__init__(chunks(), media_type='application/zip', headers={
            'Cache-Control': 'no-store', 'Vary': 'Cookie',
            'Content-Length': str(pipe.byte_count),
            'Content-Disposition': f'attachment; filename="joint-{job_id}.zip"'})

    async def __call__(self, scope, receive, send):
        try:
            self.pipe.start()
            await super().__call__(scope, receive, send)
        finally:
            self.pipe.stop.set()
            await drain(self.pipe.join)
