from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"


class LiveDisplayDeviceV138Tests(unittest.TestCase):
    def test_clean_transparent_webp_asset_is_packaged(self):
        asset=FRONTEND/"assets"/"device-v138.webp"
        payload=asset.read_bytes()
        self.assertGreater(len(payload),10000)
        self.assertEqual(payload[:4],b"RIFF")
        self.assertEqual(payload[8:12],b"WEBP")

    def test_v138_uses_new_shell_without_old_crop_or_blending(self):
        ui=(FRONTEND/"cook4me-panel-v138.js").read_text(encoding="utf-8")
        self.assertIn("./assets/device-v138.webp?v=2026.9.21.3",ui)
        self.assertIn("clip-path:none!important",ui)
        self.assertIn("mix-blend-mode:normal!important",ui)
        self.assertIn("filter:none!important",ui)
        self.assertIn("background:transparent!important",ui)
        self.assertIn("drop-shadow(0 0 5px rgba(220,230,255,.24))",ui)

    def test_existing_live_display_is_preserved_and_repositioned(self):
        ui=(FRONTEND/"cook4me-panel-v138.js").read_text(encoding="utf-8")
        v130=(FRONTEND/"cook4me-panel-v130.js").read_text(encoding="utf-8")
        self.assertIn(".v130-brand-mask{display:none!important}",ui)
        self.assertIn(".v130-live-screen",ui)
        self.assertIn("left:30.2%!important",ui)
        self.assertIn("top:49.1%!important",ui)
        self.assertIn("width:39.6%!important",ui)
        self.assertIn("height:27.8%!important",ui)
        self.assertIn("state.recipeImage",v130)
        self.assertIn("queue?.recipe?.cover",v130)
        self.assertIn("v130-recipe-photo",v130)
        for phase in ("loading","preheating","cooking","warm","done","offline","idle"):
            self.assertIn(phase,v130)

    def test_v138_inherits_folded_week_summary_panels(self):
        v137=(FRONTEND/"cook4me-panel-v137.js").read_text(encoding="utf-8")
        v138=(FRONTEND/"cook4me-panel-v138.js").read_text(encoding="utf-8")
        self.assertIn("rx-v137-week-panel",v137)
        self.assertIn(
            "if(!customElements.get(V137))await import('./cook4me-panel-v137.js?v=2026.9.21.2')",
            v138,
        )

    def test_v138_is_active_and_versioned(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v138",panel)
        self.assertIn("cook4me-panel-v138.js",panel)
        self.assertIn("/cook4me_static/2026.9.21.3",panel)
        self.assertIn("?v=2026.9.21.3",panel)
        self.assertIn('"version": "2026.9.21.3"',manifest)


if __name__=="__main__":
    unittest.main()
