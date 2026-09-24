# Offline ingredient seasons and after-opening guidance

The release catalog now includes a versioned, reviewed lifecycle sidecar:
`custom_components/cook4me/catalog/ingredient_lifecycle.v1.json`.
It is read once during the existing catalog executor warmup. No network, AI,
cloud credentials, or per-scan file reads are needed.

## Reviewed coverage (2026-09-24.5)

- 86 produce groups, including fruit, leafy vegetables, roots, asparagus,
  tomatoes, cultivated button mushrooms, potatoes, new potatoes, fresh herbs,
  savoy cabbage, pak choi, shallots, wild garlic, turnips, snow peas, walnuts,
  hazelnuts, artichokes, melons and kiwi.
- 33 numeric after-opening rule groups: pasteurized/UHT milk, low-acid canned
  foods, high-acid canned foods, Alpro plant drinks and cream/yoghurt alternatives,
  oat drinks (Alpro or Oatly), Taifun plain and silken tofu, and Reishunger
  smoked tofu and coconut milk, plus Alnatura passata, pesto, tomato sauce and
  hummus, chickpeas, kidney beans, white beans, lentils and baked beans. Separate
  canned-form profiles retain generic guidance alongside verified product rules
  for legumes, sweetcorn and tomato pieces. Brand, product and handling
  conditions remain attached. Alnatura apple purée, apple, orange, vegetable,
  sauerkraut, beetroot, lemon and ginger juices add product-specific guidance.
  There are 27 reviewed product barcodes and 1,224 exact canonical names.
- Explicit label-required guidance for reviewed foods with variable product
  formulations, including unverified pesto, dairy yoghurt, cream cheese and
  coconut cream.
- Dry staples have no invented short spoilage countdown. Their package
  instructions still apply; missing data never means indefinitely safe.

Run `python tools/audit_ingredient_lifecycle.py` for counts against the actual
shipped catalog. Counts distinguish seasonal, numeric and label-required
entries. Coverage is explicitly incomplete; unmapped ingredients remain unknown.

## Season semantics

Season months are German availability guidance from the twelve monthly
calendars published by the Hessische Lehrkräfteakademie, BZfE produce guides,
the BVEO pak choi guide, Hessen VerbraucherFenster and the Verbraucherzentrale
season calendar, BUND Naturschutz's Bavarian calendar and Hortipendium.
For the Hessian monthly calendar entries, the source region
(`DE-HE`), country (`DE`), source links and review date are preserved. The source
includes stored produce and protected cultivation; these months must not be
labelled as exclusively fresh outdoor harvest. Ordinary potatoes have year-round
availability, including stored crops, according to BZfE (`sourceRegion: DE`).
New potatoes have a separate June/July highlight profile; they do not inherit
the stored-potato calendar. Sweet potatoes and potato starch remain separate.

Fresh parsley leaves, chives, chervil and sorrel use the Frankfurt green-sauce
herb season (`sourceRegion: DE-HE`, `basis: regional_seasonal_availability`).
April–October is a conservative subset of BZfE's April-to-late-autumn description;
it does not assert an exact end to the season. Basil uses the explicit June–October
outdoor harvest period (`basis: outdoor_harvest`), independent of year-round
potted availability. Savoy cabbage uses May–February regional availability,
and pak choi uses May–October. These profiles do not apply to dried/frozen herbs,
Thai basil, parsley root, cooked cabbage or mixed ingredients.

The Verbraucherzentrale calendar's green outdoor-harvest cells on page 1 provide
May–September for dill and May–October for marjoram, oregano, rosemary, sage and
thyme (`basis: outdoor_harvest`). Protected cultivation and stored/imported
availability do not extend those profiles. BZfE identifies July–October as the
main availability period for fresh German shallots. Hessen VerbraucherFenster
places wild garlic in March–May, with the season ending around mid-May. The
month-level guidance remains approximate and does not identify wild plants.

Turnip roots use Hortipendium's sowing-dependent June–mid-November harvest
range, attributed to Gartenakademie Rheinland-Pfalz (`DE-RP`, `outdoor_harvest`).
This is horticultural harvest guidance, not a complete national market calendar.
Turnip greens and ambiguous yellow turnips/swede remain separate. Snow peas
and mangetout now have their own BZfE June–August outdoor profile instead of
sharing the shelled-pea calendar. BZfE also identifies September–October regional
walnuts (`DE`, `regional_seasonal_availability`).

The Bavarian calendar supplies artichokes (July–October), melons
(August–September), hazelnuts (September–November) and kiwi (September–October).
These retain `DE-BY` and `regional_seasonal_availability`, including the calendar's
secondary season; they are not labelled as exclusively outdoor harvest.
Plain shelled/chopped/ground nuts retain their crop's seasonal shopping hint.
This does not limit the availability of stored nuts or apply to roasted nuts,
nut flour, paste, oil or mixtures. Bitter melon is not included in the melon
profile. Preserved artichokes and cooked snow peas remain unassigned.

The calendars list monthly highlights rather than every crop. A listed month
returns `in_season`, twelve listed months return `year_round`, and an omitted
month returns `unknown`. Unsupported countries also return `unknown`. A Greek
UI does not imply Greek growing seasons. These are approximate shopping/planning
hints and do not prohibit using stored or imported food.

Only exact reviewed canonical names/forms receive a profile during loading.
The allowlist includes reviewed raw cutting/washing variants. Preserved,
frozen, cooked, dried or alternative/ambiguous forms do not inherit fresh
profiles through a substring, display synonym, translation or semantic sibling.
An ingredient's provider IDs, nutrition and dietary evidence are preserved.

## Opening-window semantics

`afterOpening.rules` contains `daysMin`, `daysMax`, refrigerator temperature,
handling conditions, source IDs and, where required, brand and `productBarcodes`.
Numeric evidence is general or manufacturer guidance, never a guaranteed
spoilage/safety threshold.
The conservative refrigerator cap for general and tofu guidance is 4 °C;
Alpro's published maximum is 7 °C. The corresponding refrigeration sources are
included with each rule.

Oat drinks retain separate Alpro (5 days) and Oatly (5–7 days) rules. The Oatly
rule also requires confirmation that the package was promptly reclosed and its
opening was not touched or drunk from. Reishunger smoked tofu requires a closed
container (2 days); its coconut milk uses the published 2–3 day range. These
manufacturer rules are not applied to other brands, dairy products, other tofu
forms or coconut cream. The coconut milk source also states a 3-day maximum in
its product storage instructions, consistent with the range's upper end.

The Alnatura rules require both the brand and one of the following verified
product barcodes, refrigerator storage at no more than 4 °C, and any listed
handling condition. Each rule links to its own manufacturer product page.

| Product | Barcode | Days after opening | Additional condition |
| --- | --- | --- | --- |
| Passierte Tomaten, 500 g carton | 4104420250345 | 3 | — |
| Passata Natur, 690 g bottle | 40045238 | 3 | — |
| Pesto Basilico, 130 g | 4104420031326 | 5 | Covered with oil |
| Pesto Rosso, 130 g | 4104420257344 | 5 | Covered with oil |
| Tomatensauce Klassik, 350 ml | 4104420213593 | 2 | — |
| Tomatensauce Kräuter, 350 ml | 4104420213517 | 2 | — |
| Hummus Natur, 180 g | 4104420229761 | 7 | — |
| Kichererbsen, 330 g jar | 4104420230224 | 2 | — |
| Kichererbsen, 400 g can | 4104420230972 | 2 | — |
| Kidneybohnen, 360 g jar | 4104420138803 | 2 | — |
| Kidneybohnen, 400 g can | 4104420187894 | 3 | Transferred to a container |
| Weiße Bohnen, 330 g jar | 4104420170179 | 2 | — |
| Weiße Bohnen, 400 g can | 4104420187979 | 3 | Transferred to a container |
| Linsen, 400 g can | 4104420187931 | 2 | — |
| Baked Beans, 360 g jar | 4104420141162 | 2 | — |
| Mais, 330 g can | 4104420234987 | 1 | Transferred to a non-metal container |
| Tomatenstücke Natur, 400 g can | 4104420234857 | 3 | Transferred to a container |
| Apfelmark, 360 g | 4104420227408 | 3 | — |
| Apfel-Direktsaft naturtrüb, 1 l | 4104420208735 | 3 | — |
| Milder Apfelsaft naturtrüb, 1 l | 4104420179677 | 3 | — |
| Orange-Direktsaft, 1 l | 4104420231214 | 3 | — |
| Gemüse-Direktsaft, 500 ml | 4104420072862 | 3 | — |
| Gemüse-Direktsaft feldfrisch verarbeitet, 330 ml | 4104420133365 | 5 | — |
| Sauerkraut-Direktsaft, 500 ml | 4104420072800 | 3 | — |
| Rote Bete-Direktsaft feldfrisch verarbeitet, 330 ml | 4104420070202 | 5 | — |
| Zitrone-Direktsaft, 750 ml | 4104420228986 | 14 | — |
| Ingwer-Direktsaft, 200 ml | 4104420260467 | 14 | — |

Juice intervals vary by product: the two vegetable juices have separate 3- and
5-day rules. The 14-day lemon and ginger intervals do not transfer to other
juices. Applesauce and juice profiles do not assign those clocks to whole fruit,
freshly squeezed juice, apple compote or juice-and-zest mixtures. General names
still need the matching packaged product; homemade preparations remain unknown.

Brand alone cannot select these product-specific intervals. Missing, invalid or
different barcodes leave the deadline unknown. Barcodes must be strings with
valid GTIN check digits; equivalent 8-, 12- and 13-digit codes and their zero-padded
14-digit representation match. Product and package instructions still take
precedence if they change.

For an exact ingredient profile that contains reviewed product rules, a matching
brand or reviewed barcode selects that product scope before testing conditions.
Both brand and barcode must then match. Missing identity, temperature or handling
confirmation returns `label_required`; it cannot fall back to a longer generic
canned-food interval. The verified product rule also takes precedence regardless
of rule ordering. Generic canned-food guidance remains available for other
products on explicitly canned ingredient profiles. Unspecified or cooked legumes
have only product-specific rules, so they cannot borrow a generic canned interval
for a homemade batch or an opened bag of dried beans.

The date helper accepts existing lot fields `openedAt`, `bestBefore`,
`useWithinDays`, `noExpiry`, `storage`, `brand` and `barcode`:

1. No opening date means no countdown.
2. A package-specific `useWithinDays` wins over generic catalog guidance.
3. Otherwise the catalog rule must match the known brand, any required product
   barcode, refrigerator storage, supplied temperature and confirmed
   handling/food-form conditions.
4. Consumption can start immediately on opening. For a 3–4 day range,
   `remindOn` is opening + 3 days and `consumeBy` is opening + 4 days. This is
   not an instruction to wait three days before eating.
5. An earlier printed date caps both calculated dates. The original printed
   date is never rewritten. A printed date before opening is explicitly flagged.
6. `noExpiry` suppresses the printed date only; it does not cancel a known
   after-opening interval. Frozen storage is not assigned a refrigerator rule.

The result has `safetyGuarantee: false`. Bad dates, fractions, boolean intervals
and calendar overflow are rejected. Unknown rules return no invented deadline.
The helper never mutates inventory or marks a package opened.

## Runtime surfaces

Catalog ingredient rows, display choices (including the scanner catalog) and
recipe ingredient rows carry compact `lifecycle` metadata. A grouped display
choice carries only its selected exact ingredient's evidence, not siblings'.

Public functions in `release_catalog.py`:

- `ingredient_lifecycle_profile(ingredient, include_sources=True)`
- `ingredient_seasonal_availability(ingredient, country=..., month=...)`
- `ingredient_opening_window(ingredient, lot, temperature_c=..., confirmed_conditions=...)`

These resolve by exact ID/key. Sending only a display name does not select
evidence. Returned metadata is independently copied, so UI edits cannot corrupt
the cached catalog.

This is a catalog/backend enrichment. It supplies metadata and calculations for
consumers; it does not add UI controls, silently apply catalog intervals to
existing packages, change weekly-plan ranking or replace existing reminders.

## Verification

`python tests/test_ingredient_lifecycle.py` covers evidence validation, country
and month boundaries, unknown/preserved forms, package precedence, brand,
product barcode and temperature gates, product-versus-generic precedence,
can/jar distinctions, juice formulation and fresh/prepared boundaries, regional
crop calendars, leap years, earlier printed dates, unopened packages, exact
identity, recipe/picker propagation, and copy isolation. The existing Validate
workflow runs it and audits the actual release catalog on Python 3.13.
