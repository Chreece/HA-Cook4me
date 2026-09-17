# Cook4Me v105: UI-language units, ingredient dropdown and reliable TTS

Build `2026.9.17.9` is cumulative from published v104 (`b0a2c7a2b0db018a6823917365795e6d0131ee21`). Previous price corrections, compact price controls, fullscreen ingredient dialogs, restored entities and dashboard behavior remain included.

## Units follow the UI language

A shared display formatter covers all 104 unit identifiers found in the bundled catalog, with authored English, German and Greek labels and singular/plural forms. Multilingual aliases are generated from the catalog; ambiguous aliases are not used to infer a conversion. Explicit identifiers and food-specific counter meanings are retained, such as vanilla pods versus garlic cloves.

Examples with Greek UI:

| Recipe source | Display |
| --- | --- |
| `1 pincée` | `1 πρέζα` |
| `1 càc` | `1 κ.γ.` |
| `2 càs` | `2 κ.σ.` |
| `20 buc` | `20 τεμ.` |
| `2 feuille` | `2 φύλλα` |

The formatter is used for recipe ingredients, price quantity estimates, price reference amounts, stock and lot displays, and weekly reservation/shopping quantities. Unit selectors show translated labels while their submitted values remain the original unit tokens. Existing custom unit tokens are retained; unrecognized free-form units are displayed as entered.

Translation is presentation-only. Recipe objects, cooker payloads, quantity conversions, nutrition and price calculations are unchanged. The price cache therefore remains at evidence version 104. `catalog/ui_units.v1.json` is the authored source; `tools/build_ui_units_v105.py` checks identifier coverage and regenerates the embedded aliases. International symbols such as ml and cl remain valid across UI languages.

## Kitchen ingredient list

The full ingredient catalog is a native dropdown beside its search field. Search matches translated names, canonical names and catalog aliases. All matching ingredients remain selectable; the former 60-item grid and pagination are removed from this view.

After selecting an ingredient, the information button opens its details and the plus button opens the product editor with that ingredient selected. Empty results and loading disable these actions. Existing catalog retry and language/request scoping remain active. Selection and search survive rerenders; a selection outside the filtered results is cleared.

Both search and dropdown remain on the same row at 360 px. Action buttons move below them on narrow displays.

## Deterministic announcements when AI is unavailable

- Fixed cooking-state, connection and test messages are already translated and bypass AI entirely.
- A saved AI selection can remain unavailable without blocking settings saves, test announcements or live delivery.
- Recipe titles and instructions use AI translation when it is available. Provider errors, timeouts, empty responses or rejected quantity changes fall back to the original recipe text with the existing localized announcement prefix.
- Fallback text is not cached as an AI translation, so a recovered provider is used again automatically. The saved AI choice is preserved.
- Device and speaker permissions, current-step checks, preference checks and duplicate-delivery suppression remain active. Cancellation/unloading never triggers fallback speech. Missing TTS or speakers still reports a delivery error.

The announcement settings explain the behavior in English, German and Greek. Original recipe text is not presented as an offline translation.

## Validation

- Six new announcement tests cover unavailable AI, settings saves, test and state messages, original recipe fallback, recovery, timeout/error/invalid-response handling, cancellation, stale steps and revoked speaker access.
- Fourteen existing announcement and registry tests pass with the updated fallback contract.
- The browser test uses the real French porridge and Romanian vegetable recipes plus the complete English/German/Greek ingredient catalogs. It checks unit labels, unchanged price payloads, canonical form values, dropdown search/details/add/retry, overlapping language requests and 360/390/1360 px layouts.
- The v104 fullscreen/price browser regression runs against the v105 bundle, retaining icon-only prices, scoped refresh, modal stacking, focus handling and retry behavior.
- Generated unit labels, bundle reproducibility, Python/JavaScript syntax and installer shell syntax are checked. The installer verifies unit data, retains the price/entity preflight tests and adds the new announcement tests before replacing any installed files.

Use the pinned `tools/deploy_offline_runtime_v105.sh` from the published v105 branch. Publishing does not install it on the Home Assistant host; the standalone installer keeps its backup, activation checks and rollback path.
