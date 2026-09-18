from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"

class FullscreenV118Tests(unittest.TestCase):
    def test_fullscreen_layout_contract(self):
        ui=(FRONTEND/"cook4me-panel-v118.js").read_text(encoding="utf-8")
        panel=PANEL.read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v118",panel)
        self.assertIn("cook4me-panel-v118-bundle.js",panel)
        self.assertIn('[data-v66-section="info"]',ui)
        self.assertIn('[data-v66-section="ingredients"]',ui)
        self.assertIn(".v79-recipe-price",ui)
        self.assertIn("infoBody.append(price)",ui)
        self.assertIn("data-v118-weighing",ui)
        self.assertIn("details.dataset.v66Section='weighing'",ui)
        self.assertIn("ingredients.after(details)",ui)

if __name__=="__main__":
    unittest.main()
