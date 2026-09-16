"""Serialize first access to each device's persistent store."""
import asyncio
from contextlib import asynccontextmanager


@asynccontextmanager
async def store_load_lock(bridge, name):
    locks = getattr(bridge, '_store_load_locks', None)
    if locks is None:
        locks = bridge._store_load_locks = {}
    lock = locks.setdefault(name, asyncio.Lock())
    async with lock:
        yield
