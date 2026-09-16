"""Cancellation scoped to the originating authenticated WebSocket connection."""
from __future__ import annotations

import asyncio
from collections import OrderedDict
from contextlib import asynccontextmanager
from time import monotonic


class JobRegistry:
    def __init__(self):
        self.jobs = OrderedDict()

    def _key(self, connection, job_id):
        if not getattr(connection, "user", None):
            raise ValueError("An authenticated connection is required")
        return (id(connection), connection.user.id, job_id)

    def _get(self, connection, job_id):
        now = monotonic()
        for key, state in list(self.jobs.items()):
            if not state["tasks"] and now - state["updated"] > 300:
                self.jobs.pop(key)
        key = self._key(connection, job_id)
        state = self.jobs.get(key)
        if state is None:
            # Bound idle records without evicting active work or cancellation tombstones.
            if len(self.jobs) >= 2048:
                for old, value in list(self.jobs.items()):
                    if not value["tasks"] and not value["cancelled"]:
                        self.jobs.pop(old)
                        break
                else:
                    raise ValueError("Too many jobs; retry shortly")
            state = {"connection": connection, "tasks": set(), "cancelled": False, "updated": now}
            self.jobs[key] = state
        state["updated"] = now
        return state

    @asynccontextmanager
    async def run(self, connection, job_id):
        state = self._get(connection, job_id)
        if state["cancelled"]:
            raise asyncio.CancelledError
        task = asyncio.current_task()
        state["tasks"].add(task)
        try:
            yield
        finally:
            state["tasks"].discard(task)
            state["updated"] = monotonic()

    def cancel(self, connection, job_id):
        state = self._get(connection, job_id)
        state["cancelled"] = True
        tasks = [task for task in state["tasks"] if not task.done()]
        for task in tasks:
            task.cancel()
        return len(tasks)
