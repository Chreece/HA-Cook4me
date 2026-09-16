# Offline observed ingredient prices (v85)

Cook4me now ships a compact, dated subset of public Open Prices observations.
First-time ingredient costing can use compatible evidence without an internet
request. These remain ingredient estimates, with the original observation ID,
country, shop, date and package basis displayed by the existing price UI.

## Measured coverage at build time

Built on 2026-09-16 from the public location/price exports and 3,590 expanded,
non-discounted German observations fetched through the documented API.

- 481 retained observations across 17 countries, including 218 for Germany.
- German observations cover 209 mapped food categories, with separate mass,
  volume and item bases where available.
- Exact-name mappings increase from 259 names / 202 categories to 550 names /
  473 categories. Eligible recipe ingredient occurrences rise from 137,135 to
  152,879 of 230,486 (59.5% to 66.3%). This is lookup eligibility, not price coverage.
- The German snapshot matches categories used in 113,898 occurrences. After
  requiring an explicit compatible recipe quantity/unit, 51,068 occurrences
  across 853 catalog ingredient IDs can use it immediately. Multilingual/local
  IDs may describe the same food; these are not 853 distinct price observations.

Other countries retain only the verified loose-food observations available in
the export. No prices are borrowed from another country or converted between
currencies. Some categories still lack local observations or compatible units.

## Retrieval and safeguards

The provider does not support filtering `/prices` directly by country. Searches
now use its documented `location_id__in` filter with a bundled country index,
then include a worldwide fallback for new or unindexed shops. At most 900 known
locations in groups of 300 are tried, with five requests and a shared 15-second
budget. Every returned record still undergoes country/currency/category/date
validation; the location index is a hint, not proof of origin.

An absent reference can be seeded from the snapshot. Existing observations are
rechecked on use after 24 hours, and the explicit refresh action bypasses the
snapshot. A source outage preserves still-valid saved evidence. Observation
expiry is based on the original observation date (180 days), not when it was
installed or cached. Automatic-price preferences and user-entered/purchase price
priority are preserved. The snapshot never supplies an actual purchase price.
A generic category observation's barcode is not treated as a user's confirmed
product assignment on later recipe lookups.

Explicit structured package amounts remain preferred. Missing quantities can be
read from an unambiguous dedicated package label, including `10 Stück`, `6 eggs`,
`250 ml` and `6 x 125 g`. Mixed/drained weights, servings, unlabeled counts and
ambiguous thousands separators are rejected. Product names are not parsed for
weights. No density, spoon volume or grams-per-item estimate is introduced.

The recipe catalog, ingredient names, cooker payloads, profile data and frontend
are unchanged. This backend update retains the v84 panel/cache URL.

## Evidence, attribution and reproduction

`custom_components/cook4me/catalog/observed_prices.v1.json` is a derived database
under **ODbL 1.0**, credited to **Open Prices / Open Food Facts contributors**,
with location data from **OpenStreetMap contributors**. This data file retains
its ODbL license independently of the integration's software license. It contains
public price evidence and location IDs, not receipt images or contributor
account details. Source download hashes are recorded in its metadata.

Sources:
- https://prices.openfoodfacts.org/
- https://prices.openfoodfacts.org/api/schema
- https://prices.openfoodfacts.org/api/v1/prices
- https://prices.openfoodfacts.org/data/prices.jsonl.gz
- https://prices.openfoodfacts.org/data/locations.jsonl.gz
- https://static.openfoodfacts.org/data/taxonomies/categories.json
- https://opendatacommons.org/licenses/odbl/1-0/

Rebuild with explicit local exports and expanded API observation JSON files:

```sh
python tools/build_observed_prices_v85.py \
  --locations locations.jsonl.gz --prices prices.jsonl.gz \
  --api-prices germany.json --as-of 2026-09-16
```

The builder selects the latest dated, usable observation per market/category/unit
basis; it does not average across unrelated products or invent missing evidence.

## Validation

119 focused Python tests passed, including the pricing, inventory, meal lifecycle,
runtime audit and offline catalog suites. The pricing suites cover offline recipe costing, country/currency/date/unit
boundaries, first-use seeding, live and manual refresh, outage fallback, manual
priority, disabled automatic prices, category/barcode separation, package labels,
country-scoped searches, worldwide fallback, and bounded request counts.
Live read-only Germany/EUR checks for rice, wheat flour and eggs each returned
usable evidence on the first country-scoped request in approximately 12 seconds.
The three checks returned respectively 20, 5 and 11 usable observations; these
counts describe those requests, not nationwide coverage.

No live Home Assistant instance or appliance was available for installation.

Runtime commit: `7fb8a9558c9ce5f4c25139cde6a3f5d6f2ddcdb5`.
Installer: `tools/deploy_offline_runtime_v85.sh`. It backs up the installed
integration, runs the catalog and pricing preflight checks, installs atomically,
restarts HA, and checks the served v84 panel plus the installed price snapshot.
All five installer tests passed, including missing-price-data refusal and
activation rollback: **124 focused tests passed in total**.
