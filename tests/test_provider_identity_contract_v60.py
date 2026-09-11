from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
COMPONENT = ROOT / "custom_components" / "cook4me"
for path in (TOOLS, COMPONENT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import build_release_catalog_v60 as builder  # noqa: E402
import provider_identity_v60 as provider_identity  # noqa: E402
import snapshot_release_catalog_nutrition_queue_v60 as nutrition_queue  # noqa: E402

fixture_spec = importlib.util.spec_from_file_location(
    "cook4me_validator_fixture_provider_contract",
    ROOT / "tests" / "test_validate_release_catalog_v60.py",
)
assert fixture_spec is not None and fixture_spec.loader is not None
fixture = importlib.util.module_from_spec(fixture_spec)
fixture_spec.loader.exec_module(fixture)


def _marketingfood_catalog() -> dict:
    payload = fixture.base_catalog()
    provider_id = "MARKETINGFOOD_510004"
    provider = payload["ingredients"][0]
    provider["id"] = provider_id
    provider["key"] = provider_id
    line = payload["recipes"][0]["variants"][0]["ingredients"][0]
    line["ingredientId"] = provider_id
    line["key"] = provider_id

    dependencies = fixture.validator.recipe_metrics_v60.compile_recipe_dependency_index(
        payload["recipes"]
    )
    payload["recipeDependencyIndex"] = {
        ident: list(indices) for ident, indices in dependencies.items()
    }
    payload["source"]["recipeDependencyIdentityCount"] = len(dependencies)
    payload["searchIndex"] = fixture.validator.catalog_search_index.compile_search_index(
        payload
    )
    payload["recipeSafetyIndex"] = (
        fixture.validator.recipe_safety_index_v60.compile_recipe_safety_index(payload)
    )
    return payload


class ProviderIdentityContractV60Tests(unittest.TestCase):
    def test_exact_marketingfood_provider_key_is_authoritative(self):
        row = {
            "id": "MARKETINGFOOD_510004",
            "key": "MARKETINGFOOD_510004",
        }
        self.assertEqual(provider_identity.provider_key(row), "MARKETINGFOOD_510004")
        self.assertTrue(provider_identity.preserved_provider_identity(row))

    def test_mismatched_or_source_local_provider_identity_is_rejected(self):
        self.assertFalse(
            provider_identity.preserved_provider_identity(
                {"id": "MARKETINGFOOD_510004", "key": "MARKETINGFOOD_500002"}
            )
        )
        self.assertFalse(
            provider_identity.preserved_provider_identity(
                {"id": "local:de:test", "key": "local:de:test"}
            )
        )

    def test_final_validator_accepts_exact_marketingfood_identity(self):
        result = fixture.validator.validate(_marketingfood_catalog())
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(result["stats"]["providerIngredientCount"], 1)

    def test_final_validator_still_rejects_provider_key_mismatch(self):
        payload = _marketingfood_catalog()
        payload["ingredients"][0]["key"] = "MARKETINGFOOD_500002"
        result = fixture.validator.validate(payload)
        self.assertFalse(result["valid"])
        self.assertTrue(
            any("matching provider key" in error for error in result["errors"])
        )

    def test_nutrition_queue_recognizes_only_preserved_provider_identity(self):
        good = {"id": "MARKETINGFOOD_510004", "key": "MARKETINGFOOD_510004"}
        bad = {"id": "MARKETINGFOOD_510004", "key": "MARKETINGFOOD_500002"}
        self.assertEqual(
            nutrition_queue._identity_kind(good, "MARKETINGFOOD_510004"),
            "provider",
        )
        self.assertEqual(
            nutrition_queue._identity_kind(bad, "MARKETINGFOOD_510004"),
            "unknown",
        )

    def test_reviewed_nutrition_accepts_exact_provider_key_without_prefix_guess(self):
        row = {
            "id": "MARKETINGFOOD_510004",
            "key": "MARKETINGFOOD_510004",
            "canonicalName": "Provider food",
        }
        self.assertTrue(
            builder._reviewed_nutrition_eligible(row, "MARKETINGFOOD_510004")
        )
        row["key"] = "MARKETINGFOOD_500002"
        self.assertFalse(
            builder._reviewed_nutrition_eligible(row, "MARKETINGFOOD_510004")
        )


if __name__ == "__main__":
    unittest.main()
