# Cook4Me v104: price and recipe fixes

Build `2026.9.17.8` is cumulative from published v103 (`f86cdec36dd8a08a713169c4f1bc62afe7e14d9d`). It retains all previous price references, portions, responsive navigation, filters and Today persistence/rotation.

## Price overview and fullscreen controls

- Recipe card badges display amounts and confidence symbols/colours, with no visible words. Loading and retry also use icons; translated accessible labels and tooltips remain available.
- The recipe price overview displays the total, a money/refresh icon beside it, and the per-serving amount with a person icon. Source details and explanations open from the information icon.
- The fullscreen title no longer contains a duplicate refresh button. Refresh uses the existing forced price refresh endpoint for the open recipe and disables its button while running.
- The global price refresh also uses `mdi:cash-sync` rather than a generic arrow.
- Ingredient details appear above the fullscreen recipe. The underlying recipe is inert while the ingredient dialog is open. Tab stays within the dialog; closing it returns focus to the ingredient without closing the recipe. A response for a recipe already closed is discarded.

## Inflated estimate audit

The reported Romanian recipe, variant `314559`, contains 20 pieces of mint. The old food-basket fallback treated each piece as a supermarket item costing €0.94, adding €18.80. Leaves, cloves, slices and whole vegetables are not comparable pieces.

Fallback comparisons now require mass or volume. A sourced conversion from pieces to edible mass remains usable. Exact product/package prices and saved household prices per piece remain valid. No arbitrary price cap, discount or invented mint weight is used.

| Reported recipe | v103 displayed budget | v104 subtotal | Remaining issue |
| --- | ---: | ---: | --- |
| Legume și mozzarella la abur, 4 servings (`314559`) | €20.92 | €2.12 | Mint quantity has no supported price basis |
| Брускети с боб и козе сирене, 4 servings (`321369`) | €14.30 | €4.90 | Some ingredient quantities remain unpriced |

These are incomplete subtotals, identified by the red confidence colour, `!` symbol, accessible label and expandable evidence. Missing ingredients are not treated as free. Unmeasured salt, pepper and water retain their existing explicit zero-budget allowance.

The full DE/EUR catalog audit covers 32,163 language/serving variants and 230,483 ingredient occurrences, without household prices:

| Measure | v103 | v104 |
| --- | ---: | ---: |
| Occurrences with ingredient-specific references | 134,964 | 134,964 |
| Occurrences with rough budget assumptions | 41,616 | 34,208 |
| Unmeasured basic zero allowances | 13,462 | 13,462 |
| Variants with complete reference coverage | 5,779 | 5,779 |
| Variants with complete estimated budgets | 15,311 | 12,785 |

The 7,408 invalid piece assumptions are removed. The lower budget coverage is intentional: previously unsupported totals now show partial or unavailable status. Existing reference counts remain 520 observations, 123 USDA portions, six recipe-specific portions, five densities and 18 benchmark groups. Calculator, quantity-evidence and browser cache tokens advance to 104 so old inflated results are discarded.

Reproduce the audit with `python tools/audit_price_fixes_v104.py --output /tmp/cook4me-v104-audit.json`. The checked-in JSON records the comparison and affected ingredients; the preview fixture comes from the real offline calculator and translated release catalog.

## Device entities

The old migration deliberately disabled 14 individual sensors and the updating binary sensor after the summary and connected entities loaded. All 17 entities now default to enabled, using the existing shared bridge subscription.

Before platform setup, a one-time migration restores only this device's Cook4Me entities whose registry disabler is `INTEGRATION`. User-disabled entities, other devices, other entries and unrelated entities are preserved. The migration retries if saving its marker fails and never runs the old disabling operation.

## Validation and installation

- Five focused price tests cover both screenshot recipes, valid mass conversions, exact/manual per-piece prices and cache invalidation.
- Six v103 price tests and eight v99 allowance tests preserve reference and zero-allowance behavior.
- Two entity setup tests and 14 announcement/registry tests cover defaults, migration ordering, user choices, persistence and existing announcement behavior.
- The browser test exercises the built v104 bundle in English, German and Greek at 360, 390 and 1,600 px. It checks text-free badges and overview, five confidence colours, evidence access, the actual scoped refresh path, retry behavior, popup hit-testing, inert background, keyboard focus and both close methods.
- Python/JavaScript syntax, bundle reproducibility and installer shell syntax are checked. The pinned installer runs price and entity tests before swapping files, validates the installed bundle, and retains backup/rollback handling.

Use the pinned `tools/deploy_offline_runtime_v104.sh` from the published v104 branch. Installation is performed on the Home Assistant host; publishing this update does not itself alter the running server.
