# Ingredient names in recipes and info windows

Recipe ingredient rows, fullscreen recipe rows and ingredient-info headings use
one presentation rule: **UI name (supermarket name, recipe name)**. Empty names
and duplicates are omitted, keeping supermarket before recipe when both differ.
For a Greek UI, German supermarket language and French recipe, an example is
`Ρύζι (Reis, Riz)`; if supermarket and recipe names are both `Reis`, it becomes
`Ρύζι (Reis)`.

The formatter uses matching-language recipe presentation metadata, the existing
indexed offline UI catalog, the configured supermarket catalog and original
recipe text. Reviewed source IDs can resolve catalog names; there is no fuzzy
name matching or implicit AI translation. Missing translations fall back to the
available original text. Catalog entries opened directly in the info window use
the same rule without inventing an additional recipe name.

Names are applied to the rendered label only. Ingredient identities, original
recipe payloads, quantities, coverage badges, storage locations and add-to-shopping
actions retain their existing data. Finished catalog reads refresh visible names
and an open info heading. A failed read cannot create a render/load retry loop.

The active runtime URL and custom-element name advance to v221 so the new module
is loaded after updating Home Assistant. The previous scroll-preservation mixin
remains active.

Validation covers language order, duplicates, stale locales, exact identity
aliases, string ingredients, unknown names, failed catalog reads, mobile and
desktop recipe/info views, delayed market loading and original payload retention.
