from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"

class CaptureV122Tests(unittest.TestCase):
    def test_v122_torch_fallback_contract(self):
        ui=(FRONTEND/"cook4me-panel-v122.js").read_text(encoding="utf-8")
        panel=PANEL.read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v122", panel)
        self.assertIn("cook4me-panel-v122-bundle.js", panel)
        self.assertIn("track?.applyConstraints", ui)
        self.assertIn("facing!=='user'", ui)
        self.assertIn("advanced:[{torch:next}]", ui)
        self.assertIn("applyConstraints({torch:next})", ui)
        self.assertIn("this._v120TorchBlocked=true", ui)
        self.assertNotIn("getCapabilities()?.torch===true", ui)

if __name__=="__main__":
    unittest.main()
