from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"


class ScannerFlowV141Tests(unittest.TestCase):
    def test_v141_is_inherited_by_active_v142(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v141.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v155",panel)
        self.assertIn("cook4me-panel-v155.js",panel)
        self.assertIn("/cook4me_static/2026.9.21.20",panel)
        self.assertIn("?v=2026.9.21.20",panel)
        self.assertIn('"version": "2026.9.21.20"',manifest)
        self.assertIn(
            "if(!customElements.get(V140))await import('./cook4me-panel-v140.js?v=2026.9.21.5')",
            ui,
        )

    def test_scanner_has_one_centered_explained_busy_surface(self):
        ui=(FRONTEND/"cook4me-panel-v141.js").read_text(encoding="utf-8")
        for text in (
            "Starting camera…",
            "Looking up product…",
            "Reading the label…",
            "Saving product to stock…",
            "Loading Cook4Me ingredients…",
            "Checking price information…",
        ):
            self.assertIn(text,ui)
        self.assertIn("data-v141-busy",ui)
        self.assertIn(".v141-busy{position:absolute;inset:0",ui)
        self.assertIn(".v141-processing [data-v111-result]{visibility:hidden!important}",ui)
        self.assertIn(".v141-processing [data-v78-status]{display:none!important}",ui)
        self.assertIn(".v141-processing .v111-spinner{display:none!important}",ui)

    def test_camera_stays_warm_while_recognition_is_paused_by_state(self):
        ui=(FRONTEND/"cook4me-panel-v141.js").read_text(encoding="utf-8")
        self.assertIn("_v141KeepCameraWarm()",ui)
        self.assertIn("getVideoTracks?.().some(track=>track.readyState==='live')",ui)
        self.assertIn("d.mode==='manual'||document.hidden",ui)
        self.assertIn("node.hidden=true;node.setAttribute('aria-hidden','true')",ui)
        self.assertIn("this._v141CameraWasHidden=true",ui)
        self.assertIn("this._v141CameraBlocked=false",ui)
        self.assertIn("this._v111NewDraft('barcode');await this._v80Scan('barcode')",ui)

    def test_unmatched_products_open_assignment_and_selected_suggestions_are_visible(self):
        ui=(FRONTEND/"cook4me-panel-v141.js").read_text(encoding="utf-8")
        self.assertIn("_v141NeedsAssignment()",ui)
        self.assertIn("d.editorOpen=true;this._v111Paint()",ui)
        self.assertIn("data-v114-links",ui)
        self.assertIn("scrollIntoView?.({block:'start',behavior:'smooth'})",ui)
        self.assertIn("button.classList.toggle('v141-selected',picked)",ui)
        self.assertIn("button.setAttribute('aria-pressed',String(picked))",ui)
        self.assertIn("[data-v78-suggestions] [data-suggest].v141-selected",ui)

    def test_no_expiry_and_optional_storage_are_persisted_without_being_required(self):
        ui=(FRONTEND/"cook4me-panel-v141.js").read_text(encoding="utf-8")
        websocket=(ROOT/"custom_components"/"cook4me"/"websocket_v33.py").read_text(encoding="utf-8")
        inventory=(ROOT/"custom_components"/"cook4me"/"inventory.py").read_text(encoding="utf-8")
        self.assertIn("noExpiry:false",ui)
        self.assertIn("data-v141-no-expiry",ui)
        self.assertIn("best_before:d.noExpiry?'':d.bestBefore",ui)
        self.assertIn("'noExpiry'",ui)
        self.assertIn("place.required=false",ui)
        self.assertNotIn('raise ValueError("Choose where this product is stored")',websocket)
        self.assertIn('"noExpiry"',websocket)
        self.assertIn('if raw.get("noExpiry") is True:',inventory)
        self.assertIn('stamp = "" if raw.get("noExpiry") is True else _best_before(',inventory)

    def test_stock_commit_side_effects_are_parallel_and_catalog_is_reused(self):
        websocket=(ROOT/"custom_components"/"cook4me"/"websocket_v33.py").read_text(encoding="utf-8")
        self.assertIn('cache = getattr(bridge, "_scanner_catalog_cache", None)',websocket)
        self.assertIn("async def save_nutrition_details()",websocket)
        self.assertIn("async def save_barcode_mapping()",websocket)
        self.assertIn("async def save_prices()",websocket)
        self.assertIn("side_effects = await asyncio.gather(",websocket)
        self.assertIn("return_exceptions=True",websocket)
        self.assertLess(
            websocket.index("committed = True"),
            websocket.index("side_effects = await asyncio.gather("),
        )

    def test_errors_are_red_and_receive_focus(self):
        ui=(FRONTEND/"cook4me-panel-v141.js").read_text(encoding="utf-8")
        self.assertIn("node.setAttribute('role','alert');node.tabIndex=-1",ui)
        self.assertIn("node.scrollIntoView?.({block:'center',behavior:'smooth'})",ui)
        self.assertIn("node.focus?.({preventScroll:true})",ui)
        self.assertIn("border:2px solid #ff4d4f!important",ui)
        self.assertIn("d.editorOpen=true;this._v141ErrorSignature='';this._v111Paint()",ui)


if __name__=="__main__":
    unittest.main()
