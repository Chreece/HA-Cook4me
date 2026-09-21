from pathlib import Path
import importlib.util
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"
CURATED=ROOT/"custom_components"/"cook4me"/"catalog_ui_locales"/"zz_el_curated.json"


def load_presentation():
    path=ROOT/"custom_components"/"cook4me"/"catalog_presentation.py"
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v163_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GreekCatalogAuditV163Tests(unittest.TestCase):
    def test_v163_is_inherited_by_active_v164(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v163.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v164",panel)
        self.assertIn("cook4me-panel-v164.js",panel)
        self.assertIn("/cook4me_static/2026.9.21.29",panel)
        self.assertIn("?v=2026.9.21.29",panel)
        self.assertIn('"version": "2026.9.21.29"',manifest)
        self.assertIn("cook4me-panel-v162.js?v=2026.9.21.27",ui)

    def test_starch_mixture_context_is_preserved(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "cornstarch diluted in a little water":"Άμυλο καλαμποκιού αραιωμένο σε λίγο νερό",
            "cornstarch diluted in a little almond milk":"Άμυλο καλαμποκιού αραιωμένο σε λίγο γάλα αμυγδάλου",
            "cornstarch dissolved in a small amount of almond milk":"Άμυλο καλαμποκιού διαλυμένο σε μικρή ποσότητα γάλακτος αμυγδάλου",
            "cornstarch mixed with a little water":"Άμυλο καλαμποκιού ανακατεμένο με λίγο νερό",
            "cornstarch in a little wine":"Άμυλο καλαμποκιού σε λίγο κρασί",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_product_form_is_not_collapsed(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "canned whole-kernel corn":"Ολόκληροι κόκκοι καλαμποκιού κονσέρβας",
            "frozen kibbeh balls":"Κατεψυγμένα μπαλάκια κίμπε",
            "melon balls":"Μπαλάκια πεπονιού",
            "turkey strips":"Λωρίδες γαλοπούλας",
            "turkey breast strips":"Λωρίδες στήθους γαλοπούλας",
            "chicken fingers or strips":"Φιλετάκια ή λωρίδες κοτόπουλου",
            "whole black peppercorns":"Ολόκληροι κόκκοι μαύρου πιπεριού",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_recipe_use_context_is_preserved(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "arborio rice for risotto":"Ρύζι αρμπόριο για ριζότο",
            "bulgur for pilaf":"Πλιγούρι για πιλάφι",
            "carnaroli rice for risotto":"Ρύζι καρναρόλι για ριζότο",
            "egg yolk for the sauce":"Κρόκος αυγού για τη σάλτσα",
            "fine bulgur for meatball":"Ψιλό πλιγούρι για κεφτέδες",
            "mixed dried and smoked fruit for compote":"Ανάμεικτα αποξηραμένα και καπνιστά φρούτα για κομπόστα",
            "semi-salted butter to add to the chocolate":"Ημιαλατισμένο βούτυρο για προσθήκη στη σοκολάτα",
            "vegetable oil for cooking":"Φυτικό λάδι για μαγείρεμα",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_singular_and_unit_fragments_are_preserved(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "dried fig":"Αποξηραμένο σύκο",
            "spinach leaf":"Φύλλο σπανακιού",
            "kaffir lime leaf":"Φύλλο λάιμ μακρούτ",
            "makrut lime leaf":"Φύλλο λάιμ μακρούτ",
            "g cabbage":"γρ. λάχανο",
            "g vinegar":"γρ. ξίδι",
            "litre of prepared sour rye starter for zur":"1 λίτρο έτοιμου ξινού προζυμιού σίκαλης για ζουρ",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_search_aliases_cover_eighteenth_pass_terms(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("άμυλο καλαμποκιού σε λίγο νερό",aliases["cornstarch diluted in a little water"])
        self.assertIn("μπαλάκια πεπονιού",aliases["melon balls"])
        self.assertIn("λωρίδες γαλοπούλας",aliases["turkey strips"])
        self.assertIn("αρμπόριο για ριζότο",aliases["arborio rice for risotto"])
        self.assertIn("σκόρδο χωρίς φύτρο",aliases["garlic with the germ removed"])
        self.assertIn("φύλλο σπανακιού",aliases["spinach leaf"])

    def test_curated_scope_expanded_eighteenth_time(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["labels"]),923)
        self.assertGreaterEqual(len(data["searchAliases"]),386)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
