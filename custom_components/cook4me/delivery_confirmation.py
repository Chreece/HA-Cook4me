"""Bounded appliance confirmation, independent of the cloud write acknowledgement."""
from __future__ import annotations

import asyncio


CONFIRMATION_TIMEOUT = 90.0


def _confirmed(state, variant):
    return (isinstance(state, dict) and state.get("connected") is True
            and str(state.get("variantFunctionalId") or "").strip() == variant)


def _state_identity(state):
    # Ignore metadata-only enrichment, but never replace newer cooking evidence
    # or a disconnect with the result of a slower one-shot state request.
    return tuple(state.get(key) for key in
                 ("variantFunctionalId", "recipeFunctionalId", "phase", "status",
                  "eventDate", "cookingVersion", "connected"))


async def wait_for_recipe(bridge, variant_id, timeout=CONFIRMATION_TIMEOUT,
                          *, poll_interval=15.0, check_interval=0.5):
    """Observe live updates and periodically read state, without resending.

    All reads share one deadline. A live confirmation wins even while a read
    is slow; cancellation/deadline cleanup reaps the outstanding read task.
    Desired shadow values and cloud acceptance are never load evidence.
    """
    target = str(variant_id).strip()
    if not target:
        return False
    loop = asyncio.get_running_loop()
    deadline = loop.time() + max(0.0, float(timeout))
    next_read = loop.time() + poll_interval
    read_task = None
    read_identity = None
    try:
        while True:
            if _confirmed(bridge.data, target):
                return True
            if read_task is not None and read_task.done():
                try:
                    fresh = read_task.result()
                except Exception:
                    fresh = None
                read_task = None
                if _confirmed(fresh, target) and _state_identity(bridge.data) == read_identity:
                    bridge._publish(fresh)
                    return True
                next_read = loop.time() + poll_interval
            remaining = deadline - loop.time()
            if remaining <= 0:
                return False
            if read_task is None and loop.time() >= next_read:
                read_identity = _state_identity(bridge.data)
                read_task = asyncio.create_task(bridge._run_client_json(
                    "state", timeout=min(30.0, remaining)))
            await asyncio.sleep(min(check_interval, remaining))
    finally:
        if read_task is not None:
            if not read_task.done():
                read_task.cancel()
            await asyncio.gather(read_task, return_exceptions=True)
