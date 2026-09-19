from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"

class CaptureV123Tests(unittest.TestCase):
    def test_v123_verified_torch_contract(self):
        ui=(FRONTEND/"cook4me-panel-v123.js").read_text(encoding="utf-8")
        panel=PANEL.read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v123", panel)
        self.assertIn("cook4me-panel-v123-bundle.js", panel)
        self.assertIn("getCapabilities()?.torch===true", ui)
        self.assertIn("advanced:[{torch:next}]", ui)
        self.assertNotIn("applyConstraints({torch:next})", ui)
        self.assertIn("this._v120TorchBlocked=true", ui)
        self.assertIn("2026.9.19.2", ui)

if __name__=="__main__":
    unittest.main()
