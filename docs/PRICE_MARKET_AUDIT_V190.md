> Consolidation note: the previously local patch documented below is included in v197. Original fixture-test and publication notes are retained as history; see BRANCH_CONSOLIDATION_V197.md for current validation and scope.

# Cook4Me pricing-market and language audit — v190

**Base:** `Chreece/HA-Cook4me` commit `175e285cae0f1f1e05ae2cdc3276134543cbf14d` (v188), with the local v189 price-audit patch retained.

**Status:** Local cumulative development patch. This conversation has not committed, pushed, merged, released, installed or deployed it. The runtime manifest remains unchanged. No current supermarket price list was downloaded or independently verified.

## Required contract

The **supermarket-language setting** selects the local ingredient label used at the pricing-adapter boundary. The **purchase-country setting** independently selects eligible price observations. Currency is an explicit price-evidence filter, not a conversion request. UI language and recipe language must not select a pricing country.

Example (illustrative names and synthetic test prices, not retailer quotations): Greek UI + Germany + German supermarket language + EUR gives `Ρύζι` in the ordinary Greek presentation, `Reis` in the price request, and only qualifying German EUR observations. The existing shopping presentation remains UI name, then distinct supermarket/original labels. It is not sent as a combined search term.

Selecting French as supermarket language while keeping Germany as the purchase country changes the name to `Riz`, not the market to France. Exact paid purchases are a separate evidence class: an explicitly paid USD lot remains a USD purchase, rather than being rewritten as EUR or deleted.

## Findings

### 1. Supermarket language was not carried through the pricing entry point

`price_settings()` already normalizes/persists `supermarketLanguage`. `shopping_rows()` uses it for shopping labels. However, `product_price()` used the supplied ingredient directly, `category_for()` depended on a canonical English price identity, and `_observations()` did not receive local ingredient context. A direct keyed request carrying only a localized UI name could be unmapped even when its catalog identity was known.

**Correction:** A separate copy of the ingredient is prepared using the existing offline catalog and configured supermarket language before price lookup. It carries the local `name`, stable `canonicalName`, stable price identity, country, currency, requested language, actual label language, and translation provenance. Recipe, stock and shopping-display rows are not overwritten. Both direct product requests and recipe hydration use the same adapter.

### 2. Localized names and provider identifiers are different things

The current provider is **Open Prices**, whose `/api/v1/prices` API queries product barcodes and category identifiers. It is not a free-text retailer search endpoint. Its documented filters include `product_code`, `category_tag`, `product__categories_tags__contains`, currency, dates and location IDs.

**Correction:** `Reis` is carried into Cook4Me's pricing adapter, while the provider still receives the appropriate barcode or stable taxonomy ID such as `en:rices`. Taxonomy IDs are not translated to German IDs. No unsupported `search_terms` or `lc` parameter is invented. This patch does **not** introduce a new retailer scraper or a new provider that searches supermarket websites by translated text.

### 3. An unset country could leave saved references unfiltered

`product_price()` selected saved barcode/generic references before reaching its `choose_country` branch. The store treats an empty country filter as no filter. Consequently, the presence of a saved observation could produce a price despite no selected market.

**Correction:** Automatic product lookup returns `choose_country` without selecting saved generic references or requesting observations when country or currency is absent. Recipe calculation receives a read-only local price-store view; offline preview uses the same restriction. Saved data is not deleted. Explicit paid-lot references remain available to actual purchase costing.

### 4. Country/currency checks were already present, but not unified at the adapter boundary

The live normalizer and existing product-result selection already check country/currency. Budget benchmark pools also already filter their source observations by country/currency and date. Those protections are retained, rather than replaced with language-based guesses.

**Correction:** An additional final boundary applies to live and snapshot observations before they can be used: selected country, selected currency, usable positive package basis, finite non-negative amount, and an observation date within the existing 180-day window, excluding future dates. Offline preview applies the same final check. Missing observations remain unknown, not zero. No implicit foreign-exchange conversion is added.

### 5. Localization must not revert reviewed food identities

The catalog's general `_global_ingredient()` lookup tries `ingredientId` before `key`. A reviewed recipe can carry a new authoritative key while retaining an old provider ID. Localizing that row through the old ID could undo a deliberate food-form distinction.

**Correction:** Price-label lookup resolves only the effective key, with no fallback to a stale conflicting ID. A synthetic reviewed key retains its canonical ingredient when no global catalog row matches it. Ingredient-ID-only requests are given a stable key in the price-only copy. Unkeyed ingredients retain their original price identity when their display name is translated.

### 6. Language changes must not reuse stale lookup labels

**Correction:** Observation and hydration coalescing keys now include supermarket language. Caller-specific ingredient labels are attached after shared numeric observation-cache reads, so two ingredients sharing one category cannot inherit each other's names. Live recipe responses and offline previews rebind market labels outside the numeric cost cache. The v190 evidence revision invalidates older previews; the existing preview token already includes price settings. UI names and numeric totals are not rewritten merely to display another language.

### 7. Missing translations must remain explicit

A display helper can return the canonical fallback when no local translation exists. That must not be described as a successful German/French translation.

**Correction:** The new catalog helper reports overlay/source/canonical-fallback provenance and actual label language. Missing translations set `translationMissing=true`; their `queryName` is empty so a future name-based provider cannot mistake a fallback for a proven local-language search term. Barcode/category matching can still work in the selected country. No AI translation, fuzzy food substitution or foreign-market fallback is used.

## Validation actually performed

- **41 new focused unit tests passed locally.** They exercise production price-market functions and the modified automatic-pricing entry points, with a controlled small catalog, storage/cache doubles, and mocked network responses.
- Re-running the suite against the **old automatic-pricing function wiring**, while retaining the new helper test fixture, reproduced **7 failures and 2 errors**. This is a before/after wiring regression check, not a complete execution of an unmodified full v188 checkout.
- **9 applicator-mechanics tests passed** on synthetic checkouts with the validation subprocesses mocked: read-only preflight, apply/repeat, refusal of unrelated edits, first/second-suite failure rollback, payload integrity, symlink refusal, concurrent-edit detection and partial-application handling. This verifies applicator mechanics, not full-checkout compatibility.
- Changed Python files and transformed function excerpts compile.
- The retained v189 payload contains its earlier 41-test suite. That historical test result is documented in `PRICE_AUDIT_V189.md`; it is **not counted as a new test execution in this audit**.
- The applicator runs both the v189 and v190 suites against the user's full checkout after applying, and rolls back on failure. The workflow is updated to run v190 tests, but GitHub CI has not run for this local patch.

Coverage includes Greek UI/German supermarket labels, explicit language overrides, normalized locale codes, missing translations, same-spelling translated names, ingredient-key precedence, unkeyed identities, local/foreign EUR observations, currency separation, stale/future/invalid observations, missing market, exact paid foreign lots, disabled automatic lookup, forced refresh, barcode requests, concurrent coalescing, language-sensitive query caches, snapshot previews, live recipe responses and current market labels after language changes.

Local source access was through GitHub reads. A full checkout download was unavailable in this environment. Local integration tests therefore used fetched production-function excerpts, not a complete Home Assistant installation or all catalog files. `test-fixtures/` and `reproduce_market_tests.py` make that limited test run reproducible; fixtures are never installed into the integration.

## Apply safely

Unpack the bundle and run from its directory:

```bash
python3 apply_market_audit_v190.py /path/to/HA-Cook4me --check
python3 apply_market_audit_v190.py /path/to/HA-Cook4me
```

The target must be a local Git checkout, not the live HA configuration. The cumulative patch accepts the pinned v188 source or the exact retained v189 patch. It refuses unrelated edits/newer affected files, verifies payload hashes and original Git blob identities, creates backups, compiles modified Python, and rolls back on failed unit validation. `--check` changes nothing. The application performs no network access, commit, push, release, restart or deployment.

## Remaining verification

Full-checkout preflight, all repository tests/CI, browser rendering, real Home Assistant interaction and inspection of the household's actual stored prices remain outstanding. The audit establishes and unit-tests the local-language/local-market contract; it does not claim every ingredient has a translated label or an available price in every country.

## Sources inspected

- `automatic_prices.py`: `price_settings`, `category_for`, `canonical_recipe`, `_observations`, `product_price`, `recipe_price`, `offline_price_inputs`, `offline_recipe_price`.
- `shopping_presentation.py`: country-language fallback and UI → supermarket → original presentation.
- `release_catalog.py`, `release_catalog_v60_core.py`, `catalog_presentation.py`: exact identity lookup and existing offline label resolution.
- `costs.py` and `price_benchmarks.py`: country/currency boundaries and local benchmark pools.
- The retained v189 source patch and report.
- Open Food Facts, Open Prices `prices_list` API documentation, inspected during this audit: https://openfoodfacts.github.io/documentation/docs/Open-prices/prices/prices_list/

All repository reads above refer to the pinned base commit, not an assumed current deployment.
