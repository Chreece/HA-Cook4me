from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]

pkg = types.ModuleType("cook4me_testpkg")
pkg.__path__ = [str(ROOT / "custom_components/cook4me")]
sys.modules.setdefault("cook4me_testpkg", pkg)

search = types.ModuleType("cook4me_testpkg.recipe_search_v8")
search.app_search_body = lambda language, market: {"language": language, "market": market}
sys.modules[search.__name__] = search

vendor = types.ModuleType("cook4me_testpkg.vendor")
vendor.__path__ = []
sys.modules[vendor.__name__] = vendor

c4m = types.ModuleType("cook4me_testpkg.vendor.cook4me_phonefree")
c4m.jwt_exp = lambda _token: 1234567890
sys.modules[c4m.__name__] = c4m

catalog = types.ModuleType("cook4me_testpkg.vendor.cook4me_recipe_catalog")
catalog.c4m = types.SimpleNamespace(curl_requests=None)
sys.modules[catalog.__name__] = catalog

path = ROOT / "custom_components/cook4me/recipe_catalog_diagnostics.py"
spec = importlib.util.spec_from_file_location("cook4me_testpkg.recipe_catalog_diagnostics", path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class RecipeCatalogDiagnosticTests(unittest.TestCase):
    def test_summary_distinguishes_body_rejection_from_auth(self):
        diagnostic = {
            "bodyMismatchProven": True,
            "legacyEmptyBody": {
                "attempts": [{"mode": "id_rcu", "status": 200, "success": True}]
            },
            "v8AppBody": {
                "attempts": [{"mode": "id_rcu", "status": 403, "errorCode": "BAD_BODY"}]
            },
        }
        text = module.diagnostic_summary(diagnostic)
        self.assertIn("credentials work", text)
        self.assertIn("id_rcu=200", text)
        self.assertIn("id_rcu=403/BAD_BODY", text)

    def test_secret_text_is_redacted(self):
        text = module._safe_text(
            "Bearer eyJaaaaaaaaaa.bbbbbbbbbb.cccccccccc token failed"
        )
        self.assertNotIn("eyJaaaaaaaaaa", text)
        self.assertIn("[REDACTED]", text)


if __name__ == "__main__":
    unittest.main()
