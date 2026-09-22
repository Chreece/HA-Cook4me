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
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v168_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GreekCatalogAuditV168Tests(unittest.TestCase):
    def test_v168_is_inherited_by_active_v177(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v168.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v177",panel)
        self.assertIn("cook4me-panel-v177.js",panel)
        self.assertIn("/cook4me_static/2026.9.22.4",panel)
        self.assertIn("?v=2026.9.22.4",panel)
        self.assertIn('"version": "2026.9.22.4"',manifest)
        self.assertIn("cook4me-panel-v167.js?v=2026.9.21.32",ui)

    def test_oil_flour_and_grain_aliases(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("ελαιόλαδο",aliases["olive oil"])
        self.assertIn("έξτρα παρθένο ελαιόλαδο",aliases["extra virgin olive oil"])
        self.assertIn("ηλιέλαιο",aliases["sunflower oil"])
        self.assertIn("κραμβέλαιο",aliases["rapeseed oil"])
        self.assertIn("ρυζάλευρο",aliases["rice flour"])
        self.assertIn("ρύζι μπασμάτι",aliases["basmati rice"])
        self.assertIn("αρμπόριο",aliases["arborio rice"])
        self.assertIn("καρναρόλι",aliases["carnaroli rice"])
        self.assertIn("πλιγούρι",aliases["bulgur"])

    def test_produce_and_pantry_aliases(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        for key in (
            "apple","pear","peach","apricot","banana","lemon","lime","orange",
            "grapefruit","pineapple","watermelon","melon","kiwi","mango",
            "tomato","potato","onion","garlic","carrot","eggplant","zucchini",
            "spinach","broccoli","cauliflower"
        ):
            self.assertIn(key,aliases)
            self.assertGreaterEqual(len(aliases[key]),2)

    def test_baking_and_sauce_aliases(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("άχνη",aliases["icing sugar"])
        self.assertIn("μπέικιν πάουντερ",aliases["baking powder"])
        self.assertIn("μαγειρική σόδα",aliases["baking soda"])
        self.assertIn("εκχύλισμα βανίλιας",aliases["vanilla extract"])
        self.assertIn("κακάο",aliases["cocoa powder"])
        self.assertIn("κουβερτούρα",aliases["baking chocolate"])
        self.assertIn("πελτές ντομάτας",aliases["tomato paste"])
        self.assertIn("πασάτα",aliases["tomato passata"])
        self.assertIn("σάλτσα σόγιας",aliases["soy sauce"])

    def test_pasta_dairy_and_protein_aliases(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("λαζάνια",aliases["lasagna"])
        self.assertIn("πένες",aliases["penne"])
        self.assertIn("σπαγγέτι",aliases["spaghetti"])
        self.assertIn("κριθαράκι",aliases["orzo"])
        self.assertIn("νιόκι",aliases["gnocchi"])
        self.assertIn("φέτα",aliases["feta"])
        self.assertIn("κατσικίσιο τυρί",aliases["goat cheese"])
        self.assertIn("μοσχαρίσιος κιμάς",aliases["ground beef"])
        self.assertIn("πανσέτα",aliases["pork belly"])
        self.assertIn("τόφου",aliases["tofu"])
        self.assertIn("σεϊτάν",aliases["seitan"])

    def test_large_search_batch_scope(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["labels"]),1253)
        self.assertGreaterEqual(len(data["searchAliases"]),820)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
