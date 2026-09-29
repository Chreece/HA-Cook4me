# Seasonal ingredient choices

The ingredient catalog in My Kitchen, product assignment, recipe ingredient
selection and recipe result sets now use **Seasonal ingredients**. It is off by
default and saved per user, integration entry and view through the existing UI
preference store. Product and catalog controls save immediately; the recipe
ingredient dialog uses its existing Apply button.

- The shopping country selects the calendar. Supermarket language never
  selects a different country, including countries sharing the same language.
- The current month follows Home Assistant's configured time zone.
- A reviewed country calendar hides ingredients outside its listed months.
  With the recipe filter enabled, a recipe is excluded when any materialized
  ingredient has reviewed evidence for the shopping country but the current
  month is outside that ingredient's listed months. The check happens before
  recipe pagination so counts and display-family selection stay consistent.
  These calendars may list seasonal highlights rather than exhaustive harvest
  dates; this filter does not change the lifecycle advisory `unknown` status.
- Unknown countries, ingredients without a reviewed calendar, and foods without
  applicable seasonality remain visible. Preserved food forms do not inherit
  a fresh-food calendar. Already selected ingredients remain available to undo.
- Ingredient names follow UI language (supermarket language, original language),
  with duplicates omitted. The calendar's country and month are displayed in
  supermarket language. The toggle and explanation support Greek, German and
  English, with the existing English fallback.
- Inventory, stored recipe ingredient data, purchase lists and food exclusions
  are not altered by the filter. Recipe result visibility changes only while
  the toggle is enabled. Existing search, keyboard selection and
  interaction-position behavior are retained.

The feature was introduced in frontend runtime v223. No new web service, AI lookup or
additional ingredient catalog download is required for season data.

Local verification covers real catalog metadata in Greek/German/English,
country and time-zone boundaries, unknown/preserved/year-round cases, strict
preference normalization, and the real ES-module graph in 390px and 1440px
browsers. Browser scenarios exercise product assignment, suggestions,
search, selected-item exceptions, per-view persistence and country changes
while a picker is open. Existing interaction-position regressions cover both
document scrolling and Home Assistant shadow-host scrolling.
