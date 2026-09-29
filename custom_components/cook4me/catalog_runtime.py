"""Non-blocking lifecycle for Cook4Me's large immutable release catalog."""
from __future__ import annotations

import asyncio
import logging
from time import monotonic
from typing import Any

from .catalog_storage import prepare_release_catalog_storage
from .const import DOMAIN
from .release_catalog import (
    async_warm_release_catalog,
    release_catalog_ready,
    set_release_catalog_path,
)
from .stock_coverage import warm_stock_catalog

_LOGGER = logging.getLogger(__name__)

DATA_CATALOG_WARM_TASK = "catalog_warm_task"
DATA_CATALOG_WARM_STATE = "catalog_warm_state"


def _domain_data(hass: Any) -> dict[str, Any]:
    return hass.data.setdefault(DOMAIN, {})


async def _async_warm_catalog_runtime(hass: Any) -> bool:
    """Prepare immutable catalog/index caches without holding HA domain setup open."""
    data = _domain_data(hass)
    state = data.setdefault(DATA_CATALOG_WARM_STATE, {})
    state.clear()
    state.update(status="warming", started=monotonic())
    total_started = monotonic()

    try:
        storage_started = monotonic()
        config_dir = getattr(getattr(hass, "config", None), "config_dir", None)
        if config_dir:
            catalog_path = await hass.async_add_executor_job(
                prepare_release_catalog_storage, config_dir
            )
            set_release_catalog_path(catalog_path)
        storage_seconds = monotonic() - storage_started

        catalog_started = monotonic()
        payload = await async_warm_release_catalog(hass)
        catalog_seconds = monotonic() - catalog_started

        stock_started = monotonic()
        stock_count = await hass.async_add_executor_job(
            warm_stock_catalog, payload
        )
        stock_seconds = monotonic() - stock_started

        ancillary_started = monotonic()
        from .price_benchmarks import warm_price_benchmarks
        from .price_measurements import _densities, _portions
        from .price_snapshot import _load as load_price_snapshot

        await asyncio.gather(
            hass.async_add_executor_job(_portions),
            hass.async_add_executor_job(_densities),
            hass.async_add_executor_job(load_price_snapshot),
            hass.async_add_executor_job(warm_price_benchmarks),
        )
        ancillary_seconds = monotonic() - ancillary_started
        total_seconds = monotonic() - total_started

        ready = release_catalog_ready()
        state.update(
            status="ready" if ready else "unavailable",
            ready=ready,
            storageSeconds=storage_seconds,
            catalogSeconds=catalog_seconds,
            stockSeconds=stock_seconds,
            ancillarySeconds=ancillary_seconds,
            totalSeconds=total_seconds,
            stockIdentityCount=stock_count,
        )
        _LOGGER.info(
            "Cook4Me background catalog warm-up finished in %.2f seconds "
            "(storage %.2fs, catalog %.2fs, stock %.2fs, ancillary %.2fs; %d stock identities)",
            total_seconds,
            storage_seconds,
            catalog_seconds,
            stock_seconds,
            ancillary_seconds,
            stock_count,
        )
        return ready
    except asyncio.CancelledError:
        state.update(status="cancelled", ready=False)
        raise
    except Exception as exc:
        state.update(
            status="failed",
            ready=False,
            error=type(exc).__name__,
            totalSeconds=monotonic() - total_started,
        )
        _LOGGER.exception("Cook4Me background catalog warm-up failed")
        return False


def start_catalog_warmup(hass: Any):
    """Start one shared warm-up task and return it without awaiting it."""
    data = _domain_data(hass)
    task = data.get(DATA_CATALOG_WARM_TASK)
    if task is not None and not task.done():
        return task

    state = data.get(DATA_CATALOG_WARM_STATE)
    if (
        isinstance(state, dict)
        and state.get("status") == "ready"
        and release_catalog_ready()
    ):
        return task

    task = hass.async_create_background_task(
        _async_warm_catalog_runtime(hass),
        "Cook4Me catalog warm-up",
    )
    data[DATA_CATALOG_WARM_TASK] = task
    return task


async def async_ensure_catalog_ready(hass: Any) -> bool:
    """Await the shared warm-up for a request without cancelling it on disconnect."""
    data = _domain_data(hass)
    state = data.get(DATA_CATALOG_WARM_STATE)
    if (
        isinstance(state, dict)
        and state.get("status") == "ready"
        and release_catalog_ready()
    ):
        return True

    task = start_catalog_warmup(hass)
    if task is None:
        return release_catalog_ready()

    try:
        return bool(await asyncio.shield(task))
    except asyncio.CancelledError:
        raise
    except Exception:
        _LOGGER.exception("Cook4Me request could not await catalog warm-up")
        return False


def catalog_warm_state(hass: Any) -> dict[str, Any]:
    """Return small diagnostic timing/status data, never catalog or user data."""
    state = _domain_data(hass).get(DATA_CATALOG_WARM_STATE)
    return dict(state) if isinstance(state, dict) else {"status": "not_started"}
