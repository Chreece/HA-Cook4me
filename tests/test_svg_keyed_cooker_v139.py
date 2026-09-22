from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"


class SvgKeyedCookerV139Tests(unittest.TestCase):
    def test_v139_replaces_broken_alpha_asset_with_svg_keyed_source_photo(self):
        ui=(FRONTEND/"cook4me-panel-v139.js").read_text(encoding="utf-8")
        self.assertIn("./assets/device-v133.jpg?v=2026.9.21.4",ui)
        self.assertIn("document.createElementNS('http://www.w3.org/2000/svg','svg')",ui)
        self.assertIn("v139-white-key",ui)
        self.assertIn('<feFuncA type="linear" slope="4.76" intercept="-0.19"/>',ui)
        self.assertIn(".v130-model-photo{display:none!important}",ui)

    def test_v139_blanks_baked_screen_and_branding_but_keeps_live_screen(self):
        ui=(FRONTEND/"cook4me-panel-v139.js").read_text(encoding="utf-8")
        v130=(FRONTEND/"cook4me-panel-v130.js").read_text(encoding="utf-8")
        self.assertIn('<rect x="174" y="248" width="127" height="80"',ui)
        self.assertIn('<rect x="218" y="231" width="40" height="15"',ui)
        self.assertIn('<rect x="219" y="357" width="38" height="13"',ui)
        self.assertIn(".v130-live-screen",ui)
        self.assertIn("state.recipeImage",v130)
        self.assertIn("v130-recipe-photo",v130)

    def test_v139_adds_light_glow_around_visible_cooker(self):
        ui=(FRONTEND/"cook4me-panel-v139.js").read_text(encoding="utf-8")
        self.assertIn("drop-shadow(0 0 4px rgba(220,230,255,.30))",ui)
        self.assertIn("drop-shadow(0 0 10px rgba(170,195,255,.12))",ui)

    def test_v139_is_inherited_by_active_v140(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v178",panel)
        self.assertIn("cook4me-panel-v178.js",panel)
        self.assertIn("/cook4me_static/2026.9.22.5",panel)
        self.assertIn("?v=2026.9.22.5",panel)
        self.assertIn('"version": "2026.9.22.5"',manifest)


if __name__=="__main__":
    unittest.main()
