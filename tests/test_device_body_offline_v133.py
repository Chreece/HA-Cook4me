from pathlib import Path
import hashlib
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"


def git_blob_sha(payload: bytes) -> str:
    header=f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header+payload).hexdigest()


class DeviceBodyOfflineV133Tests(unittest.TestCase):
    def test_correct_reference_photo_is_packaged(self):
        asset=FRONTEND/"assets"/"device-v133.jpg"
        payload=asset.read_bytes()
        self.assertGreater(len(payload),10000)
        self.assertEqual(payload[:2],b"\xff\xd8")
        self.assertEqual(payload[-2:],b"\xff\xd9")
        self.assertEqual(
            git_blob_sha(payload),
            "232baad9e67b61f7d1417e2c0ecc2a4ccc0f49a4",
        )

    def test_v133_uses_reference_asset_and_keeps_body_visible(self):
        ui=(FRONTEND/"cook4me-panel-v133.js").read_text(encoding="utf-8")
        self.assertIn(
            "new URL('./assets/device-v133.jpg?v=2026.9.20.7',import.meta.url)",
            ui,
        )
        self.assertIn("image.src=DEVICE_ASSET_V133",ui)
        self.assertIn("mix-blend-mode:multiply",ui)
        self.assertIn("filter:brightness(1.08) contrast(1.1)",ui)
        self.assertIn("opacity:1!important",ui)

    def test_nutrient_spacing_is_structural_not_regex_dependent(self):
        ui=(FRONTEND/"cook4me-panel-v133.js").read_text(encoding="utf-8")
        self.assertIn("document.createTreeWalker(chip,NodeFilter.SHOW_TEXT)",ui)
        self.assertIn("v133-nutrient-spacer",ui)
        self.assertIn("width:7px",ui)
        self.assertIn("querySelectorAll('.v131-nutrient-gap').forEach(node=>node.remove())",ui)

    def test_offline_screen_never_falls_back_to_ready(self):
        ui=(FRONTEND/"cook4me-panel-v133.js").read_text(encoding="utf-8")
        self.assertIn("this._v130Phase(entry)!=='offline'",ui)
        self.assertIn("strong.textContent=this._v130Text('offline')",ui)
        self.assertIn("state.textContent=this._v133Text('noConnection')",ui)
        self.assertIn("v133-offline-screen .v130-screen-progress{display:none}",ui)
        self.assertIn("Χωρίς σύνδεση",ui)
        self.assertIn("Keine Verbindung",ui)
        self.assertIn("No connection",ui)

    def test_v133_inherits_hard_refresh_recovery(self):
        v132=(FRONTEND/"cook4me-panel-v132.js").read_text(encoding="utf-8")
        v133=(FRONTEND/"cook4me-panel-v133.js").read_text(encoding="utf-8")
        v134=(FRONTEND/"cook4me-panel-v134.js").read_text(encoding="utf-8")
        self.assertIn("this._v132UpgradeProperty('hass')",v132)
        self.assertIn(
            "if(!customElements.get(V132))await import('./cook4me-panel-v132.js?v=2026.9.20.6')",
            v133,
        )

    def test_v133_is_inherited_by_active_v138(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        v134=(FRONTEND/"cook4me-panel-v134.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v167",panel)
        self.assertIn("cook4me-panel-v167.js",panel)
        self.assertIn("/cook4me_static/2026.9.21.32",panel)
        self.assertIn("?v=2026.9.21.32",panel)
        self.assertIn('"version": "2026.9.21.32"',manifest)
        self.assertIn("if(!customElements.get(V133))await import('./cook4me-panel-v133.js?v=2026.9.20.7')",v134)


if __name__=="__main__":
    unittest.main()
