from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"


class StockSummaryExpiryV142Tests(unittest.TestCase):
    def test_v142_is_inherited_by_active_v143(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v142.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v178",panel)
        self.assertIn("cook4me-panel-v178.js",panel)
        self.assertIn("/cook4me_static/2026.9.22.5",panel)
        self.assertIn("?v=2026.9.22.5",panel)
        self.assertIn("async_register_websocket_v39",panel)
        self.assertIn('"version": "2026.9.22.5"',manifest)
        self.assertIn(
            "if(!customElements.get(V141))await import('./cook4me-panel-v141.js?v=2026.9.21.6')",
            ui,
        )

    def test_stock_summary_uses_price_coverage_and_nutrition_coverage(self):
        api=(ROOT/"custom_components"/"cook4me"/"websocket_v39.py").read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v142.js").read_text(encoding="utf-8")
        self.assertIn('store.best_reference("lot:" + lot_id',api)
        self.assertIn("store.barcode_reference(",api)
        self.assertIn("inventory_identity(row)",api)
        self.assertIn('"totalsByCurrency"',api)
        self.assertIn('"pricedPackages"',api)
        self.assertIn('"exactPackages"',api)
        self.assertIn("nutrition_for_amount(",api)
        self.assertIn('"coveredPackages"',api)
        self.assertIn("nutritionCoverage:'nutrition coverage'",ui)
        self.assertIn("stockNutrition:'Nutrients currently in stock'",ui)
        self.assertIn("v142-stock-nutrient-chips",ui)

    def test_expiry_section_is_a_seven_day_physical_lot_view(self):
        api=(ROOT/"custom_components"/"cook4me"/"websocket_v39.py").read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v142.js").read_text(encoding="utf-8")
        self.assertIn("_EXPIRY_WINDOW_DAYS = 7",api)
        self.assertIn("expiring_inventory_items(",api)
        self.assertIn("include_past=True",api)
        self.assertIn('"lotId": str(item.get("id") or "")',api)
        self.assertIn('"effectiveBestBefore"',api)
        self.assertIn("data-v142-expiry",ui)
        self.assertIn("data-v142-expiry-lot",ui)
        self.assertIn("void this._v112EditLot(id)",ui)
        self.assertIn("v142-expired",ui)
        self.assertIn("noneExpiring:'No products expire within the next 7 days.'",ui)

    def test_existing_stock_count_remains_and_extra_summary_is_injected(self):
        ui=(FRONTEND/"cook4me-panel-v142.js").read_text(encoding="utf-8")
        self.assertIn("data-v142-stock-summary",ui)
        self.assertIn("v142-summary-grid",ui)
        self.assertIn("packages:'Packages'",ui)
        self.assertIn("stockValue:'Stock value'",ui)
        self.assertIn("expiringCount:'Expiring soon'",ui)
        self.assertNotIn("replaceChildren(launch",ui)

    def test_meal_name_and_date_have_spacing(self):
        ui=(FRONTEND/"cook4me-panel-v142.js").read_text(encoding="utf-8")
        self.assertIn(".v131-history-main>strong+.muted{margin-left:12px}",ui)


if __name__=="__main__":
    unittest.main()
