from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_module():
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

    package_name = "cook4me_currency_test"
    package = types.ModuleType(package_name)
    package.__path__ = []
    const = types.ModuleType(f"{package_name}.const")
    const.DOMAIN = "cook4me"
    sys.modules[package_name] = package
    sys.modules[f"{package_name}.const"] = const

    spec = importlib.util.spec_from_file_location(
        f"{package_name}.currency_fx",
        ROOT / "custom_components/cook4me/currency_fx.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CurrencyFxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fx = load_module()

    def test_language_currency_defaults_follow_current_currency(self):
        self.assertEqual(self.fx.default_currency_for_language("de-DE"), "EUR")
        self.assertEqual(self.fx.default_currency_for_language("el"), "EUR")
        self.assertEqual(self.fx.default_currency_for_language("en-GB"), "GBP")
        self.assertEqual(self.fx.default_currency_for_language("pl"), "PLN")
        self.assertEqual(self.fx.default_currency_for_language("ja"), "JPY")
        self.assertEqual(self.fx.default_currency_for_language("bg"), "EUR")

    def test_ecb_cross_rate_conversion_uses_euro_bridge(self):
        rates = {"EUR": 1.0, "USD": 1.2, "GBP": 0.8}
        self.assertAlmostEqual(self.fx.convert_amount(12, "USD", "EUR", rates), 10)
        self.assertAlmostEqual(self.fx.convert_amount(12, "USD", "GBP", rates), 8)
        self.assertAlmostEqual(self.fx.convert_amount(8, "GBP", "USD", rates), 12)

    def test_currency_map_collapses_to_selected_currency(self):
        result = self.fx.convert_currency_map(
            {"EUR": 10, "USD": 12, "GBP": 8},
            "EUR",
            {"EUR": 1.0, "USD": 1.2, "GBP": 0.8},
        )
        self.assertEqual(result["amount"], 30.0)
        self.assertEqual(result["currency"], "EUR")
        self.assertTrue(result["complete"])
        self.assertEqual(result["unconverted"], {})

    def test_unknown_rate_is_preserved_not_dropped(self):
        result = self.fx.convert_currency_map(
            {"EUR": 10, "XYZ": 5},
            "EUR",
            {"EUR": 1.0, "USD": 1.2},
        )
        self.assertEqual(result["amount"], 10.0)
        self.assertEqual(result["unconverted"], {"XYZ": 5.0})
        self.assertFalse(result["complete"])

    def test_ecb_xml_parser_adds_euro_base(self):
        xml = b'''<?xml version="1.0" encoding="UTF-8"?>
        <gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01" xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
          <Cube><Cube time="2026-09-07"><Cube currency="USD" rate="1.1622"/><Cube currency="GBP" rate="0.85894"/></Cube></Cube>
        </gesmes:Envelope>'''
        parsed = self.fx.parse_ecb_daily_xml(xml)
        self.assertEqual(parsed["date"], "2026-09-07")
        self.assertEqual(parsed["rates"]["EUR"], 1.0)
        self.assertAlmostEqual(parsed["rates"]["USD"], 1.1622)

    def test_existing_cost_currency_migrates_as_fixed(self):
        class CostStore:
            def __init__(self):
                self.settings = {"currency": "USD"}
                self.writes = []

            async def async_set_settings(self, **kwargs):
                self.settings.update(kwargs)
                self.writes.append(kwargs)
                return self.settings

        async def run():
            store = self.fx.Cook4MeCurrencyFxStore(object(), "entry")
            store._loaded = True
            cost = CostStore()
            selected = await store.async_resolve_currency("de", cost)
            return store, cost, selected

        store, cost, selected = asyncio.run(run())
        self.assertEqual(selected, "USD")
        self.assertEqual(store.preference["mode"], "fixed")
        self.assertFalse(cost.writes)


if __name__ == "__main__":
    unittest.main()
