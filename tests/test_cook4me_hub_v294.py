"""Cook4Me v294: fast panel registration, Hub routing, localized egg aliases."""
from __future__ import annotations

import ast
import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMP = ROOT / "custom_components" / "cook4me"
FRONTEND = COMP / "frontend"


def _hub_method():
    """Run only the production routing method, without importing Home Assistant."""
    path = COMP / "announcements.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    parent = next(node for node in tree.body
                  if isinstance(node, ast.ClassDef) and node.name == "Announcements")
    method = next(node for node in parent.body
                  if isinstance(node, ast.AsyncFunctionDef) and node.name == "_send_hub")
    stub = ast.ClassDef(
        name="StandaloneAnnouncement",
        bases=[], keywords=[], body=[method], decorator_list=[],
    )
    fake = {
        "asyncio": asyncio,
        "device_access": lambda hass, bridge, user: True,
        "Context": lambda **kwargs: kwargs,
        "hub_choices": lambda hass, user: {
            "announcementHubAvailable": True,
            "hubAreas": [{"id": "kitchen", "name": "Kitchen"},
                         {"id": "living", "name": "Living"}],
            "hubPersons": [{"id": "person.alex", "name": "Alex"},
                           {"id": "person.sam", "name": "Sam"}],
        },
    }
    exec(compile(ast.fix_missing_locations(ast.Module(body=[stub], type_ignores=[])), str(path), "exec"), fake)
    return fake["StandaloneAnnouncement"]


class HubRoutingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.calls = []
        self.events = []
        user = SimpleNamespace(id="u1", is_active=True)
        async def get_user(_user_id):
            return user

        async def call(domain, service, data, *, blocking, context):
            assert (domain, service, blocking) == ("notify", "announcement_hub", True)
            assert "manual_targets" not in data or "target_person" not in data
            assert "area" not in data or "target_person" not in data
            self.calls.append(data)

        self.worker = _hub_method()()
        self.worker.hass = SimpleNamespace(
            auth=SimpleNamespace(async_get_user=get_user),
            services=SimpleNamespace(async_call=call),
        )
        self.worker.bridge = object()
        self.worker.closed = False
        self.worker.report = lambda user_id, state, *args: self.events.append((user_id, state))
        self.user = user
        self.base = {
            "announcement_hub": True,
            "hub_auto_routing": True,
            "hub_areas": [],
            "hub_persons": [],
        }

    async def send(self, **changes):
        settings = {**self.base, **changes}
        delivered = set()
        await self.worker._send_hub(
            self.user, settings, "Food is ready",
            still_current=lambda: True, delivered=delivered,
        )
        return delivered

    async def test_automatic_hub_only(self):
        delivered = await self.send()
        self.assertEqual(self.calls, [{"text": "Food is ready", "title": "Cook4Me", "level": "info"}])
        self.assertEqual(len(delivered), 1)

    async def test_manual_room_targets(self):
        await self.send(hub_auto_routing=False, hub_areas=["kitchen", "living"])
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0]["area"], ["kitchen", "living"])
        self.assertIs(self.calls[0]["manual_targets"], True)
        self.assertNotIn("target_person", self.calls[0])

    async def test_manual_person_targets(self):
        await self.send(hub_auto_routing=False, hub_persons=["person.alex"])
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0]["target_person"], ["person.alex"])
        self.assertNotIn("manual_targets", self.calls[0])
        self.assertNotIn("area", self.calls[0])

    async def test_manual_rooms_and_people_separate(self):
        delivered = await self.send(
            hub_auto_routing=False, hub_areas=["kitchen"],
            hub_persons=["person.sam"],
        )
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(len(delivered), 2)
        self.assertIn("area", self.calls[0])
        self.assertIn("target_person", self.calls[1])

    async def test_no_manual_destinations_rejected(self):
        with self.assertRaisesRegex(ValueError, "room or person"):
            await self.send(hub_auto_routing=False)
        self.assertEqual(self.calls, [])

    async def test_deduplication(self):
        delivered = await self.send(hub_auto_routing=False, hub_areas=["kitchen"])
        await self.worker._send_hub(
            self.user, {**self.base, "hub_auto_routing": False,
                        "hub_areas": ["kitchen"]},
            "Food is ready", still_current=lambda: True, delivered=delivered,
        )
        self.assertEqual(len(self.calls), 1)


class EggCatalogTests(unittest.TestCase):
    def test_ei_and_eggs_share_one_greek_display_choice(self):
        path = COMP / "catalog_presentation.py"
        spec = importlib.util.spec_from_file_location("cook4me_catalog_v294_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sources = [
            {"id": "de-ei", "key": "de-ei", "canonicalName": "Ei",
             "classification": "food"},
            {"id": "en-eggs", "key": "en-eggs", "canonicalName": "Eggs",
             "classification": "food"},
            {"id": "egg-white", "key": "egg-white",
             "canonicalName": "Egg white", "classification": "food"},
        ]
        result = module.ingredient_choices({"ingredients": sources}, "el")
        generic = [row for row in result if row["name"] == "Αυγό"]
        self.assertEqual(len(generic), 1)
        self.assertCountEqual(generic[0]["sourceIngredientIds"], ["de-ei", "en-eggs"])
        self.assertNotEqual(generic[0]["ingredientId"], "egg-white")
        self.assertTrue(any(row["name"] == "Ασπράδι αυγού" for row in result))
        self.assertEqual(sources[0]["canonicalName"], "Ei")
        self.assertEqual(sources[1]["canonicalName"], "Eggs")

    def test_catalog_endpoints_keep_display_identity(self):
        v11 = (COMP / "websocket_v11.py").read_text(encoding="utf-8")
        v31 = (COMP / "websocket_v31.py").read_text(encoding="utf-8")
        self.assertIn("release_index.ingredient_rows(language)", v11)  # AI/stock exact IDs
        self.assertIn("release_catalog.ingredient_choices, language", v31)


class PanelBootTests(unittest.TestCase):
    def test_immediate_lightweight_shell_and_new_runtime(self):
        panel = (COMP / "panel.py").read_text(encoding="utf-8")
        boot = (FRONTEND / "cook4me-panel-bootstrap-v294.js").read_text(encoding="utf-8")
        ui = (FRONTEND / "cook4me-panel-v180.js").read_text(encoding="utf-8")
        self.assertIn('cook4me-quick-panel-v294', panel)
        self.assertIn('cook4me-panel-bootstrap-v294.js', panel)
        self.assertIn("const moduleReady = import(", boot)
        self.assertIn("customElements.define('cook4me-quick-panel-v294'", boot)
        self.assertIn("cook4me-recipe-hub-panel-v180-runtime-v294", boot)
        self.assertIn("AnnouncementHubMixin(customElements.get(", ui)


if __name__ == "__main__":
    unittest.main()
