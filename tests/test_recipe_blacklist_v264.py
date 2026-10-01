from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
COMP=ROOT/"custom_components"/"cook4me"


class RecipeBlacklistV264Tests(unittest.TestCase):
    def test_backend_filters_every_main_recipe_surface(self):
        hub=(COMP/"recipe_hub.py").read_text(encoding="utf-8")
        websocket=(COMP/"websocket.py").read_text(encoding="utf-8")
        v10=(COMP/"websocket_v10.py").read_text(encoding="utf-8")
        v13=(COMP/"websocket_v13.py").read_text(encoding="utf-8")
        v28=(COMP/"websocket_v28.py").read_text(encoding="utf-8")
        v30=(COMP/"websocket_v30.py").read_text(encoding="utf-8")
        shared=(COMP/"shared_recipe_runtime.py").read_text(encoding="utf-8")
        weekly=(COMP/"weekly_plan.py").read_text(encoding="utf-8")
        book=(COMP/"websocket_v18.py").read_text(encoding="utf-8")

        self.assertIn('"recipeBlacklist": []',hub)
        self.assertIn("async_blacklist_recipe",hub)
        self.assertIn("async_unblacklist_recipe",hub)
        self.assertIn("is_recipe_blacklisted",hub)
        self.assertIn("filter_blacklisted",hub)
        self.assertIn('"cook4me/recipe_blacklist_add"',websocket)
        self.assertIn('"cook4me/recipe_blacklist_remove"',websocket)
        self.assertIn("bridge.recipe_hub.is_recipe_blacklisted(item)",websocket)
        self.assertIn("_hide_blacklisted",v10)
        self.assertIn('blacklist_check = getattr(bridge.recipe_hub, "is_recipe_blacklisted", None)',v13)
        self.assertIn("blacklist_check(recipe)",v13)
        self.assertIn("visible_recipes = bridge.recipe_hub.filter_blacklisted(",v28)
        self.assertIn("book_snapshot[collection] = bridge.recipe_hub.filter_blacklisted(",v28)
        self.assertIn("bridge.recipe_hub.is_recipe_blacklisted(item)",v30)
        self.assertIn('per_entry["todayResults"] = bridge.recipe_hub.filter_blacklisted(',v30)
        self.assertIn('blacklist_filter = getattr(bridge.recipe_hub, "filter_blacklisted", None)',shared)
        self.assertIn("rows = blacklist_filter(rows)",shared)
        self.assertIn('blacklist_check = getattr(bridge.recipe_hub, "is_recipe_blacklisted", None)',weekly)
        self.assertIn("blacklist_check(recipe)",weekly)
        self.assertIn('for collection in ("favorites", "recipeList")',book)
        self.assertIn("bridge.recipe_hub.filter_blacklisted(",book)
        self.assertIn("official = bridge.recipe_hub.filter_blacklisted(",book)

    def test_active_panel_is_cache_busted_to_v264(self):
        panel=(COMP/"frontend"/"cook4me-panel-v180.js").read_text(encoding="utf-8")
        registration=(COMP/"panel.py").read_text(encoding="utf-8")
        self.assertIn("RecipeBlacklistMixin",panel)
        self.assertIn("runtime-v264",panel)
        self.assertIn("data-cook4me-ui-revision','264'",panel)
        self.assertIn("runtime-v264",registration)
        self.assertIn("blacklist=264",registration)


if __name__=="__main__":
    unittest.main()
