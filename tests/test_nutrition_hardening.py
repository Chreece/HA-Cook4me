from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_modules():
    ha = types.ModuleType("homeassistant")
    ha_core = types.ModuleType("homeassistant.core")
    ha_helpers = types.ModuleType("homeassistant.helpers")
    ha_storage = types.ModuleType("homeassistant.helpers.storage")
    ha_core.HomeAssistant = object

    class Store:
        def __init__(self, *args, **kwargs):
            self.saved = None

        def __class_getitem__(cls, _item):
            return cls

        async def async_load(self):
            return None

        async def async_save(self, data):
            self.saved = data

    ha_storage.Store = Store
    sys.modules["homeassistant"] = ha
    sys.modules["homeassistant.core"] = ha_core
    sys.modules["homeassistant.helpers"] = ha_helpers
    sys.modules["homeassistant.helpers.storage"] = ha_storage

    package_name = "cook4me_nutrition_hardening_test"
    package = types.ModuleType(package_name)
    package.__path__ = []
    const = types.ModuleType(f"{package_name}.const")
    const.DOMAIN = "cook4me"
    sys.modules[package_name] = package
    sys.modules[f"{package_name}.const"] = const

    def load(name: str, filename: str):
        spec = importlib.util.spec_from_file_location(
            f"{package_name}.{name}",
            ROOT / "custom_components/cook4me" / filename,
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    nutrition = load("nutrition", "nutrition.py")
    fdc = load("nutrition_fdc", "nutrition_fdc.py")
    resolution = load("nutrition_resolution", "nutrition_resolution.py")
    return nutrition, fdc, resolution


class NutritionHardeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nutrition, cls.fdc, cls.resolution = load_modules()

    def test_equal_plausibility_variants_remain_unresolved(self):
        foods = [
            {
                "fdcId": 1,
                "description": "Milk, whole",
                "dataType": "Foundation",
                "foodNutrients": [],
            },
            {
                "fdcId": 2,
                "description": "Milk, skim",
                "dataType": "Foundation",
                "foodNutrients": [],
            },
        ]
        food, score, runner = self.fdc.select_fdc_candidate_strict("Milk", foods)
        self.assertIsNone(food)
        self.assertGreaterEqual(score, 0.86)
        self.assertAlmostEqual(score, runner)

    def test_exact_description_is_allowed_even_with_close_runner_up(self):
        foods = [
            {
                "fdcId": 1,
                "description": "Milk",
                "dataType": "Foundation",
                "foodNutrients": [],
            },
            {
                "fdcId": 2,
                "description": "Milk, whole",
                "dataType": "Foundation",
                "foodNutrients": [],
            },
        ]
        food, score, runner = self.fdc.select_fdc_candidate_strict("Milk", foods)
        self.assertIsNotNone(food)
        self.assertEqual(food["fdcId"], 1)
        self.assertGreaterEqual(score, runner)

    def test_duplicate_descriptions_do_not_create_fake_ambiguity(self):
        foods = [
            {"fdcId": 1, "description": "Tomato", "dataType": "SR Legacy"},
            {"fdcId": 2, "description": "Tomato", "dataType": "Foundation"},
        ]
        ranked = self.fdc.ranked_fdc_candidates("Tomato", foods)
        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0][1]["fdcId"], 2)

    def test_semantic_failure_blocks_across_api_modes(self):
        now = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)
        store = self.resolution.Cook4MeNutritionResolutionStore(object(), "entry")
        store._data = {
            "failures": {
                "k:M_FOOD_MILK": {
                    "query": "Milk",
                    "mode": "demo",
                    "reason": "ambiguous",
                    "retryAt": (now + timedelta(days=2)).isoformat(),
                }
            }
        }
        self.assertIsNotNone(
            store.get_blocked(
                "k:M_FOOD_MILK", query="Milk", mode="custom", now=now
            )
        )

    def test_transient_failure_does_not_block_different_api_mode(self):
        now = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)
        store = self.resolution.Cook4MeNutritionResolutionStore(object(), "entry")
        store._data = {
            "failures": {
                "k:M_FOOD_MILK": {
                    "query": "Milk",
                    "mode": "demo",
                    "reason": "http_429",
                    "retryAt": (now + timedelta(hours=2)).isoformat(),
                }
            }
        }
        self.assertIsNone(
            store.get_blocked(
                "k:M_FOOD_MILK", query="Milk", mode="custom", now=now
            )
        )

    def test_expired_failure_is_not_blocking(self):
        now = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)
        store = self.resolution.Cook4MeNutritionResolutionStore(object(), "entry")
        store._data = {
            "failures": {
                "k:M_FOOD_MILK": {
                    "query": "Milk",
                    "mode": "demo",
                    "reason": "ambiguous",
                    "retryAt": (now - timedelta(seconds=1)).isoformat(),
                }
            }
        }
        self.assertIsNone(
            store.get_blocked(
                "k:M_FOOD_MILK", query="Milk", mode="demo", now=now
            )
        )

    def test_ambiguous_retry_window_is_longer_than_rate_limit_window(self):
        self.assertGreater(
            self.resolution.retry_ttl("ambiguous"),
            self.resolution.retry_ttl("http_429"),
        )

    def test_websocket_uses_strict_lookup_cache_and_exact_catalog_stats(self):
        source = (
            ROOT / "custom_components/cook4me/websocket_v16.py"
        ).read_text(encoding="utf-8")
        self.assertIn("lookup_food_data_central_strict", source)
        self.assertIn("nutrition_resolution_store_for_bridge", source)
        self.assertIn("resolution_store.get_blocked", source)
        self.assertIn('"blockedFailures"', source)
        self.assertIn('"actionableRemaining"', source)
        self.assertIn("_catalog_identity_rows", source)
        self.assertNotIn("lookup_food_data_central,", source)


if __name__ == "__main__":
    unittest.main()
