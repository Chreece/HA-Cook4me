# Scanner compatibility audit v194

Base: `0052f12dfeb1620771bb719e7530362ff3d26b03` (Greek audit v193). PR #236.

## Findings

The review-first scanner called the legacy matcher, which defaulted to 12 suggestions and never returned more than 30. Its frontend then displayed only five suggestion buttons. Word subsets and partial overlap could confuse products with their components. The complete catalog picker already supported multiple saved ingredient links, but those relevant choices were not all surfaced as suggestions.

## Implemented

Barcode and product-photo review now use a dedicated scanner matcher. It returns all evidenced candidates by default, preserving stable keys, current UI names and source identities. Exact multilingual catalog aliases, whole-name phrases and specific categories provide evidence; same-food preparation variants can also be suggested. Generic categories and a product's ingredient list do not establish a match. Explicit food-form guards keep raw, cooked, canned, dried, frozen, pickled, smoked and transformed forms separate where evidence distinguishes them. Dried variants require explicit dried-product evidence, including after preparation expansion. Ordering and evidence selection are deterministic.

The active panel uses a scrollable, filterable multi-select suggestion list with visible counts, selected-state feedback and English/German/Greek guidance. Selecting another suggestion does not discard existing links. A selected candidate stays visible during filtering. Source IDs are normalized before display and selection; stale handlers cannot assign a candidate from a replaced scan. Scroll position and keyboard focus survive the inherited renderer's replacement of the old five-button markup. The full catalog manual picker remains available. The panel module URL includes `scanner=194` to refresh the changed active module.

Recognition stays review-only. The v33 barcode and photo endpoints never assign the top suggestion automatically or write stock. Existing remembered mappings remain separate. Product photo prompts retain food form and forbid replacing a mixture with its components. Date and nutrition scans do not suggest product ingredients. No camera lifecycle, save/idempotency logic, physical quantity, nutritional profile or price calculation is changed. Existing ingredient-link normalization has no artificial result cap and preserves a single shared physical package.

## Validation

Reproducible commands:

```sh
python tests/test_scanner_matching_v194.py
node --test tests/test_scanner_suggestions_v194.mjs
python tests/test_scanner_routes_v194.py
```

The final matcher and interaction changes have 37 Python matcher tests and 22 JavaScript tests locally. The route/catalog suite contains 11 tests. The initial CI run passed all 65 then-existing tests and the existing Validate/Greek workflows; final CI must also pass for the follow-up commit before merge.

The shipped-catalog checks load 3,365 Greek and 4,069 German choices from the repository. Actual sample lookup results include five canned/cooked/generic chickpea entries without dried chickpeas or chickpea flour; coconut milk without dairy milk; and Greek product names resolving to German catalog names. The initial carrot sample exposed a dried-carrot false positive despite green tests; the final correction adds a regression rejecting dried variants without evidence.

The JavaScript suite uses a minimal DOM double. Endpoint tests execute production handler bodies with controlled Home Assistant, product lookup and AI boundaries. Real cameras, image-recognition accuracy, user stock and a live Home Assistant deployment were not tested. This is not a claim that every possible compatible food or culinary substitution is recognized. Missing or contradictory catalog/product evidence remains a manual-search/review case, and candidate scores are ranking signals, not allergy or nutritional assurances.

The separate unmerged v189/v190 pricing bundles are not included or overwritten. No release version is bumped and no live deployment is performed.
