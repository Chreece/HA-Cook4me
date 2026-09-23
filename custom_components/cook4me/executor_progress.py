"""Bounded executor progress and cooperative cancellation of read-only work."""
from __future__ import annotations

import asyncio
from functools import partial
from threading import Event
from time import monotonic


class WorkStopped(Exception):
    """A read-only worker reached a cancellation checkpoint."""


class ExecutorProgress:
    """Never fire HA events from a worker or leave cancelled CPU work running.

    The callback is only invoked on the creating event loop. Checkpoints always
    check cancellation, even when reporting is absent or a notification is
    throttled. Normal stage boundaries and the last count are not throttled.
    """

    def __init__(self, callback=None, *, interval=0.25):
        self._loop = asyncio.get_running_loop()
        self._callback = callback
        self._stopped = Event()
        self._closed = False
        self._interval = interval
        self._key = None
        self._last = 0.0

    def __call__(self, phase, **values):
        if self._stopped.is_set():
            raise WorkStopped()
        if not self._callback or self._closed:
            return
        now = monotonic()
        key = (phase, values.get('total'))
        done, total = values.get('completed'), values.get('total')
        final = (isinstance(done, (int, float)) and
                 isinstance(total, (int, float)) and total > 0 and done >= total)
        if key != self._key or final or now - self._last >= self._interval:
            self._key, self._last = key, now
            self._loop.call_soon_threadsafe(self._deliver, phase, values)

    def _deliver(self, phase, values):
        if not self._closed and not self._stopped.is_set():
            self._callback(phase, **values)

    def close(self):
        self._closed = True

    async def run(self, hass, function, *args):
        """Keep the caller's serialization lock until its worker has stopped."""
        work = asyncio.ensure_future(hass.async_add_executor_job(partial(function, *args)))
        try:
            return await asyncio.shield(work)
        except asyncio.CancelledError:
            self._stopped.set()
            # Cancelling an asyncio waiter does not stop its executor thread.
            # Drain it before releasing the weekly mutation lane. Repeated
            # cancellation must not release that lane early either.
            while not work.done():
                try:
                    await asyncio.shield(work)
                except asyncio.CancelledError:
                    continue
                except Exception:
                    break
            if not work.cancelled():
                work.exception()  # Consume checkpoint/provider errors on cancel.
            raise
        finally:
            self.close()
