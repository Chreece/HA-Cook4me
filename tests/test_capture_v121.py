from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"

class CaptureV121Tests(unittest.TestCase):
    def test_v121_mobile_back_and_camera_contract(self):
        ui=(FRONTEND/"cook4me-panel-v121.js").read_text(encoding="utf-8")
        panel=PANEL.read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v121",panel)
        self.assertIn("cook4me-panel-v121-bundle.js",panel)
        self.assertIn("history.pushState",ui)
        self.assertIn("'popstate'",ui)
        self.assertIn("this._v78Close(true)",ui)
        self.assertIn("power.hidden=true",ui)
        self.assertIn("bottom.prepend(camera)",ui)
        self.assertIn("camera.hidden=false",ui)
        self.assertIn("camera-off-outline",ui)
        self.assertIn("if(this._v120LiveTrack()||this._v80CameraPending)this._v78StopCamera()",ui)

if __name__=="__main__":
    unittest.main()
