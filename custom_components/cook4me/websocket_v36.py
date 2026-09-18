"""Run existing validated Cook4Me commands as cancellable UI jobs."""
import asyncio
import inspect

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.components.websocket_api.const import DOMAIN as WS_DOMAIN
from homeassistant.core import callback

from .const import DOMAIN
from .job_runtime import JobRegistry
from . import websocket as legacy

_JOB_ID = vol.All(str, vol.Length(min=1, max=160))


@websocket_api.websocket_command({vol.Required("type"): "cook4me/v36/job_run",
    vol.Required("job_id"): _JOB_ID, vol.Required("request"): dict})
@websocket_api.async_response
async def ws_job_run(hass, connection, msg):
    try:
        state = hass.data[DOMAIN]["ui_jobs"]
        command = state["commands"].get(msg["request"].get("type"))
        if command is None:
            connection.send_error(msg["id"], "job_unsupported", "Command has no cancellable handler")
            return
        # Use the original schema and coroutine: entry authorization and all other
        # command checks still run. The client cannot supply another response ID.
        schema, handler = command
        request = schema({**msg["request"], "id": msg["id"]})
        async with state["registry"].run(connection, msg["job_id"]):
            await handler(hass, connection, request)
    except asyncio.CancelledError:
        connection.send_error(msg["id"], "job_cancelled", "Job cancelled")
    except Exception as exc:
        legacy._send_error(connection, msg, exc)


@websocket_api.websocket_command({vol.Required("type"): "cook4me/v36/job_cancel",
    vol.Required("job_id"): _JOB_ID})
@websocket_api.async_response
async def ws_job_cancel(hass, connection, msg):
    try:
        count = hass.data[DOMAIN]["ui_jobs"]["registry"].cancel(connection, msg["job_id"])
        connection.send_result(msg["id"], {"cancelled": True, "requestsStopped": count})
    except Exception as exc:
        legacy._send_error(connection, msg, exc)


@callback
def async_register(hass):
    commands = {}
    # Reuse only commands already registered with HA, including their exact
    # schema. Never expose an unregistered/deprecated handler or another domain.
    for name, (command, schema) in hass.data.get(WS_DOMAIN, {}).items():
        if not name.startswith("cook4me/") or name.startswith("cook4me/v36/") or name.endswith("_subscribe"):
            continue
        handler = getattr(command, "__wrapped__", None)
        # Only unwrap async_response itself. An outer permission wrapper remains
        # unsupported and is sent through its original endpoint by the client.
        if callable(schema) and inspect.iscoroutinefunction(handler):
            commands[name] = (schema, handler)
    hass.data.setdefault(DOMAIN, {})["ui_jobs"] = {"registry": JobRegistry(), "commands": commands}
    websocket_api.async_register_command(hass, ws_job_run)
    websocket_api.async_register_command(hass, ws_job_cancel)
