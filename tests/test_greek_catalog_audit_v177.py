from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"
BASE=ROOT/"custom_components"/"cook4me"/"catalog_ui_locales"/"el.json"
CURATED=ROOT/"custom_components"/"cook4me"/"catalog_ui_locales"/"zz_el_curated.json"

INTENTIONAL_PARSER_FRAGMENTS={
    "confit of","cups of","fleur de sel and","grams of","half a","handful of",
    "large","peeled","pinch of","portion of","red","salt and","sprig of",
    "tablespoon of","tails of","tbsp","teaspoon of dried","tender","thick",
    "tomato or","tsp","tsp fresh","washed","whole",
}


class GreekCatalogAuditV177Tests(unittest.TestCase):
    def test_v177_is_inherited_by_active_v178(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v177.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v178",panel)
        self.assertIn("cook4me-panel-v178.js",panel)
        self.assertIn("/cook4me_static/2026.9.22.5",panel)
        self.assertIn("?v=2026.9.22.5",panel)
        self.assertIn('"version": "2026.9.22.5"',manifest)
        self.assertIn("cook4me-panel-v176.js?v=2026.9.22.3",ui)

    def test_every_real_alias_group_contains_source_and_display_label(self):
        base=json.loads(BASE.read_text(encoding="utf-8"))
        curated=json.loads(CURATED.read_text(encoding="utf-8"))
        for key,values in curated["searchAliases"].items():
            if key in INTENTIONAL_PARSER_FRAGMENTS:
                continue
            normalized={str(value).strip().casefold() for value in values}
            self.assertIn(key.strip().casefold(),normalized,key)
            label=str(curated["labels"].get(key,base["labels"].get(key,""))).strip()
            self.assertTrue(label,key)
            self.assertIn(label.casefold(),normalized,key)

    def test_parser_fragments_stay_unsearchable(self):
        aliases=json.loads(CURATED.read_text(encoding="utf-8"))["searchAliases"]
        for key in INTENTIONAL_PARSER_FRAGMENTS:
            self.assertNotIn(key,aliases)

    def test_representative_integrity_repairs(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        aliases=data["searchAliases"]
        expected={
            "veal":("veal","μοσχαράκι"),
            "watercress":("watercress","νεροκάρδαμο"),
            "cornflour":("cornflour","Κορν φλάουρ (άμυλο καλαμποκιού)"),
            "curd cheese":("curd cheese","Φρέσκο τυρί τύπου quark"),
            "kohlrabi":("kohlrabi","Κολράμπι (γογγυλοκράμβη)"),
            "mace":("mace","Μασίς (άνθος μοσχοκάρυδου)"),
            "saffron":("saffron","Σαφράν (κρόκος)"),
            "pork spare rib":("pork spare rib","Χοιρινά παϊδάκια (spare ribs)"),
            "sole":("sole","Γλώσσα (ψάρι)"),
            "oxtail":("oxtail","Μοσχαρίσια ουρά"),
            "bonito flakes":("bonito flakes","Κατσουομπούσι (νιφάδες παλαμίδας)"),
            "wood ear mushroom":("wood ear mushroom","Μανιτάρι wood ear (αυτί του Ιούδα)"),
        }
        for key,(source,label) in expected.items():
            normalized={str(v).casefold() for v in aliases[key]}
            self.assertIn(source.casefold(),normalized,key)
            self.assertIn(label.casefold(),normalized,key)

    def test_large_integrity_sweep_scope(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        alias_entries=sum(len(values) for values in data["searchAliases"].values())
        self.assertGreaterEqual(len(data["labels"]),1272)
        self.assertEqual(len(data["searchAliases"]),3689)
        self.assertGreaterEqual(alias_entries,8755)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
