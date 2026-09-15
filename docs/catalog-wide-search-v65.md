# Catalog-wide multilingual search and editions, v65

Queries previously used a small fixed culinary vocabulary. A Greek word missing
from that vocabulary could return nothing even when translated ingredient labels
and matching foreign recipes were already bundled. Query preparation now indexes
all reviewed UI ingredient labels, source ingredient translations and aliases,
and bilingual recipe titles. Exact phrases are matched first; independently
identifiable words can be recovered from bilingual labels. Ambiguous residual
phrases are left unresolved and unknown query words remain constraints. This is
an offline catalog lookup, with no Ollama or translation service dependency.
There is no recipe-specific dictionary entry, family whitelist or special branch.
Search remains bounded by the bundled catalog's translation and recipe coverage.

The same query index serves recipe searches and ingredient lookup. Ingredient
picker responses include their source-language aliases, allowing searches in
another catalog language while the visible ingredient names stay in the UI
language. All reviewed UI labels are checked for query-translation coverage.

Recipe display families now use canonical title, image and yield dimension.
Matching publications are evaluated individually against shared filters before
collapsing cards and applying pagination. This includes publications whose foods
look identical but have separate IDs or nutrient evidence. Matching editions
remain available in each selected catalog language. Distinct covers, canonical
titles or yield dimensions remain separate. Different food proportions preserve
same-language, same-serving editions with numbered version options. Grouping
never transfers ingredient nutrients or grants device-send compatibility.

Serving selectors use each original display variant ID, including editions with
no compatible send ID. Rendering no longer silently changes such editions to the
first serving. Selecting another edition loads its own ingredient quantities,
nutrition, steps and delivery identity. These controls apply to the common recipe
cards and dialogs used throughout the UI. Plural canonical seafood names are
also recognized by the vegetarian filter.

Validation covers a newly introduced synthetic bilingual food without vocabulary
changes, every reviewed ingredient label, different real dishes and ingredients
across German, English, French, Spanish and Italian, ingredient picker searches,
filtering before grouping, pagination and edition identity. The reported ramen
query is one regression example: the five catalogs contain thirteen matching
publications before vegetarian filtering. Five vegetable publications share a
family, while the French vegetable recipe has a distinct cover and ingredients.
The result is two cards with their available editions; selecting all languages
retains ten publications and thirty serving options in the larger family. Other
ramen styles in this release contain meat or seafood and remain excluded by a
vegetarian filter. Additional recipes are not fabricated.

The DOM check consumes real Today and Official backend responses, exercises Greek
and Latin queries, translated ingredient searches and changes serving editions.
It also checks the existing progress popup, delayed completion, empty/error
outcomes and stale responses. Shared controls, stored navigation and recipe
dialog checks run against the active v65 bundle, build `2026.9.15.7`.

`tools/deploy_offline_runtime_v65.sh` validates the checkout in the user's Home
Assistant container before stopping it, retains the previous integration,
restores failed activation and verifies the exact served bundle. It includes the
new multilingual regressions. The homeserver is not reachable from this workspace;
installation there and physical-device visual verification remain pending.

The full Python run completed 1,215 tests: 1,204 passed, with the same eleven
historical nutrition-review assertions in batches 42–50 failing as in v64. No
new failures were introduced. After the final publication-filter and cache
invalidation adjustments, all eleven multilingual regressions and both active
frontend DOM suites passed. The installer uses isolated command-stub tests for
success, backup/rollback, missing locales and mount validation; its final source
pin is rechecked before publication.

Published runtime: `76dbeaa5d113e402448abdeb979ef1076246e561`.
