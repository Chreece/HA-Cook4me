from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "custom_components/cook4me/websocket_v10.py").read_text(encoding="utf-8")
V9 = (ROOT / "custom_components/cook4me/websocket_v9.py").read_text(encoding="utf-8")


class WebsocketV10AuthPathTests(unittest.TestCase):
    def test_v10_uses_v9_http_only_refresh_path(self):
        self.assertIn("from . import websocket_v9 as v9", SOURCE)
        self.assertIn("raw, cache_hit = await v9._raw_search(", SOURCE)
        self.assertNotIn("raw, cache_hit = await v8._raw_search(", SOURCE)

    def test_v9_refresh_uses_auth_only_not_status_command(self):
        start = V9.index("async def _refresh_catalog_auth")
        end = V9.index("async def _async_catalog_call", start)
        refresh = V9[start:end]
        self.assertIn('"--force-login"', refresh)
        self.assertIn('"--auth-only"', refresh)
        self.assertNotIn('bridge._run_client_json("status"', refresh)
        self.assertNotIn('"status", timeout=', refresh)

    def test_v10_still_diagnoses_post_refresh_catalog_rejection(self):
        self.assertIn(
            "KRUPS recipe-catalog authentication is still rejected after refresh",
            SOURCE,
        )
        self.assertIn("diagnostic = await _diagnose", SOURCE)
        self.assertIn("bodyMismatchProven", SOURCE)


if __name__ == "__main__":
    unittest.main()
