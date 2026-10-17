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


## Official SEB API result and evidence-backed mapping (17 October 2026)

Uploaded read-only SEB report: `cook4me-seb-official-programs-20261017-161424.tar.gz`.

- 10 markets queried, **8** returning full recipe details; 30 successful details
  from 36 attempts; 56 bounded actions.
- **25 distinct source-name / program-key pairs** and **4 distinct IDs** observed.
  All four correlate with earlier cached SEB recipe evidence from more locales.
- Portugal had no successful details, and Netherlands returned no searched
  variants; `SEB_DETAIL_CatalogAuthError` plus `INCOMPLETE_MARKET_COVERAGE`
  warn against treating this sample as exhaustive.
- Source identifiers were preserved; no user recipes, credentials, stock, or
  account-specific IDs are part of the report.

| SEB program key | Reviewed semantic class | Source languages/markets |
| --- | --- | --- |
| `PROGRAM_200156` | High pressure | de, fr, es, it, pl, cs, en, tr |
| `PROGRAM_200157` | Low pressure | fr |
| `PROGRAM_200159` | Browning/searing | de, fr, es, it, pl, cs, en, tr |
| `PROGRAM_200161` | Keep warm | de, fr, es, it, pl, cs, en, tr |

Cross-checking both user-provided audit archives yields **61 distinct reviewed
(key, exact localized name) pairs**: 25 pairs from the bounded current API
sample and further cached SEB recipe names consistent with those four keys.
The UI resolver `recipe-step-modes-v259.js` recognizes these **pairs only**.
It does *not* map an arbitrary unknown name or a numeric `PROGRAM_n` ID alone.

The previously captured local sample contained 361 program references, 141
recognized and 220 unrecognized. The newly reviewed pairs can resolve exactly
**200** of the 220 previously unknown references; projected coverage for that
same sample becomes **341 / 361 = 94.46%**, with 20 unresolved. A fresh audit
may contain more recipe steps because the catalog scanner was corrected after
the original sample.

| Remaining unreviewed source key | Misses in original sample | Program name or ambiguity |
| --- | ---: | --- |
| `PROGRAM_200018` | 5 | Manual P |
| `PROGRAM_000013` | 2 | Manual P |
| `PROGRAM_200009` | 3 | Slow cook P1 |
| `PROGRAM_000004` | 1 | Slow cook P1 |
| `PROGRAM_000005` | 1 | Slow cook P2 |
| `PROGRAM_200011` | 1 | Slow cook P3 |
| `PROGRAM_200160` | 4 | Simmering/boiling/braising, ambiguous terminology |
| `PROGRAM_200063` | 3 | High-heat fry/stir-fry, conflicting translated names |

**Do not infer** the meaning of any of these eight program IDs. Manufacturer
documentation lists 13 model-specific Cookeo Touch modes, but that is not a
mapping of every SEB recipe `PROGRAM_n` ID to a model program.

Regression tests in `tests/test_recipe_step_modes_v259.mjs` cover all 61
pairs, German generic-pressure versus verified high-pressure distinction,
all UI languages, key-only protection, and every unresolved sample category.

## Deeper official eight-market SEB audit (17 October 2026)

The sanitized `cook4me-seb-deep-programs-20261017-170353.json` covers Cook4Me
appliance group 15 on sampled SEB recipe search pages **1, 5 and 12** in
DE, FR, ES, IT, PL, CZ, GB and TR. The report records **72** detail attempts,
**67** successful details, **24** successful searches, and **104** network actions
including configuration requests. **30** distinct exact source-name/key pairs,
**5** unique keys and **8** markets with usable details were observed. It is
not an exhaustive SEB catalog: some detail requests failed with
`SEB_DETAIL_CatalogAuthError`.

- Newly observed `PROGRAM_200160` with Polish name `Gotowanie na wolnym
  ogniu` (one observation) is confirmed *simmering*. Other names for this
  opaque key are **not** silently assumed to mean simmering.
- Newly verified `PROGRAM_200157` names `Düşük basınçlı pişirme` (Turkish)
  and `Low Pressure Cooking` (English) mean *low-pressure cooking*.
- Exception: the same key was named `Dampfgaren` in three German recipe
  details, which means *steaming*. This exact German source pair is kept
  as steam rather than translated based on the opaque key's English name.

The reviewed name matrix now has **64** standard exact name/key pairs and **1**
explicit German source-locale exception. All **30** distinct pairs present in
the deeper API sample have a localized mode label in English, German, Greek,
and French. Numeric IDs alone remain unusable as cooking-mode evidence.

The prior **94.46% projected** local sample recognition is **not** a fresh
measured coverage result. Manual P, Slow cook P1/P2/P3, key
`PROGRAM_200063`, and other names under `PROGRAM_200160` remain
unverified as Cook4Me modes. Moulinex publishes Manual P and Slow cook P1
for Companion recipes too, so applying them universally to Cookeo is unsafe.

Run the read-only `tools/run_cook4me_mode_audit_v288.sh` against the actual
Home Assistant recipe caches and release catalog with the verified candidate
resolver. This audit neither installs a candidate, alters stock, nor commands
the appliance. Inspect its full coverage and remaining names before releasing.

## Complete local catalog audit and Cook4Me/Companion distinction (17 October 2026)

Uploaded sanitized `cook4me-recipe-programs-full-20261017-181612.tar.gz`
from the hash-pinned candidate runner. The audit produced **no scanner
warnings**, scanned the 16,952-row local release catalog and 156 cached recipe
details, and found 256 unique recipe containers with 1,447 steps.
Of those, **361** program references had named evidence, **341** resolved,
**20** remained in 12 exact key/name pairs; **1,086** steps had no program
metadata, including **482** classified manual/preparation steps.

After reviewing those 12 pairs, **six** new exact key/name pairs cover
**seven occurrences** as *Cook4Me source cooking modes*:
- `PROGRAM_200063` / `Braten bei hoher Hitze` (DE),
  `Estofado alto` (ES), `Magas stir fry` (HU):
  **high-heat browning**. Spanish `Estofado alto` is misleading in isolation,
  but actual official Cookeo recipe directions say `Dorar` (brown) at this
  program; German/Hungarian Cookeo instructions explicitly describe high-heat
  browning. Preserves the high intensity instead of flattening to browning.
- `PROGRAM_200160` / `Варка на слабом огне` (RU),
  `煮燉` (ZH): **simmering/braising** wording (three cached occurrences).
- `PROGRAM_200160` / `غليان` (AR): **boiling** (one occurrence),
  explicitly **not** relabeled as gentle simmering.

This means **348/361 (96.40%) projected recognition** in the original full
local archive; rerun the read-only scanner to obtain a measured result.

The other six pairs (**13 references**) are named `Manual P`,
`Slow cook P1`, `Slow cook P2`, and `Slow cook P3` across six IDs.
These are documented **Companion** kitchen-robot programs, not a
Cook4Me mode. They must not be converted into a fake Cook4Me pressure or
slow-cooking device setting. The recipe UI now shows a localized
`Companion program (not Cook4Me): <trusted exact program name>`
chip. It preserves the original name, and the audit separately counts
`possibleCompanionPrograms`, retaining these references in the unresolved
count until original recipe appliance provenance can be independently
verified. Zero mismatched/key-only source IDs gain a false mapping.

Manufacturer evidence:
- Companion recipe with all four modes:
  https://www.moulinex.fr/recette/detail/PRO/saumon-a-laneth-accompagne-de-legumes/3072685
- Cookeo DE high-heat browning:
  https://www.tefal.de/rezepte/detail/PRO/champions-rahm-so%C3%9Fe/2633682
- Cookeo ES "Estofado alto" in an explicit `Dorar` step:
  https://www.moulinex.es/recetas/detail/PRO/pollo-y-patatas-cocidos-a-fuego-lento/3164396
- Cookeo HU "Magas stir fry" labeled `Erős pirítás`:
  https://www.tefal.hu/recept/detail/index/source/PRO/id/833921/

The revised hash-pinned `tools/run_cook4me_mode_audit_v289.sh` scans the
candidate without installing it, and preserves the cooker's operating state,
the saved recipes, user stock, Home Assistant availability, and SSH connection.
Do not merge/release until this follow-up report and CI are reviewed.
