"""Exercise the real notification, inventory, AI and completion paths."""
from __future__ import annotations

import ast
from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import date, datetime
from enum import StrEnum
import importlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components/cook4me"
PREFIX = "cook4me_notification_test"


class MemoryStore:
    saved = {}

    def __init__(self, hass, version, key):
        self.key = key
        self.pending = None

    async def async_load(self):
        return deepcopy(self.saved.get(self.key))

    def async_delay_save(self, getter, delay):
        self.pending = getter

    async def async_save(self, data):
        self.saved[self.key] = deepcopy(data)
        self.pending = None

    async def flush(self):
        if self.pending:
            await self.async_save(self.pending())


class FakeNotifications:
    class UpdateType(StrEnum):
        REMOVED = "removed"

    def __init__(self):
        self.visible = {}
        self.created = []
        self.callbacks = []

    def async_register_callback(self, hass, callback):
        self.callbacks.append(callback)
        return lambda: self.callbacks.remove(callback)

    def async_create(self, hass, message, *, title, notification_id):
        item = {"message": message, "title": title}
        self.visible[notification_id] = item
        self.created.append((notification_id, item))

    def async_dismiss(self, hass, ident):
        if item := self.visible.pop(ident, None):
            for callback in list(self.callbacks):
                callback(self.UpdateType.REMOVED, {ident: item})

    def dismiss_all(self):
        removed, self.visible = self.visible, {}
        for callback in list(self.callbacks):
            callback(self.UpdateType.REMOVED, removed)


def functions(filename, names, namespace):
    nodes = [node for node in ast.parse((COMPONENT / filename).read_text()).body
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names]
    assert len(nodes) == len(names)
    for node in nodes:
        node.decorator_list = []
    tree = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), *nodes], type_ignores=[])
    exec(compile(ast.fix_missing_locations(tree), filename, "exec"), namespace)
    return namespace


class NotificationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        MemoryStore.saved = {}
        self.ha = FakeNotifications()
        package = ModuleType(PREFIX)
        package.__path__ = [str(COMPONENT)]
        self.patcher = patch.dict(sys.modules, {
            PREFIX: package,
            "homeassistant.components": NS(persistent_notification=self.ha),
            "homeassistant.core": NS(callback=lambda f: f),
            "homeassistant.helpers.storage": NS(Store=MemoryStore),
            "homeassistant.helpers.event": NS(async_track_time_change=lambda *args, **kwargs: lambda: None),
            "homeassistant.util": NS(dt=NS(now=datetime.now)),
        })
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        for name in ("notifications", "expiry"):
            sys.modules.pop(PREFIX + "." + name, None)
        self.module = importlib.import_module(PREFIX + ".notifications")
        self.expiry = importlib.import_module(PREFIX + ".expiry")
        self.inventory = importlib.import_module(PREFIX + ".inventory")
        self.hass = NS(config=NS(language="el"), data={})
        self.notices = self.module.Cook4MeNotifications(self.hass, "one")
        await self.notices.async_load()
        self.addAsyncCleanup(self.notices.async_close)
        self.bridge = NS(hass=self.hass, entry=NS(entry_id="one"), notifications=self.notices,
                         recipe_hub=NS(profile={"houseIngredients": []}))
        self.ident = self.expiry.notification_id("one")

    def stock(self, name="Milk", deadline="2026-09-28", **extra):
        return {"name": name, "key": name.lower(), "unit": "ml", "lots": [
            {"id": str(uuid4()), "quantity": 200, "bestBefore": deadline, **extra}
        ]}

    def check(self, today=date(2026, 9, 25)):
        self.expiry.update_expiry_notification(self.bridge, today=today)

    async def test_expiry_is_created_once_across_polls_edits_order_and_day_changes(self):
        house = self.bridge.recipe_hub.profile["houseIngredients"]
        house.extend([self.stock(), self.stock("Tofu")])
        self.check()
        for today in (date(2026, 9, 25), date(2026, 9, 26), date(2026, 9, 29)):
            house.reverse()
            house[0]["lots"][0].update(quantity=100, storage="fridge")
            self.check(today)
        self.assertEqual(len(self.ha.created), 1)
        self.assertEqual(len(self.ha.visible), 1)

    async def test_dismissed_warning_stays_gone_when_a_product_is_removed_or_added(self):
        house = self.bridge.recipe_hub.profile["houseIngredients"]
        house.extend([self.stock(), self.stock("Tofu")])
        self.check()
        self.ha.async_dismiss(self.hass, self.ident)
        house.pop()
        self.check()
        house.append(self.stock("Carrots"))
        self.check()
        message = self.ha.visible[self.ident]["message"]
        self.assertIn("Carrots", message)
        self.assertNotIn("Milk", message)
        self.assertNotIn("Tofu", message)
        self.assertEqual(len(self.ha.created), 2)

    async def test_new_use_date_can_notify_without_resurrecting_the_old_date(self):
        house = self.bridge.recipe_hub.profile["houseIngredients"]
        house.append(self.stock())
        self.check()
        self.ha.async_dismiss(self.hass, self.ident)
        house[0]["lots"][0]["bestBefore"] = "2026-09-27"
        self.check()
        self.assertEqual(len(self.ha.created), 2)
        self.ha.async_dismiss(self.hass, self.ident)
        house[0]["lots"][0]["bestBefore"] = "2026-09-28"
        self.check()
        self.assertNotIn(self.ident, self.ha.visible)

    async def test_unread_summary_keeps_old_items_and_removes_consumed_items(self):
        house = self.bridge.recipe_hub.profile["houseIngredients"]
        house.append(self.stock())
        self.check()
        house.append(self.stock("Tofu"))
        self.check()
        self.assertIn("Milk", self.ha.visible[self.ident]["message"])
        self.assertIn("Tofu", self.ha.visible[self.ident]["message"])
        house.pop(0)
        self.check()
        self.assertNotIn("Milk", self.ha.visible[self.ident]["message"])
        house.clear()
        self.check()
        self.assertNotIn(self.ident, self.ha.visible)
        house.append(self.stock())
        self.check()
        self.assertEqual(len(self.ha.created), 3)

    async def test_regenerated_legacy_ids_and_same_product_date_do_not_repeat(self):
        house = self.bridge.recipe_hub.profile["houseIngredients"]
        house.append({"key": "milk", "name": "Milk", "quantity": 200,
                      "unit": "ml", "bestBefore": "2026-09-28"})
        self.check()
        self.ha.dismiss_all()
        self.check()
        house[:] = [self.stock()]
        self.check()
        self.assertEqual(len(self.ha.created), 1)

    async def test_all_batches_share_one_alert_with_an_overflow_count(self):
        house = self.bridge.recipe_hub.profile["houseIngredients"]
        row = self.stock()
        row["lots"] *= 45
        house.append(row)
        self.check()
        self.assertIn("5 ακόμη παρτίδες", self.ha.visible[self.ident]["message"])
        self.assertEqual(self.ha.visible[self.ident]["message"].count("- **Milk**"), 40)
        self.ha.dismiss_all()
        self.check()
        self.assertEqual(len(self.ha.created), 1)

    async def test_opened_package_limit_has_one_stable_warning(self):
        self.bridge.recipe_hub.profile["houseIngredients"] = [self.stock(
            deadline="2026-12-01", openedAt="2026-09-25", useWithinDays=2)]
        self.check()
        self.assertIn("2026-09-27", self.ha.visible[self.ident]["message"])
        self.assertIn("όριο μετά το άνοιγμα", self.ha.visible[self.ident]["message"])
        self.ha.dismiss_all()
        self.check(date(2026, 10, 1))
        self.assertEqual(len(self.ha.created), 1)

    async def test_ledger_survives_reload_and_restart_and_is_entry_scoped(self):
        self.notices.publish("cook4me_consumption_one", ["meal-1"], "Ready", title="Cook4Me")
        self.ha.dismiss_all()
        await self.notices._store.flush()  # HA's delayed-save/stop hook.
        await self.notices.async_close()
        restarted = self.module.Cook4MeNotifications(self.hass, "one")
        await restarted.async_load()
        self.addAsyncCleanup(restarted.async_close)
        self.assertFalse(restarted.publish("cook4me_consumption_one", ["meal-1"], "Ready", title="Cook4Me", update=True))
        self.assertTrue(restarted.publish("cook4me_consumption_one", ["meal-2"], "Ready", title="Cook4Me"))
        await restarted.async_close()
        before = deepcopy(MemoryStore.saved)
        await self.notices.async_close()  # An old cleanup cannot overwrite new history.
        self.assertEqual(MemoryStore.saved, before)
        other = self.module.Cook4MeNotifications(self.hass, "two")
        await other.async_load()
        self.addAsyncCleanup(other.async_close)
        self.assertTrue(other.publish("cook4me_consumption_two", ["meal-1"], "Ready", title="Cook4Me"))
        self.assertEqual(len(self.ha.created), 3)

    async def test_late_status_cannot_overwrite_a_new_request_or_reopen_a_dismissal(self):
        ident = "cook4me_ai_recipe_one"
        self.notices.publish(ident, ["first"], "Running", title="Cook4Me")
        self.ha.async_dismiss(self.hass, ident)
        self.assertFalse(self.notices.publish(ident, ["first"], "Finished", title="Cook4Me", update=True))
        self.notices.publish(ident, ["second"], "Running", title="Cook4Me")
        self.assertFalse(self.notices.publish(ident, ["first"], "Failed", title="Cook4Me", update=True))
        self.assertTrue(self.notices.publish(ident, ["second"], "Finished", title="Cook4Me", update=True))
        self.assertFalse(self.notices.publish(ident, ["second"], "Finished", title="Cook4Me", update=True))
        self.assertEqual(len(self.ha.created), 3)

    async def test_ai_handlers_respect_dismissal_on_success_and_failure(self):
        @asynccontextmanager
        async def operation(*args, **kwargs):
            yield

        for version in (22, 25):
            for outcome in ("done", "failed"):
                with self.subTest(version=version, outcome=outcome):
                    ident = "cook4me_ai_recipe_one"
                    before = len(self.ha.created)

                    async def generate(*args):
                        self.ha.async_dismiss(self.hass, ident)
                        if outcome == "failed":
                            raise ValueError("generation failed")
                        return {"recipe": {"title": "Soup"}}

                    text = lambda lang, state, *detail: ("Cook4Me", state)
                    connection = NS(send_result=Mock())
                    ns = {"uuid4": uuid4, "_text": lambda v: str(v or ""),
                          "legacy": NS(_bridge=lambda *a: self.bridge, _send_error=Mock()),
                          "request_coordinator": AsyncMock(return_value=NS(operation=operation)),
                          "_create_ai_recipe": generate, "_notification_text": text,
                          "v22": NS(_create_ai_recipe=generate, _notification_text=text)}
                    functions(f"websocket_v{version}.py", {"ws_ai_create"}, ns)
                    await ns["ws_ai_create"](self.hass, connection, {"id": 1})
                    self.assertNotIn(ident, self.ha.visible)
                    self.assertEqual(len(self.ha.created), before + 1)
                    self.assertEqual(connection.send_result.call_count, int(outcome == "done"))
                    self.assertEqual(ns["legacy"]._send_error.call_count, int(outcome == "failed"))

    async def test_completion_reconnect_and_done_flag_jitter_do_not_make_new_pending_meals(self):
        handled = []

        async def completed(bridge, data):
            handled.append(data)

        coroutines = []
        self.bridge.data = {"connected": False}
        self.bridge.async_add_listener = lambda callback: setattr(self, "listener", callback)
        self.bridge.async_create_task = lambda coro, name: coroutines.append(coro)
        ns = {"deepcopy": deepcopy, "_handle_recipe_completed": completed}
        functions("__init__.py", {"_register_completion_listener"}, ns)
        ns["_register_completion_listener"](self.bridge)

        def packet(phase, connected=True, active=False):
            self.bridge.data = {"phase": phase, "connected": connected, "active": active}
            self.listener()

        packet("done")  # Startup snapshot.
        packet("done", active=True)
        packet("cooking", active=True)
        packet("done")
        packet("done", active=True)
        packet("", connected=False)
        packet("done", active=True)
        packet("keep_warm", active=True)
        packet("done")
        packet("idle")
        packet("done")
        self.assertEqual(len(coroutines), 1)
        packet("preparation", active=True)
        packet("cooking", active=True)
        packet("done")
        self.assertEqual(len(coroutines), 2)
        for coro in coroutines:
            await coro
        self.assertEqual(len(handled), 2)

    async def test_consumption_notification_uses_pending_confirmation_identity(self):
        self.bridge.data = {"variantFunctionalId": "soup"}
        self.bridge._recipe_cache = {"soup": {"title": "Soup"}}
        self.bridge.recipe_hub.async_prepare_consumption = AsyncMock(return_value={
            "id": "meal-1", "recipeTitle": "Soup", "ingredients": [{"name": "Rice", "quantity": 50, "unit": "g"}]})
        ns = {"deepcopy": deepcopy, "event_key": self.module.event_key,
              "smart_scale_store_for_bridge": AsyncMock(side_effect=OSError("no scale"))}
        functions("__init__.py", {"_handle_recipe_completed", "_consumption_notification_id", "_format_recipe_amount"}, ns)
        await ns["_handle_recipe_completed"](self.bridge)
        self.assertIn("/cook4me?consumption=meal-1", self.ha.created[-1][1]["message"])
        self.ha.dismiss_all()
        await ns["_handle_recipe_completed"](self.bridge)
        self.assertEqual(len(self.ha.created), 1)

    async def test_close_and_failed_load_do_not_publish_or_erase_saved_history(self):
        self.notices.publish("expiry", ["one"], "Soon", title="Cook4Me")
        await self.notices.async_close()
        self.assertFalse(self.notices.publish("expiry", ["two"], "Soon", title="Cook4Me"))
        before = deepcopy(MemoryStore.saved)
        failed = self.module.Cook4MeNotifications(self.hass, "one")
        failed._store.async_load = AsyncMock(side_effect=OSError("disk unavailable"))
        with self.assertRaises(OSError):
            await failed.async_load()
        await failed.async_close()
        self.assertEqual(MemoryStore.saved, before)

    async def test_setup_loads_history_before_listeners_and_flushes_on_failure(self):
        for fail_at in ("device", "platforms"):
            with self.subTest(fail_at=fail_at):
                await self.notices.async_close()
                self.notices = self.module.Cook4MeNotifications(self.hass, "one")
                events = []

                async def start():
                    self.assertTrue(self.bridge.notifications._loaded)
                    events.append("start")

                async def stop():
                    self.assertFalse(self.bridge.notifications._closed)
                    events.append("stop")

                async def load_device():
                    if fail_at == "device":
                        raise OSError("device settings unavailable")

                async def forward(*args):
                    raise OSError("platform setup unavailable")

                def expiry(bridge):
                    events.append("expiry")
                    bridge.notifications.publish("setup-warning", ["one"], "Soon", title="Cook4Me")

                self.bridge.async_start = start
                self.bridge.async_stop = stop
                self.hass.config_entries = NS(async_forward_entry_setups=forward)
                ns = {"__name__": PREFIX + ".entry", "__package__": PREFIX,
                      "DOMAIN": "cook4me", "DATA_BRIDGES": "bridges",
                      "PLATFORMS": [], "Cook4MeBridge": lambda *a: self.bridge,
                      "Cook4MeNotifications": lambda *a: self.notices,
                      "_register_completion_listener": Mock(), "register_send_queue_listener": Mock(),
                      "update_expiry_notification": expiry,
                      "register_daily_expiry_check": lambda bridge: Mock(),
                      "dismiss_expiry_notification": self.expiry.dismiss_expiry_notification}
                functions("__init__.py", {"async_setup_entry", "_async_cleanup_bridge"}, ns)
                with patch.dict(sys.modules, {
                    PREFIX + ".device_settings": NS(DeviceSettings=lambda bridge: NS(
                        async_load=load_device, async_consolidate_entities=AsyncMock())),
                    PREFIX + ".announcements": NS(Announcements=Mock()),
                }):
                    with self.assertRaises(OSError):
                        await ns["async_setup_entry"](self.hass, self.bridge.entry)
                self.assertTrue(self.notices._closed)
                self.assertEqual(self.ha.callbacks, [])
                self.assertNotIn("one", self.hass.data.get("cook4me", {}).get("bridges", {}))
                self.assertEqual(events, ["stop"] if fail_at == "device" else ["start", "expiry", "stop"])
                if fail_at == "platforms":
                    self.assertIn("one", MemoryStore.saved[self.notices._store.key]["seen"]["setup-warning"])

    async def test_cleanup_flushes_history_even_when_device_stop_fails(self):
        self.notices.publish("expiry", ["one"], "Soon", title="Cook4Me")
        self.bridge.async_stop = AsyncMock(side_effect=OSError("device stop unavailable"))
        ns = {"DOMAIN": "cook4me", "DATA_BRIDGES": "bridges",
              "dismiss_expiry_notification": self.expiry.dismiss_expiry_notification}
        functions("__init__.py", {"_async_cleanup_bridge"}, ns)
        with self.assertRaises(OSError):
            await ns["_async_cleanup_bridge"](self.bridge)
        self.assertTrue(self.notices._closed)
        self.assertEqual(self.ha.callbacks, [])
        self.assertEqual(MemoryStore.saved[self.notices._store.key]["seen"]["expiry"], ["one"])

    def test_all_ha_notification_producers_use_the_shared_manager(self):
        creators = []
        for path in COMPONENT.glob("*.py"):
            tree = ast.parse(path.read_text())
            if any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                   and isinstance(node.func.value, ast.Name) and node.func.value.id == "persistent_notification"
                   and node.func.attr == "async_create" for node in ast.walk(tree)):
                creators.append(path.name)
        self.assertEqual(creators, ["notifications.py"])


if __name__ == "__main__":
    unittest.main()
