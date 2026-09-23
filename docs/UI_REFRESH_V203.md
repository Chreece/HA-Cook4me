# App-wide interface refresh — v203

## Scope

This is an integration-wide visual implementation, not a weekly-only mockup.
The shared presentation layer covers the seven main navigation views (Today,
Week, Discover, Recipe book, My recipes, Shopping and My kitchen), their recipe
cards and fullscreen details, filters, storage/preferences/settings panels,
manual product entry/editing, receipt review and progress notifications.

Navigation uses readable short labels alongside the existing icons, consistent
spacing, a restrained active state and a compact device header. Surfaces, headings,
forms, chips, disclosure sections and buttons use shared Home Assistant theme
variables. English, German and Greek presentation labels are provided. Existing
HA fonts and icons are used; there are no remote fonts, new image assets, runtime
libraries, analytics or third-party network requests.

## Recipes, days and actions

Recipe titles remain above their photographs. Language becomes a separate small
chip. Long titles wrap instead of shrinking to an unreadable size. Images use a
consistent aspect ratio. Existing cost badges and their uncertainty semantics
remain unchanged.

Send and Favorite stay visible in a separate dock below the photograph. The other
original controls, including shopping, translation, replacement, removal and
expanded details, are accessible under a native More disclosure. Their original
nodes, selectors, handlers, disabled states and backend owners are retained.
Opening a recipe through its photograph is unchanged. The same action structure
is used for fullscreen recipe details. More supports touch, keyboard and outside
click dismissal; Escape closes an active More disclosure before closing the
underlying recipe, including inside Home Assistant's nested shadow roots.

Weekly meals are visibly enclosed within their own day containers, with the
original day selector, a meal count and an explicit Today badge. Known missing
recipes remain in their day as non-actionable information cards. Desktop uses up
to four day columns, with fewer columns as width decreases and stacked days on
phones. Existing date order, meal order, day/slot identities, selection requests,
filters, prices and shopping calculations are not changed.

## Kitchen, forms, shopping and scanner

Kitchen subnavigation, stock groups, package rows, storage forms and preferences
share the new surfaces and spacing. The existing shopping heading and controls
are reused in one page header rather than displaying a duplicate heading. Toolbars
wrap instead of overflowing narrow screens.

Manual product entry/editing uses a normal-flow form surface rather than an
absolute-positioned form over a camera image. The original scanner mode controls
remain available. The v196 Save and Discard footer remains outside the form at the
bottom; its actual height is observed so content can scroll clear of it. Quantity
inputs no longer shrink to the width of their digits. Barcode lookup, ingredient
suggestions, validation focus, stock edit target/revision, empty-form reset and
uncertain-save retry behavior remain owned by their existing implementations.

Manual fields and labels are readable under both tested HA light and dark themes;
the light-theme text-input foreground/background contrast is checked. Camera mode
continues using its existing high-contrast overlays. The v202 live camera sizing,
portrait/landscape behavior and unframed full-image receipt capture are retained.
Receipt review still uses its separate draft and per-item apply workflow, not the
manual-form reset buttons. Resizing does not clear product or receipt drafts.

## State, safety and accessibility

The visual layer does not call APIs, mutate inventory, change recipe eligibility,
replace filter persistence, rewrite recipe data or start cameras. Explicitly
closed fullscreen recipes stay closed and selected-first filter ordering is kept.
Day and recipe controls continue using their original IDs and operation handlers.
Disabled actions remain disabled; ineligible recipes are not exposed by styling.
UI-only More state uses the pre-existing scoped recipe-view state.

The stylesheet includes visible keyboard focus, retained invalid-field emphasis,
reduced-motion support and forced-color borders. Long Greek text, narrow viewports,
touch disclosure controls and nested-shadow keyboard dismissal are tested. This is
not a claim of a complete accessibility conformance audit. Listeners and footer
observers are removed on context reset or disconnect. Repeated decoration is
idempotent and does not produce a navigation MutationObserver loop.

## Implementation and delivery

Two new frontend modules, `app-design-v203.js` and `app-theme-v203.js`, form the
presentation layer. The current active panel composes it outside all existing
mixins. `panel.py` advances the runtime URL, query and active element to v203 so a
long-lived HA page cannot reuse a registered v202 constructor. The manifest
version and HACS installation channel are unchanged. The v201 reduced archive
rules remain unchanged and retain both new runtime modules.

This batch does not migrate user data or alter backend catalog, pricing, diet,
stock, generation, recognition or receipt-persistence implementations.

## Design references

The public product pages below were inspected for organization and visual
hierarchy: recipe-focused presentation, separated planning/shopping tasks and
clear day-based calendars. No third-party code, brand artwork or product images
were copied into the integration.

- Mealie: https://mealie.io/
- AnyList meal planning: https://www.anylist.com/meal-planning
- Mealime: https://www.mealime.com/

## Validation before publication

- 9 new Node checks of localization, runtime activation, theme foundations,
  route boundaries, input sizing and cleanup passed.
- 128 retained Node checks for manual editing, receipt review, scanner suggestions
  and weekly progress passed (137 combined with the new checks).
- 256 browser assertions passed across 360x800, 390x844, 844x390 and 1440x1000.
  They load the actual frontend inheritance chain and exercise all seven real
  view renderers, card/slot controls, More actions, fullscreen close, selected
  filters, kitchen subpages, barcode lookup, validation, save/discard, existing
  package edits, light-theme contrast, rotation, receipt navigation, observer
  cleanup, dietary exclusion and nested HA shadow roots.

The browser fixture replaces only HA/API, storage, video, icon rendering and
sample-data boundaries. Tests and previews use synthetic recipe illustrations and
local icon stand-ins, not the user's inventory or live HA icon rendering. The
existing cooker asset is retained. Browser code is loaded offline from repository
files using an import map; no local HTTP server or external network is required.
No live Home Assistant deployment, cooker action, physical-camera or AI-provider
test was performed.

Local bootstrap used a retained Git repository and verified current frontend
blobs; its backend catalog is older. Publication applies only the explicit new
UI/test/documentation/workflow files and the two verified active-runtime edits
onto current main `4475a138a1f32d38a2a5b2f2139c88f7e063045e`. It does not publish
the bootstrap checkout wholesale. The App-wide interface refresh workflow and all
existing workflows validate the complete current repository on the pull request.

```sh
node --test tests/test_app_design_v203.mjs
python -m pip install playwright==1.57.0
python -m playwright install chromium
python tests/browser_ui_refresh_v203.py
```
