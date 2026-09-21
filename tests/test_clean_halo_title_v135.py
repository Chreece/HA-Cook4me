from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"


class CleanHaloTitleFitV135Tests(unittest.TestCase):
    def test_v135_reuses_clean_v133_photo_not_artifact_cutout(self):
        ui=(FRONTEND/"cook4me-panel-v135.js").read_text(encoding="utf-8")
        self.assertIn("./assets/device-v133.jpg?v=2026.9.20.9",ui)
        self.assertIn("mix-blend-mode:multiply!important",ui)
        self.assertIn("background:transparent!important",ui)
        self.assertNotIn("device-v134.webp",ui)

    def test_no_bright_radial_halo_is_reintroduced(self):
        ui=(FRONTEND/"cook4me-panel-v135.js").read_text(encoding="utf-8")
        self.assertNotIn("radial-gradient(circle at 50% 49%,#d8dcdd",ui)
        self.assertIn("drop-shadow(0 8px 12px rgba(0,0,0,.28))",ui)

    def test_live_screen_geometry_is_restored_for_v133_photo(self):
        ui=(FRONTEND/"cook4me-panel-v135.js").read_text(encoding="utf-8")
        for token in (
            "left:31.2%!important","top:47.5%!important",
            "width:38.2%!important","height:40.5%!important",
            "left:34.2%!important","top:51%!important",
            "width:32.2%!important","height:31%!important",
        ):
            self.assertIn(token,ui)

    def test_recipe_titles_shrink_with_bottom_safety_reserve(self):
        ui=(FRONTEND/"cook4me-panel-v135.js").read_text(encoding="utf-8")
        self.assertIn("_v71FitTitle(title)",ui)
        self.assertIn("padding-bottom','3px'",ui)
        self.assertIn("box.clientHeight-verticalPadding-4",ui)
        self.assertIn("let low=11,high=20",ui)
        self.assertIn("-webkit-line-clamp','unset'",ui)
        self.assertIn("overflow','visible'",ui)
        self.assertIn("line-height','1.18'",ui)

    def test_v135_is_active_and_versioned(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v135.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v172",panel)
        self.assertIn("cook4me-panel-v172.js",panel)
        self.assertIn("/cook4me_static/2026.9.21.37",panel)
        self.assertIn("?v=2026.9.21.37",panel)
        self.assertIn('"version": "2026.9.21.37"',manifest)
        self.assertIn(
            "if(!customElements.get(V134))await import('./cook4me-panel-v134.js?v=2026.9.20.8')",
            ui,
        )


if __name__=="__main__":
    unittest.main()
