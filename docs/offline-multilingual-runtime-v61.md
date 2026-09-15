# Offline catalog and query fixes

Continuation of `cook4me-nutrition-enrichment-post-activation-v60`, starting at
`8a9b0d4a0393467221eeb51c5ed0518b4a041cf9`.

## Reproduced failures

- The v31 transliteration resolver changed Greek `ριζότο` to Croatian `rizoto`
  in the actual catalog: 35 matches, versus 205 for canonical `risotto`.
- `ριζότο ντομάτα` returned no matches. `μακαρόνια` was guessed as `makaronie`
  and returned one unrelated recipe.
- Unsupported or prematurely cached source-language selections could exclude
  the entire catalog. Empty selections displayed unchecked boxes while silently
  searching a fallback language.
- Local search results waited for optional AI result translation. A later
  response could also overwrite a newer search.
- Empty per-serving nutrition suppressed available recipe totals. Null values
  could become zero, and inherited rendering layers duplicated nutrient chips.

## Behavior

The shared offline index now intersects query terms and unions each term's
original spelling with its exact culinary translations. A separate, versioned
`query_vocabulary.json` supplies common Greek dishes, ingredients, grammatical
forms, and cooking terms, plus selected equivalents in other catalog languages.
Longest known phrases are matched before connective words are removed. Greek
script is recognized independently of the interface language. Unknown words and
negations remain literal; nearest-word guessing is removed.

This is a deterministic culinary search vocabulary, **not unrestricted sentence
translation**. The catalog's existing provider titles and ingredient aliases
remain searchable in all 21 source languages. Additional exact query aliases can
be added as data. Query translations never assign ingredient identity, safety,
nutrition, or appliance IDs, and never modify the bundled catalog.

The v31 websocket uses the same search/materialization path as the other offline
callers. Source languages and safety filters apply before pagination. Search and
recipe detail expose the same locally calculated nutrition. Partial values remain
labelled as estimates with coverage; unavailable nutrients remain unavailable.

Panel v61 starts with all available source catalogs unless the user has a valid
saved selection. It offers the audited language list while capabilities load,
repairs unsupported saved selections, and requires a selection after explicit
"Deselect all". The picker has a Done button and restores outside-click/Escape
listeners after reattachment. Local search results display before optional result
translation, and only the latest search may update the results. Immutable local
reads do not wait behind AI/cloud work; other operations retain the existing
request queue.

## Verification

Against the unchanged 16,952-recipe / 32,163-variant catalog:

| Query | Source catalogs | Results |
| --- | --- | ---: |
| `ριζότο` | All | 205 |
| `ριζότο ντομάτα` | All | 25 |
| `σούπα με φακές` | All | 77 |
| `ριζότο` / `risotto` | German | 11 each |
| `soupe de tomates` | German | 9 |

- Eight new full-catalog/runtime tests pass, including the actual v31 websocket
  search/detail handlers with socket creation forbidden during their execution.
- Query-unit tests cover original-label preservation, plural and phrase matching,
  conflicting vocabulary, and refusal to guess unknown words.
- The new DOM smoke test passes for picker interactions, reattachment, language
  persistence, nutrition, immediate results, and stale response protection. The
  existing v59 and menu smoke tests also pass.
- Version validation, Python compilation, JavaScript syntax, and diff checks pass.
- Full Python suite: **1,162 tests, 1,151 passed, 11 failed**. All 11 remaining
  failures were reproduced on the untouched starting commit. They are historical
  nutrition-review snapshot assertions in batches 42–50, including a live count
  of 5,159 compared with the old expectation of 5,080. Review evidence and those
  assertions were not changed by this runtime fix.
- Visual mobile verification remains pending: the browser could not access the
  local preview in this environment.

## Installation scope

Install the complete integration from the review branch and restart Home
Assistant, then reopen Recipe Hub. Copying only `merged_catalog.v1.json` does not
install the query engine, vocabulary, websocket, or panel fixes. This change has
not been deployed to the homeserver or published as a release.
