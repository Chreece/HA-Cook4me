from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"

class CaptureV119Tests(unittest.TestCase):
    def test_v119_capture_contract(self):
        ui=(FRONTEND/"cook4me-panel-v119.js").read_text(encoding="utf-8")
        panel=PANEL.read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v119",panel)
        self.assertIn("cook4me-panel-v119-bundle.js",panel)
        self.assertIn("data-v116-weight",ui)
        self.assertIn("mdi:scale-balance",ui)
        self.assertIn("_v119IsMassUnit",ui)
        self.assertIn("_v119FitInput",ui)
        self.assertIn("data-v111-guide",ui)
        self.assertIn("_v119CaptureAi",ui)
        self.assertIn("_v112Editor(true,mode)",ui)
        self.assertIn("_v113CanRestart",ui)
        self.assertIn("_v113Restart",ui)

if __name__=="__main__":
    unittest.main()
