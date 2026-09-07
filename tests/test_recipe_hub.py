from __future__ import annotations

import asyncio
from datetime import datetime
import importlib.util
import sys
import types
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "custom_components/cook4me"

# Minimal Home Assistant stubs: this test exercises hub logic, not HA storage.
ha = types.ModuleType("homeassistant")
ha_core = types.ModuleType("homeassistant.core")
ha_helpers = types.ModuleType("homeassistant.helpers")
ha_storage = types.ModuleType("homeassistant.helpers.storage")
ha_util = types.ModuleType("homeassistant.util")
ha_dt = types.ModuleType("homeassistant.util.dt")
class HomeAssistant: pass
class Store:
    def __init__(self, *args, **kwargs): self.saved = None
    async def async_load(self): return None
    async def async_save(self, data): self.saved = data
ha_core.HomeAssistant = HomeAssistant
ha_storage.Store = Store
ha_dt.now = datetime.now
ha_util.dt = ha_dt
sys.modules.setdefault("homeassistant", ha)
sys.modules["homeassistant.core"] = ha_core
sys.modules["homeassistant.helpers"] = ha_helpers
sys.modules["homeassistant.helpers.storage"] = ha_storage
sys.modules["homeassistant.util"] = ha_util
sys.modules["homeassistant.util.dt"] = ha_dt

# Load cook4me package modules without importing integration __init__.py.
pkg = types.ModuleType("cook4me_testpkg")
pkg.__path__ = [str(PACKAGE)]
sys.modules["cook4me_testpkg"] = pkg
for name in ("const", "recipe_logic", "recipe_hub"):
    path = PACKAGE / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"cook4me_testpkg.{name}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"cook4me_testpkg.{name}"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)

hubmod = sys.modules["cook4me_testpkg.recipe_hub"]


class RecipeHubTests(unittest.TestCase):
    def new_hub(self):
        hass = HomeAssistant()
        return hubmod.Cook4MeRecipeHub(hass, "entry")

    def test_ai_recipe_is_revalidated_against_profile(self):
        hub = self.new_hub()
        hub._data["profile"] = {"diet":"vegan","allergies":[],"avoid":[],"preferences":[],"pantry":[]}
        with self.assertRaisesRegex(ValueError, "dietary profile"):
            asyncio.run(hub.async_save_recipe({
                "title":"Cheese pasta","ingredients":["cheese","pasta"],"steps":["Cook it"]
            }, source="ai"))

    def test_history_habits_are_ranking_only_and_require_repeat(self):
        hub = self.new_hub()
        hub._data["history"] = [
            {"ingredientNames":["mushroom","rice"],"courses":[{"name":"Main"}]},
            {"ingredientNames":["mushroom","potato"],"courses":[{"name":"Main"}]},
        ]
        terms = hub._habit_terms()
        self.assertIn("mushroom", terms)
        self.assertIn("Main", terms)
        self.assertNotIn("rice", terms)
        recipe = {"title":"Mushroom stew","ingredients":[{"name":"mushroom"}],"excludedFoods":[]}
        annotated = hub.annotate(recipe)
        self.assertTrue(annotated["match"]["safe"])
        self.assertIn("mushroom", annotated["match"]["habitHits"])


if __name__ == "__main__":
    unittest.main()
