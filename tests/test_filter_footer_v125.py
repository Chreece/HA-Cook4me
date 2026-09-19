from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"

class FilterFooterV125Tests(unittest.TestCase):
    def test_filter_footer_reaches_dialog_bottom(self):
        ui=(FRONTEND/"cook4me-panel-v125.js").read_text(encoding="utf-8")
        panel=PANEL.read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v125", panel)
        self.assertIn("cook4me-panel-v125-bundle.js", panel)
        self.assertIn("margin:0 -18px -18px!important", ui)
        self.assertIn("padding:10px 18px 18px!important", ui)
        self.assertIn("border-radius:0 0 19px 19px", ui)
        self.assertIn("2026.9.19.4", ui)

if __name__=="__main__":
    unittest.main()
