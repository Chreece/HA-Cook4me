# v99: recipe price confidence and unmeasured basics

Recipe cards show compact prices at the upper-left of the image. Colour describes
the evidence behind the amount. Icons, accessible labels and a legend in the
price details also explain the state.

| Colour | Meaning |
| --- | --- |
| Green | Complete cost based on saved manual prices or actual purchases, with known quantities |
| Blue | Complete estimate using ingredient price references or sourced quantity conversions |
| Amber | Complete estimated budget using comparable-food prices and/or zero allowances |
| Red | Incomplete subtotal: at least one ingredient still lacks an amount or usable price |
| Grey | No usable total yet, loading, or failed lookup |

Saved prices are not a guarantee of a future checkout price. The colours describe
price evidence, not whether a recipe is cheap or expensive. Costs for recipes
requiring substitutions continue to describe the original ingredients.

## Explicit zero allowances

Unmeasured salt, seasoning pepper, salt-and-pepper combinations, water and reviewed
exact canonical forms receive a zero-cost **budgeting allowance**. Details show
the assumption next to each ingredient. This does not invent a quantity, create a
price observation or increase known-price coverage. The policy applies even when
automatic external estimates are disabled, using the selected currency.

Measured amounts and source-recovered amounts keep their normal calculation.
An amount with an unsupported unit, an invalid quantity, oil, saffron, stock,
salted butter, vegetables and other non-basic ingredients do not become free.
Ambiguous provider “Pepper” requires the reviewed black-pepper identity or an
explicit seasoning unit; otherwise it remains unresolved. Excluded catalogue
items cannot acquire a zero allowance.

## Catalogue audit

The 17 September 2026 audit covered 32,163 language/serving variants and 230,483
ingredient occurrences, using DE/EUR references without household prices.

| Measure | Before | v99 |
| --- | ---: | ---: |
| Ingredients with price references | 132,921 | 132,921 |
| Ingredients with comparable-food estimates | 43,460 | 43,460 |
| Explicit zero allowances | 0 | 13,462 |
| Variants with complete known prices | 5,575 | 5,575 |
| Variants with complete estimated budgets | 11,465 | 15,252 |

The allowance affects 11,679 variants and completes 3,787 additional estimated
budgets. These counts include translated and serving variants, not unique recipe
families. Evidence remains 509 observations: 371 receipt observations and 138
retail references. The detailed audit records eligible names and remaining gaps
in `price-allowances-v99-audit.json`.

## Verification and installation

Focused backend checks cover online/offline agreement, duplicate measured and
unmeasured rows, saved and purchase prices, separate currencies, excluded items,
source-recovered quantities, fallbacks, translated recipes and persisted caches.
The browser check uses the shipped v99 bundle and real calculator fixtures. It
checks confidence states, zero amounts, retry controls, and card placement at
360, 390 and 1600 pixels in English, German and Greek.

Reproduce with:

```sh
python -m unittest discover -s tests -p test_price_allowances_v99.py
python -m unittest discover -s tests -p test_price_fallback_v91.py
python -m unittest discover -s tests -p test_price_conversions_v94.py
python tools/audit_price_allowances_v99.py --output docs/price-allowances-v99-audit.json
python tests/build_price_fixture_v99.py docs/price-confidence-v99-preview.json
python tools/build_frontend_bundle_v99.py --check
node tests/frontend_v99_price_confidence_browser.mjs
python -m unittest discover -s tests -p test_deploy_offline_runtime_v99.py
```

The pinned `tools/deploy_offline_runtime_v99.sh` installer retains the previous
integration for rollback, checks the offline evidence and allowance policy before
stopping Home Assistant, and verifies the installed bundle after restart. Runtime
build: `2026.9.17.3`. Cost-cache evidence/calculator versions: `99`.

The release includes v98 Today persistence, suggestion rotation and filter
controls. Live Home Assistant installation must be run on the user's server.
