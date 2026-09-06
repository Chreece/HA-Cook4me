from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
vp = ROOT / "custom_components/cook4me/vendor/cook4me_phonefree.py"
spec = importlib.util.spec_from_file_location("cook4me_vendor_search", vp)
v = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(v)


class _Response:
    status_code = 200
    def json(self):
        return {
            "content": [
                {"identifier": {"functionalId": "100"}, "title": "One"},
                {"identifier": {"functionalId": "200"}, "title": "Two"},
                {"identifier": {"functionalId": "300"}, "title": "Three"},
            ],
            "page": {"number": 0, "size": 3},
        }


class _Requests:
    @staticmethod
    def post(*args, **kwargs):
        return _Response()


class VendorSearchTests(unittest.TestCase):
    def setUp(self):
        self.old_requests = v.curl_requests
        self.old_discover = v.discover_rcu
        self.old_headers = v._recipe_request_headers
        self.old_meta = v.recipe_metadata
        v.curl_requests = _Requests
        v.discover_rcu = lambda *a, **k: {"apim_url": "x", "apim_subscription_key": "y", "profile_perimeter": "z"}
        v._recipe_request_headers = lambda *a, **k: iter([("app", {})])

    def tearDown(self):
        v.curl_requests = self.old_requests
        v.discover_rcu = self.old_discover
        v._recipe_request_headers = self.old_headers
        v.recipe_metadata = self.old_meta

    def test_concurrent_enrichment_preserves_result_order(self):
        def meta(cfg, tokens, recipe, variant, *a, **k):
            return {
                "searchVariantId": variant,
                "recipeFunctionalId": variant,
                "groupingFunctionalId": "g" + variant,
                "title": "D" + variant,
                "ingredients": [],
            }
        v.recipe_metadata = meta
        out = v.search_recipes({"platform_base_url": "https://example.invalid"}, {}, size=3, max_details=3)
        self.assertEqual([x["searchVariantId"] for x in out["items"]], ["100", "200", "300"])
        self.assertEqual([x["title"] for x in out["items"]], ["D100", "D200", "D300"])

    def test_failed_detail_keeps_lightweight_row(self):
        def meta(cfg, tokens, recipe, variant, *a, **k):
            if variant == "200":
                raise OSError("nope")
            return {"searchVariantId": variant, "recipeFunctionalId": variant, "groupingFunctionalId": "g" + variant}
        v.recipe_metadata = meta
        out = v.search_recipes({"platform_base_url": "https://example.invalid"}, {}, size=3, max_details=3)
        self.assertEqual(out["items"][1]["searchVariantId"], "200")
        self.assertEqual(out["items"][1]["detailError"], "OSError")
        self.assertEqual(out["items"][2]["groupingFunctionalId"], "g300")


if __name__ == "__main__":
    unittest.main()
