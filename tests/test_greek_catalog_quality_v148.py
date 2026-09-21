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
QUALITY=COMPONENT/"catalog_ui_locales"/"zzz_el_quality.json"


def presentation_module():
    path=COMPONENT/"catalog_presentation.py"
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v148_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    module.labels.cache_clear()
    module.excluded_names.cache_clear()
    module.locale_search_aliases.cache_clear()
    return module


class GreekCatalogQualityV148Tests(unittest.TestCase):
    def test_v148_is_active_and_versioned(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v148.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v148",panel)
        self.assertIn("cook4me-panel-v148.js",panel)
        self.assertIn("/cook4me_static/2026.9.21.13",panel)
        self.assertIn("?v=2026.9.21.13",panel)
        self.assertIn('"version": "2026.9.21.13"',manifest)
        self.assertIn(
            "if(!customElements.get(V147))await import('./cook4me-panel-v147.js?v=2026.9.21.12')",
            ui,
        )

    def test_quality_overlay_preserves_v146_v147_curated_terms(self):
        p=presentation_module()
        labels=p.labels()["el"]
        # Existing curated work from v146/v147 remains authoritative.
        self.assertEqual(labels["veal"],"Μοσχαράκι")
        self.assertEqual(labels["mint"],"Μέντα")
        self.assertEqual(labels["spearmint"],"Δυόσμος")
        self.assertEqual(labels["cornflour"],"Κορν φλάουρ (άμυλο καλαμποκιού)")
        self.assertEqual(labels["cardamom"],"Κακουλές (καρδάμωμο)")
        self.assertEqual(labels["saffron"],"Σαφράν (κρόκος)")
        self.assertEqual(labels["red cabbage"],"Μωβ λάχανο")
        self.assertEqual(labels["oxtail"],"Μοσχαρίσια ουρά")

    def test_v148_fills_remaining_usage_audited_gaps(self):
        labels=presentation_module().labels()["el"]
        expected={
            "any fruit":"Φρούτα της επιλογής σας",
            "any berries":"Μούρα της επιλογής σας",
            "any seed":"Σπόροι της επιλογής σας",
            "liquid cream":"Ρευστή κρέμα γάλακτος",
            "butternut squash":"Κολοκύθα μπάτερνατ",
            "fromage frais":"Φρέσκο τυρί fromage frais",
            "pistachio":"Κελυφωτό φιστίκι",
            "pistachio cream":"Κρέμα κελυφωτού φιστικιού",
            "100% pistachio cream":"Κρέμα κελυφωτού φιστικιού 100%",
            "pistachio paste":"Πάστα κελυφωτού φιστικιού",
            "bacon lardon":"Κυβάκια μπέικον (lardons)",
            "chervil":"Μυρώνι",
            "bay leaf":"Φύλλο δάφνης",
            "leaf gelatine":"Ζελατίνη σε φύλλα",
            "gelatin sheet":"Ζελατίνη σε φύλλα",
            "bird's eye chili":"Πολύ καυτερή πιπεριά τσίλι τύπου Bird’s Eye",
            "gruyere":"Τυρί Γκριγιέρ",
            "strained tomato":"Πασάτα ντομάτας",
            "tomato coulis":"Κουλί ντομάτας (λεπτή σάλτσα)",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value,key)

    def test_malformed_food_fragments_are_globally_excluded(self):
        p=presentation_module()
        excluded=p.excluded_names()
        for fragment in ("and","or","for serving","and steamed eggplant","optional"):
            self.assertIn(fragment,excluded)

    def test_synthetic_picker_has_only_real_reviewed_greek_foods(self):
        p=presentation_module()
        payload={"ingredients":[
            {"id":"1","key":"V","canonicalName":"Veal","classification":"food"},
            {"id":"2","key":"P","canonicalName":"Pistachio","classification":"food"},
            {"id":"3","key":"C","canonicalName":"Cornflour","classification":"food"},
            {"id":"4","key":"B","canonicalName":"Bird's eye chili","classification":"food"},
            {"id":"5","canonicalName":"and","classification":"food"},
            {"id":"6","canonicalName":"For serving","classification":"food"},
            {"id":"7","canonicalName":"Optional","classification":"food"},
        ]}
        rows=p.ingredient_choices(payload,"el")
        names={row["canonicalName"]:row["name"] for row in rows}
        self.assertEqual(names["Veal"],"Μοσχαράκι")
        self.assertEqual(names["Pistachio"],"Κελυφωτό φιστίκι")
        self.assertEqual(names["Cornflour"],"Κορν φλάουρ (άμυλο καλαμποκιού)")
        self.assertEqual(names["Bird's eye chili"],"Πολύ καυτερή πιπεριά τσίλι τύπου Bird’s Eye")
        for fragment in ("and","For serving","Optional"):
            self.assertNotIn(fragment,names)
        greek=re.compile(r"[\u0370-\u03ff\u1f00-\u1fff]")
        self.assertTrue(all(greek.search(row["name"]) for row in rows))
        self.assertTrue(all("Απροσδιόριστο" not in row["name"] for row in rows))

    def test_new_greek_synonyms_and_original_aliases_are_searchable(self):
        p=presentation_module()
        aliases=p.locale_search_aliases()["el"]
        self.assertIn("φιστίκι αιγίνης",aliases["pistachio"])
        self.assertIn("δαφνόφυλλο",aliases["bay leaf"])
        self.assertIn("passata",aliases["strained tomato"])
        payload={"ingredients":[
            {"id":"1","key":"P","canonicalName":"Pistachio","classification":"food","translations":{"en":"pistachio"}},
        ]}
        by_greek=p.ingredient_choices(payload,"el","κελυφωτό")
        by_english=p.ingredient_choices(payload,"el","pistachio")
        self.assertEqual([r["ingredientId"] for r in by_greek],["1"])
        self.assertEqual([r["ingredientId"] for r in by_english],["1"])

    def test_quality_overlay_documents_usage_audit(self):
        data=json.loads(QUALITY.read_text(encoding="utf-8"))
        self.assertEqual(data["language"],"el")
        self.assertIn("Usage-audited",data["translationSource"])
        self.assertGreaterEqual(len(data["labels"]),20)
        self.assertGreaterEqual(len(data["searchAliases"]),15)
        self.assertEqual(
            set(data["excludedNames"]),
            {"and","or","for serving","and steamed eggplant","optional"},
        )


if __name__=="__main__":
    unittest.main()
