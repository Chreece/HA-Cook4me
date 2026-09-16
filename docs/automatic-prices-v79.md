# Automatic product and recipe prices (v79)

The scanner and recipe view now share country-scoped price evidence. Your kitchen → Integration settings → Prices & recipe costs selects the shopping country, currency and automatic lookup. First use defaults to Home Assistant's country and that country's currency, rather than the UI language. Currency defaults use bundled Unicode CLDR 48 data, effective 2026-09-16, with no optional Python locale dependency. A country change selects its currency unless the user explicitly enters another.

## Product capture

Barcode lookup and selecting a catalog ingredient automatically request a price preview. This covers barcode capture, reviewed AI product photos and manual products. Changing the package quantity/unit recalculates the preview. The preview shows the observed price basis, country, shop, date and a link to the observation.

An optional “Amount paid for this package” field saves the actual expense for that stock lot. Zero is a valid paid amount; an empty field means unknown. Observed prices never populate the paid amount. The paid amount, currency and shop are frozen in the existing product retry payload. A failure after stock is saved can be retried without adding stock twice.

Confirmed barcode-to-ingredient prices and entered purchase prices remain useful estimates for later recipes, including when that stock has been consumed. Actual lot costs take priority over estimates.

## Recipe costs

Opening or expanding a recipe automatically calculates ingredient costs, the recipe total and per-serving cost. Changing the recipe/serving variant calculates from the new ingredient amounts. Original ingredients are used; advisory dietary replacements are explicitly excluded from these costs.

Each ingredient displays its cost. The source disclosure gives the price basis, shop, date and source evidence. If any amount or price is missing, the card shows **Known subtotal · incomplete**, with the number of fully priced ingredients. Unknown amounts count as missing. Mass, volume and item counts are never converted into one another without a known conversion. Paid expenses in different currencies remain separate; no exchange rate is implied.

Unpriced stock can use an explicit ingredient estimate. The recipe cache now fingerprints the actual composite-key reference store, so changed prices invalidate the cost. Daily expiry, stock lots, amounts, serving variants and country/currency preferences also affect the fingerprint. The browser ignores replies for an old product, recipe variant, user or device.

## Price source and limits

The source is [Open Prices](https://openfoodfacts.github.io/open-prices/), using its [read-only API](https://prices.openfoodfacts.org/api/docs) and published [API schema](https://prices.openfoodfacts.org/api/schema).

- Barcode matches use the exact product code and a documented package amount. The current API allows `price_per: null` for packaged products; that price uses the product's stated package quantity.
- Supported exact English catalog names can use explicitly mapped ingredient categories. These are similar-ingredient estimates, not exact brand matches or national averages. Prepared or mixed foods are not matched by fuzzy name stripping.
- Raw category observations use the API's explicit `KILOGRAM` or `UNIT` basis. Packaged category matches must also contain the requested product taxonomy tag.
- Only matching country and currency observations dated within the previous 180 days are usable. Unknown countries, future/undated observations, duplicates and discounted prices are excluded.
- The current prices endpoint does **not** expose a country filter. Country is strictly checked against returned shop locations. Each query examines a bounded sample of the latest 100 matching observations; an empty result does not prove a country/product has no prices.
- Automatic lookups allow 15 seconds per query, three concurrent requests and a 30-second recipe budget. Recent saved observations can be reused for a day; misses are cached for an hour and source failures for one minute. A slow or unavailable source leaves a partial cost rather than inventing a number.
- No AI price guessing, receipt uploads, retailer account access or automatic purchases are involved. Open Prices coverage varies, and a shop's current price can differ from the observation.

The user can enter paid prices during capture and maintain existing lot/ingredient price references through the existing Week cost controls.

## Deployment and validation

Active panel: `cook4me-panel-v79-bundle.js`; cache path: `2026.9.16.4`.
Installer: `tools/deploy_offline_runtime_v79.sh`. It fetches a pinned runtime, runs preflight tests before stopping Home Assistant, preserves a backup, verifies the served bundle and rolls back failed activation.

Tested runtime: `c7096d7e3824cf1a998e07fffe95dff057d29c51`.

- Full Python suite: 1,424 tests passed, including 24 automatic-pricing cases.
- Final pinned installer: four isolated preflight, backup and rollback checks passed.
- Chromium: automatic barcode/ingredient estimates, zero paid amount, exact retry payload, country settings, mobile capture, totals/per-serving/partial costs, serving changes and stale responses passed.
- Existing capture/storage, dietary replacements, original-program Send, device settings, navigation and responsive photo/card checks passed on active v79.
- English, German and Greek labels checked. Mobile product pricing and recipe cost screenshots inspected.
- Live API/schema checks confirmed package-null and per-kilogram semantics, and usable German rice/tomato observations. Country currency defaults were checked against Unicode CLDR 48 data.
- Syntax, generated bundles, workflow parsing and diff checks passed. Published Git trees match the tested local trees.

No live Home Assistant or cooker deployment was performed from this workspace.
