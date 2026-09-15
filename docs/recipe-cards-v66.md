# Recipe cards and explicit local translation, v66

Active panel: `cook4me-panel-v66-bundle.js`, build `2026.9.15.8`.

Today, Weekly, Official, saved recipes and ingredient recipe references share the
same compact card. Lists initially display eight recipes; the bottom button adds
eight more. Official search requests eight grouped results per page. New searches
reset pagination. A collapsed card shows the photo and title with its language.
An expand button reveals Info, Ingredients and Steps disclosures, language and
serving selectors, and icon actions. Generated recipes use the same card.

Diet and meal tags update the shared filters. Official results are searched again;
existing Today/Weekly plans can be filtered without regenerating the saved plan.
Ingredients preserve their source identity and quantities while displaying reviewed
UI-language labels, original labels and individual stock coverage. Instructions
are loaded on expansion from the exact edition's persistent detail cache, or fetched
and cached when internet access is available. The compact release catalog does not
contain cooking steps; missing instructions are reported and can be retried.

Language preference is UI language, Home Assistant country language, English, then
the first actual available edition. Hydration retains the filtered set of catalog
languages and publications instead of replacing it with every language in the
release. Serving changes use original edition IDs and load their own quantities.

The photo opens a fullscreen recipe. Cooking mode supports manual next/previous
steps and highlights the reported device step only when the device's recipe ID
matches the displayed edition. Ingredient information, shopping additions and
recipe actions work in the same view. A device selector appears when multiple
Cook4Me integrations are installed; sending resolves compatibility against that
specific target, with the existing offline/busy queue.

Translate appears only when an Ollama AI Task is available and the UI language is
absent from the recipe's editions. Cloud AI availability alone never enables it.
Home Assistant state changes hide/show the action. The server rechecks availability
on an explicit click and after waiting for other work, then passes the resolved
local entity ID to the AI Task API. No automatic AI translation runs during search,
rendering or expansion. Complete saved or assistant-authored phrase translations
are reused; otherwise local AI is called. Incomplete output or changed instruction
numbers is rejected. Translation changes display text, preserving IDs, ingredient
quantities and original step structure. All task progress uses the existing popup.

The reported ramen example still has two matching vegetarian recipe families in
the bundled release. The German and French vegetable editions share a photo but
differ in ingredients and quantities; other ramen styles contain meat or seafood.
They remain excluded by the selected vegetarian filter. Search and grouping are
generic and do not create additional recipes or silently relax dietary criteria.

Validation covers actual catalog responses, Greek/Latin queries, shared controls,
8/16/remaining pagination, edition changes, ingredient popups, target queuing,
fullscreen cooking, local-AI availability and explicit translation. The installer
preserves backups and rollback, runs the focused regressions inside the HA container,
and checks the exact served bundle. Server installation and physical-device visual
verification require running the supplied installer on the homeserver.

The full regression run completed 1,228 tests: 1,217 passed, with the same eleven
historical nutrition-review failures in batches 42–50 and no new failures.
The final focused suite also covers retrying a cached summary without steps.
All three active frontend DOM suites passed. A graphical browser could not be
installed in this workspace, so mobile layout and physical-device verification
remain pending.
