# Unlimited ingredients: recipe availability and presentation audit

## Scope

This audit covers **any stock item saved with `unlimited: true`**, not just
salt or rice. It traces the saved ingredient through stock normalization,
verified catalog assignments, server-side recipe quantity allocation, cached
recipe availability and the final fullscreen and recipe-card chips.

The original user symptom is a dash (`—`) on a recipe ingredient even though
My kitchen correctly shows infinite (`∞`) stock. This is not interchangeable
with a dash on an **ingredient price or nutrition value**: unlimited inventory
says nothing about a product's purchase price, calories or other nutrients.

## Verified root causes

1. In `food_intelligence.recipe_quantity_feasibility`, the
   `required is None` branch executed **before** the `current.unlimited`
   branch. For source recipes that describe salt, seasoning or water "to
   taste" without a measurable amount, the function returned
   `unknown_requirement`, `coverage: null` and reduced
   `quantityConfidence` even after finding the stored unlimited row.
   These became `—` in the frontend. The branch order is now reversed:
   a genuinely matched unlimited row gives `coverage: 1.0`,
   `status: enough`, `unlimited: true`, and no quantity shortage.
2. The `recipe-coverage-v198` frontend intentionally prefers backend
   `quantityAvailability` (including unknown) to the weaker
   `ingredientAvailability` presence list. That policy is still correct,
   but saved recipe details can carry stale quantity evidence.
   The active frontend reconciler now detects **explicitly linked**
   infinite stock and renders **∞ / Unlimited stock** using the selected
   UI language rather than treating the old dash as authoritative.
3. Multiple inherited recipe-rendering layers can replace a freshly
   resolved chip with a storage-home badge. The final active v293 pass
   sets the infinity label **after** those layers while preserving the
   storage-location icon and its known location text. A standalone
   recipe whose every requirement is proven unlimited no longer has an
   erroneous `—` aggregate availability badge.

## Safety and semantics

- An ingredient name translated to Greek does **not** prove it is the
  same physical product: only the saved primary item identity, exact
  ingredient/lot assignment or vetted backend source evidence is used.
- Unlimited stock is not guessed from the recipe title, salt/pepper
  keywords, a generic source category, empty units or another ingredient
  with a similar localized display name.
- **Finite** stock with an unknown recipe quantity remains unknown.
  Finite zero stays zero; partial quantities remain partial.
- A package shared by multiple ingredient requests is not double
  allocated. Physical stock amounts, expiry, price and nutrition remain
  unchanged. No inventory files are migrated or rewritten.
- When an old backend result is stale and a positive finite package
  matches, the UI continues to say **At home — quantity unverified**;
  it does not manufacture 100% availability.
- Unverified cross-unit conversions remain unknown. Neither infinite
  stock nor ingredient presence invents a purchase price or nutrition.

## Regression matrix

- **Backend:** salt, pepper, sugar, water, flour, oil, vinegar, rice and
  other arbitrary unlimited foods; empty/missing recipe quantities;
  incompatible or missing source units; alternate Japanese/Korean
  source names and explicit catalog ingredient links; stale
  `ingredientAvailability: missing`; finite controls; mixed finite
  and unlimited recipes; repeated unlimited ingredients; exact
  source assignments and non-mutating stock inspection.
- **JavaScript:** stale zero/unknown cached coverage, labeled infinity,
  translated names with different stable IDs, finite shortfalls,
  expired or removed matches, and mixed recipe-card evidence.
- **Actual Chromium frontend:** 390px phone and 1440px desktop,
  Japanese/Korean recipe ingredients using saved unlimited salt,
  an existing Greek storage-place name and the final displayed
  recipe chip. The unrelated ingredient and removed-stock cases
  cannot inherit the infinity label.
- Standard cookbook, shopping, expiry, pricing, dietary safety,
  scanning, HACS packaging and broader frontend tests remain enabled.

The regression fixtures reproduce the reported class of problem. They do
not prove the exact private user's salt product has a particular catalog
identifier; that would require inspecting its saved sanitized assignment
and corresponding recipe variant on the user's own Home Assistant host.

## Installation / cache behavior

The active panel uses a fresh `ingredient-home-filter-v293.js` import
and `cook4me-recipe-hub-panel-v180-runtime-v293`, while old versioned
modules remain available for backwards compatibility. The new URL
query version prevents an already open Home Assistant browser from
reusing stale constructor and asset code. User inventory, recipe details
and saved per-view filter preferences remain untouched by the upgrade.
