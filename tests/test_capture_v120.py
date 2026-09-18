from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"

class CaptureV120Tests(unittest.TestCase):
    def test_v120_camera_contract(self):
        ui=(FRONTEND/"cook4me-panel-v120.js").read_text(encoding="utf-8")
        panel=PANEL.read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v120",panel)
        self.assertIn("cook4me-panel-v120-bundle.js",panel)
        self.assertIn("_nativeBarcodeScannerAvailable(){",ui)
        self.assertIn("return false;",ui)
        self.assertIn("data-v120-torch",ui)
        self.assertIn("getCapabilities()?.torch===true",ui)
        self.assertIn("applyConstraints({advanced:[{torch:next}]})",ui)
        self.assertIn("mdi:${on?'flashlight-off':'flashlight'}",ui)
        self.assertIn("querySelector('[data-v78-native]')?.remove()",ui)

if __name__=="__main__":
    unittest.main()
