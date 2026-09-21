from pathlib import Path
import importlib.util
import json
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
COMPONENT=ROOT/"custom_components"/"cook4me"
FRONTEND=COMPONENT/"frontend"
PANEL=COMPONENT/"panel.py"
MANIFEST=COMPONENT/"manifest.json"
LOCALE=COMPONENT/"catalog_ui_locales"/"el.json"


def presentation_module():
    path=COMPONENT/"catalog_presentation.py"
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v146_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    module.labels.cache_clear()
    module.excluded_names.cache_clear()
    return module


class GreekIngredientCatalogV146Tests(unittest.TestCase):
    def test_v146_is_active_and_versioned(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v146.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v146",panel)
        self.assertIn("cook4me-panel-v146.js",panel)
        self.assertIn("/cook4me_static/2026.9.21.11",panel)
        self.assertIn("?v=2026.9.21.11",panel)
        self.assertIn('"version": "2026.9.21.11"',manifest)
        self.assertIn(
            "if(!customElements.get(V145))await import('./cook4me-panel-v145.js?v=2026.9.21.10')",
            ui,
        )

    def test_reviewed_greek_labels_use_natural_culinary_terms(self):
        data=json.loads(LOCALE.read_text(encoding="utf-8"))
        labels=data["labels"]
        self.assertIn("usage-prioritized quality pass",data["translationSource"])
        expected={
            "any berries":"Μούρα της επιλογής σας",
            "any fruit":"Φρούτα της επιλογής σας",
            "any seed":"Σπόροι της επιλογής σας",
            "veal":"Μοσχάρι γάλακτος",
            "veal stock":"Ζωμός από μοσχάρι γάλακτος",
            "welsh onion":"Μακρύ φρέσκο κρεμμυδάκι",
            "liquid cream":"Ρευστή κρέμα γάλακτος",
            "heavy cream":"Κρέμα γάλακτος υψηλών λιπαρών",
            "sour cream":"Ξινή κρέμα γάλακτος",
            "butternut squash":"Κολοκύθα μπάτερνατ",
            "fromage frais":"Φρέσκο τυρί",
            "cornflour":"Άμυλο καλαμποκιού",
            "pistachio":"Κελυφωτό φιστίκι",
            "pistachio cream":"Κρέμα κελυφωτού φιστικιού",
            "pistachio paste":"Πάστα κελυφωτού φιστικιού",
            "bacon lardon":"Κυβάκια μπέικον",
            "chervil":"Μυρώνι",
            "bay leaf":"Φύλλο δάφνης",
            "leaf gelatine":"Ζελατίνη σε φύλλα",
            "bird's eye chili":"Μικρή πολύ καυτερή πιπεριά τσίλι",
            "bird's eye chili powder":"Σκόνη πολύ καυτερής πιπεριάς τσίλι",
            "gruyere":"Τυρί Γκριγιέρ",
            "strained tomato":"Πασάτα ντομάτας",
            "tomato coulis":"Λεπτή σάλτσα ντομάτας",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value,key)

    def test_malformed_food_fragments_are_excluded_not_translated(self):
        data=json.loads(LOCALE.read_text(encoding="utf-8"))
        excluded=set(data.get("excludedNames") or [])
        for fragment in ("and","or","for serving","and steamed eggplant","optional"):
            self.assertIn(fragment,excluded)
        for fragment in (
            "cups of","grams of","half a","handful of","large","pinch of",
            "portion of","sprig of","stalk of","tablespoon of","tbsp","tsp","whole",
        ):
            self.assertIn(fragment,excluded)

    def test_real_picker_uses_reviewed_greek_labels_and_hides_fragments(self):
        presentation=presentation_module()
        payload={"ingredients":[
            {"id":"1","key":"VEAL","canonicalName":"Veal","classification":"food"},
            {"id":"2","key":"PISTACHIO","canonicalName":"Pistachio","classification":"food"},
            {"id":"3","key":"CORN","canonicalName":"Cornflour","classification":"food"},
            {"id":"4","key":"CHILI","canonicalName":"Bird's eye chili","classification":"food"},
            {"id":"5","canonicalName":"and","classification":"food"},
            {"id":"6","canonicalName":"For serving","classification":"food"},
            {"id":"7","canonicalName":"Optional","classification":"food"},
        ]}
        rows=presentation.ingredient_choices(payload,"el")
        names={row["canonicalName"]:row["name"] for row in rows}
        self.assertEqual(names["Veal"],"Μοσχάρι γάλακτος")
        self.assertEqual(names["Pistachio"],"Κελυφωτό φιστίκι")
        self.assertEqual(names["Cornflour"],"Άμυλο καλαμποκιού")
        self.assertEqual(names["Bird's eye chili"],"Μικρή πολύ καυτερή πιπεριά τσίλι")
        self.assertNotIn("and",names)
        self.assertNotIn("For serving",names)
        self.assertNotIn("Optional",names)
        greek=re.compile(r"[\u0370-\u03ff\u1f00-\u1fff]")
        self.assertTrue(all(greek.search(row["name"]) for row in rows))
        self.assertTrue(all("Απροσδιόριστο" not in row["name"] for row in rows))

    def test_greek_search_finds_reviewed_name_without_losing_original_alias(self):
        presentation=presentation_module()
        payload={"ingredients":[
            {"id":"1","key":"P","canonicalName":"Pistachio","classification":"food","translations":{"en":"pistachio"}},
        ]}
        greek=presentation.ingredient_choices(payload,"el","κελυφωτό")
        english=presentation.ingredient_choices(payload,"el","pistachio")
        self.assertEqual(len(greek),1)
        self.assertEqual(len(english),1)
        self.assertEqual(greek[0]["ingredientId"],english[0]["ingredientId"])
        self.assertEqual(greek[0]["name"],"Κελυφωτό φιστίκι")


if __name__=="__main__":
    unittest.main()
