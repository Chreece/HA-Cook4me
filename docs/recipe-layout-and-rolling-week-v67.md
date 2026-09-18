# Recipe layout and rolling planner, v67

Active panel: `cook4me-panel-v67-bundle.js`, build `2026.9.15.9`.

Recipe actions now remain directly beneath the photo, including when the recipe
is collapsed. Title/expand follows the actions; Info, Ingredients, edition
selectors and Steps remain expandable below it. The shared renderer applies to
Today, Official, Weekly, saved/generated recipes and ingredient recipe references.
Local-AI availability still controls whether Translate is offered. Actions that
need ingredients or steps can explicitly hydrate a collapsed summary first.

Info separates diet, meal type and nutrients with more space. Nutrients have a
heading and a vertical list with the quantity and daily percentage on separate
lines. Percentages use each recipe's actual per-serving values. Missing nutrients
stay absent, known zero stays zero, and recipe totals without a serving basis do
not acquire a daily percentage. Ingredient-data coverage remains separately
labelled, including partial estimates. Search targets remain per-serving targets.

Daily percentages use the adult reference intakes in Regulation (EU) 1169/2011,
Annex XIII: energy 2,000 kcal, protein 50 g, carbohydrates 260 g, fat 70 g,
saturates 20 g, sugars 90 g and salt 6 g. Sodium uses the equivalent 2.4 g.
Fibre uses the EFSA adult adequate intake of 25 g/day. The UI identifies these as
daily reference values rather than personalised dietary advice.

Sources:
- [Regulation (EU) 1169/2011, Annex XIII](https://eur-lex.europa.eu/eli/reg/2011/1169/oj/eng)
- [EFSA dietary reference values for carbohydrates and dietary fibre](https://www.efsa.europa.eu/en/efsajournal/pub/1462)

Cooking opens the fullscreen recipe directly from its action button. The dialog
fits the viewport, keeps its close control visible and scrolls content inside it.
The photo/action area and the instructions are arranged for desktop and mobile;
current-step highlighting and manual controls remain available. The Weekly tab
uses an inline SVG calendar, independent of Home Assistant's icon loading.

The planner renders today and the following six days using Home Assistant's time
zone. All seven day sections and their recipe cards are present together; Weekly
is now exempt from the eight-card list limit. Other lists retain eight-result
pagination. Empty days have explicit placeholders. Midnight updates roll the
visible date window forward, and opening the planner refreshes its server state.

Server generation starts on today's date instead of rounding back to Monday or
reusing an expired saved start. An explicit future API start is preserved. Reading
the planner filters existing slots to the seven-day window without moving their
dates or deleting stored records. Reservations, weekly costs and plan shopping
use the same window. Regenerating an expired/missing slot fails instead of
accidentally replacing the entire plan. An old, fully expired plan therefore
shows empty current days until the user generates the next seven days.

Validation covers collapsed actions, local-AI gating, exact nutrient percentages,
zero/missing/recipe-total values, direct cooking fullscreen, all seven days with
nineteen recipes, empty days, an old saved start, midnight and year rollover,
Home Assistant time zone, original date preservation and shopping scope. Shared
controls and the real catalog response flow run against the active v67 bundle.
The pinned installer retains preflight checks, backups and rollback.

The full Python suite ran 1,237 tests: 1,226 passed and the same 11 historical
catalog checkpoint assertions failed as in v66; there were no new failures.
The active-bundle layout, shared controls and real catalog DOM checks passed.
Mobile rendering and a physical cooking device still need confirmation on the
installed system; the automated frontend checks use a DOM, not a real browser.
