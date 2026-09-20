from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"


class PhotorealDeviceV130Tests(unittest.TestCase):
    def test_device_model_is_debranded_and_embedded(self):
        ui=(FRONTEND/"cook4me-panel-v130.js").read_text(encoding="utf-8")
        self.assertIn("data:image/jpeg;base64,",ui)
        self.assertIn("v130-brand-mask",ui)
        self.assertNotIn("KRUPS",ui)
        self.assertNotIn(">Cook4Me<",ui)
        self.assertIn("Smart cooker",ui)
        self.assertIn("Multikocher",ui)
        self.assertIn("Έξυπνη χύτρα",ui)

    def test_loaded_recipe_photo_is_rendered_on_device_display(self):
        ui=(FRONTEND/"cook4me-panel-v130.js").read_text(encoding="utf-8")
        self.assertIn("state.recipeImage",ui)
        self.assertIn("queue?.recipe?.cover",ui)
        self.assertIn("v130-recipe-photo",ui)
        self.assertIn("_v130LastPhoto",ui)
        self.assertIn("_v130LastPhotoTitle",ui)

    def test_live_phases_have_distinct_animations(self):
        ui=(FRONTEND/"cook4me-panel-v130.js").read_text(encoding="utf-8")
        for value in ("preheating","cooking","warm","done","loading","offline","idle"):
            self.assertIn(value,ui)
        for animation in ("v130Steam","v130Pressure","v130Float","v130Done","v130Load"):
            self.assertIn(animation,ui)
        self.assertIn("prefers-reduced-motion:reduce",ui)

    def test_v130_inherits_pending_delivery_without_product_brand_text(self):
        ui=(FRONTEND/"cook4me-panel-v130.js").read_text(encoding="utf-8")
        self.assertIn("V130_QUEUE_TEXT",ui)
        self.assertIn("Sending to appliance",ui)
        self.assertIn("Αποστολή στη συσκευή",ui)
        self.assertIn("Wird an das Gerät gesendet",ui)
        self.assertIn("if(!customElements.get(V129))await import('./cook4me-panel-v129.js?v=2026.9.20.3')",ui)

    def test_v130_is_inherited_by_active_v131(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        v131=(FRONTEND/"cook4me-panel-v131.js").read_text(encoding="utf-8")
        self.assertIn('cook4me-recipe-hub-panel-v131',panel)
        self.assertIn('cook4me-panel-v131.js',panel)
        self.assertIn('/cook4me_static/2026.9.20.5',panel)
        self.assertIn('?v=2026.9.20.5',panel)
        self.assertIn('"version": "2026.9.20.5"',manifest)
        self.assertIn("if(!customElements.get(V130))await import('./cook4me-panel-v130.js?v=2026.9.20.4')",v131)


if __name__=="__main__":
    unittest.main()
