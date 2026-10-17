# Official SEB / Moulinex cooking-program name audit (v286)

## Scope and evidence hierarchy

Cook4Me's vendor client uses the SEB platform recipe endpoints:

- Search: \`POST https://sebplatform.api.groupe-seb.com/common-api/v4/search/recipes\`
- Official mobile recipe definition: \`GET .../common-api/v3/recipes/PRO/{variantId}/?format=mobile\`
- Filter: \`applianceGroups.reference.key=APPLIANCE_GROUP_15\`, then for each
  step \`sequences[].operations[].program.{key,name}\`.

These are the **existing proven app endpoints** in
\`custom_components/cook4me/vendor/cook4me_recipe_catalog.py\` and
\`cook4me_recipe_search_proven.py\`. The audit does not guess an unpublished
"all programs" endpoint. It counts language-specific program names linked
to the exact program key and cooking step.

### Manufacturer documentation — model capabilities, not API key mappings

Cookeo Touch models list **13 programs**:
1. Pressure: low, high, express (3)
2. Steam: gentle, boost (2)
3. Simmer: gentle, medium, strong (3)
4. Browning: gentle, medium, strong (3)
5. Reheating (1)
6. Keep warm (1)

The 13 options are model-specific; some Cookeo/Cookeo+ models are advertised
with **six** cooking modes and may have an automatic keep-warm feature.
No source establishes that a specific \`PROGRAM_*\` is universally a
Cookeo Touch setting merely because its recipe label sounds similar.

Source — Moulinex manufacturer website:
- https://www.moulinex.be/fr/cookeo-buying-guide
- https://www.moulinex.fr/notices/cuisson-electrique/autocuiseur-electrique/cookeo-touch-wifi-recettes-illimitees-6l/csp/1510002402
- https://www.moulinex.fr/notices/cuisson-electrique/autocuiseur-electrique/cookeo-100-recettes/csp/7211003573

### First observed actual recipe evidence, 17 October 2026

The anonymized on-device diagnostic archive
\`cook4me-modes-20261017-175100.tar.gz\` contains 256 recipes with steps,
361 recipe-program references, 141 recognized, 220 unknown named,
0 unknown-key-only, and 63 distinct unrecognized name/key pairs.
It reports 1,086 steps without cooking-program evidence. Its catalog scan
stopped at the configured node limit, so it is **not exhaustive**.

| Program key | Unknown program references | Examples from SEB programName | Evidence judgment |
| --- | ---: | --- | --- |
| \`PROGRAM_200156\` | 76 | Cuisson haute pression; Gotowanie pod wysokim ciśnieniem; Vaření pod vysokým tlakem | High pressure — coherent across markets |
| \`PROGRAM_200159\` | 61 | Dorage; Smażenie; Opékání | Browning/frying — coherent but localized terminology varies |
| \`PROGRAM_200161\` | 51 | Mantener en caliente; Utrzymywanie ciepła; 보온 | Keep warm — coherent across markets |
| \`PROGRAM_200157\` | 12 | Cuisson basse pression; Gotowanie pod niskim ciśnieniem | Low pressure — coherent across markets |
| \`PROGRAM_200160\` | 4 | Варка на слабом огне; غليان; 煮燉 | Simmering/boiling/braising *ambiguous* — retain for review |
| \`PROGRAM_200063\` | 3 | Braten bei hoher Hitze; Estofado alto; Magas stir fry | High-heat fry/stir-fry *ambiguous* |
| \`PROGRAM_200018\` / \`PROGRAM_000013\` | 7 | Manual P | Not established as pressure mode |
| \`PROGRAM_200009\` / \`PROGRAM_000004\` | 4 | Slow cook P1 | Distinct from slow cook P2/P3, confirm program tiers |
| \`PROGRAM_000005\` | 1 | Slow cook P2 | Confirm tier meaning |
| \`PROGRAM_200011\` | 1 | Slow cook P3 | Confirm tier meaning |

The archive is user-generated from real SEB recipe metadata but does not
independently prove which options a given appliance model supports.

## New bounded official SEB scan

\`tools/audit_seb_official_programs_v286.py\` queries official recipe
search and detail using the *same vendor API client as HA-Cook4me*.
It runs inside the Home Assistant container using the locally available
read-only token file, when present, and otherwise attempts app-key
content requests. It does not publish credentials, recipe names, user IDs,
or individual recipe identifiers.

Defaults:

- Markets: DE/de, FR/fr, ES/es, IT/it, PL/pl, CZ/cs, PT/pt, NL/nl, GB/en, TR/tr
- Max four official recipe definitions per market, 52 bounded API actions,
  240 seconds and a 0.6s pacing interval
- Generates **key + exact localized name + market + language + count** evidence
- Never writes Home Assistant storage, inventory, recipes, device state,
  or token cache; \`discover_rcu(..., save=False)\` is used
- Does not contact MQTT or issue any recipe-send/cooking commands
- A partial or empty report is explicitly marked **not a complete catalog**.

The audit is *sampling*, not a guarantee that every recipe across the
Groupe SEB cloud has been examined. Additional bounded market/page
sampling can be added if the first samples reveal new program keys.

## Mode mapping acceptance contract

Add names to the UI's mode alias list only when their meaning is
supported by a non-conflicting official SEB recipe name or other manufacturer
material. Respect locale differences, case/diacritics and all supported UI
translations. Numeric IDs alone must **not** authorize a cooking-mode guess.

Preserve existing behavior for:
- preparation/manual steps with no automatic program;
- multiple operations in a single recipe step;
- other-appliance sequences;
- cached recipes that contain no program metadata;
- live cooker program fallback only for the exact current recipe/step.

Review ambiguous Manual P, slow-cook tiers, high stir-fry and simmer/boil
before adding new mappings. Report missing data rather than inventing modes.
