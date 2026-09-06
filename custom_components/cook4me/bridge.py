from __future__ import annotations

import asyncio
import json
import logging
import os
import pathlib
import sys
import time
from typing import Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady, HomeAssistantError

from .recipe_hub import Cook4MeRecipeHub

from .const import (
    CONF_APP_VERSION, CONF_COUNTRY, CONF_DEVICE_UUID, CONF_EMAIL, CONF_LANGUAGE,
    CONF_PASSWORD, DEFAULT_APP_VERSION, DEFAULT_COUNTRY, DEFAULT_LANGUAGE,
)

_LOGGER = logging.getLogger(__name__)

class Cook4MeInvalidAuth(ConfigEntryAuthFailed):
    pass

class Cook4MeCloudUnavailable(ConfigEntryNotReady):
    pass

class Cook4MeDiscoveryError(HomeAssistantError):
    pass

class Cook4MeInternalError(HomeAssistantError):
    pass

class Cook4MeBridge:
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.data: dict[str, Any] = {}
        self._listeners: list[Callable[[], None]] = []
        self._task: asyncio.Task | None = None
        self._proc: asyncio.subprocess.Process | None = None
        self._stopping = False
        self._first_state = asyncio.Event()
        self._recipe_cache: dict[str, dict[str, Any]] = {}
        self._recipe_metadata_task: asyncio.Task | None = None
        self._recipe_metadata_variant: str | None = None
        self.recipe_hub = Cook4MeRecipeHub(hass, entry.entry_id)
        self._search_cache: dict[tuple[str, int, int, int], tuple[float, dict[str, Any]]] = {}

    @property
    def available(self) -> bool:
        return self.data.get("connected") is True

    @property
    def device_uuid(self) -> str:
        return str(self.entry.data[CONF_DEVICE_UUID])

    @property
    def storage_home(self) -> pathlib.Path:
        return pathlib.Path(self.hass.config.path(".storage", "cook4me", self.entry.entry_id))

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        self.storage_home.mkdir(parents=True, exist_ok=True)
        env["HOME"] = str(self.storage_home)
        env["COOK4ME_EMAIL"] = str(self.entry.data[CONF_EMAIL])
        env["COOK4ME_PASSWORD"] = str(self.entry.data[CONF_PASSWORD])
        env["PYTHONUNBUFFERED"] = "1"
        return env

    def _base_cmd(self) -> list[str]:
        vendor = pathlib.Path(__file__).parent / "vendor"
        return [
            sys.executable, "-u", str(vendor / "cook4me_auto.py"),
            "--country", str(self.entry.data.get(CONF_COUNTRY, DEFAULT_COUNTRY)),
            "--language", str(self.entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)),
            "--app-version", str(self.entry.data.get(CONF_APP_VERSION, DEFAULT_APP_VERSION)),
            "--device-uuid", self.device_uuid,
            "--json-lines",
        ]

    async def async_start(self) -> None:
        await self.recipe_hub.async_load()
        self._stopping = False
        self._task = self.hass.async_create_background_task(self._run_forever(), "cook4me_mqtt")
        try:
            await asyncio.wait_for(self._first_state.wait(), timeout=75)
        except TimeoutError as exc:
            if self._task.done():
                err = self._task.exception()
                if isinstance(err, ConfigEntryAuthFailed):
                    raise err
                raise ConfigEntryNotReady(str(err or "Cook4Me connection failed")) from exc
            raise ConfigEntryNotReady("Timed out waiting for initial Cook4Me state") from exc

    async def async_stop(self) -> None:
        self._stopping = True
        if self._proc and self._proc.returncode is None:
            self._proc.terminate()
            try:
                await asyncio.wait_for(self._proc.wait(), 10)
            except TimeoutError:
                self._proc.kill()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(listener)
        def remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)
        return remove

    def _apply_recipe_metadata(self) -> None:
        variant = self.data.get("variantFunctionalId")
        if not variant:
            return
        meta = self._recipe_cache.get(str(variant))
        if not isinstance(meta, dict):
            return
        steps = meta.get("steps") if isinstance(meta.get("steps"), list) else []
        self.data["recipeStepCount"] = meta.get("stepCount", len(steps))
        if meta.get("groupingFunctionalId"):
            self.data["groupingFunctionalId"] = meta.get("groupingFunctionalId")
        if meta.get("ingredients") is not None:
            self.data["recipeIngredients"] = meta.get("ingredients")
        if meta.get("excludedFoods") is not None:
            self.data["recipeExcludedFoods"] = meta.get("excludedFoods")
        if meta.get("durations") is not None:
            self.data["recipeDurations"] = meta.get("durations")
        if meta.get("yield") is not None:
            self.data["recipeYield"] = meta.get("yield")
        if meta.get("cover"):
            self.data["recipeImage"] = meta.get("cover")

        current_id = str(self.data.get("stepFunctionalId") or "")
        current_index = self.data.get("stepIndex")
        current_pos = None
        for pos, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            if current_id and str(step.get("functionalId") or "") == current_id:
                current_pos = pos
                break
        if current_pos is None and current_index is not None:
            for pos, step in enumerate(steps):
                if isinstance(step, dict) and step.get("stepIndex") == current_index:
                    current_pos = pos
                    break
        if current_pos is None:
            return
        current = steps[current_pos]
        self.data["currentInstruction"] = current.get("instruction")
        self.data["currentInstructions"] = current.get("instructions") or []
        if current_pos + 1 < len(steps):
            nxt = steps[current_pos + 1]
            if isinstance(nxt, dict):
                self.data["nextInstruction"] = nxt.get("instruction")
                self.data["nextStepFunctionalId"] = nxt.get("functionalId")

    def _maybe_schedule_recipe_metadata(self) -> None:
        variant = self.data.get("variantFunctionalId")
        recipe = self.data.get("recipeFunctionalId")
        if not variant or not recipe:
            return
        variant = str(variant)
        if variant in self._recipe_cache:
            return
        if self._recipe_metadata_task and not self._recipe_metadata_task.done() and self._recipe_metadata_variant == variant:
            return
        self._recipe_metadata_variant = variant
        self._recipe_metadata_task = self.hass.async_create_background_task(
            self._async_fetch_recipe_metadata(str(recipe), variant),
            f"cook4me_recipe_metadata_{variant}",
        )

    async def _async_fetch_recipe_metadata(self, recipe_id: str, variant_id: str) -> None:
        vendor = pathlib.Path(__file__).parent / "vendor"
        proc = await asyncio.create_subprocess_exec(
            *self._base_cmd(), "recipe-metadata", recipe_id, variant_id,
            cwd=str(vendor), env=self._env(),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        out, err = await proc.communicate()
        if proc.returncode:
            msg = err.decode("utf-8", "replace")[-1200:].strip()
            _LOGGER.warning("Cook4Me recipe metadata unavailable for variant %s: %s", variant_id, msg or f"client exit {proc.returncode}")
            return
        meta = None
        for line in reversed(out.decode("utf-8", "replace").splitlines()):
            if not line.startswith("{"):
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and isinstance(obj.get("steps"), list):
                meta = obj
                break
        if meta is None:
            _LOGGER.warning("Cook4Me recipe metadata returned no parseable steps for variant %s", variant_id)
            return
        self._recipe_cache[variant_id] = meta
        # Only enrich the live state if the same recipe is still active.
        if str(self.data.get("variantFunctionalId") or "") == variant_id:
            self._apply_recipe_metadata()
            for listener in list(self._listeners):
                listener()
        _LOGGER.debug("Cook4Me recipe metadata loaded for variant %s (%s steps)", variant_id, meta.get("stepCount"))

    @callback
    def _publish(self, payload: dict[str, Any]) -> None:
        self.data = payload
        self._apply_recipe_metadata()
        self._maybe_schedule_recipe_metadata()
        self._first_state.set()
        for listener in list(self._listeners):
            listener()

    async def _run_forever(self) -> None:
        failures = 0
        while not self._stopping:
            vendor = pathlib.Path(__file__).parent / "vendor"
            self._proc = await asyncio.create_subprocess_exec(
                *self._base_cmd(), "watch-state",
                cwd=str(vendor), env=self._env(),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            assert self._proc.stdout and self._proc.stderr
            stderr_task = self.hass.async_create_background_task(self._drain_stderr(self._proc.stderr), "cook4me_stderr")
            got_state = False
            try:
                while line := await self._proc.stdout.readline():
                    text = line.decode("utf-8", "replace").strip()
                    if not text.startswith("{"):
                        continue
                    try:
                        obj = json.loads(text)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(obj, dict):
                        got_state = True
                        failures = 0
                        self._publish(obj)
                rc = await self._proc.wait()
            finally:
                stderr_task.cancel()
            if self._stopping:
                return
            failures += 1
            if not got_state and failures >= 2:
                raise ConfigEntryNotReady(f"Cook4Me watcher exited repeatedly (rc={rc})")
            await asyncio.sleep(min(30, failures * 3))

    async def _drain_stderr(self, stream: asyncio.StreamReader) -> None:
        while line := await stream.readline():
            text = line.decode("utf-8", "replace").strip()
            if text:
                _LOGGER.debug("Cook4Me client: %s", text)

    async def _run_client_json(self, *args: str, timeout: float = 90) -> dict[str, Any]:
        vendor = pathlib.Path(__file__).parent / "vendor"
        proc = await asyncio.create_subprocess_exec(
            *self._base_cmd(), *[str(x) for x in args],
            cwd=str(vendor), env=self._env(),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except TimeoutError as exc:
            proc.kill()
            await proc.wait()
            raise HomeAssistantError(f"Cook4Me client timed out while running {args[0] if args else 'command'}") from exc
        if proc.returncode:
            message = err.decode("utf-8", "replace")[-1600:].strip()
            raise HomeAssistantError(message or f"Cook4Me client exited with code {proc.returncode}")
        for line in reversed(out.decode("utf-8", "replace").splitlines()):
            if not line.startswith("{"):
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                return obj
        raise HomeAssistantError("Cook4Me client returned no JSON result")

    @property
    def loaded_recipe(self) -> dict[str, Any] | None:
        recipe_id = self.data.get("recipeFunctionalId")
        title = self.data.get("recipeTitle")
        if not recipe_id and not title:
            return None
        return {
            "title": title,
            "groupingFunctionalId": recipe_id,
            "recipeFunctionalId": self.data.get("variantFunctionalId"),
            "status": self.data.get("status"),
        }

    @property
    def can_accept_recipe(self) -> bool:
        return self.available and self.loaded_recipe is None

    async def async_recipe_detail(self, variant_id: str, *, refresh: bool = False) -> dict[str, Any]:
        variant_id = str(variant_id).strip()
        if not variant_id:
            raise HomeAssistantError("Recipe variant ID is required")
        if not refresh and variant_id in self._recipe_cache:
            return dict(self._recipe_cache[variant_id])
        meta = await self._run_client_json("recipe-metadata", "", variant_id, timeout=60)
        self._recipe_cache[variant_id] = meta
        return dict(meta)

    async def async_search_recipes(
        self, query: str = "", *, page: int = 0, size: int = 20, max_details: int = 20,
        refresh: bool = False,
    ) -> dict[str, Any]:
        query = str(query or "").strip()
        page = max(0, int(page)); size = max(1, min(int(size), 50)); max_details = max(0, min(int(max_details), 50))
        cache_key = (query.casefold(), page, size, max_details)
        cached = self._search_cache.get(cache_key)
        if not refresh and cached and time.monotonic() - cached[0] < 900:
            result = json.loads(json.dumps(cached[1]))
        else:
            result = await self._run_client_json(
                "search-recipes", query, "--page", str(page), "--size", str(size),
                "--max-details", str(max_details), timeout=150,
            )
            self._search_cache[cache_key] = (time.monotonic(), result)
        items = []
        for item in result.get("items") or []:
            if not isinstance(item, dict):
                continue
            variant = str(item.get("searchVariantId") or item.get("variantFunctionalId") or "")
            if variant and item.get("steps") is not None:
                self._recipe_cache[variant] = item
            annotated = self.recipe_hub.annotate(item)
            annotated["sendable"] = bool(item.get("groupingFunctionalId") and item.get("recipeFunctionalId"))
            annotated["deviceCanAccept"] = self.can_accept_recipe
            items.append(annotated)
        result = dict(result)
        result["items"] = items
        result["deviceCanAccept"] = self.can_accept_recipe
        result["loadedRecipe"] = self.loaded_recipe
        return result

    async def async_recommend_recipes(self, *, limit: int = 12, catalog_size: int = 18) -> dict[str, Any]:
        catalog_size = max(int(limit), min(int(catalog_size), 50))
        result = await self.async_search_recipes("", page=0, size=catalog_size, max_details=catalog_size)
        ranked = self.recipe_hub.rank(result.get("items") or [], limit=limit)
        for item in ranked:
            item["deviceCanAccept"] = self.can_accept_recipe
        return {
            "items": ranked,
            "profile": self.recipe_hub.profile,
            "deviceCanAccept": self.can_accept_recipe,
            "loadedRecipe": self.loaded_recipe,
        }

    def _profile_match_or_raise(self, meta: dict[str, Any]) -> dict[str, Any]:
        annotated = self.recipe_hub.annotate(meta)
        match = annotated.get("match") or {}
        if not match.get("safe", True):
            violations = ", ".join(match.get("violations") or []) or "dietary profile"
            raise HomeAssistantError(
                f"Recipe is blocked by the Cook4Me dietary/allergy profile: {violations}"
            )
        return annotated

    async def _async_send_resolved(self, meta: dict[str, Any]) -> dict[str, Any]:
        grouping = str(meta.get("groupingFunctionalId") or "").strip()
        recipe = str(meta.get("recipeFunctionalId") or "").strip()
        if not grouping or not recipe:
            raise HomeAssistantError("Official recipe does not contain the SEB IDs required for Cook4Me delivery")
        if not self.available:
            raise HomeAssistantError("Cook4Me is not connected to the cloud")
        loaded = self.loaded_recipe
        if loaded:
            loaded_title = loaded.get("title") or loaded.get("groupingFunctionalId") or "another recipe"
            raise HomeAssistantError(
                f"Cook4Me already has a loaded recipe/session ({loaded_title}). Exit the current recipe on the Cook4Me before sending another one."
            )
        annotated = self._profile_match_or_raise(meta)
        result = await self._run_client_json("send-recipe", grouping, recipe, timeout=45)
        await self.recipe_hub.async_record_send(annotated)
        return {"accepted": result, "recipe": annotated}

    async def async_send_recipe(
        self,
        grouping_functional_id: str,
        recipe_functional_id: str,
        *,
        allow_loaded: bool = False,
        title: str | None = None,
    ) -> dict[str, Any]:
        # Exact-ID service calls are still resolved through official recipe detail
        # so dietary/allergy rules cannot be bypassed by skipping the dashboard.
        grouping_functional_id = str(grouping_functional_id).strip()
        recipe_functional_id = str(recipe_functional_id).strip()
        if not grouping_functional_id or not recipe_functional_id:
            raise HomeAssistantError("Both grouping and recipe functional IDs are required")
        meta = await self.async_recipe_detail(recipe_functional_id)
        resolved_grouping = str(meta.get("groupingFunctionalId") or "")
        resolved_recipe = str(meta.get("recipeFunctionalId") or "")
        if resolved_grouping != grouping_functional_id or resolved_recipe != recipe_functional_id:
            raise HomeAssistantError(
                "Provided recipe IDs do not match the official SEB recipe detail; refusing an unverified send"
            )
        if title and not meta.get("title"):
            meta["title"] = title
        if allow_loaded:
            # Kept only for internal compatibility. It is intentionally not exposed
            # in the dashboard/services because live evidence shows Cook4Me consumes
            # but ignores a new recipe while another recipe/session is loaded.
            loaded = self.loaded_recipe
            if loaded:
                _LOGGER.warning("Cook4Me allow_loaded send requested despite active recipe: %s", loaded)
        return await self._async_send_resolved(meta)

    async def async_send_variant(self, variant_id: str) -> dict[str, Any]:
        meta = await self.async_recipe_detail(variant_id)
        return await self._async_send_resolved(meta)


async def async_discover_appliances(hass: HomeAssistant, data: dict[str, Any]) -> list[dict[str, Any]]:
    """Authenticate and return Cook4Me appliances owned/accessible by the account."""
    _LOGGER.warning("Cook4Me config-flow discovery starting (country=%s language=%s)",
                    data.get(CONF_COUNTRY, DEFAULT_COUNTRY),
                    data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE))
    class EntryLike:
        entry_id = "config_flow"
        def __init__(self, d):
            self.data = d

    bridge = Cook4MeBridge(hass, EntryLike(data))
    vendor = pathlib.Path(__file__).parent / "vendor"
    cmd = [
        sys.executable, "-u", str(vendor / "cook4me_auto.py"),
        "--country", str(data.get(CONF_COUNTRY, DEFAULT_COUNTRY)),
        "--language", str(data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)),
        "--app-version", DEFAULT_APP_VERSION,
        "--json-lines", "discover",
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=str(vendor), env=bridge._env(),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    _LOGGER.warning("Cook4Me discovery subprocess started pid=%s", proc.pid)
    try:
        out, err = await asyncio.wait_for(proc.communicate(), 90)
    except TimeoutError as exc:
        proc.kill()
        await proc.wait()
        _LOGGER.error("Cook4Me appliance discovery timed out after 90 seconds")
        raise Cook4MeCloudUnavailable("Cook4Me appliance discovery timed out after 90 seconds") from exc
    _LOGGER.warning("Cook4Me discovery subprocess finished rc=%s stdout_bytes=%s stderr_bytes=%s",
                    proc.returncode, len(out), len(err))
    if proc.returncode:
        msg = err.decode("utf-8", "replace")[-2400:].strip()
        low = msg.lower()
        # Never log credential values; the vendor client already redacts its auth log.
        _LOGGER.error("Cook4Me setup failed: %s", msg or f"client exit {proc.returncode}")
        if any(x in low for x in (
            "invalid credentials", "incorrect username", "incorrect password",
            "login failed", "authentication failed", "invalid_grant",
        )):
            raise Cook4MeInvalidAuth("KRUPS rejected the supplied credentials")
        if any(x in low for x in (
            "timed out", "timeout", "network error", "name or service not known",
            "temporary failure", "connection refused", "connection reset",
            "http 502", "http 503", "http 504",
        )):
            raise Cook4MeCloudUnavailable(msg or "KRUPS cloud is unavailable")
        if any(x in low for x in (
            "contains no cook4me iot uuid", "no appliance discovery result",
            "no compatible cook4me", "profiles/me",
        )):
            raise Cook4MeDiscoveryError(msg or "KRUPS account appliance discovery failed")
        raise Cook4MeInternalError(msg or f"Cook4Me client exited with code {proc.returncode}")
    for line in reversed(out.decode("utf-8", "replace").splitlines()):
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        appliances = obj.get("appliances") if isinstance(obj, dict) else None
        if isinstance(appliances, list):
            return [x for x in appliances if isinstance(x, dict) and x.get("uuid")]
    tail = out.decode("utf-8", "replace")[-800:].replace("\n", " | ")
    _LOGGER.error("Cook4Me discovery returned no parseable appliance result; stdout tail=%s", tail)
    raise Cook4MeDiscoveryError("Cook4Me returned no appliance discovery result")


async def async_validate_credentials(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Compatibility helper: discovery is now the credential validation."""
    appliances = await async_discover_appliances(hass, data)
    if not appliances:
        raise ConfigEntryNotReady("No compatible Cook4Me appliances found")
    return {"appliances": appliances}
