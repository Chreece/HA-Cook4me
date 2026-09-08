# Currency display and FX conversion (Recipe Hub v45)

Cook4Me keeps exact purchase prices in the currency in which they were recorded. A separate display-currency preference controls how mixed-currency totals are shown.

## Preference

- `Auto` follows the Cook4Me interface language.
- An explicitly selected ISO-4217 currency stays fixed across interface-language changes.
- Existing non-empty v44 cost currency settings migrate as fixed preferences.

Examples: German and Greek default to EUR, English to GBP, Polish to PLN, Japanese to JPY. Bulgarian defaults to EUR because Bulgaria adopted the euro on 1 January 2026.

## Rates

- Primary source: European Central Bank euro foreign-exchange reference rates.
- Rates are cached in Home Assistant storage and reused while fresh.
- Cross-rates are derived through EUR because the ECB publishes currencies against EUR.
- If refresh fails, a cached rate set may be used and is explicitly marked stale.
- If a currency is absent from the rate set, its original amount remains visible instead of being dropped or guessed.

## Evidence contract

Currency conversion changes presentation/aggregation only. It never changes the stored exact purchase currency, stock quantity, nutrition, ingredient unit, or price evidence. No density or physical-unit conversion is introduced by the FX layer.
