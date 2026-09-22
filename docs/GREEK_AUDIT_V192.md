# Greek catalog audit v192 — pass 45

Continues after merged v191 (PR #233). Eleven exact-key Greek wording changes retain prior aliases. Mixed-colour peppers no longer sound like one multicoloured pepper. Three chocolate-powder descriptions retain the powder and keep the low-calorie modifier on that ingredient rather than extending it to the whole biscuit/cake. Grapefruit, vanilla seeds and breadcrumb forms receive clearer wording. Source ingredient, nutrition and price identities are unchanged.

## Display-unit defects

The original shopping_presentation.py (Git blob 13fe8296e2154d9e3ba6a9c3727109eb4f15ca3a) had an over-escaped whitespace character class: it removed literal s characters and did not remove spaces. Correct it and normalize both lookup labels and lookup keys consistently.

Reuse canonical units, reviewed aliases/label overrides, explicit provider unit IDs and unique translated unit labels from ui_units.v1.json. Ambiguous labels such as German Glas and Stück stay unresolved unless an explicit key disambiguates them. This changes display strings only, never conversion factors or purchase/recipe quantities.

Resolve the existing weight fallback before displayUnit. Preserve explicit top-level quantities. Recognize decimal-comma singular values for Greek unit grammar without changing stored values.

Examples: uppercase TSP -> κ.γ.; TBSP -> κ.σ.; Greek κ. σ. -> German EL; 1,0 kg -> κιλό; fallback weight 120 g -> 120 γρ. UI / supermarket / original name ordering remains unchanged.

## Validation

18 new regression tests plus the retained 22 v191 tests pass locally with sampled unit/locale data and production function bodies. The original source was reconstructed and verified against its Git blob hash; the new unit regressions fail on that original implementation. CI must run both the existing Validate suite and Greek audit regressions on the actual repository data before merge. Live HA/browser testing is not performed here.

Run: python -m unittest discover -s tests -p 'test_greek_catalog_audit_v19*.py' -v

This does not merge or replace the separate v189/v190 pricing bundles, and does not create a release or deploy Home Assistant.
