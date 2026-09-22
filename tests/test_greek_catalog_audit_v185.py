from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"
CURATED=ROOT/"custom_components"/"cook4me"/"catalog_ui_locales"/"zz_el_curated.json"


class GreekCatalogAuditV185Tests(unittest.TestCase):
    def test_backend_only_audit_keeps_current_frontend_build(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v180",panel)
        self.assertIn("cook4me-panel-v180.js",panel)
        self.assertIn("/cook4me_static/2026.9.22.7",panel)
        self.assertIn('"version": "2026.9.22.7"',manifest)

    def test_fortieth_pass_uses_greek_readable_specialty_food_labels(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "sake lees":"Υπόλειμμα ζύμωσης σάκε (sake kasu)",
            "milk jam":"Καραμελωμένο γάλα (dulce de leche)",
            "fromage frais":"Φρέσκο τυρί (fromage frais)",
            "herbed fromage frais":"Φρέσκο τυρί με μυρωδικά (fromage frais)",
            "herbed fromage frais cheese":"Φρέσκο τυρί με μυρωδικά (fromage frais)",
            "ricotta salata":"Αλατισμένη ρικότα (ricotta salata)",
            "tarako cod roe":"Αυγά μπακαλιάρου ταράκο (tarako)",
            "hijiki seaweed":"Φύκια χιτζίκι (hijiki)",
            "aonori":"Πράσινα φύκια αονόρι (aonori)",
            "mentsuyu":"Συμπυκνωμένη βάση για νουντλς μεντσούγιου (mentsuyu)",
            "mentsuyu noodle soup base":"Συμπυκνωμένη βάση για νουντλς μεντσούγιου (mentsuyu)",
            "nuoc mam fish sauce":"Βιετναμέζικη σάλτσα ψαριού νουόκ μαμ (nước mắm)",
            "nuoc-mam fish sauce":"Βιετναμέζικη σάλτσα ψαριού νουόκ μαμ (nước mắm)",
            "shiro dashi":"Λευκή βάση ντάσι (shiro dashi)",
            "doubanjiang":"Πικάντικη ζυμωμένη πάστα φασολιών ντουμπαντζιάνγκ (doubanjiang)",
            "shaoxing wine":"Κινέζικο κρασί ρυζιού Σαοσίνγκ (Shaoxing)",
            "salted fermented shrimp":"Αλατισμένες ζυμωμένες γαρίδες σεουτζότ (saeujeot)",
            "thick tofu skin":"Παχιά πέτσα τόφου γιούμπα (yuba)",
            "atsuage fried tofu":"Τηγανητό τόφου ατσουάγκε (atsuage)",
            "atsuage fried tofu, 130 g per piece":"Τηγανητό τόφου ατσουάγκε (atsuage), 130 g το τεμάχιο",
            "aburaage":"Λεπτό τηγανητό τόφου αμπουραάγκε (aburaage)",
            "shiso":"Ιαπωνική περίλλα σίσο (shiso)",
            "gochugaru":"Κορεάτικο τσίλι γκοτσουγκάρου (gochugaru)",
            "gochugaru chili flakes":"Κορεάτικες νιφάδες τσίλι γκοτσουγκάρου (gochugaru)",
            "shichimi chili pepper":"Ιαπωνικό μείγμα 7 μπαχαρικών σιτσίμι τογκαράσι (shichimi togarashi)",
            "shichimi chili seasoning":"Ιαπωνικό μείγμα 7 μπαχαρικών σιτσίμι τογκαράσι (shichimi togarashi)",
            "shichimi togarashi":"Ιαπωνικό μείγμα 7 μπαχαρικών σιτσίμι τογκαράσι (shichimi togarashi)",
            "ichimi chili pepper":"Ιαπωνικό τσίλι ιτσίμι τογκαράσι (ichimi togarashi)",
            "sansho pepper":"Ιαπωνικό πιπέρι σάνσο (sansho)",
            "yuzu kosho":"Πάστα γιούζου και τσίλι γιούζου κόσο (yuzu kosho)",
            "gochujang":"Κορεάτικη πάστα τσίλι γκοτσουτζάνγκ (gochujang)",
            "doenjang":"Κορεάτικη πάστα σόγιας ντοεντζάνγκ (doenjang)",
            "cheonggukjang fermented soybean paste":"Κορεάτικη πάστα ζυμωμένης σόγιας τσονγκουκτζάνγκ (cheonggukjang)",
            "ajvar":"Βαλκανική πάστα ψητής πιπεριάς άιβαρ (ajvar)",
            "sambal":"Ινδονησιακό καυτερό καρύκευμα σάμπαλ (sambal)",
            "tianmianjiang sweet bean sauce":"Γλυκιά πάστα φασολιών τιανμιεντζιάνγκ (tianmianjiang)",
            "yakiniku sauce":"Ιαπωνική σάλτσα για ψητό κρέας γιακινίκου (yakiniku)",
            "yakitori sauce":"Ιαπωνική σάλτσα τάρε για γιακιτόρι (yakitori tare)",
            "sweet red bean paste":"Γλυκιά πάστα κόκκινων φασολιών άνκο (anko)",
            "smooth red bean paste":"Λεία πάστα κόκκινων φασολιών κόσιαν (koshi-an)",
            "chunky red bean paste":"Πάστα κόκκινων φασολιών με κομμάτια τσουμπουάν (tsubu-an)",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value,key)

    def test_source_names_and_new_display_labels_remain_searchable(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        old_labels={
            "sake lees":"Sake kasu (υπόλειμμα ζύμωσης σάκε)",
            "milk jam":"Dulce de leche (καραμελωμένο γάλα)",
            "fromage frais":"Fromage frais (φρέσκο τυρί)",
            "ricotta salata":"Ricotta salata (αλατισμένη ρικότα)",
            "tarako cod roe":"Tarako (αυγά μπακαλιάρου)",
            "hijiki seaweed":"Hijiki (φύκια χιτζίκι)",
            "aonori":"Aonori (πράσινα φύκια)",
            "mentsuyu":"Mentsuyu (συμπυκνωμένη βάση για νουντλς)",
            "nuoc mam fish sauce":"Nước mắm (βιετναμέζικη σάλτσα ψαριού)",
            "shiro dashi":"Shiro dashi (λευκή βάση dashi)",
            "doubanjiang":"Doubanjiang (πικάντικη ζυμωμένη πάστα φασολιών)",
            "shaoxing wine":"Shaoxing (κινέζικο κρασί ρυζιού)",
            "salted fermented shrimp":"Saeujeot (αλατισμένες ζυμωμένες γαρίδες)",
            "thick tofu skin":"Yuba (παχιά πέτσα τόφου)",
            "atsuage fried tofu":"Atsuage (τηγανητό τόφου)",
            "aburaage":"Aburaage (λεπτό τηγανητό τόφου)",
            "gochugaru":"Gochugaru (κορεάτικο τσίλι)",
            "shichimi togarashi":"Shichimi togarashi (ιαπωνικό μείγμα 7 μπαχαρικών)",
            "gochujang":"Gochujang (κορεάτικη πάστα τσίλι)",
            "doenjang":"Doenjang (κορεάτικη πάστα σόγιας)",
            "cheonggukjang fermented soybean paste":"Cheonggukjang (κορεάτικη πάστα ζυμωμένης σόγιας)",
            "ajvar":"Ajvar (βαλκανική πάστα ψητής πιπεριάς)",
            "sambal":"Sambal (ινδονησιακό καυτερό καρύκευμα)",
            "tianmianjiang sweet bean sauce":"Tianmianjiang (γλυκιά πάστα φασολιών)",
            "yakiniku sauce":"Yakiniku sauce (ιαπωνική σάλτσα για ψητό κρέας)",
            "yakitori sauce":"Yakitori tare (ιαπωνική σάλτσα yakitori)",
            "sweet red bean paste":"Anko (γλυκιά πάστα κόκκινων φασολιών)",
            "smooth red bean paste":"Koshi-an (λεία πάστα κόκκινων φασολιών)",
            "chunky red bean paste":"Tsubu-an (πάστα κόκκινων φασολιών με κομμάτια)",
        }
        for key,old_label in old_labels.items():
            aliases={str(value).strip().casefold() for value in data["searchAliases"][key]}
            self.assertIn(key.casefold(),aliases,key)
            self.assertIn(old_label.casefold(),aliases,key)
            self.assertIn(data["labels"][key].casefold(),aliases,key)

    def test_fortieth_audit_scope(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        alias_entries=sum(len(values) for values in data["searchAliases"].values())
        self.assertGreaterEqual(len(data["labels"]),1278)
        self.assertEqual(len(data["searchAliases"]),3689)
        self.assertGreaterEqual(alias_entries,8879)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
