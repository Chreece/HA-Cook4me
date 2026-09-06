from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "custom_components/cook4me/recipe_grouping.py"
spec = importlib.util.spec_from_file_location("cook4me_recipe_grouping_proof", path)
grouping = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(grouping)


PROOF = {
    "237284": ("Risotto \"Aus Vorräten\"", [("241598", 2), ("241599", 4), ("241600", 6)]),
    "257575": ("Pfifferling-Risotto", [("270858", 2), ("270859", 4), ("270860", 6)]),
    "1959890": ("Risotto mit roten Linsen", [("395110", 6)]),
    "232130": ("Pesto-Hähnchen-Risotto", [("232850", 2), ("232862", 4), ("232865", 6)]),
    "232124": ("Erbsen-Schinken-Risotto", [("232835", 2), ("232841", 4), ("232845", 6)]),
    "232190": ("Erbsen-Minze-Risotto", [("232991", 2), ("232994", 4), ("232996", 6)]),
    "1004968": ("Buchweizen-Pilz-Risotto", [("316526", 2), ("316525", 4), ("316524", 6)]),
    "2308071": ("Heidelbeer-Ziegenkäse-Risotto", [("467132", 2), ("467133", 4), ("467134", 6)]),
    "2433340": ("Karotten-Muschelnudel-Risotto", [("503261", 6)]),
    "232157": ("Spinatrisotto", [("232928", 2), ("232931", 4), ("232932", 6)]),
    "232194": ("Pilzrisotto", [("233022", 2), ("233026", 4), ("233027", 6)]),
}


def proof_items():
    rows = []
    for grouping_id, (title, variants) in PROOF.items():
        for variant_id, servings in variants:
            rows.append(
                {
                    "groupingFunctionalId": grouping_id,
                    "recipeFunctionalId": variant_id,
                    "variantFunctionalId": variant_id,
                    "searchVariantId": variant_id,
                    "displayVariantId": variant_id,
                    "sendVariantId": variant_id,
                    "language": "de",
                    "market": "GS_DE",
                    "title": title,
                    "yield": {"quantity": servings, "quantityDisplay": str(servings)},
                    "sendable": True,
                }
            )
    return rows


class StandaloneProofContractTests(unittest.TestCase):
    def test_proven_29_serving_variants_collapse_to_11_logical_recipes(self):
        rows = proof_items()
        self.assertEqual(len(rows), 29)
        source = {
            "items": rows,
            "applianceGroup": "APPLIANCE_GROUP_15",
            "recipeType": "BRAND",
        }
        result = grouping.merge_hydrated_catalogs(
            source,
            source,
            target_language="de",
            configured_language="de",
            device_country="DE",
            strict_language=True,
        )
        self.assertEqual(len(result["items"]), 11)
        by_title = {row["title"]: row for row in result["items"]}
        self.assertEqual(
            by_title["Pfifferling-Risotto"]["availableServings"],
            [2.0, 4.0, 6.0],
        )
        self.assertIn('Risotto "Aus Vorräten"', by_title)
        self.assertIn("Risotto mit roten Linsen", by_title)


if __name__ == "__main__":
    unittest.main()
