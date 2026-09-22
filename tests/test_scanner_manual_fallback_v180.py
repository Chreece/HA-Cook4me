from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
UI=FRONTEND/"cook4me-panel-v180.js"


class ScannerManualFallbackV180Tests(unittest.TestCase):
    def test_outside_barcode_guide_opens_manual_entry_with_hint(self):
        ui=UI.read_text(encoding="utf-8")
        self.assertIn("Tap outside the barcode box to enter the product manually.",ui)
        self.assertIn("Πάτησε έξω από το πλαίσιο του barcode",ui)
        self.assertIn("[data-v111-guide]",ui)
        self.assertIn("if(!inside)",ui)
        self.assertIn("_v180OpenManualFromFrame()",ui)
        self.assertIn("this._v78StopCamera?.()",ui)
        self.assertIn("d.mode='manual'",ui)
        self.assertIn("this._v112Editor?.(true,'product')",ui)

    def test_no_camera_goes_directly_to_manual_mode(self):
        ui=UI.read_text(encoding="utf-8")
        self.assertIn("navigator.mediaDevices?.getUserMedia",ui)
        self.assertIn("enumerateDevices",ui)
        self.assertIn("mode='manual'",ui)
        self.assertIn("d.editorOpen=true",ui)
        self.assertIn("No usable camera is available",ui)
        self.assertIn("Δεν υπάρχει διαθέσιμη ή υποστηριζόμενη κάμερα",ui)

    def test_no_camera_hides_camera_specific_controls(self):
        ui=UI.read_text(encoding="utf-8")
        for token in (
            "[data-v80-scan]","[data-v111-power]","[data-v78-camera]",
            "[data-v78-take]","[data-v78-native]","[data-v78-file]",
        ):
            self.assertIn(token,ui)
        self.assertIn("node.hidden=true",ui)
        self.assertIn("v180-manual-only",ui)
        self.assertIn(".v180-manual-only .v111-modes",ui)

    def test_runtime_camera_failure_falls_back_to_manual(self):
        ui=UI.read_text(encoding="utf-8")
        self.assertIn("!live&&this._v141CameraBlocked",ui)
        self.assertIn("this._v180SetManualOnly(this._v180Text('noCamera'))",ui)


if __name__=="__main__":
    unittest.main()
