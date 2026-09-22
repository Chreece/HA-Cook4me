from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"


class PriceProvenanceEtaV143Tests(unittest.TestCase):
    def test_v143_is_inherited_by_active_v144(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v143.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v180",panel)
        self.assertIn("cook4me-panel-v180.js",panel)
        self.assertIn("/cook4me_static/2026.9.22.7",panel)
        self.assertIn("?v=2026.9.22.7",panel)
        self.assertIn('"version": "2026.9.22.7"',manifest)
        self.assertIn(
            "if(!customElements.get(V142))await import('./cook4me-panel-v142.js?v=2026.9.21.7')",
            ui,
        )

    def test_product_prices_explain_exact_barcode_and_fallback_evidence(self):
        ui=(FRONTEND/"cook4me-panel-v143.js").read_text(encoding="utf-8")
        self.assertIn("paidExact:'Paid price · exact package'",ui)
        self.assertIn("barcodeObservation:'Same-barcode price observation'",ui)
        self.assertIn("previousPurchase:'Estimate from a previous purchase'",ui)
        self.assertIn("categoryEstimate:'Category estimate'",ui)
        self.assertIn("ingredientEstimate:'Ingredient estimate'",ui)
        self.assertIn("source==='purchase'||confidence==='exact_purchase'",ui)
        self.assertIn("source==='purchase_reference'",ui)
        self.assertIn("matchKind==='barcode'||identity.startsWith('barcode:')||(source==='open_prices'&&Boolean(ref.barcode))",ui)
        self.assertIn("source==='open_prices_category'",ui)

    def test_price_source_shows_location_age_provider_and_basis(self):
        ui=(FRONTEND/"cook4me-panel-v143.js").read_text(encoding="utf-8")
        self.assertIn("if(ref.location)items.push(String(ref.location))",ui)
        self.assertIn("_v143DateAge(reference)",ui)
        self.assertIn("observedDays:'observed {days} days ago'",ui)
        self.assertIn("_v143Provider(reference)",ui)
        self.assertIn("prices.openfoodfacts.org/prices/",ui)
        self.assertIn("v143-price-basis",ui)
        self.assertIn("v143-price-provider",ui)

    def test_price_provenance_is_visible_in_product_and_recipe_views(self):
        ui=(FRONTEND/"cook4me-panel-v143.js").read_text(encoding="utf-8")
        self.assertIn("this._v79Reference(ref,r.matchKind)",ui)
        self.assertIn("_v112PaintPrice()",ui)
        self.assertIn("this._v143CompactPriceSource(ref,r.matchKind)",ui)
        self.assertIn("_v79PaintItem(node,state)",ui)
        self.assertIn("source?' · '+source:''",ui)
        self.assertIn("value.estimatedPackages||0",ui)
        self.assertIn("estimatedPrices:'estimated prices'",ui)

    def test_bottom_right_job_card_has_rate_or_history_based_eta(self):
        ui=(FRONTEND/"cook4me-panel-v143.js").read_text(encoding="utf-8")
        self.assertIn("eta:'Estimated remaining'",ui)
        self.assertIn("estimatingEta:'Estimating remaining time…'",ui)
        self.assertIn("data-v143-eta",ui)
        self.assertIn("_v143EtaSamples",ui)
        self.assertIn("const rate=(d-base.done)/((now-base.at)/1000)",ui)
        self.assertIn("_v143HistoricalDuration(token)",ui)
        self.assertIn("cook4me.jobEta.v1.",ui)
        self.assertIn("slice(0,80)",ui)
        self.assertIn("duration<250||duration>6*60*60*1000",ui)

    def test_eta_does_not_claim_a_number_without_evidence_and_stops_on_finish(self):
        ui=(FRONTEND/"cook4me-panel-v143.js").read_text(encoding="utf-8")
        self.assertIn("eta===null?this._v143Text('estimatingEta')",ui)
        self.assertIn("token.failed||token.cancelled||token.ended",ui)
        self.assertIn("token&&!token.ended&&!token.failed&&!token.cancelled",ui)
        self.assertIn("querySelector('[data-v143-eta]')?.setAttribute('hidden','')",ui)


if __name__=="__main__":
    unittest.main()
