from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"

class MenuFooterV126Tests(unittest.TestCase):
    def test_all_menu_card_footers_reach_card_bottom(self):
        ui=(FRONTEND/"cook4me-panel-v126.js").read_text(encoding="utf-8")
        panel=PANEL.read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v138", panel)
        self.assertIn("cook4me-panel-v138.js", panel)
        self.assertIn(".rx-overlay>.rx-dialog:has(>footer)", ui)
        self.assertIn(".rx-overlay>.rx-dialog:has(>form>footer)", ui)
        self.assertIn(".rx-overlay>.rx-dialog>form>footer", ui)
        self.assertIn("padding-bottom:0!important", ui)
        self.assertIn("[data-device-settings] .rx-dialog", ui)
        self.assertIn("[data-filter-dialog] .rx-dialog", ui)
        self.assertNotIn(".v78-capture footer", ui)
        self.assertIn("2026.9.19.5", ui)

if __name__=="__main__":
    unittest.main()
