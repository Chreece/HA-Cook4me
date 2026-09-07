# Recipe Hub UI/UX audit — 2026-09-07

## Scope

Audit of the active Recipe Hub v31 after the modern-UI pass, with emphasis on mobile usability, visual hierarchy, discoverability, semantic iconography, filtering, and long-running/background work.

## Research inputs

- Home Assistant frontend design portal and developer guidance: mobile-first UI, reusable HA visual language, Material Design Icons (MDI), light/dark theme compatibility.
  - https://developers.home-assistant.io/docs/frontend/design/
  - https://developers.home-assistant.io/docs/frontend/
  - https://www.home-assistant.io/docs/frontend/icons/
- Nielsen Norman Group guidance:
  - Icons should retain text labels for important navigation/actions instead of becoming unlabeled glyphs: https://www.nngroup.com/articles/icon-usability/
  - Progressive disclosure should keep common choices visible while moving secondary filters behind an obvious disclosure control: https://www.nngroup.com/articles/progressive-disclosure/
  - Batch filtering is appropriate when a filter set can trigger slow/network work, especially on mobile: https://www.nngroup.com/articles/applying-filters/
  - Bottom sheets are useful for contextual detail while preserving the user's current context: https://www.nngroup.com/articles/bottom-sheet/

## Findings in v31

1. Navigation and primary buttons had MDI icons, but important choice surfaces were still visually plain:
   - interface language was a native text-only select;
   - recipe/catalog language selectors had no flags/language identity;
   - Today meal types were checkbox chips with no food/meal icon;
   - nutrition goals and diet were visually indistinguishable selects;
   - nutrition values were plain chips rather than semantically grouped metrics.
2. Today exposed too many secondary controls at once. The page was functional but visually dense rather than task-focused.
3. Recipe cards lacked a strong visual indicator for source language and meal/course type.
4. Background-work UX was modal and single-job only. Starting another tracked task replaced the previous progress overlay. Several real background tasks were not represented at all, notably visible-recipe nutrition hydration and on-demand catalog loads.
5. Cancellation was represented only as a flag on one modal token. It did not scale to concurrent background work.
6. Ingredient detail was a centered dialog even on mobile, where a contextual bottom sheet preserves recipe context better.

## v32 design decisions

- Keep HA-native MDI icons and text together for important actions.
- Add country flags plus language names/codes to language choices; keep `mdi:translate` as the semantic language control icon.
- Make Today meal types visual choice cards with dedicated MDI icons and selected states.
- Add a concise live "Your plan" summary and move secondary Today filters into a clear **More filters** disclosure section.
- Add semantic icons/tints to nutrition metrics and meal/course chips.
- Add recipe source-language badges and meal/course badges when catalog metadata exposes them.
- Convert ingredient detail into a bottom-sheet presentation on narrow/mobile screens.
- Replace the single modal progress overlay with a non-blocking multi-job progress-card stack. Every tracked job gets its own title, current activity, progress indicator, and cancel action. Short jobs use a small reveal delay to prevent distracting flashes.
- Add explicit job coverage for catalog loading, Today option loading, Recipe Book loading, barcode lookup, local recipe opening, recipe language/serving changes, visible nutrition hydration, and the existing search/recommend/open/send/ingredient/AI workflows.
- Add automatic progress cards for long mutations such as nutrition-catalog building, barcode mapping, nutrition-label saving, stock updates, Shopping List updates, profile/recipe saves, and nutrition settings.
- For operations backed by a single already-dispatched Home Assistant/server request, cancellation stops further client-side work and marks the UI request cancelled; it cannot retract a command already delivered to the server/device.
