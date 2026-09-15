from __future__ import annotations

import asyncio
from copy import deepcopy
import importlib
import json
from pathlib import Path
import socket
import sys
import types
import unittest
from unittest.mock import patch

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components/cook4me"


class OfflineMultilingualRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        package = types.ModuleType("cook4me_offline_v61_test")
        package.__path__ = [str(COMPONENT)]
        sys.modules[package.__name__] = package
        cls.release = importlib.import_module(f"{package.__name__}.release_catalog")
        cls.index = importlib.import_module(f"{package.__name__}.catalog_search_index")
        with patch.object(socket, "socket", side_effect=AssertionError("offline catalog opened network")):
            cls.payload = cls.release.load_release_catalog()

    def search(self, query, language="el", **kwargs):
        with patch.object(socket, "socket", side_effect=AssertionError("offline search opened network")):
            return self.release.search_release_recipes(
                query, language=language, configured_language="de", country="DE", size=50, **kwargs
            )

    def test_real_catalog_risotto_matches_canonical_query_in_all_source_catalogs(self):
        greek = self.search("ριζότο")
        english = self.search("risotto", "en")
        self.assertGreater(greek["page"]["totalElements"], 100)
        self.assertEqual(greek["page"], english["page"])
        self.assertEqual(greek["resolvedQuery"], "risotto")
        self.assertEqual([r["searchVariantId"] for r in greek["items"]], [r["searchVariantId"] for r in english["items"]])

    def test_general_greek_phrases_find_real_recipes(self):
        for query, canonical in [
            ("ριζότο ντομάτα", "risotto tomato"),
            ("ριζότο με μανιτάρια", "risotto mushroom"),
            ("σούπα με φακές", "soup lentil"),
            ("ντοματόσουπα", "tomato soup"),
            ("μακαρόνια", "pasta"),
        ]:
            with self.subTest(query=query):
                result = self.search(query)
                self.assertGreater(result["page"]["totalElements"], 0)
                self.assertEqual(result["page"], self.search(canonical, "en")["page"])

    def test_query_language_does_not_select_a_nonexistent_greek_source_catalog(self):
        greek = self.search("ριζότο", catalog_languages=["de"])
        self.assertGreater(greek["page"]["totalElements"], 0)
        self.assertEqual(greek["page"], self.search("risotto", "en", catalog_languages=["de"])["page"])
        self.assertTrue(all(row["catalogLanguage"] == "de" for row in greek["items"]))
        self.assertGreater(self.search("soupe de tomates", "fr", catalog_languages=["de"])["page"]["totalElements"], 0)
        self.assertGreater(self.search("ризото", "bg", catalog_languages=["de"])["page"]["totalElements"], 0)

    def test_selected_languages_filter_before_pagination_without_duplicates(self):
        first = self.search("soup", "en", catalog_languages=["de", "fr"], page=0)
        second = self.search("soup", "en", catalog_languages=["de", "fr"], page=1)
        self.assertEqual(first["page"]["totalElements"], second["page"]["totalElements"])
        ids = [{row["groupingFunctionalId"] for row in result["items"]} for result in (first, second)]
        self.assertFalse(ids[0] & ids[1])
        self.assertTrue(all(row["catalogLanguage"] in {"de", "fr"} for result in (first, second) for row in result["items"]))
        self.assertEqual(self.search("soup", catalog_languages=[])["items"], [])
        self.assertEqual(self.search("soup", catalog_languages=["el"])["items"], [])

    def test_nutrition_and_proven_device_identity_survive_search_and_detail(self):
        result = self.search("ριζότο", catalog_languages=["de"])
        rows = [row for row in result["items"] if row["catalogNutrition"].get("perServing")]
        self.assertTrue(rows)
        for row in rows:
            with self.subTest(variant=row["searchVariantId"]):
                detail = self.release.recipe_by_variant(row["searchVariantId"], language="de", configured_language="de", country="DE")
                self.assertEqual(row["catalogNutrition"], detail["catalogNutrition"])
                self.assertEqual(row["sendVariantId"], detail["sendVariantId"])
                self.assertTrue(row["nutrition"]["estimated"])
                self.assertGreater(row["nutrition"]["coverage"], 0)
                self.assertLessEqual(row["nutrition"]["coverage"], 1)

    def test_original_greek_labels_are_not_lost_when_translations_expand_the_query(self):
        payload = {"recipes": [{"canonicalName": "ριζότο"}, {"canonicalName": "Risotto"}, {"canonicalName": "Rizoto"}]}
        before = deepcopy(payload)
        prepared = self.index.prepare_search_index(self.index.compile_search_index(payload))
        self.assertEqual(set(self.index.search_index(prepared, "ριζότο", language="el")["indices"]), {0, 1})
        self.assertEqual(payload, before)
        self.assertEqual(self.index.search_index(prepared, "ριζότα", language="el")["indices"], [])

    def test_query_vocabulary_is_valid_and_has_no_conflicting_translations(self):
        vocabulary = json.loads((COMPONENT / "query_vocabulary.json").read_text())
        seen = {}
        for row in vocabulary["terms"]:
            for language, aliases in row.items():
                for alias in aliases:
                    key = language, self.index.normalize_search_text(alias)
                    if key in seen:
                        self.assertEqual(seen[key], row["en"], key)
                    seen[key] = row["en"]

    def test_websocket_search_and_detail_use_the_same_offline_catalog(self):
        prefix = "cook4me_offline_v61_test"
        identity = lambda value: value
        websocket_api = types.SimpleNamespace(websocket_command=lambda _: identity, async_response=identity)
        bridge = types.SimpleNamespace(can_accept_recipe=False, recipe_hub=types.SimpleNamespace(annotate=deepcopy))
        legacy = types.SimpleNamespace(_bridge=lambda *_: bridge, _send_error=lambda *args: self.fail(str(args)))
        v30 = types.SimpleNamespace(_device_language=lambda _: "de", _device_country=lambda _: "DE", _annotate_search=lambda _, result: result)

        async def forbid_live(*args, **kwargs):
            self.fail("Offline recipe unexpectedly entered the live request queue")

        modules = {
            "voluptuous": types.SimpleNamespace(Required=lambda value, **_: value, Optional=lambda value, **_: value, All=lambda *args: None, Coerce=lambda _: None, Range=lambda **kwargs: None),
            "homeassistant.core": types.SimpleNamespace(HomeAssistant=object, callback=identity),
            "homeassistant.components": types.SimpleNamespace(websocket_api=websocket_api),
            f"{prefix}.websocket": legacy,
            f"{prefix}.websocket_v30": v30,
            f"{prefix}.request_coordinator": types.SimpleNamespace(request_coordinator=forbid_live),
        }
        with patch.dict(sys.modules, modules):
            ws = importlib.import_module(f"{prefix}.websocket_v31")
        responses = {}
        connection = types.SimpleNamespace(send_result=lambda ident, result: responses.update({ident: result}))

        async def run():
            with patch.object(socket, "socket", side_effect=AssertionError("offline websocket opened network")):
                await ws.ws_official_search(None, connection, {"id": 1, "query": "ριζότο", "query_language": "el", "languages": ["de"]})
                result = responses[1]
                self.assertGreater(result["page"]["totalElements"], 0)
                self.assertEqual(result["resolvedQuery"], "risotto")
                self.assertTrue(result["offline"])
                self.assertFalse(result["serverFetch"])
                first = result["items"][0]
                await ws.ws_recipe_detail(None, connection, {"id": 2, "variant_id": first["searchVariantId"], "language": "de"})
                self.assertEqual(responses[2]["catalogNutrition"], first["catalogNutrition"])
                self.assertTrue(responses[2]["offline"])

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
