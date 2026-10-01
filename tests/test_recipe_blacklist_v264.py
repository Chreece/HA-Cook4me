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
        self.assertIn("bridge.recipe_hub.is_recipe_blacklisted(recipe)",v13)
        self.assertIn("not bridge.recipe_hub.is_recipe_blacklisted(row)",shared)
        self.assertIn("bridge.recipe_hub.is_recipe_blacklisted(recipe)",weekly)
        self.assertIn('for collection in ("favorites", "recipeList")',book)
        self.assertIn("bridge.recipe_hub.filter_blacklisted(",book)

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
