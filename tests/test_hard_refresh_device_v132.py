from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"


class HardRefreshDeviceAssetV132Tests(unittest.TestCase):
    def test_hard_refresh_recovers_pre_upgrade_home_assistant_properties(self):
        ui=(FRONTEND/"cook4me-panel-v132.js").read_text(encoding="utf-8")
        self.assertIn("Object.prototype.hasOwnProperty.call(this,name)",ui)
        self.assertIn("this._v132UpgradeProperty('panel')",ui)
        self.assertIn("this._v132UpgradeProperty('hass')",ui)
        self.assertIn("if(this._hass&&this.shadowRoot&&!this.shadowRoot.innerHTML)",ui)
        self.assertIn("void this._loadOverview()",ui)

    def test_device_model_uses_real_static_jpeg_not_embedded_data_uri(self):
        ui=(FRONTEND/"cook4me-panel-v132.js").read_text(encoding="utf-8")
        asset=FRONTEND/"assets"/"device-v132.jpg"
        payload=asset.read_bytes()
        self.assertGreater(len(payload),5000)
        self.assertEqual(payload[:2],b"\xff\xd8")
        self.assertEqual(payload[-2:],b"\xff\xd9")
        self.assertIn("new URL('./assets/device-v132.jpg?v=2026.9.20.6',import.meta.url)",ui)
        self.assertIn("image.src=DEVICE_ASSET_V132",ui)
        self.assertNotIn("data:image/jpeg;base64",ui)

    def test_asset_failure_has_visible_fallback_instead_of_broken_image(self):
        ui=(FRONTEND/"cook4me-panel-v132.js").read_text(encoding="utf-8")
        self.assertIn("v132-model-image-error",ui)
        self.assertIn("image.addEventListener('error'",ui)
        self.assertIn(".v130-model-photo{opacity:0}",ui)

    def test_v132_is_inherited_by_active_v138(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v132.js").read_text(encoding="utf-8")
        v133=(FRONTEND/"cook4me-panel-v133.js").read_text(encoding="utf-8")
        v134=(FRONTEND/"cook4me-panel-v134.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v150",panel)
        self.assertIn("cook4me-panel-v150.js",panel)
        self.assertIn("/cook4me_static/2026.9.21.15",panel)
        self.assertIn("?v=2026.9.21.15",panel)
        self.assertIn('"version": "2026.9.21.15"',manifest)
        self.assertIn("if(!customElements.get(V133))await import('./cook4me-panel-v133.js?v=2026.9.20.7')",v134)
        self.assertIn("if(!customElements.get(V132))await import('./cook4me-panel-v132.js?v=2026.9.20.6')",v133)
        self.assertIn("if(!customElements.get(V131))await import('./cook4me-panel-v131.js?v=2026.9.20.5')",ui)


if __name__=="__main__":
    unittest.main()
