from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"

class FilterCheckboxV124Tests(unittest.TestCase):
    def test_compact_multi_checkbox_filters(self):
        ui=(FRONTEND/"cook4me-panel-v124.js").read_text(encoding="utf-8")
        panel=PANEL.read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v124", panel)
        self.assertIn("cook4me-panel-v124-bundle.js", panel)
        self.assertIn("input[type=\"checkbox\"][data-list]", ui)
        self.assertIn("dataset.v124SelectAll", ui)
        self.assertIn("dataset.v124DeselectAll", ui)
        self.assertIn("margin:2px 0!important", ui)
        self.assertIn("Επιλογή όλων", ui)
        self.assertIn("Αποεπιλογή όλων", ui)
        self.assertIn("2026.9.19.3", ui)

if __name__=="__main__":
    unittest.main()
