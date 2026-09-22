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
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v160_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GreekCatalogAuditV160Tests(unittest.TestCase):
    def test_v160_is_inherited_by_active_v161(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v160.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v175",panel)
        self.assertIn("cook4me-panel-v175.js",panel)
        self.assertIn("/cook4me_static/2026.9.22.2",panel)
        self.assertIn("?v=2026.9.22.2",panel)
        self.assertIn('"version": "2026.9.22.2"',manifest)
        self.assertIn("cook4me-panel-v159.js?v=2026.9.21.24",ui)

    def test_packaging_words_are_not_dropped(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "jar of fish stock":"Βάζο ζωμού ψαριού",
            "small bottle of almond flavouring":"Μικρό μπουκαλάκι αρώματος αμυγδάλου",
            "malted barley packet":"Συσκευασία βυνοποιημένου κριθαριού",
            "package of pre-cooked udon noodle":"Συσκευασία προμαγειρεμένων udon noodles",
            "package of salted nachos":"Συσκευασία αλατισμένων nachos",
            "packet chinese soup":"Φακελάκι κινέζικης σούπας",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_singular_source_items_remain_singular(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "anchovy fillet":"Φιλέτο αντζούγιας",
            "anchovy fillet in oil":"Φιλέτο αντζούγιας σε λάδι",
            "graham cracker":"Μπισκότο Graham",
            "kaiser roll":"Ψωμάκι Kaiser",
            "pork slice":"Φέτα χοιρινού",
            "fresh mini meatball":"Φρέσκο μίνι κεφτεδάκι",
            "fresh mussel":"Φρέσκο μύδι",
            "fresh potato":"Φρέσκια πατάτα",
            "frozen artichoke":"Κατεψυγμένη αγκινάρα",
            "frozen beef meatball":"Κατεψυγμένο μοσχαρίσιο κεφτεδάκι",
            "frozen king prawn":"Κατεψυγμένη μεγάλη γαρίδα",
            "frozen mushroom":"Κατεψυγμένο μανιτάρι",
            "dried apricot":"Αποξηραμένο βερίκοκο",
            "dried blueberry":"Αποξηραμένο μύρτιλο",
            "dried mushroom":"Αποξηραμένο μανιτάρι",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_stalk_and_piece_forms_are_preserved(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        self.assertEqual(labels["fresh spring onion stalk"],"Κοτσάνι φρέσκου κρεμμυδιού")
        self.assertEqual(labels["spring onion stalk"],"Κοτσάνι φρέσκου κρεμμυδιού")
        self.assertEqual(labels["stalk of spring onion"],"Κοτσάνι φρέσκου κρεμμυδιού")
        self.assertEqual(labels["piece of crustless white bread"],"Κομμάτι λευκού ψωμιού χωρίς κόρα")
        self.assertEqual(labels["slice of crustless sandwich bread"],"Φέτα ψωμιού τοστ χωρίς κόρα")

    def test_search_aliases_cover_fifteenth_pass_terms(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("βάζο ζωμού ψαριού",aliases["jar of fish stock"])
        self.assertIn("μπουκαλάκι αρώματος αμυγδάλου",aliases["small bottle of almond flavouring"])
        self.assertIn("φιλέτο αντζούγιας",aliases["anchovy fillet"])
        self.assertIn("ψωμάκι kaiser",aliases["kaiser roll"])
        self.assertIn("fresh mussel",aliases["fresh mussel"])
        self.assertIn("frozen mushroom",aliases["frozen mushroom"])
        self.assertIn("dried apricot",aliases["dried apricot"])

    def test_curated_scope_expanded_fifteenth_time(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["labels"]),644)
        self.assertGreaterEqual(len(data["searchAliases"]),312)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
