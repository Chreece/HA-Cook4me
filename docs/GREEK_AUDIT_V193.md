# Greek audit v193 — ingredient-first spoon and cup labels

Base: `4353a3a6e7e520829c742c90626e7998f6623b7b` (v192).

## Finding

91 existing Greek labels insert a fixed `1` into an ingredient name whose source mentions a spoon or cup without a numeric quantity. This fixed number does not follow the recipe's structured amount or serving changes. The exact-key overlay removes it, puts the ingredient first and retains the source measurement hint: `Ελαιόλαδο (κ.σ.)`, not `1 κ.σ. ελαιόλαδο`.

The batch covers 53 tablespoon, 34 teaspoon and 4 cup labels. Breadcrumb wording follows v192: `Τρίμματα ψωμιού`, without asserting that the bread was toasted. Greek declension is corrected for standalone ingredient names. Every old label and source key is recorded alongside its replacement in `custom_components/cook4me/catalog_ui_locales/zz_el_curated_v193.json`.

## Examples

| Source | Greek label |
|---|---|
| tablespoon of olive oil | Ελαιόλαδο (κ.σ.) |
| tbsp fresh coriander | Φρέσκος κόλιανδρος (κ.σ.) |
| tablespoon of frozen green pea | Κατεψυγμένος αρακάς (κ.σ.) |
| tsp breadcrumbs | Τρίμματα ψωμιού (κ.γ.) |
| tsp turmeric | Κουρκουμάς (κ.γ.) |
| cup of long-grain white rice | Λευκό μακρύκοκκο ρύζι (φλιτζάνι) |

## Boundaries

No generic number stripping or food substitution is added. Explicit fractions, percentages, heaped spoons and ambiguous measures remain untouched. Ingredient IDs, original names, units, quantities, nutrition, price categories and country/currency settings are not edited. Source hints remain labels, not new conversions or claims that a cup has a particular volume. The v189/v190 pricing bundles are not included.

Old Greek labels and exact English keys remain searchable; previous alias layers are retained. Non-Greek label maps are unchanged. The German supermarket label remains German with a Greek UI; choosing Greek supermarket language changes its label only.

## Validation

`python -m unittest discover -s tests -p 'test_greek_catalog_audit_v19*.py' -v`

The existing Greek-audit workflow discovers v193 automatically. The 15 new tests read the actual repository presentation/shopping functions, complete locale files and unit files. Only catalog identity resolution is controlled in shopping tests. Coverage includes all 91 labels, earlier aliases, numeric and food-form boundaries, unchanged structured data and Greek/German label separation. Local preflight used reviewed source/data excerpts (13 tests); the two shopping integration tests require the repository run.

No workflow triggers or release versions change. Live Home Assistant/browser validation remains outstanding; a repository merge is not a production deployment.
