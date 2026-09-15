# Catalog presentation and ingredient popup follow-up

The September 15 screenshots exposed three separate issues: a stale ingredient
popup constructor, genuinely absent generic-rice nutrient data, and raw provider
publications/names being presented as separate user choices.

## Ingredient nutrients

The active panel is now v62, build `2026.9.15.4`. Its generated bundle scopes base
custom-element registrations to this build, so a previously loaded v61 class
cannot supply the old popup. The backend and popup exchange an explicit v62
contract; a mismatched deployment produces an error instead of a blank legacy
dialog. The ingredient popup reads reviewed catalog profiles using the original
ingredient ID, including when recipe text has been translated.

The exact screenshot ingredient `M_FOOD_421` (Arroz/Rice) has **no reviewed
nutrient profile in the bundled catalog**. It remains unassigned. The popup
explains this and separately shows reviewed reference values for specific rice
types, such as cooked rice. These comparisons do not become generic rice's
nutrients or enter recipe totals. Ingredients with known profiles continue to
show their own values and per-100-g/ml basis; missing values are not rendered as
zero. Scanned product data stays distinct.

## Recipe publications

UI searches group publications before pagination when their canonical title,
image URL, cleaned ingredient identities and yield dimension match exactly.
Language and quantity variants remain selectable. On the bundled data, the 60
matching rice publications become one family with 14 languages and 200, 300,
400, 500 and 600 g choices. Selecting a quantity loads that exact publication's
ingredients. A separate rice photo/publication family remains separate.

Device-send identity is still derived from the original provider group and
matching quantity. Presentation similarity does not establish cross-language
device compatibility. The source catalog and ungrouped API remain unchanged.

## Ingredient choices and UI language

The v31 ingredient-catalog endpoint returns 3,713 choices from 11,748 source
ingredient records, one per normalized name. Amounts and preparation prose are stripped, explicit common plurals are
merged, and non-food headings are excluded. Food specifications such as `00`
flour and cream percentages remain. All member source IDs remain display
metadata; the chosen ingredient keeps its own identity and nutrient provenance.

Ingredient selectors follow the Home Assistant UI language, independently of
recipe source languages. Greek search accepts omitted accents. Bundled Greek
labels cover common foods and the screenshot examples. The v62 installer builds
the remaining Greek names through an already installed local Ollama text model,
then stores the completed locale next to the component. Catalog use after this
preparation is offline. No model is downloaded. Translations affect labels only;
they are machine translations and have not all been manually reviewed.

The preparation cache lives under `.storage/cook4me_ui_locales` and resumes on a
retry. Home Assistant keeps running until translation and source preflight have
succeeded. `COOK4ME_UI_LANGUAGE`, `COOK4ME_OLLAMA_URL` and
`COOK4ME_OLLAMA_MODEL` can override the Greek/local-Ollama defaults. A locale
must be prepared for each additional UI language that needs complete coverage.

## Verification and deployment

Real-catalog regression tests cover rice families, pagination, source-language
filters, exact quantity selection, device-send restrictions, nutrient provenance
and cleaned ingredient names. Websocket tests exercise the actual ingredient
responses without network access. DOM tests instantiate the generated bundle
after registering the old panel, exercise the rice dialog and Greek ingredient
picker, and verify offline variant routing. Installer fixtures cover backup,
mount validation, translation failure before restart, and rollback.

The complete Python suite ran 1,182 tests: 1,171 passed and the same 11 existing
nutrition-review assertions failed in historical batches 42–50. Those assertions
are not relaxed by this change. `tools/build_frontend_bundle_v62.py --check` verifies that the
committed bundle matches its source modules.

The homeserver cannot be reached from this workspace. Its Ollama translation
job and the final Home Assistant/mobile behavior must therefore be verified
when the pinned installer runs there. The installer checks that Home Assistant
serves the exact new bundle and validates the installed offline catalog; it
restores the previous component if startup or post-install checks fail.

The v62 installer is pinned to runtime commit
`66d813be424447c42bbdd00168264e5f1264d4de`.
