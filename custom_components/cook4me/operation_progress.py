from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

EVENT_OPERATION_PROGRESS = "cook4me_operation_progress"


def publish_operation_progress(
    hass: HomeAssistant,
    operation_id: str | None,
    *,
    phase: str,
    message: str = "",
    completed: int | float | None = None,
    total: int | float | None = None,
    done: bool = False,
    error: str = "",
    waiting_count: int | None = None,
) -> None:
    """Publish evidence-based progress for one explicit client operation.

    Percent is emitted only when both completed and total are known. Callers
    must use an indeterminate phase when the upstream provider exposes no real
    completion measurement (for example while an AI provider is generating).
    """
    op_id = str(operation_id or "").strip()
    if not op_id:
        return
    payload: dict[str, Any] = {
        "operationId": op_id,
        "phase": str(phase or "work"),
        "message": str(message or ""),
        "done": bool(done),
        "error": str(error or ""),
    }
    if completed is not None:
        payload["completed"] = completed
    if total is not None:
        payload["total"] = total
    if completed is not None and total is not None:
        try:
            denominator = float(total)
            numerator = float(completed)
        except (TypeError, ValueError):
            denominator = 0.0
            numerator = 0.0
        if denominator > 0:
            payload["percent"] = max(0, min(100, round(numerator / denominator * 100)))
    if waiting_count is not None:
        payload["waitingCount"] = max(0, int(waiting_count))
    hass.bus.async_fire(EVENT_OPERATION_PROGRESS, payload)
