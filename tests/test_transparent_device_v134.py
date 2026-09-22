from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"


class TransparentDeviceV134Tests(unittest.TestCase):
    def test_transparent_webp_asset_is_packaged(self):
        asset=FRONTEND/"assets"/"device-v134.webp"
        payload=asset.read_bytes()
        self.assertGreater(len(payload),5000)
        self.assertEqual(payload[:4],b"RIFF")
        self.assertEqual(payload[8:12],b"WEBP")

    def test_v134_removes_bright_device_background(self):
        ui=(FRONTEND/"cook4me-panel-v134.js").read_text(encoding="utf-8")
        self.assertIn("background:transparent!important",ui)
        self.assertIn("mix-blend-mode:normal!important",ui)
        self.assertIn("drop-shadow(0 8px 12px rgba(0,0,0,.34))",ui)
        self.assertIn("border-radius:0!important",ui)
        self.assertNotIn("radial-gradient(circle at 50% 49%,#d8dcdd",ui)

    def test_baked_screen_is_masked_and_live_screen_aligned(self):
        ui=(FRONTEND/"cook4me-panel-v134.js").read_text(encoding="utf-8")
        self.assertIn(".v130-brand-mask",ui)
        self.assertIn("left:36.1%!important",ui)
        self.assertIn("top:52.5%!important",ui)
        self.assertIn("width:27.4%!important",ui)
        self.assertIn("height:19.2%!important",ui)
        self.assertIn(".v130-live-screen",ui)
        self.assertIn("background:#070909!important",ui)

    def test_dynamic_recipe_screen_is_still_inherited(self):
        v130=(FRONTEND/"cook4me-panel-v130.js").read_text(encoding="utf-8")
        v134=(FRONTEND/"cook4me-panel-v134.js").read_text(encoding="utf-8")
        self.assertIn("state.recipeImage",v130)
        self.assertIn("v130-recipe-photo",v130)
        self.assertIn(
            "if(!customElements.get(V133))await import('./cook4me-panel-v133.js?v=2026.9.20.7')",
            v134,
        )

    def test_v134_is_inherited_by_active_v138(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v180",panel)
        self.assertIn("cook4me-panel-v180.js",panel)
        self.assertIn("/cook4me_static/2026.9.22.8",panel)
        self.assertIn("?v=2026.9.22.8",panel)
        self.assertIn('"version": "2026.9.22.8"',manifest)


if __name__=="__main__":
    unittest.main()
