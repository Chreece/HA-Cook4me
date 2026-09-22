from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"
CURATED=ROOT/"custom_components"/"cook4me"/"catalog_ui_locales"/"zz_el_curated.json"


class GreekCatalogAuditV186Tests(unittest.TestCase):
    def test_backend_only_audit_keeps_current_frontend_build(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v180",panel)
        self.assertIn("cook4me-panel-v180.js",panel)
        self.assertIn("/cook4me_static/2026.9.22.7",panel)
        self.assertIn('"version": "2026.9.22.7"',manifest)

    def test_forty_first_pass_large_mixed_language_cleanup(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
    "white pudding": "Λευκό λουκάνικο (white pudding)",
    "curd cheese": "Φρέσκο τυρί κουάρκ (quark)",
    "cream quark": "Κρεμώδες τυρί κουάρκ (quark)",
    "beefsteak tomato": "Μεγάλη σαρκώδης ντομάτα (beefsteak)",
    "boudin blanc": "Λευκό λουκάνικο μπουντέν μπλαν (boudin blanc)",
    "fromage blanc": "Φρέσκο τυρί φρομάζ μπλαν (fromage blanc)",
    "black cabbage": "Μαύρο λάχανο (cavolo nero)",
    "cavolo nero": "Μαύρο λάχανο (cavolo nero)",
    "calvo nero": "Μαύρο λάχανο (cavolo nero)",
    "calvo nero or kale": "Μαύρο λάχανο (cavolo nero) ή κέιλ",
    "full-fat creme fraiche": "Πλήρης κρεμ φρες (crème fraîche)",
    "thick full-fat creme fraiche": "Παχύρρευστη πλήρης κρεμ φρες (crème fraîche)",
    "runner bean": "Αναρριχώμενα φασόλια (runner beans)",
    "snow pea": "Μπιζέλια μανζτού (mangetout / snow peas)",
    "boiled snow pea": "Βρασμένα μπιζέλια μανζτού (mangetout)",
    "frozen edamame": "Κατεψυγμένο ενταμάμε (edamame)",
    "frozen edamame bean": "Κατεψυγμένο ενταμάμε (edamame)",
    "frozen edamame pods": "Κατεψυγμένο ενταμάμε με τον λοβό (edamame)",
    "onion squash": "Χειμωνιάτικη κολοκύθα (onion squash)",
    "large beefsteak tomato": "Μεγάλη σαρκώδης ντομάτα (beefsteak)",
    "scampi with tails": "Καραβίδες με ουρές (scampi)",
    "chia seed": "Σπόροι τσία (chia)",
    "wood ear mushroom": "Μανιτάρι «αυτί του Ιούδα» (wood ear)",
    "dried wood ear mushroom": "Αποξηραμένο μανιτάρι «αυτί του Ιούδα» (wood ear)",
    "king oyster mushroom": "Μανιτάρι ερίντζι (king oyster)",
    "button mushroom": "Λευκό μανιτάρι σαμπινιόν (champignon)",
    "fresh button mushroom": "Φρέσκο λευκό μανιτάρι σαμπινιόν (champignon)",
    "mushroom / button mushroom": "Μανιτάρια / λευκά σαμπινιόν (champignon)",
    "chestnut mushroom": "Καφέ μανιτάρι σαμπινιόν (champignon)",
    "jasmine rice": "Ρύζι γιασεμί (jasmine)",
    "worcestershire sauce": "Σάλτσα Γούστερ (Worcestershire)",
    "worcestershire-style sauce": "Σάλτσα τύπου Γούστερ (Worcestershire)",
    "worcester sauce": "Σάλτσα Γούστερ (Worcestershire)",
    "monk fruit sweetener": "Γλυκαντικό λουό χαν γκουό (monk fruit)",
    "white bitter melon": "Λευκό πικρό πεπόνι (bitter melon)",
    "japanese dashi stock granules": "Κόκκοι ιαπωνικού ντάσι (dashi)",
    "store-bought seasoned inari tofu pouches": "Έτοιμα καρυκευμένα πουγκιά τηγανητού τόφου ινάρι-άγκε (inari-age)",
    "firm atsuage fried tofu": "Σφιχτό τηγανητό τόφου ατσουάγκε (atsuage)",
    "silken atsuage fried tofu": "Μαλακό τηγανητό τόφου ατσουάγκε (atsuage)",
    "large ganmodoki fried tofu": "Μεγάλο τηγανητό τόφου με λαχανικά γκανμοντόκι (ganmodoki)",
    "kidney bean": "Φασόλια κίντνεϊ (kidney beans)",
    "red kidney bean": "Κόκκινα φασόλια κίντνεϊ (kidney beans)",
    "canned red kidney bean": "Κόκκινα φασόλια κίντνεϊ κονσέρβας (kidney beans)",
    "dried kidney bean": "Ξερά φασόλια κίντνεϊ (kidney beans)",
    "cannellini bean": "Φασόλια κανελίνι (cannellini)",
    "soaked cannellini bean": "Μουλιασμένα φασόλια κανελίνι (cannellini)",
    "lima bean": "Φασόλια λίμα (lima beans)",
    "mung bean": "Φασόλια μουνγκ (mung beans)",
    "mung bean sprouts": "Φύτρα μουνγκ (mung bean sprouts)",
    "shiso leaf": "Φύλλο σίσο (shiso)",
    "konjac noodle": "Νουντλς σιρατάκι / κόντζακ (shirataki / konjac)",
    "boiled somen noodle": "Βρασμένα νουντλς σόμεν (somen)",
    "ramen noodle": "Νουντλς ράμεν (ramen)",
    "udon noodle": "Νουντλς ούντον (udon)",
    "fresh udon noodle": "Φρέσκα νουντλς ούντον (udon)",
    "package of pre-cooked udon noodle": "Συσκευασία προμαγειρεμένων νουντλς ούντον (udon)",
    "whole albacore tuna": "Ολόκληρος λευκός τόνος (albacore)",
    "package of skyr": "Συσκευασία σκιρ (skyr)",
    "daikon radish sprouts": "Φύτρα ντάικον (daikon)",
    "daikon sprouts": "Φύτρα ντάικον (daikon)",
    "gochujang sauce": "Σάλτσα γκοτσουτζάνγκ (gochujang)",
    "sambal sauce": "Σάλτσα σάμπαλ (sambal)",
    "instant miso soup mix": "Μείγμα για στιγμιαία σούπα μίσο (miso)",
    "store-bought yakiniku sauce": "Έτοιμη σάλτσα γιακινίκου (yakiniku)",
    "canned yakitori in tare sauce": "Κονσέρβα γιακιτόρι σε σάλτσα τάρε (yakitori tare)",
    "teriyaki marinade sauce": "Σάλτσα / μαρινάδα τεριγιάκι (teriyaki)",
    "dried daikon strips": "Αποξηραμένες λωρίδες ντάικον (daikon)",
    "slices of gingerbread": "Φέτες μελόψωμου (gingerbread)",
    "dried shiitake mushroom": "Αποξηραμένο μανιτάρι σιτάκε (shiitake)",
    "enoki mushroom": "Μανιτάρι ενόκι (enoki)",
    "fresh shiitake mushroom": "Φρέσκο μανιτάρι σιτάκε (shiitake)",
    "maitake mushroom": "Μανιτάρι μαϊτάκε (maitake)",
    "nameko mushroom": "Μανιτάρι ναμέκο (nameko)",
    "porcini mushroom": "Μανιτάρι πορτσίνι (porcini)",
    "shiitake mushroom": "Μανιτάρι σιτάκε (shiitake)",
    "shimeji mushroom": "Μανιτάρι σιμέτζι (shimeji)",
    "small dried shiitake mushroom": "Μικρό αποξηραμένο μανιτάρι σιτάκε (shiitake)",
    "white shimeji mushroom": "Λευκό μανιτάρι σιμέτζι (shimeji)",
    "package of salted nachos": "Συσκευασία αλατισμένων νάτσος (nachos)",
    "graham cracker": "Μπισκότο Γκράχαμ (Graham cracker)",
    "kaiser roll": "Ψωμάκι Κάιζερ (Kaiser roll)",
    "tablespoon of mirin": "1 κ.σ. μίριν (mirin)",
    "tbsp mirin": "1 κ.σ. μίριν (mirin)",
    "tbsp sherry vinegar": "1 κ.σ. ξίδι σέρι (sherry)",
    "tsp madras curry blend": "1 κ.γ. μείγμα κάρι Μαδράς (Madras)",
    "tsp miso paste": "1 κ.γ. πάστα μίσο (miso)",
    "tsp tandoori spices": "1 κ.γ. μπαχαρικά ταντούρι (tandoori)",
    "tsp tex-mex spice blend": "1 κ.γ. μείγμα μπαχαρικών Τεξ-Μεξ (Tex-Mex)"
}
        self.assertEqual(len(expected),88)
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value,key)
            self.assertRegex(value,r"[\u0370-\u03FF]",key)

    def test_old_labels_source_keys_and_new_labels_all_remain_searchable(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        legacy={
    "white pudding": "Λευκό λουκάνικο τύπου white pudding",
    "curd cheese": "Φρέσκο τυρί τύπου quark",
    "cream quark": "Κρεμώδες τυρί quark",
    "beefsteak tomato": "Ντομάτα beefsteak (μεγάλη σαρκώδης)",
    "boudin blanc": "Λευκό λουκάνικο boudin blanc",
    "fromage blanc": "Φρέσκο τυρί fromage blanc",
    "black cabbage": "Cavolo nero (μαύρο λάχανο)",
    "cavolo nero": "Cavolo nero (μαύρο λάχανο)",
    "calvo nero": "Cavolo nero (μαύρο λάχανο)",
    "calvo nero or kale": "Cavolo nero ή κέιλ",
    "full-fat creme fraiche": "Πλήρης crème fraîche",
    "thick full-fat creme fraiche": "Παχύρρευστη πλήρης crème fraîche",
    "runner bean": "Φασόλια runner (αναρριχώμενα)",
    "snow pea": "Μπιζέλια mangetout (snow peas)",
    "boiled snow pea": "Βρασμένα μπιζέλια mangetout",
    "frozen edamame": "Κατεψυγμένα edamame",
    "frozen edamame bean": "Κατεψυγμένα edamame",
    "frozen edamame pods": "Κατεψυγμένα edamame με τον λοβό",
    "onion squash": "Κολοκύθα onion squash (χειμωνιάτικη)",
    "large beefsteak tomato": "Μεγάλη ντομάτα beefsteak (σαρκώδης)",
    "scampi with tails": "Καραβίδες scampi με ουρές",
    "chia seed": "Σπόροι chia (τσία)",
    "wood ear mushroom": "Μανιτάρι wood ear (αυτί του Ιούδα)",
    "dried wood ear mushroom": "Αποξηραμένο μανιτάρι wood ear (αυτί του Ιούδα)",
    "king oyster mushroom": "Μανιτάρι eryngii (king oyster)",
    "button mushroom": "Λευκό μανιτάρι champignon",
    "fresh button mushroom": "Φρέσκο λευκό μανιτάρι champignon",
    "mushroom / button mushroom": "Μανιτάρια / λευκά champignon",
    "chestnut mushroom": "Καφέ μανιτάρι champignon",
    "jasmine rice": "Ρύζι jasmine (γιασεμί)",
    "worcestershire sauce": "Σάλτσα Worcestershire (Γούστερ)",
    "worcestershire-style sauce": "Σάλτσα τύπου Worcestershire",
    "worcester sauce": "Σάλτσα Worcestershire (Γούστερ)",
    "monk fruit sweetener": "Γλυκαντικό monk fruit (λουό χαν γκουό)",
    "white bitter melon": "Λευκό bitter melon (πικρό πεπόνι)",
    "japanese dashi stock granules": "Κόκκοι ιαπωνικού dashi",
    "store-bought seasoned inari tofu pouches": "Έτοιμα καρυκευμένα inari-age (πουγκιά τηγανητού τόφου)",
    "firm atsuage fried tofu": "Σφιχτό atsuage (τηγανητό τόφου)",
    "silken atsuage fried tofu": "Μαλακό atsuage (τηγανητό τόφου)",
    "large ganmodoki fried tofu": "Μεγάλο Ganmodoki (τηγανητό τόφου με λαχανικά)",
    "kidney bean": "Φασόλια kidney",
    "red kidney bean": "Κόκκινα φασόλια kidney",
    "canned red kidney bean": "Κόκκινα φασόλια kidney κονσέρβας",
    "dried kidney bean": "Ξερά φασόλια kidney",
    "cannellini bean": "Φασόλια cannellini",
    "soaked cannellini bean": "Μουλιασμένα φασόλια cannellini",
    "lima bean": "Φασόλια Lima",
    "mung bean": "Φασόλια mung",
    "mung bean sprouts": "Φύτρα mung",
    "shiso leaf": "Φύλλο shiso",
    "konjac noodle": "Νουντλς shirataki / konjac",
    "boiled somen noodle": "Βρασμένα νουντλς somen",
    "ramen noodle": "Νουντλς ramen",
    "udon noodle": "Νουντλς udon",
    "fresh udon noodle": "Φρέσκα νουντλς udon",
    "package of pre-cooked udon noodle": "Συσκευασία προμαγειρεμένων νουντλς udon",
    "whole albacore tuna": "Ολόκληρος τόνος albacore (λευκός τόνος)",
    "package of skyr": "Συσκευασία skyr",
    "daikon radish sprouts": "Φύτρα daikon",
    "daikon sprouts": "Φύτρα daikon",
    "gochujang sauce": "Σάλτσα gochujang",
    "sambal sauce": "Σάλτσα sambal",
    "instant miso soup mix": "Μείγμα για στιγμιαία σούπα miso",
    "store-bought yakiniku sauce": "Έτοιμη σάλτσα yakiniku",
    "canned yakitori in tare sauce": "Κονσέρβα yakitori σε σάλτσα tare",
    "teriyaki marinade sauce": "Σάλτσα / μαρινάδα teriyaki",
    "dried daikon strips": "Αποξηραμένες λωρίδες daikon",
    "slices of gingerbread": "Φέτες gingerbread",
    "dried shiitake mushroom": "Αποξηραμένο μανιτάρι shiitake",
    "enoki mushroom": "Μανιτάρι enoki",
    "fresh shiitake mushroom": "Φρέσκο μανιτάρι shiitake",
    "maitake mushroom": "Μανιτάρι maitake",
    "nameko mushroom": "Μανιτάρι nameko",
    "porcini mushroom": "Μανιτάρι porcini",
    "shiitake mushroom": "Μανιτάρι shiitake",
    "shimeji mushroom": "Μανιτάρι shimeji",
    "small dried shiitake mushroom": "Μικρό αποξηραμένο μανιτάρι shiitake",
    "white shimeji mushroom": "Λευκό μανιτάρι shimeji",
    "package of salted nachos": "Συσκευασία αλατισμένων nachos",
    "graham cracker": "Μπισκότο Graham",
    "kaiser roll": "Ψωμάκι Kaiser",
    "tablespoon of mirin": "1 κ.σ. mirin",
    "tbsp mirin": "1 κ.σ. mirin",
    "tbsp sherry vinegar": "1 κ.σ. ξίδι sherry",
    "tsp madras curry blend": "1 κ.γ. μείγμα κάρι Madras",
    "tsp miso paste": "1 κ.γ. πάστα miso",
    "tsp tandoori spices": "1 κ.γ. μπαχαρικά tandoori",
    "tsp tex-mex spice blend": "1 κ.γ. μείγμα μπαχαρικών Tex-Mex"
}
        for key,old_label in legacy.items():
            aliases={str(value).strip().casefold() for value in data["searchAliases"][key]}
            self.assertIn(key.casefold(),aliases,key)
            self.assertIn(old_label.casefold(),aliases,key)
            self.assertIn(data["labels"][key].casefold(),aliases,key)
            raw=[str(value).strip().casefold() for value in data["searchAliases"][key]]
            self.assertEqual(len(raw),len(set(raw)),key)

    def test_forty_first_audit_scope(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        alias_entries=sum(len(values) for values in data["searchAliases"].values())
        self.assertGreaterEqual(len(data["labels"]),1278)
        self.assertEqual(len(data["searchAliases"]),3689)
        self.assertGreaterEqual(alias_entries,8967)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
