# Offline ingredient seasons and after-opening guidance

The release catalog now includes a versioned, reviewed lifecycle sidecar:
`custom_components/cook4me/catalog/ingredient_lifecycle.v1.json`.
It is read once during the existing catalog executor warmup. No network, AI,
cloud credentials, or per-scan file reads are needed.

## Reviewed coverage (2026-09-26.2)

- 113 produce groups, including fruit, leafy vegetables, roots, asparagus,
  tomatoes, cultivated button mushrooms, potatoes, new potatoes, fresh herbs,
  savoy cabbage, pak choi, shallots, wild garlic, turnips, snow peas, walnuts,
  hazelnuts, artichokes, melons, kiwi, chestnuts, sweet potatoes, swede and
  chanterelles, mint, tarragon, lovage, oyster/king oyster mushrooms, shiitake,
  fresh coriander leaves, watercress, lemon balm, Romanesco, fresh chillies
  and romaine/Little Gem lettuce, fresh ginger, figs and summer purslane,
  plus Greek regional lemon, orange, grapefruit, mandarin and clementine calendars.
  Ten further produce groups now have Greek evidence, including pomegranate
  and watermelon from Ilia and Trifylia in the Peloponnese.
  Fresh nettle leaves now have a Bavarian harvest profile; national German
  guidance expands bell-pepper, spring-onion and parsnip availability.
- 87 numeric after-opening rule groups: pasteurized/UHT milk, low-acid canned
  foods, high-acid canned foods, Alpro plant drinks and cream/yoghurt alternatives,
  oat drinks (Alpro, Oatly or verified Alnatura packages), Taifun plain and silken tofu, and Reishunger
  smoked tofu and coconut milk, plus Alnatura passata, pesto, tomato sauce and
  hummus, chickpeas, kidney beans, white beans, lentils and baked beans. Separate
  canned-form profiles retain generic guidance alongside verified product rules
  for legumes, sweetcorn and tomato pieces. Brand, product and handling
  conditions remain attached. Alnatura apple purée, apple, orange, vegetable,
  sauerkraut, beetroot, lemon, ginger and grape juices add product-specific
  guidance, along with Alnatura natural/smoked tofu, salsa, curry sauces,
  cooking creams, olives, pickled cucumbers, capers, marinated artichokes and
  preserved pineapple, coconut milk, sauerkraut, tomato juice and peanut sauce,
  carrot juice, lime juice and pickled beetroot. Beetroot juice now distinguishes
  three verified packages with either three- or five-day instructions. Alnatura
  plant drinks and dried-tomato antipasti now also retain exact package windows.
  Bonduelle's canned-vegetable family adds conditional one-day guidance across
  six explicitly canned profiles, alongside the existing generic can intervals.
  Galbani mozzarella, mascarpone, ricotta and Gorgonzola, Dodoni feta and halloumi,
  and a verified Alnatura millet-flake package add separate opening profiles.
  Two verified US Philadelphia Original packages add exact-product cream-cheese rules.
  Five dmBio packages add preserved jackfruit, hummus, tomato paste and separate
  tomato-sauce package windows.
  Cream and yoghurt profiles are separate; olive
  profiles distinguish green, black, mixed and unspecified forms.
  Eleven further dmBio packages cover passata, chickpeas, coconut milk and
  soy, rice, coconut and oat drinks, retaining their exact handling conditions.
  Ten further dmBio packages add cans, cooking creams and apple purées.
  Tofu, seitan, olive products and basil pesto add ten more packages; plain and
  smoked tofu, specific olive forms, and basil/red pesto keep separate rules.
  Eight juice packages add separate flavour/size rules and upright storage where labelled.
  Five more plant-drink packages and one ginger juice retain their storage instructions.
  Seven condiment/sauce packages add ketchup, Ajvar, curry and tomato sauces.
  Two fermented-vegetable packages add kimchi and sauerkraut guidance.
  A verified dmBio satay sauce adds its own three-day package rule.
  Three Xucker fruit spreads have separate strawberry, raspberry and red-fruit package rules.
  Four Lacroix stock packages add separate beef, fish, chicken and vegetable
  guidance, also selectable from the generic stock entry by exact barcode.
  There are 140 reviewed product barcodes, 1,829 exact canonical names and
  184 reviewed provider ingredient IDs.
- Explicit label-required guidance for reviewed foods with variable product
  formulations, including unverified pesto, dairy yoghurt, unverified cream cheese and
  coconut cream, unverified tomato paste, unverified ketchup and Skyr, plus mustard, mayonnaise and
  additional cream, cream-cheese and yoghurt variants, plus plain/brewed soy sauce,
  cottage cheese and further crème fraîche variants, ground nuts, nut butters
  and tahini, plus reviewed fruit jams without a verified numeric package rule,
  dry stock cubes, powders and granules.
- Dry staples have no invented short spoilage countdown. Their package
  instructions still apply; missing data never means indefinitely safe.

Run `python tools/audit_ingredient_lifecycle.py` for counts against the actual
shipped catalog. Counts distinguish seasonal, numeric and label-required
entries. Coverage is explicitly incomplete; unmapped ingredients remain unknown.

## Batch 28: stock packages, dry bouillon and edible pumpkin names

Coverage reaches **3,538 ingredient rows**: 2,257 seasonal, 664 with numeric
opening guidance and 617 label-required. This adds 108 enriched rows, ten exact
provider IDs and 27 canonical names. The lifecycle version is `2026-09-26.2`;
there are 113 seasonal groups, 87 opening-rule groups and 140 unique reviewed
numeric-rule barcodes. Sources were checked on 2026-09-26.

### Four exact stock packages

Each package below has a two-day refrigerated opening limit. The source pages
explicitly identify their information as manufacturer-supplied data and include
the consumer GTIN and pack size. Their additional case/alternate GTINs are not
added without separate package verification.

| Lacroix package | Consumer GTIN | Manufacturer data |
| --- | --- | --- |
| Rinder Fond, 400 ml | `4009062800395` | [Handelshof](https://www.handelshof.de/eigenmarken/produkte/131253005/lacroix-rinder-fond-400ml) |
| Fisch Fond, 400 ml | `4009062800203` | [Handelshof](https://www.handelshof.de/eigenmarken/produkte/131252002/lacroix-fisch-fond-400ml) |
| Bio Geflügel Fond, 300 ml | `4009062801200` | [EDEKA Foodservice](https://edeka-foodservice.de/eigenmarken/produkte/3084182008/bio-lacroix-gefluegel-fond-300ml) |
| Bio Gemüse Fond, 300 ml | `4009062801309` | [EDEKA Foodservice](https://edeka-foodservice.de/eigenmarken/produkte/3084170005/bio-lacroix-gemuese-fond-300ml) |

The catalog now gives beef, fish, chicken and vegetable stock their own
product-only profiles. Generic stock accepts any of these four verified packages.
The exact provider IDs are `M_FOOD_54`, `M_FOOD_214`, `M_FOOD_209`, `M_FOOD_55`
and `M_FOOD_49`. The conflicting cube/powder translations of `M_FOOD_56` have
not been approved as a separate raw lifecycle identity; display grouping does
not supply evidence to direct-ID lookups.

No two-day limit is inferred from an ingredient name alone. Brand, exact barcode,
refrigeration and an opening date are required. The existing BfR 4 °C cap applies;
the product data specifies cool storage without a numeric temperature. The
freezing alternative does not become a refrigerated countdown. Manual package
instructions and an earlier printed date retain precedence. Selecting guidance
requires confirmation and does not itself open the package or restart its clock.

Prepared/hot broths, stock-and-water alternatives, salt-free stock, veal stock,
concentrated pastes and other flavours cannot borrow these rules. Original
recipe quantities, nutrients and raw ingredient identities are unchanged.

### Dry stock and supermarket names

Seventeen exact dry-stock names and provider IDs `M_FOOD_50`, `M_FOOD_51`,
`M_FOOD_52`, `M_FOOD_53` now use label-required guidance. The reviewed
[dmBio vegetable cubes](https://www.dm.de/p/d/1490263/dmbio-gemuesebruehwuerfel)
(`4066447992373`) and
[powder refill](https://www.dm.de/p/d/1490261/dmbio-gemuesebruehe-nachfuellbeutel)
(`4066447523027`) specify protected, dry, closed storage without a numeric
opening interval. Neither receives a short refrigerated limit or an unlimited
safety claim. Their evidence barcodes are not counted as numeric-rule barcodes.

German search now accepts Rinderfond, Fischfond, Hühnerfond, Geflügelfond,
Gemüsefond and Bouillon variants. Cubes retain Brühwürfel labels and powder and
granules retain their form. Greek labels preserve the distinct liquid and cube
entries, with all source IDs retained by the existing amount-free grouping.

### Pumpkin display correction

The multilingual food identity `M_FOOD_399` now uses the existing regional
August–December pumpkin calendar for Hesse, including stored produce. Its
incorrect German provider label `Zierkürbis` is overridden in the UI by `Kürbis`,
with `Speisekürbis` as a search term. The other provider translations and reviewed
food identity describe edible pumpkin. [Hesse's pumpkin guidance](https://schulverpflegung.hessen.de/informieren-und-vernetzen/rezepte-und-warenkunde/warenkunde/kuerbis)
distinguishes edible pumpkins from ornamental ones. Greek remains `Κολοκύθα`.
No season is inferred for Greece, unlisted months, frozen/canned pumpkin, seeds,
oil, jam or ornamental pumpkins. The original provider translation is retained
as source data.

The broader `Squash` row `M_FOOD_145` has conflicting summer/winter squash
translations and remains unknown. Its Greek label is now `Κολοκύθι ή κολοκύθα`
so it no longer absorbs the reviewed pumpkin choice merely because both used
to display as `Κολοκύθα`. The two raw pumpkin provider IDs still deduplicate
together, while this ambiguous identity stays separate in every language.

Local tests cover exact package/food/form matching, real multilingual choices,
opening consent, date precedence, twelve-month country boundaries and supermarket
search. Browser checks exercise the actual picker and opening editor at 390 and
1440 px in Greek with German supermarket names.

## Batch 27: sweet pantry foods, turnips and Greek watermelons

Coverage reaches **3,430 ingredient rows**: 2,256 seasonal, 592 with numeric
opening guidance and 582 label-required. This adds 70 enriched rows, seven exact
provider IDs and 19 canonical names. One existing red-fruit jam entry moves from
label-required to its own exact-product profile. The lifecycle version is
`2026-09-26.1`; there are 113 seasonal groups, 82 opening-rule groups and 136
unique reviewed numeric-rule barcodes. Sources were checked on 2026-09-26.

### Regional produce and supermarket names

| Ingredient | Provider ID | Evidence and scope |
| --- | --- | --- |
| Turnip | `M_FOOD_328` | Existing June–November Rheinland-Pfalz harvest profile, rechecked against [Hortipendium](https://hortipendium.de/Speiser%C3%BCben_im_Hausgarten) |
| Watermelon | `M_FOOD_572` | May–September availability in Ilia and Trifylia, Peloponnese, from [grower/exporter Tzioutzias](https://tzioutzias.gr/watermelon/) |

The provider's turnip row had the German label `Steckrübe`, although its English,
French, Italian, Japanese and other translations identify a turnip. Its German
UI label is now `Speiserübe`, with `Mairübe`, `Herbstrübe` and `Navet` search terms.
The distinct swede row `M_FOOD_433` displays as `Steckrübe`, with `Kohlrübe`,
`Wruke` and `Rutabaga` search terms. Greek keeps `Γογγύλι` and
`Ρουταμπάγκα (γογγύλι Σουηδίας)` separate. Original provider translations remain
available as source data; only display/search labels change.

Greek watermelon evidence is regional and does not establish a German harvest
season. Unlisted months and unsupported countries remain unknown. Turnip greens,
daikon, pickles, dried roots and watermelon juice or jam do not inherit these
fresh-produce profiles.

### Red-fruit spread package

[Xucker Rote Früchte, 220 g](https://www.xucker.de/aufstriche/fruchtaufstrich-rote-fruechte)
has a ten-day refrigerated opening instruction and requires clean utensils.
[The retailer's exact-package listing](https://foodsetter.de/zuckerarmer-fruchtaufstrich-rote-fruechte-74-frucht-220g-glas)
confirms GTIN `4260248063939`, size and matching fruit composition. The generic jam
profile can select this package; the red-fruit profile can select only this
flavour. Strawberry, raspberry, generic berry jam and fresh fruit cannot borrow
its rule. The rule retains the existing BfR 4 °C cap, explicit opening/handling
confirmation, manual-interval precedence and earlier-printed-date cap. Selecting
a rule does not open a package. German search accepts Rote-Früchte-Konfitüre and
Rote-Früchte-Fruchtaufstrich.

### Honey, syrups and chocolate spreads

Eighteen exact pantry names now have form-specific label-required guidance:
plain honey and reviewed liquid/crystallized/floral variants, maple syrup,
agave syrup, chocolate spread, cocoa/chocolate-and-hazelnut spreads and Nutella.
The official provider rows are included. German labels/search now cover
`Ahornsirup`, `Agavendicksaft`, `Honig`, `Schokoaufstrich` and `Nuss-Nougat-Creme`,
while retaining the distinct ingredients and all original recipe quantities.

| Reviewed package | GTIN | Published storage information |
| --- | --- | --- |
| [dmBio maple syrup Grade A, 250 ml](https://www.dm.de/p/d/1445499/dmbio-ahornsirup-grad-a) | `4067796084849` | Refrigerate after opening and use promptly; no exact day count |
| [dmBio agave syrup, 250 ml](https://www.dm.de/p/d/1457811/dmbio-agavendicksaft) | `4066447413052` | Dry storage, protected from heat/light; no numeric opening period |
| [dmBio blossom honey, 500 g](https://www.dm.de/p/d/1546636/dmbio-bluetenhonig-aus-deutschland) | `4067796063790` | Dry storage protected from light; no numeric opening period |
| [dmBio dark chocolate spread, 400 g](https://www.dm.de/p/d/1448561/dmbio-schokocreme-zartbitter) | `4066447948417` | Dry storage away from heat/light, explicitly not refrigerated |
| [dmBio hazelnut chocolate spread, 400 g](https://www.dm.de/p/d/1433589/dmbio-schokocreme-nuss-nougat) | `4066447948394` | Cool, dry storage away from sunlight, explicitly not refrigerated |

These five reviewed barcodes are evidence only and do not add numeric expiry
rules. Vague words such as “promptly” are not converted into days. The catalog
also does not impose a refrigerator rule on chocolate spreads or mark any food
as indefinitely safe. Honey mustard, dressings, dessert creams, ambiguous
hazelnut spreads and homemade mixtures remain separate. User-entered package
instructions still work.

Local regression tests cover exact multilingual identities, the real German
search results, twelve-month/country boundaries, package/flavour exclusions,
manual/printed precedence and opening consent. Browser checks at 390 and
1440 px exercise both country filters, Greek UI with German supermarket names,
and the actual opening-guidance controls.

## Batch 26: exact produce identities and fruit-spread packages

Nineteen more provider IDs now expose reviewed lifecycle guidance on the real
Greek, German and English catalog choices. Exact singular/plural canonical
mappings are added alongside the provider allowlist; the identity gate is unchanged.

| Ingredients | Exact provider IDs | Reviewed season / guidance |
| --- | --- | --- |
| Button, shiitake and king oyster mushrooms | `M_FOOD_89`, `M_FOOD_460`, `M_FOOD_591` | German cultivated production, all year |
| Mirabelle plum | `M_FOOD_315` | July–September, Hesse |
| Walnut | `M_FOOD_331` | September–October, Germany |
| Pomegranate | `M_FOOD_227` | October–November, Limni in northern Evia; German season unknown |
| Hokkaido squash | `M_FOOD_398` | August–December, Hesse |
| Melon | `M_FOOD_307` | August–September, Bavaria |
| Welsh/spring onion | `M_FOOD_114` | March–November, German outdoor harvest |
| Capers, olives, black/green olives, pickled gherkins | `M_FOOD_76`, `M_FOOD_344`, `M_FOOD_345`, `M_FOOD_346`, `M_FOOD_138` | Existing exact-package rules only |
| Chickpea, kidney bean, dried tomato | `M_FOOD_385`, `M_FOOD_237`, `M_FOOD_679` | Existing exact-package rules only; generic legumes do not imply canned form |
| Jam, orange marmalade | `M_FOOD_133`, `M_FOOD_644` | New fruit-spread profiles below |

The [BZfE cultivated-mushroom guidance](https://www.bzfe.de/kueche-und-alltag/kochen/how-to-obst-und-gemuese/how-to-pilze)
now supports national year-round availability for button mushrooms, matching the
existing shiitake and king oyster profiles. The remaining seasonal mappings use
existing reviewed regional evidence: [Hesse](https://schulverpflegung.hessen.de/informieren-und-vernetzen/rezepte-und-warenkunde/saisonkalender/),
[Bavaria](https://www.bund-naturschutz.de/oekologisch-leben/essen-und-trinken/bayerischer-saisonkalender),
[BZfE walnuts](https://www.bzfe.de/presse/pressemeldungen-archiv-2024-und-frueher/walnuss-fuer-die-herbstkueche),
[BZfE spring onions](https://www.bzfe.de/presse/pressemeldungen-archiv/feinwuerzige-fruehlingszwiebel)
and [Elymnion pomegranates](https://elimnionrodi.gr/en/elymnion-rodi/).
Unlisted months and unsupported countries remain unknown. Preserved, powdered,
frozen and dried forms do not acquire a fresh harvest calendar.

Two verified Xucker 220 g spreads have a ten-day after-opening instruction:

| Flavour | GTIN | Manufacturer instruction | Retailer GTIN evidence |
| --- | --- | --- | --- |
| Strawberry | `4260248063892` | [Xucker](https://www.xucker.de/aufstriche/fruchtaufstrich-erdbeere) | [dm](https://www.dm.de/p/d/1559917/xucker-fruchtaufstrich-erdbeere-mit-xylit) |
| Raspberry | `4260248063908` | [Xucker](https://www.xucker.de/aufstriche/fruchtaufstrich-himbeere) | [dm](https://www.dm.de/p/d/1559922/xucker-fruchtaufstrich-himbeere-mit-xylit) |

Both require refrigeration and clean utensils. The 4 °C cap comes from the
existing BfR cooling policy; the manufacturer specifies refrigeration without a
numeric temperature. The generic jam choice accepts either exact package;
strawberry and raspberry profiles each accept only the matching flavour. Brand,
barcode, refrigeration, opening and handling confirmation are required. Selecting
guidance does not mark a package open. Manual package intervals and earlier
printed dates retain precedence.

[dmBio strawberry spread](https://www.dm.de/p/d/1058435/dmbio-fruchtaufstrich-erdbeere-75-prozent-frucht)
(`4067796111118`) says to consume within a few days, and
[Alnatura sweet-orange spread](https://www.alnatura.de/de-de/produkte/alle-produkte/vorratskammer/brotaufstriche/suesse-aufstriche/bio-fruchtaufstrich-bio-gelee/fruchtaufstrich-suesse-orange-244231/)
specifies refrigeration without an exact duration. Neither receives a numeric
rule. Apple, berry, blueberry, cherry, cranberry, orange and red-fruit jams use
label-required guidance. Milk jam, chestnut jam, mixed alternatives, homemade
jams and fresh berries cannot borrow the Xucker limits. Sources checked 2026-09-25.

German supermarket labels now include `Kräuterseitlinge`, `Granatapfel`,
`Erdbeermarmelade`, `Himbeermarmelade` and `Orangenmarmelade`; search also accepts
Konfitüre and Fruchtaufstrich variants. The provider's Hokkaido squash identity,
confirmed by German, Czech, French and Polish translations, now displays as
`Κολοκύθα Χοκάιντο` in Greek. Raw recipe amounts, IDs, nutrients and translations
are unchanged.

Coverage reaches 3,360 rows: 2,254 seasonal, 591 with numeric opening guidance
and 515 label-required, adding 42 enriched rows. There are 112 season groups,
81 opening-rule groups and 135 unique reviewed numeric-rule barcodes. Local
checks cover real multilingual choices, twelve-month German/Greek filters,
flavour and product boundaries, manual/printed precedence and opening
confirmation, including mobile and desktop browser paths in
`tests/browser_catalog_lifecycle_v240.py`.

### Recipe preview stock percentage (runtime v241)

Every recipe preview now shows a home icon and the at-home percentage in the
top-right corner of its photo. The shared renderer covers Today, Week, Discover,
recommendations, saved recipes, personal recipes and ingredient-usage previews.
It uses the existing quantity coverage, then legacy pantry/presence data when
needed. Partial known coverage is marked `≈`; entirely unknown availability is
`—`, including the backend's all-unknown average. Price labels stay top-left and
dietary-change notices remain readable below the percentage. Rendering adds no
network request or stock mutation. Greek, German and English accessible labels
are provided, and runtime v241 refreshes the cached frontend module graph.
Local tests cover numeric/unknown/partial values, identity-safe fallback, all
preview routes, mobile/desktop positioning and the existing photo-open action.

## Batch 25: ground nuts, nut/seed pastes and two fresh herbs

Ground hazelnuts no longer borrow the harvest calendar for whole hazelnuts.
Ground almonds and hazelnuts have a separate processed-form profile with
package-label guidance, including the reviewed cup-measure canonical variant.
The exact provider IDs `M_FOOD_330` and `M_FOOD_400` expose this guidance on
the actual choices. Whole nuts remain distinct. Browser validation exposed a
missing whole-hazelnut mapping: `M_FOOD_329` and the singular `Hazelnut` canonical
name now expose the existing September–November Bavarian calendar, rechecked
against the [BUND Naturschutz source](https://www.bund-naturschutz.de/oekologisch-leben/essen-und-trinken/bayerischer-saisonkalender).

The [Verbraucherzentrale nut-storage guidance](https://www.verbraucherzentrale.de/wissen/lebensmittel/auswaehlen-zubereiten-aufbewahren/nuesse-laenger-haltbar-durch-richtige-lagerung-58935)
gives an approximate four-week refrigerated interval for opened, chopped nuts.
However, the reviewed [dmBio ground-hazelnut package](https://www.dm.at/p/d/3060015/dmbio-haselnuesse-gemahlen)
(`4066447856439`, Austrian product page) calls for consumption within a few days.
This batch therefore does not set a universal 28-day clock, or convert vague
package wording into an exact day count. Users can still enter their own
package instructions. The product-specific difference remains documented.

Peanut butter, crunchy peanut butter and almond butter now have a separate
label-required profile. Seven reviewed tahini and paste canonical names share
another label-required profile; the ambiguous sesame-sauce variant stays
unmapped. Provider IDs `M_FOOD_34` and `M_FOOD_706` are explicitly allowed.
The reviewed product pages below give storage instructions without a numeric
after-opening duration, so none is invented:

| Reviewed package | GTIN | Source |
| --- | --- | --- |
| dmBio peanut butter, 250 g | `4066447948271` | [Peanut butter](https://www.dm.de/p/d/1446281/dmbio-erdnussmus) |
| dmBio white almond butter, 250 g | `4070765069976` | [Almond butter](https://www.dm.de/p/d/1449136/dmbio-mandelmus-weiss) |
| dmBio tahini, 250 g | `4066447948318` | [Sesame paste](https://www.dm.de/p/d/3064622/dmbio-sesammus-tahin) |

These barcodes document the review; they do not enter the numeric-rule barcode
count. All sources in this batch were checked on 2026-09-25.

One new numeric rule applies to the exact
[dmBio satay peanut sauce, 325 ml](https://www.dm.de/p/d/1682196/dmbio-erdnusssosse-sate-wuerzig-nussig),
GTIN `4066447377903`: three days after opening under refrigeration. It extends
the existing satay profile and selectable `M_FOOD_534`, while retaining the
Alnatura package rule. The 4 °C cap comes from the existing BfR cooling policy;
the manufacturer page specifies refrigeration without a numerical temperature.
Brand, barcode, storage and opening must match. Selection requires confirmation
and does not itself mark the package open. Earlier printed dates and manual
package intervals retain precedence. Peanut butter, tahini, peanuts, seasoning
and homemade satay cannot borrow this sauce's rule.

Two further provider rows now expose their existing regional herb calendars:

| Ingredient | Provider ID | Existing season | Source |
| --- | --- | --- | --- |
| Lemon balm | `M_FOOD_697` | June–September, Bavaria | [LWG garden herbs](https://www.lwg.bayern.de/gartenakademie/gartendokumente/infoschriften/157754/index.php) |
| Sorrel | `M_FOOD_571` | April–October, Hesse | [BZfE green-sauce herbs](https://www.bzfe.de/presse/pressemeldungen-archiv/frankfurter-gruene-sosse) |

The canonical identities and Czech `Meduňka` / Polish `Szczaw` names were
reviewed directly. The catalog's low-confidence lemongrass and mustard-green
nutrient proxies are not evidence of culinary identity and do not transfer
their species to the lifecycle data. This batch does not alter nutrition.
Unsupported countries and months remain unknown; extracts, teas, dried and
frozen forms do not inherit the fresh calendars.

German supermarket labels now use `Zitronenmelisse`, `Sauerampfer`, `Mandelmus`,
`Erdnussbutter mit Stückchen`, `Gemahlene Mandeln`, `Gemahlene Haselnüsse` and
`Sesammus (Tahin)`. Search also accepts `Melisse`, `Mandelbutter`, `Tahin`,
`Tahini` and `Sesampaste`. Whole nuts, ground nuts, nut butter, sauce and seeds
retain separate source identities and choices.

Coverage reaches 3,318 rows: 2,245 seasonal, 574 with numeric opening guidance
and 499 label-required. There are 46 newly enriched rows; three existing ground
hazelnut rows move from seasonal to processed guidance. The numeric row count
stays unchanged because the new sauce rule extends an existing profile.
Local validation includes `tests/test_catalog_lifecycle_v239.py`, the lifecycle,
amount/deduplication and seasonal-filter regressions, plus
`tests/browser_catalog_lifecycle_v239.py` on mobile and desktop. Browser checks
cover twelve months, whole/ground distinctions, supermarket names, storage
confirmation and rejection of a peanut-butter barcode for satay guidance.

## Batch 24: fresh herbs, dried pantry forms and edible pea pods

Sixteen further provider identities now expose their reviewed profiles on the
actual Greek, German and English choices. Existing catalog nutrition reviews
identify the seven herbs below as fresh/raw culinary herbs; their translations
and explicit dried-herb counterparts were reviewed together. The runtime still
requires the exact provider allowlist and does not infer form from nutrients,
search text or a related ingredient.

| Ingredients | Exact provider IDs | Existing guidance |
| --- | --- | --- |
| Basil | `M_FOOD_30` | German outdoor harvest, June–October |
| Chives, parsley | `M_FOOD_115`, `M_FOOD_369` | Hesse seasonal availability, April–October |
| Dill | `M_FOOD_16` | German outdoor harvest, May–September |
| Mint | `M_FOOD_308` | North Rhine-Westphalia outdoor harvest, May–October |
| Rosemary, thyme | `M_FOOD_425`, `M_FOOD_476` | German outdoor harvest, May–October |
| Mangetout | `M_FOOD_386` | German snow-pea harvest, June–August |
| Dried pasta, dried beans, flour, milk powder, ground black pepper, rice, salt, sugar | `M_FOOD_361`, `M_FOOD_512`, `M_FOOD_186`, `M_FOOD_270`, `M_FOOD_764`, `M_FOOD_421`, `M_FOOD_457`, `M_FOOD_467` | Dry-staple profile; package label required, no numeric opening interval |

The seasonal sources were rechecked on 2026-09-25:
[BZfE basil](https://www.bzfe.de/presse/pressemeldungen-archiv/volles-sommeraroma-basilikum),
[BZfE green-sauce herbs](https://www.bzfe.de/presse/pressemeldungen-archiv/frankfurter-gruene-sosse),
[Verbraucherzentrale seasonal calendar](https://www.verbraucherzentrale.de/sites/default/files/migration_files/media222992A.pdf),
[Landservice mint](https://www.landservice.de/regionale-lebensmittel/kraeuter-getreide/minze)
and [BZfE snow peas](https://www.bzfe.de/presse/pressemeldungen-archiv/zeit-fuer-zuckerschoten).
Month lists and regional scope are unchanged. Unlisted months and countries
without supporting evidence remain unknown. Chervil, oregano, sage and tarragon
provider rows retain unknown guidance because their generic names and dried or
ground nutrition references do not establish a consistent fresh identity.

The two exact mangetout canonical names now use the edible-pod snow-pea
profile instead of the shelled-pea profile. German choices use `Zuckerschoten`,
with `Zuckererbsen` and `Kaiserschoten` search aliases. Fresh shelled peas remain
a separate profile; frozen and canned forms do not inherit this calendar.

Nine explicitly dried herb canonical names cover 18 existing rows: dried
basil, mint, oregano, oregano leaves, thyme, herbs, herbs such as rosemary,
mixed herbs and the recipe fragment `Pinch of dried mint`. These receive the
dry-staple profile, so the seasonal filter keeps them available throughout the
year without implying a fresh harvest or an unlimited shelf life. The existing
[package-label policy](https://www.verbraucherzentrale.de/wissen/lebensmittel/auswaehlen-zubereiten-aufbewahren/lebensmittel-nach-dem-oeffnen-gekuehlt-lagern-angaben-oft-zu-vage-109122)
still applies: no short expiry is invented, manual package intervals remain
possible, and a milk or canned-bean barcode cannot turn a dry ingredient into
that product's opening rule.

German labels now explicitly say `Getrockneter Basilikum`, `Getrocknete Minze`,
`Getrockneter Oregano`, `Getrockneter Thymian`, `Getrocknete Kräuter`,
`Getrocknete Kräutermischung`, `Getrocknete Bohnen` and
`Gemahlener schwarzer Pfeffer`. An exact display override merges the leftover
pinch-of-dried-mint choice with dried mint in all three tested languages.
Its original canonical name, recipe quantities, nutrition and source identity
remain intact; fresh mint remains separate.

Coverage reaches 3,272 rows: 2,245 seasonal, 574 with numeric opening guidance
and 453 label-required. No new barcode, numeric interval, ingredient or recipe
is introduced. Local validation includes `tests/test_catalog_lifecycle_v238.py`,
the lifecycle regressions, amount-free choices and seasonal-filter tests,
plus `tests/browser_catalog_lifecycle_v238.py` at mobile and desktop sizes.
The browser checks all twelve months, unsupported-country fallback, preserved
fresh/dried distinctions, supermarket labels and the deduplicated mint entry.

## Batch 23: existing guidance on selectable provider ingredients

Twenty reviewed provider rows lacked lifecycle metadata because these official
rows have no classification field and require an explicit identity allowlist.
The classification gate remains intact. The following exact IDs now expose
their already reviewed profiles on the real Greek, German and English choices:

| Ingredients | Provider IDs | Existing guidance |
| --- | --- | --- |
| Milk, semi-skimmed milk, whole milk | `M_FOOD_263`, `M_FOOD_269`, `M_FOOD_271` | Conditional milk rule; heat treatment and refrigeration must be confirmed |
| Hazelnut drink | `M_FOOD_268` | Alpro brand guidance or the exact Alnatura package |
| Lentils, red kidney beans | `M_FOOD_280`, `M_FOOD_653` | Verified Alnatura/dmBio packages with their own handling conditions |
| Salsa, satay sauce | `M_FOOD_533`, `M_FOOD_534` | Their exact Alnatura packages |
| Coconut cream, cream, crème fraîche, cottage cheese, sour cream, thick crème fraîche, yoghurt, liquid cream | `M_FOOD_507`, `M_FOOD_681`, `M_FOOD_150`, `M_FOOD_184`, `M_FOOD_614`, `M_FOOD_151`, `M_FOOD_497`, `M_FOOD_152` | Package label required; no numeric interval |
| Mayonnaise, mustard, wholegrain mustard, soy sauce | `M_FOOD_306`, `M_FOOD_323`, `M_FOOD_324`, `M_FOOD_444` | Package label required; no numeric interval |

This batch adds no new barcode or opening duration. The
[milk guidance](https://www.bzfe.de/kueche-und-alltag/vom-acker-bis-zum-teller/milch/vom-einkauf-in-die-kueche),
[Alnatura hazelnut drink](https://www.alnatura.de/de-de/produkte/alle-produkte/milch-milchprodukte/milchalternativen/bio-mandeldrink-bio-nussdrink/haselnussdrink-natur-229385/),
[salsa](https://www.alnatura.de/de-de/produkte/alle-produkte/vorratskammer/wuerzen-oele-essige/bio-senf-mayo-ketchup-bio-dip/salsa-dip-218906/)
and [peanut sauce](https://www.alnatura.de/de-de/produkte/alle-produkte/schnelle-kueche/bio-sossen/erdnuss-sauce-243700/)
were rechecked on 2026-09-25. Existing exact-package rules, temperature limits,
container-transfer requirements, printed-date precedence and opening opt-in
remain unchanged. Generic lentil/bean names cannot select a canned-product
interval without that product's identity. The milk rule does not establish
heat treatment from fat content and does not apply to raw or powdered milk.
The previously unmapped `M_FOOD_653` has an unspecified English kidney-bean
form and a canned Japanese label. It now receives the product-only profile,
whose season is unknown and whose every rule requires a reviewed barcode;
the generic canned-food profile remains inapplicable. The earlier regression
now verifies that missing package identity cannot produce an opening date,
including with a canned-food brand such as Bonduelle.
Unreviewed herb forms, ambiguous identities and non-food rows are not made
eligible by this mapping work.

German supermarket labels now use `Haselnussdrink`, `Satésauce` and
`Fettarme Milch`, retaining search aliases such as `Haselnussmilch`,
`Sataysauce`, `Saté-Sauce` and `Teilentrahmte Milch`. Crème fraîche is labelled
`Crème fraîche` instead of `Sahne`; the thick variant shares that supermarket
name while retaining its source identity. Cream remains a separate choice.
Locale lookup keys use the presentation layer's accent-free normalization;
display labels retain their accents. Existing Greek labels are preserved.

Two German profiles now use national Alnatura calendars:

| Ingredient | Reviewed availability | Source |
| --- | --- | --- |
| Broccoli | May–November, including smaller supply in May, June, October and November | [Broccoli calendar](https://www.alnatura.de/de-de/magazin/saisonkalender/saisongemuese-gemuese-im-saisonkalender/brokkoli-saison/) |
| Fresh tomatoes | June–October, including smaller supply in June, July and October | [Tomato calendar](https://www.alnatura.de/de-de/magazin/saisonkalender/saisongemuese-gemuese-im-saisonkalender/tomaten-saison/) |

Tomatoes retain their previous months, with a national supply basis replacing
regional monthly highlights; broccoli gains May. Both remain approximate,
with unlisted months and unsupported countries unknown. The ambiguous exact
entry `Tomato, tomato paste` no longer borrows a fresh-tomato calendar.
Preserved, dried and frozen forms do not inherit these seasons.

Coverage reaches 3,238 ingredient rows: 2,237 seasonal, 574 with numeric opening
guidance and 427 label-required. The numeric and label increases come from
making existing evidence available on eight and twelve provider rows,
respectively. One mixed entry is removed from seasonal coverage.

Local validation: `tests/test_catalog_lifecycle_v237.py`, the lifecycle
regression suite, amount-free choices and seasonal-filter tests, and
`tests/browser_catalog_lifecycle_v237.py` on mobile and desktop. The browser
checks the actual multilingual rows, seasonal boundaries and package editors,
including the milk heat-treatment and non-metal-container confirmations.

## Batch 22: fermented vegetables, roots and stalks

Two dmBio packages were reviewed on 2026-09-25. Each requires the exact brand
and GTIN, refrigeration and the catalog's existing conservative maximum of
4 °C. This numerical temperature cap comes from the BfR cooling policy; the
product pages themselves specify refrigeration without a temperature.

| Package and label source | Verified GTIN | Days after opening |
| --- | --- | --- |
| [Kimchi, pasteurized fermented white cabbage, 270 g / 240 g drained](https://www.dm.de/p/d/1639878/dmbio-kimchi-fermentiertes-gemuese) | `4066447087130` | 3 |
| [Mild sauerkraut, 520 g / 500 g drained](https://www.dm.de/p/d/1530880/dmbio-mildes-sauerkraut) | `4066447677652` | 3 |

The existing plain kimchi ingredient gains a processed-food profile. Its rule
does not transfer to napa-cabbage kimchi, kimchi brine, aged/sour kimchi or a
homemade preparation. Sauerkraut retains its existing Alnatura package rule.
Exact provider mappings for `M_FOOD_595` and `M_FOOD_548` make both profiles
available on the actual Greek, German and English picker entries. Canonical
names alone had left the selectable provider sauerkraut row without guidance.
No new ingredient rows or duplicates are created.

Choosing guidance still requires storage confirmation. It does not mark the
package opened or apply an expiry automatically; manual package instructions
and earlier printed dates retain priority. Neither fermented vegetable inherits
fresh cabbage seasonality. Cooking a product is not a new package-opening event.

The reviewed [dmBio capers](https://www.dm.de/p/d/3095647/dmbio-kapern),
[tomatoes in oil](https://www.dm.de/p/d/1488097/dmbio-tomaten-sonnengetrocknet-eingelegt-in-oel)
and [soft dried tomatoes](https://www.dm.de/p/d/1638727/dmbio-soft-tomaten)
only specify prompt use or a few days. Their GTINs `4066447876468`,
`4066447898729` and `4066447885019` therefore receive no numeric rule.

Three German produce profiles now use national Alnatura calendars:

| Ingredient | Reviewed availability | Basis/source |
| --- | --- | --- |
| Celeriac | January–March and May–December | [Fresh May–November, stored December–March](https://www.alnatura.de/de-de/magazin/saisonkalender/saisongemuese-gemuese-im-saisonkalender/sellerie-saison/) |
| Celery stalks | May–October | [Domestic supply, including smaller May, June and October availability](https://www.alnatura.de/de-de/magazin/saisonkalender/saisongemuese-gemuese-im-saisonkalender/stangensellerie-saison/) |
| Brussels sprouts | September–February | [Domestic supply, including smaller September, January and February availability](https://www.alnatura.de/de-de/magazin/saisonkalender/saisongemuese-gemuese-im-saisonkalender/rosenkohl-saison/) |

These remain approximate German calendars. Unlisted months and other countries
remain unknown; fresh seasons do not apply to frozen or cooked products.
The exact mixed name `Celery stalk, carrot` is removed from the celery allowlist
because one component's calendar cannot establish availability for the mixture.

German supermarket labels now distinguish `Stangensellerie` from
`Knollensellerie`; `Staudensellerie` and `Bleichsellerie` remain searchable.
Parsley root uses `Petersilienwurzel`, with `Wurzelpetersilie` as a search alias.
Existing Greek names and ingredient identities are preserved.

Coverage reaches 3,219 ingredient rows: 2,238 seasonal, 566 with numeric opening
guidance and 415 label-required. The seasonal count decreases by one because
the mixed celery/carrot entry no longer borrows a single-vegetable calendar.
The source catalog remains explicitly incomplete.

Local checks: `tests/test_catalog_lifecycle_v236.py`, the lifecycle regression
suite, amount-free catalog choices and seasonal-filter tests, plus
`tests/browser_catalog_lifecycle_v236.py` at mobile and desktop sizes. Browser
coverage uses the real enriched rows, Greek UI with German supermarket names,
month boundaries, both package editors and opening confirmation.

## Batch 21: condiments, year-round produce and catalog identity

Seven dmBio packages were reviewed on 2026-09-25. These rules require the exact
brand and GTIN, refrigeration, and the existing conservative catalog cap of
4 °C. The temperature cap comes from the catalog's BfR cooling policy, not a
numeric temperature on these product pages.

| Package and label source | Verified GTIN | Days after opening | Extra handling |
| --- | --- | --- | --- |
| [Tomato ketchup, 450 ml](https://www.dm.de/p/d/1622220/dmbio-tomaten-ketchup) | `4066447887723` | 30 | Store upright |
| [Thai curry sauce, 325 ml](https://www.dm.de/p/d/1488554/dmbio-currysosse-thai) | `4066447675887` | 3 | — |
| [Indian curry sauce, 325 ml](https://www.dm.de/p/d/1488553/dmbio-currysosse-indisch-cremig-pikant) | `4067796097245` | 3 | — |
| [Tomato sauce with grilled pepper, 325 ml](https://www.dm.de/p/d/1372859/dmbio-tomatensauce-gegrillte-paprika) | `4066447887785` | 3–4 | — |
| [Tomato sauce with goat cream cheese, 320 ml](https://www.dm.de/p/d/3120498/dmbio-tomatensauce-ziegenfrischkaese) | `4070765100709` | 5 | — |
| [Tomato sauce with goat cream cheese, 340 g](https://www.dm.de/p/d/1638721/dmbio-tomatensosse-ziegenfrischkaese) | `4066447257748` | 5 | — |
| [Ajvar cream dip, Austrian listing, 180 g](https://www.dm.at/p/d/3042443/dmbio-gemueseaufstrich-ajvar-creme-dip) | `4067796185997` | 3 | — |

Ajvar gains a profile for the already existing exact ingredient; it does not
create another catalog entry. The reviewed provider ketchup ID `M_FOOD_259` now
carries the same evidence as the existing unambiguous ketchup names. This fixes
the German picker choosing an official ketchup row without lifecycle metadata.
The historic `ketchup_label` profile ID is preserved, now with a conditional
product rule. Unverified ketchup and Alnatura's refrigeration-only package still
have no catalog duration. Curry powder/paste, passata, fresh peppers, cheese,
homemade Ajvar and mixed condiment alternatives cannot borrow these rules.
The reviewed dmBio red/basil pesto pages say to use promptly but give no numeric
duration, so no numeric rule was added for those packages.

Four German calendars now use national evidence:

- [Beetroot](https://www.alnatura.de/de-de/magazin/saisonkalender/saisongemuese-gemuese-im-saisonkalender/rote-bete-saison/): April–November domestic supply plus December–March stored produce.
- [Red cabbage](https://www.alnatura.de/de-de/magazin/saisonkalender/saisongemuese-gemuese-im-saisonkalender/rotkohl-saison/): May–November domestic supply plus December–April stored produce.
- [White cabbage](https://www.bzfe.de/kueche-und-alltag/kochen/how-to-obst-und-gemuese/how-to-weisskohl-und-spitzkohl): available from Germany throughout the year. The separate pointed-cabbage profile is unchanged.
- [Spinach](https://www.alnatura.de/de-de/magazin/saisonkalender/saisongemuese-gemuese-im-saisonkalender/spinat-saison/): March–November, including the smaller March/July/August supply.

These remain approximate availability calendars rather than a claim of outdoor
harvest throughout every listed month. Greek calendars are unchanged, and cooked,
frozen or pickled forms do not inherit fresh-produce seasons. The existing German
curry-sauce choice now displays **Currysauce**, searchable as **Currysoße** or
**Currysosse**, while retaining its Greek name and original identity.

Coverage reaches 3,211 ingredient rows: 2,239 seasonal, 557 with numeric opening
rules and 415 requiring package instructions, backed by 219 sources. Backend
checks cover all seven exact packages, wrong/missing identity, food forms,
temperature/handling conditions, earlier printed dates, manual precedence and
all 12 seasonal months. Mobile/desktop checks exercise the real Greek/German
catalog choices and the opening confirmation flow. Run
`python tests/test_catalog_lifecycle_v235.py` and, with Playwright installed,
`python tests/browser_catalog_lifecycle_v235.py` locally.

## Batch 20: plant drinks, winter produce and supermarket names

Six additional dmBio packages were reviewed on 2026-09-25. German and Austrian
listings retain separate exact GTINs and day ranges; one market's package does
not identify another market's package.

| Package | Verified GTIN | Days after opening | Extra handling |
| --- | --- | --- | --- |
| Almond drink, German listing, 1 l | `4070765022797` | 4 | Store upright |
| Almond drink, Austrian listing, 1 l | `4067796002065` | 4 | Store upright |
| Gluten-free oat drink, 1 l | `4070765022780` | 4 | Store upright |
| Oat drink natur, Austrian listing, 1 l | `4067796194807` | 3–4 | Store upright |
| Cashew drink natur, 1 l | `4070765022810` | 3–4 | Store upright |
| Ginger juice, 200 ml | `4066447982046` | 14 | Use a clean spoon |

All labels require refrigeration, and the existing BfR-based catalog policy
adds the conservative 4 °C cap. The new clean-spoon condition is translated into
English, German and Greek in the shared opening-editor/cooking-review helper.
Confirmation, an explicit opening date, manual-label precedence and earlier
printed expiry dates remain required or respected as before.

The five plant drinks are reachable through the existing generic Plant milk
choice; almond milk also gains the exact provider mapping M_FOOD_265. Specific
almond/oat/cashew profiles keep their own products, and ginger juice cannot use
a plant-drink rule. Existing Alpro guidance remains available. No new ingredient
names are inferred merely because a product was found.

Four German calendars replace the older monthly highlights with national
sources. Alnatura lists carrots in January–March and May–December, including
stored produce; April remains unknown. BZL documents year-round domestic onions
through variety selection and storage, with smaller summer supply. Alnatura
lists chicory year-round and lamb's lettuce in September–April. The latter
corrects both the missing winter/spring months and the old summer highlights;
May–August are now unknown and hidden by the opt-in seasonal view. These are
approximate availability calendars, not guarantees of local stock or claims
that storage/protected production equals outdoor harvest.

Three exact display/search labels now supply German supermarket names where
English was previously shown: Feldsalat, Pflanzendrink and Ingwersaft. The Greek
names and original catalog identities remain intact. Pflanzenmilch is also a
search alias. Backend and mobile/desktop checks cover the actual catalog rows,
month boundaries, both languages and translated handling confirmation.

Coverage now reaches 3,209 catalog rows: 2,239 seasonal, 535 with numeric
opening rules and 435 requiring package instructions, backed by 208 sources.

## Batch 19: juice packages and seasonal gaps

Eight additional dmBio juice packages were reviewed on 2026-09-25. Each source
URL is stored with its rule. The brand and exact barcode must match; package
size alone never selects a rule.

| Package | Verified GTIN | Days after opening | Extra handling |
| --- | --- | --- | --- |
| Orange juice, 1 l | `4066447855494` | 3 | Store upright |
| Beetroot juice, 1 l | `4070765031096` | 3 | — |
| Beetroot juice, 500 ml | `4070765031126` | 3 | — |
| Cloudy grape juice, 330 ml | `4066447855449` | 3 | Store upright |
| Sauerkraut juice, 500 ml | `4070765031140` | 3–4 | Store upright |
| Lemon juice, 200 ml | `4066447855579` | 14 | Store upright |
| Vegetable juice, 500 ml | `4066447855630` | 3–4 | Store upright |
| Tomato juice with sea salt, 500 ml | `4066447855685` | 3 | — |

All labels require refrigeration. The catalog retains its conservative 4 °C
cap with BfR cooling evidence; that numeric cap is not attributed to dmBio.
Range rules retain the earlier reminder and later maximum date. Selecting
catalog guidance still requires confirmation and does not mark a package open.
Manual package instructions and earlier printed dates retain precedence.

Different juices, fresh produce and freshly squeezed preparations do not borrow
these package rules. The lemon interval cannot apply to orange juice. Two
verified carrot-juice labels were held because no matching selectable ingredient
exists in the shipped catalog. The checked apple
juices and 1 l grape juice did not expose numeric opening instructions on the
reviewed German pages, so they were not added in this batch.

BZfE's national Chinese-cabbage guidance adds March (stored domestic produce)
and May (protected cultivation), alongside June–November outdoor harvest and
December–February storage. April remains unknown. Alnatura's national radish
calendar lists domestic availability throughout April–November, closing the
previous August gap and adding November. Its smaller April/May/October/November
offer is included; this is availability, not a peak-harvest claim. Both calendars
remain approximate and do not apply to kimchi, pickled or frozen forms.

No new ingredient identities are inferred. Coverage remains 3,208 ingredient
rows, with 117 verified product barcodes and 198 evidence sources. Regression
checks exercise all eight packages through actual Greek/German catalog choices,
all seasonal month boundaries, and mobile/desktop opening confirmation.

## Batch 18: tofu temperatures, olive packages and pesto forms

Ten additional dmBio packages were reviewed on 2026-09-25. Source URLs and
the exact verified GTINs are stored alongside each rule.

| Package | Verified GTIN | Days after opening | Refrigeration |
| --- | --- | --- | --- |
| Natural tofu, 200 g | `4067796251999` | 2 | 2–6 °C, as labelled |
| Smoked tofu, 200 g | `4067796252019` | 2 | 2–6 °C, as labelled |
| Green pitted olives, German listing | `4070765075939` | 14 | Catalog cap of 4 °C |
| Green pitted olives, Austrian listing | `4066447870411` | 14 | Catalog cap of 4 °C |
| Kalamon pitted olives, German listing | `4070765075953` | 14 | Catalog cap of 4 °C |
| Kalamon pitted olives, Austrian listing | `4066447898743` | 14 | Catalog cap of 4 °C |
| Olive mix with herbs, 180 g | `4070765075892` | 7 | Catalog cap of 4 °C |
| Seitan, 200 g | `4066447884883` | 2 | Catalog cap of 4 °C; keep closed |
| Black olive spread with feta, 190 g | `4066447087161` | 14 | Catalog cap of 4 °C |
| Pesto Verde with basil and cashews, 190 g | `4066447887822` | 5 | Catalog cap of 4 °C |

An optional `minTemperatureC` now preserves a labelled lower temperature bound.
The validator rejects invalid or inverted ranges; the evaluator rejects a
temperature below that bound. Rules without it retain the existing zero-degree
lower bound. The opening editor and cooking review share translated range text
in English, German and Greek. Both tofu products use their manufacturer's
explicit 2–6 °C range. Other products retain the conservative 4 °C cap with BfR
cooling evidence. Barcode/brand checks and explicit handling confirmation still
apply, and neither choosing guidance nor scanning starts the opening clock.

Basil and red pesto now have separate profiles. The generic pesto profile keeps
all reviewed choices; basil pesto accepts the verified basil packages, while red,
tomato and sun-dried-tomato pesto accept the reviewed red package. In particular,
the new dmBio Verde instruction cannot be borrowed by a red pesto ingredient.
Seitan and black olive spread gain separate product-scoped profiles; plain,
smoked, silken and fried tofu do not share these new rules. Four reviewed provider
IDs (M_FOOD_477, M_FOOD_733, M_FOOD_539 and M_FOOD_370) expose the matching profiles.

German seasons now use BZfE's national guidance for chard (March–September,
including early protected cultivation), fresh green beans (approximately June
to mid-November), and cauliflower (approximately May/June to October/November).
The month-level windows remain approximate. Deutschland – Mein Garten documents
year-round fresh domestic leek harvest across summer and winter varieties.
Preserved/frozen forms do not inherit these calendars. Coverage now reaches
3,208 catalog rows: 2,239 seasonal, 534 with numeric opening rules and 435
requiring package instructions; the catalog remains incomplete.

## Batch 17: everyday packages and official catalog coverage

These ten additional dmBio instructions were reviewed on 2026-09-25. The exact
brand-owner product URLs and review date accompany each rule in the sidecar.

| Package | Verified GTIN | Days after opening | Extra handling |
| --- | --- | --- | --- |
| Kidney beans, 240 g drained | `4067796187038` | 3–4 | Transfer to non-metal container |
| Cannellini beans, 240 g drained | `4067796187052` | 3–4 | Transfer to non-metal container |
| Brown lentils, 240 g drained | `4066447373189` | 3–4 | Transfer to non-metal container |
| Sweetcorn, 340 g / 230 g drained | `4067796153903` | 2 | — |
| Tomato pieces, 400 g | `4066447887679` | 3 | Transfer to non-metal container |
| Oat cooking cream, 200 ml | `4066447965988` | 4 | — |
| Soy cooking cream, 200 ml | `4070765067460` | 4 | — |
| Almond cooking cream, 200 ml | `4066447876642` | 4 | — |
| Apple purée, 360 g | `4067796068498` | 3 | — |
| Cold-grated apple purée, 360 g | `4067796068559` | 3 | — |

All retain exact brand/GTIN matching, confirmation and the conservative 4 °C
refrigeration cap. For sweetcorn, the two-day period is the product instruction;
refrigeration is the catalog's conservative handling requirement supported by
the BfR cooling guidance, not a temperature printed on that product page.
For 3–4 day ranges, the lifecycle evaluator returns day 3 as the advisory
reminder and day 4 as the maximum deadline. Selecting the rule in the package
editor stores the four-day maximum. Earlier printed dates and manual package values retain
precedence. Cooking creams do not supply drink or dairy-cream rules, and these
can instructions do not transfer to dried beans or lentils.

Three existing seasonal profiles now use national BZfE evidence: courgettes
approximately May–October (harvest starts around mid-May), cucumbers
March–October (including greenhouse salad cucumbers, not a blanket outdoor
claim), and cultivated blueberries approximately June–October (starts late
June). Pickled cucumbers, juice, dried berries, jam, mixed dishes and courgette
flowers do not inherit these fresh-produce windows. Unlisted months remain
unknown in the evidence API and are excluded by the seasonal-only picker.

Another 87 individually reviewed official IDs now receive their existing
profiles: 75 produce rows and 12 cheese, juice and sauce rows. Their exact IDs
are recorded in `ingredientIds`; this remains an allowlist. Conflicting
translations (including M_FOOD_399 and M_FOOD_328), the dry/canned ambiguity of
M_FOOD_653, and spice homonyms were not added. This brings evidence to 3,199
actual catalog rows: 2,239 seasonal, 525 with numeric opening rules, and 435
requiring package instructions. Overall coverage is still incomplete.

## Batch 16: verified dmBio packages and German season gaps

The following additional package instructions were reviewed on 2026-09-25.
Each product's brand-owner URL is stored with its rule in the sidecar.

| dmBio package | Verified GTIN | Days after opening | Additional condition |
| --- | --- | --- | --- |
| Passierte Tomaten, 500 g | `4066447887730` | 3 | — |
| Passata, 690 g bottle | `4070765018783` | 3 | Keep closed |
| Chickpeas, 350 g / 220 g drained | `4070765042894` | 2 | — |
| Chickpeas, 700 g / 410 g drained | `4070765071559` | 2 | — |
| Coconut milk, 400 ml | `4067796063882` | 4 | — |
| Coconut milk, 250 ml carton | `4067796075519` | 4 | — |
| Soy drink natur, 1 l | `4070765022803` | 4 | Store upright |
| Rice drink natur, 1 l (verified Austrian package) | `4067796002102` | 4 | Store upright |
| Coconut drink natur, 1 l | `4070765022827` | 4 | Store upright |
| Oat drink natur, 1 l | `4070765022759` | 4 | Store upright |
| Oat drink Barista, 1 l | `4070765022841` | 4 | Store upright |

All require the exact brand and barcode, refrigeration at the existing
conservative 4 °C cap, and confirmation of the listed handling instructions.
The upright-storage condition is translated into English, German and Greek.
These periods do not transfer between coconut milk and coconut drink, between
drink types, or to dried legumes, homemade hummus, tomato paste or coconut cream.
Earlier printed dates still cap the calculated deadline; opening and applying
the deadline remain explicit user actions. Old or changed GTINs do not inherit
instructions just because a product name or package size looks the same.

BZfE's national guidance replaces the shorter Hessian highlight lists for three
existing groups: bell peppers March–November (domestic availability, including
protected growing rather than an outdoor-only claim), spring onions approximately
March–November (outdoor harvest from mid-March), and parsnips October–March
(regional availability, not an outdoor-only claim). Preserved/frozen forms and
unlisted months or countries remain unknown. VerbraucherService Bayern adds
March–September harvesting for fresh nettle leaves; blanched leaves, seeds and
dried nettles do not receive that fresh-leaf calendar. Nine exact fresh names
also gain coverage, including prepared whole peppers, red radicchio and baby
spinach salad.

Ten explicitly reviewed provider IDs now receive their existing food profiles
even where the official row omits `classification`. This covers bell peppers,
spring onions, parsnip, coconut milk and soy milk. In particular, M_FOOD_389 is
the vegetable pepper; M_FOOD_388 (pepper spice), M_FOOD_358 (paprika powder) and
the ambiguous fresh/dried chilli entry M_FOOD_377 do not borrow its season.
Non-food classifications and rows requiring semantic confirmation are still
excluded. No fuzzy label matching or blanket acceptance of unclassified rows
is introduced. Actual picker choices and opening-guidance requests are tested
against these IDs.

## Season semantics

German season months are availability guidance from the twelve monthly
calendars published by the Hessische Lehrkräfteakademie, BZfE produce guides,
the BVEO pak choi guide, Hessen VerbraucherFenster and the Verbraucherzentrale
season calendar, BUND Naturschutz's Bavarian calendar, Hortipendium, LWG and
Landwirtschaftskammer Nordrhein-Westfalen's Landservice, EDEKA meinLand,
Kressepark Erfurt, Industrieverband Agrar (IVA), Dehner's cultivation guide
and Biohof Stövesandt's regional ginger harvest.
For the Hessian monthly calendar entries, the source region
(`DE-HE`), country (`DE`), source links and review date are preserved. The source
includes stored produce and protected cultivation; these months must not be
labelled as exclusively fresh outdoor harvest. Ordinary potatoes have year-round
availability, including stored crops, according to BZfE (`sourceRegion: DE`).
New potatoes have a separate June/July highlight profile; they do not inherit
the stored-potato calendar. Sweet potatoes and potato starch remain separate.

Batch 14 adds 62 exact fresh citrus names. Bio Net West Hellas's cooperative
calendar supplies approximate Western Greece (`country: GR`) availability:
lemons December–March, sweet oranges October–May, grapefruit November–March
and mandarins October–March. The source starts some crops partway through a
month; this month-level guidance is approximate. Sparta Orange's Skala,
Laconia calendar supplies a separate December–January clementine season.
Both sources use `regional_seasonal_availability` and `listed_months_only`:
other months and countries remain unknown. They do not represent every Greek
region or cultivar, or German import availability. Blood/bitter oranges,
preserves, bottled juice, mixed ingredients and flavourings do not inherit
these calendars. Explicit fresh juice and fruit/zest preparations do.

Batch 15 adds Greek evidence to eight existing produce profiles and a new
pomegranate profile, covering 55 exact names. Existing German regions remain
unchanged. NEA EXFRUT's calendar and product pages identify these supply periods
and growing regions:

| Produce | Greek region | Listed availability |
| --- | --- | --- |
| Apricots | Pella, Chalkidiki | May–August |
| Sweet cherries | Pella | May–August |
| Peaches and nectarines | Pella | May–September |
| Plums | Pella | July–October |
| Table grapes | Pella, Kavala | July–October |
| White and green asparagus | Pella | February–May |
| Kiwi | Pella, Pieria | October–May, including cold storage |
| Sweet chestnuts | Pella | October–December |

These are approximate regional availability windows, including controlled
cultivation for asparagus. Kiwi explicitly uses
`seasonal_calendar_including_stored_produce`, as the supplier documents cold
storage. Elimnion Rodi separately supports an October–November outdoor harvest
for pomegranate seeds from Limni, northern Evia, based on local Ermioni fruit.
That harvest window does not inherit an exporter's longer stored-fruit season.
Unlisted months remain unknown. Sour cherries, Mirabelle plums, juice, preserves,
frozen fruit and dried-cranberry alternatives do not borrow the new Greek rules.

Fresh parsley leaves, chives, chervil and sorrel use the Frankfurt green-sauce
herb season (`sourceRegion: DE-HE`, `basis: regional_seasonal_availability`).
April–October is a conservative subset of BZfE's April-to-late-autumn description;
it does not assert an exact end to the season. Basil uses the explicit June–October
outdoor harvest period (`basis: outdoor_harvest`), independent of year-round
potted availability. Savoy cabbage uses May–February regional availability,
and pak choi uses May–October. These profiles do not apply to dried/frozen herbs,
Thai basil, parsley root, cooked cabbage or mixed ingredients.

Fresh chilli entries use Dehner's August-to-first-frost guidance, with its
explicit October harvest endpoint. These approximate August–October months use
`regional_seasonal_availability`, because the cultivation guide covers both
garden and protected growing. They do not describe all supermarket availability.
Only reviewed fresh or clearly fresh-pod forms are mapped. Generic chilli,
pinches of chilli, dried/powdered forms and ambiguous translated red-chilli
entries remain unknown. Deseeding or slicing alone does not prove freshness;
Japanese red-chilli entries that can also mean dried pods are deliberately
excluded. Fresh jalapeño forms share the fresh-chilli profile; pickled forms do
not.

Romaine and Little Gem use BZfE's German outdoor availability from mid-May to
the end of November, encoded as approximate May–November months. BZfE explicitly
identifies Little Gem as a romaine variety. This dedicated profile does not
replace the existing general lettuce calendar or apply to cooked/mixed salads.

Fresh ginger uses Biohof Stövesandt's October–December harvest in the
Lüneburger Heide (`DE-NI`, `regional_seasonal_availability`). This is one
regional producer's young-ginger season, not a nationwide outdoor or import
calendar. Reviewed root, fresh, peeled, sliced and chopped forms are included;
paste, pickled, dried, ground and candied forms stay separate. Unqualified
grated/minced entries that may refer to prepared ginger remain unknown.
The producer's storage advice for a fresh root does not create an opening clock.

Figs use approximate August–October outdoor harvest highlights from LWG's
Veithshöchheim trials (`DE-BY`). The source distinguishes once-bearing varieties
from September and twice-bearing varieties from early August and October.
The month list combines those reported harvests, rather than promising one
continuous crop or specifying the season's final day. Ripening depends on
variety and autumn weather. Dried figs, preserves and imports do not extend it.

Summer purslane uses BZfE's May–September availability (`DE`,
`regional_seasonal_availability`). The existing `Purslane` row, whose Turkish
source is Semizotu, refers to this species (Portulaca oleracea); it does not
borrow a lettuce calendar. `Summer purslane` is also prepared as an exact name
for future catalog rows. Winter purslane/Postelein is a different species and
does not receive these months. Preserved, cooked and mixed forms remain unknown.
The source's short storage advice does not create an after-opening clock.

Sixteen additional exact names carrying quantity fragments or leading gram
markers now retain their reviewed produce/herb profile. These are individual
allowlist additions; there is no general suffix stripping or quantity parser.
Mixtures and unreviewed variants remain unknown.

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
profile. Preserved artichokes and cooked snow peas do not receive fresh seasons.

LWG's Bavarian horticultural guidance supplies late September–October chestnut
harvest and an October sweet-potato harvest highlight (`DE-BY`, `outdoor_harvest`).
Both are approximate and weather-dependent; the sweet-potato source describes
harvesting around the first surface frost, before the tubers freeze. These are
not complete market calendars and do not extend to imported or stored produce.
Yams, chestnut flour, sweetened chestnuts and explicitly cooked forms stay separate.

Swede/rutabaga uses BZfE's September–November domestic harvest followed by storage
until about April (`DE`, `seasonal_calendar_including_stored_produce`). It does
not inherit the turnip calendar. Chanterelles use BZfE's July–August collection
peak (`outdoor_harvest`). Applying that stated Central European peak to Germany
is a geographic inference, recorded under `DE`; it is not a complete collection
season or mushroom-identification advice. The article's unusually early Balkan
imports in 2026 do not extend the recurring highlight months. Preserved mushrooms
and mixed-species entries do not receive this profile.

Fresh mint uses Landservice's May–October harvest guidance (`DE-NW`). LWG's
garden-herb guide supplies June–September for tarragon and May–October for
lovage (`DE-BY`). All three use `outdoor_harvest`; year-round retail or potted
availability does not extend those months. Exact fresh leaf, washed and chopped
forms are included. Dried/frozen herbs, extracts and herb mixtures stay separate.

Oyster mushrooms, king oyster mushrooms and shiitake use BZfE's year-round
German cultivated availability (`DE`, `regional_seasonal_availability`). This
is shopping guidance for cultivated produce, not a wild collection calendar.
Exact fresh sliced/chopped/washed forms are included; explicitly wild, dried,
rehydrated, frozen, pickled, mixed-species and unspecified mushrooms are excluded.
The source's storage durations after purchase or cooking do not create an
after-opening clock.

Fresh coriander leaves and stems use EDEKA meinLand's explicit May–October
outdoor calendar for its NRW regional supply (`DE-NW`, `outdoor_harvest`). This
is a regional shopping hint, not a national calendar or a seed-harvest period.
Only exact fresh, chopped, washed, sliced, leaf/stem and sprig forms are mapped.
Unqualified "Coriander", seed/powder, dried/frozen forms, other species and herb
mixtures remain unknown because the ingredient name does not establish that form.
Lemon balm uses LWG's June–September garden harvest (`DE-BY`, `outdoor_harvest`).
It does not extend to tea, dried herbs or frozen products.

Watercress uses Kressepark Erfurt's traditional cultivated harvest peak from
mid-September through the end of May (`DE-TH`, `outdoor_harvest`). The source
also describes availability outside that peak; omitted summer months remain
unknown rather than unavailable. This is a cultivated-crop highlight, not a wild
foraging calendar, identification aid or statement that washed greens are safe.
Garden cress, mixed watercress/arugula, soups and preserved forms stay separate.
Romanesco uses IVA's late-May–October availability for German-grown produce
(`DE`, `regional_seasonal_availability`). Its exact raw heads and florets do not
inherit an ordinary broccoli calendar. Both partially covered months remain
approximate; the sources' post-purchase storage advice creates no opening clock.

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
Alpro's published maximum is 7 °C; Dodoni halloumi uses its published 6 °C maximum.
The corresponding refrigeration sources are
included with each rule.

Oat drinks retain separate Alpro (5 days) and Oatly (5–7 days) rules. The Oatly
rule also requires confirmation that the package was promptly reclosed and its
opening was not touched or drunk from. Reishunger smoked tofu requires a closed
container (2 days); its coconut milk uses the published 2–3 day range. These
manufacturer rules are not applied to other brands, dairy products, other tofu
forms or coconut cream. The coconut milk source also states a 3-day maximum in
its product storage instructions, consistent with the range's upper end.

Bonduelle publishes a family-wide instruction for opened canned vegetables:
use within 24 hours, refrigerated after transfer to a clean, closable container.
The catalog represents this as one day, with a conservative 4 °C limit and
explicit `transferred_to_clean_container` plus `closed_container` confirmations.
The helper returns dates, not an hour-precise timer. This brand rule applies to
reviewed canned peas/carrots/beans, chickpeas, kidney beans, white beans, lentils
and sweetcorn; it does not require a barcode. Fresh/frozen vegetables, dry or
home-cooked legumes, fruit, seafood, creamed corn and ready meals cannot select
it. Missing handling evidence cannot fall back to the generic three-to-four-day
can window. Other brands retain existing guidance and package-label overrides.

Galbani's [cheese FAQ](https://www.galbani.de/kasewissen) gives two days for
mozzarella, three for mascarpone and ricotta, and five for Gorgonzola after
opening. Each rule requires the Galbani brand and refrigerator storage. The
catalog uses a conservative 4 °C cap with BfR cooling evidence; this is narrower
than Galbani's stated cheese-storage temperatures. These are family instructions,
so no barcode is required. Reviewed plain, sliced, grated and drained forms are
included, while ricotta salata, dessert creams, cooked dishes, cheese mixtures,
generic blue cheese and other brands cannot select them.

Dodoni's [FAQ](https://uk.dodoni.com/contact-us/) distinguishes vacuum-packed
feta (four days) from feta packed in brine (eight days). Both require the Dodoni
brand, refrigeration at the conservative BfR-backed 4 °C cap, and explicit package
form confirmation. `vacuum_packed_feta` means the product was supplied in a vacuum
pack; `feta_in_original_brine` means it was supplied in brine and remains in that
original brine. Residual moisture in a vacuum pack, added water, homemade brine,
oil marinade or an unspecified container do not confirm the brine-packed form.
If both forms are confirmed, the shorter rule wins. Missing package information
leaves the opening window label-required. Dodoni halloumi has a separate three-day
rule requiring an `airtight_container` and the manufacturer's explicit 0–6 °C
refrigeration range. Cooked/grilled halloumi, salad cheese and vegan alternatives
are excluded. Package instructions and earlier printed dates still take precedence.

Alnatura millet flakes are an explicit exception to ordinary dry-staple storage:
the reviewed 500 g package says to refrigerate, close well and use within 14 days
after opening. The rule requires Alnatura, its verified GTIN, `closed_container`
and the conservative 4 °C cap. Whole millet, flour, porridge and mixed flakes do
not inherit it. This is a manufacturer's product window, not a generic claim
that dry grains spoil after two weeks.

Kikkoman's [storage guidance](https://www.kikkoman.de/ueber-kikkoman/anwendungstipps/haltbarkeit-lagerung)
recommends refrigeration and replacing the cap after opening naturally brewed soy
sauce, but describes the duration only as several months. The reviewed plain/brewed
soy-sauce names therefore remain label-required; no month-to-day conversion is
invented. Light/dark/sweet/soup variants, mixed sauces and ambiguous quantity
fragments remain outside this profile. An explicit saved package window still works.

The Alnatura rules require both the brand and one of the following verified
product barcodes, refrigerator storage at no more than 4 °C, and any listed
handling condition. Each rule links to its own manufacturer product page.

| Product | Barcode | Days after opening | Additional condition |
| --- | --- | --- | --- |
| Hirseflocken, 500 g | 4104420013308 | 14 | Closed container |
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
| Tofu Natur (ungekühlt), 200 g | 4104420094840 | 2 | — |
| Räuchertofu (ungekühlt), 200 g | 4104420094864 | 2 | — |
| Rote-Traube-Direktsaft naturtrüb, 1 l | 4104420262676 | 3 | — |
| Salsa-Dip, 245 ml | 42398479 | 3 | — |
| Curry indische Art, 325 ml | 4104420213128 | 2–3 | — |
| Kokoscurry thailändische Art, 325 ml | 4104420212794 | 2–3 | — |
| Soja-Cuisine, 200 ml | 4104420095205 | 4 | — |
| Hafer-Cuisine, 200 ml | 4104420241176 | 4 | — |
| Kokos-Cuisine, 200 ml | 4104420240940 | 4 | — |
| Origin Grüne Oliven ohne Stein, 350 g jar | 4104420211827 | 14 | — |
| Origin Grüne Oliven mit Stein, 310 g jar | 4104420129849 | 5 | — |
| Origin Kalamata-Oliven ohne Stein, 350 g jar | 4104420132085 | 14 | — |
| Origin Oliven-Mix mit Kräutern, 180 g | 42400660 | 14 | — |
| Oliven-Mix mit Kräutern, 125 g fresh antipasti | 40045542 | 2 | — |
| Gewürzgurken, 670 g | 4104420257603 | 5 | — |
| Gewürzgurken ohne Zuckerzusatz, 670 g | 4104420228795 | 5 | — |
| Cornichons, 330 g | 4104420257641 | 5 | — |
| Cornichons ohne Zuckerzusatz, 330 g | 4104420228832 | 5 | — |
| Kapern, 150 g | 42298601 | 5 | — |
| Artischockenherzen mit Kräutern, 125 g fresh antipasti | 40045559 | 2 | — |
| Ananas, 350 g jar | 4104420033900 | 3 | — |
| Origin Sugo Toscano, 325 ml | 4104420129603 | 5 | — |
| Kokosmilch, 400 ml | 4104420034327 | 3 | — |
| Kokosmilch, 200 ml | 4104420033641 | 3 | — |
| Sauerkraut, 520 g pouch | 4104420033849 | 5 | — |
| Tomate-Direktsaft, 500 ml | 4104420072787 | 3 | — |
| Erdnuss-Sauce, 325 ml | 4104420257863 | 3 | — |
| Karotte-Direktsaft, 1 l | 4104420221970 | 3 | — |
| Karotten-Direktsaft feldfrisch verarbeitet, 330 ml | 4104420070189 | 5 | — |
| Karotten-Direktsaft milchsauer vergoren, 500 ml | 4104420072848 | 3 | — |
| Rote Bete-Direktsaft, 1 l | 4104420261136 | 3 | — |
| Rote Bete-Direktsaft milchsauer vergoren, 500 ml | 4104420259980 | 3 | — |
| Limette-Direktsaft, 200 ml | 4104420072121 | 14 | — |
| Rote Bete ungesüßt, 330 g jar | 4104420235397 | 5 | — |
| Sojadrink Natur, 1 l | 4104420266827 | 3 | — |
| Reisdrink Natur, 1 l | 4104420260337 | 4 | — |
| Haferdrink, Bioland, 1 l | 4104420186279 | 3 | — |
| Haferdrink, Naturland, 1 l | 4104420260139 | 3 | — |
| Haselnussdrink Natur, 1 l | 4104420237292 | 4 | — |
| Cashewdrink Natur, 1 l | 4104420234383 | 4 | — |
| Kokosdrink ungesüßt, 1 l | 4104420204225 | 3 | — |
| Origin Getrocknete Tomaten, 180 g jar | 42271017 | 5 | — |
| Getrocknete Tomaten mit Basilikum, 125 g fresh antipasti | 40045528 | 2 | — |

Plant-drink profiles distinguish soy, rice, oat, hazelnut, cashew, coconut and
almond. Only a generic plant-drink ingredient may select any of the seven
verified Alnatura drink packages; a named type cannot borrow another type's
barcode. Existing Alpro five-day and Oatly five-to-seven-day rules and handling
conditions remain intact. The current plain soy package has a three-day
instruction; an older or unreviewed barcode cannot inherit it. Coconut drink
is separate from coconut milk, cooking cream and coconut water. Flavoured,
sweetened, mixed and homemade drinks are not inferred. A room-temperature
recipe instruction does not waive the actual lot's refrigeration requirement.
The four exact cashew/coconut drink names prepare those profiles for future
catalog rows; they do not create picker ingredients by themselves.

Dried-tomato names select a numeric interval only when the verified package
identity establishes one of the two marinated products. The 180 g Origin jar
has five-day guidance, while the 125 g fresh antipasti has two-day guidance.
Only the Origin jar accepts the `Alnatura Origin` brand alias. The separate
dry Soft-Tomaten pouch, dry-packed tomatoes, paste, powder, oil alone and
mixtures cannot inherit those intervals. The common 4 °C gate is the catalog's
conservative refrigeration requirement, not an Alnatura temperature quote.

The new carrot-juice profile and expanded beetroot-juice profile retain each
package's own interval. A 330 ml bottle's five-day instruction cannot select
the three-day litre or fermented bottle, or vice versa. Generic carrot/beetroot
juice names still require the verified brand and barcode; freshly squeezed
juice, juice mixtures and beet kvass remain outside those profiles. The carrot
juice exact name is prepared in the sidecar for future catalog rows; it does
not create a new picker ingredient by itself.

Lime juice's 14-day package instruction does not transfer to whole limes,
freshly squeezed juice, juice-and-zest combinations or other citrus juices.
The preserved-beetroot profile requires the verified vinegar-pickled Alnatura
jar. Exact canned/preserved beetroot names may select it only with that package
identity; the profile contains no generic can interval. Cooked beetroot without
a preserved form, raw roots, mixed pickles and the liquid alone remain separate.
The new `Pickled beetroot` exact name is also available for future catalog rows.

The two coconut-milk packs add Alnatura's three-day instructions to the existing
profile while retaining Reishunger's two-to-three-day range and historical
profile ID. They do not apply to coconut drinks, cream, light milk or mixed
milk/cream alternatives. Alnatura Kokos-Cuisine still has its separate four-day
rule. A verified Alnatura milk barcode paired with the Reishunger brand cannot
fall back to Reishunger's rule.

Sauerkraut uses the verified blanched pouch, including the exact chopped-with-juice
ingredient. It does not assign a clock to raw fermented cabbage, cooked leftovers
or sauerkraut juice; the latter keeps its own three-day product instruction.
The new tomato-juice rule does not transfer to sauce, passata, vegetable-juice
blends or freshly squeezed juice. Satay sauce can select the manufacturer's
peanut sauce explicitly offered for saté skewers, but only with the matching
barcode and brand. Seasoning powder, peanut butter and homemade sauce do not
receive that package rule. All five additions require refrigeration at no more
than 4 °C; package instructions and an earlier printed date still take precedence.

Pickled cucumbers and gherkin cutting forms require one of the four verified
Alnatura cucumber products. Explicit sweet-and-sour forms use only the two
sweetened products. Neither profile includes pickle brine, other pickled
vegetables or fresh cucumbers. The caper rule is for the reviewed vinegar-brine
product, not salt-packed capers or caper berries. Marinated artichoke hearts use
the fresh antipasti package; fresh, frozen and canned-in-water forms stay separate.
All require the exact brand, verified GTIN and refrigeration at the conservative
4 °C cap. They do not infer a fresh growing season for preserved food.

The preserved-pineapple profile adds Alnatura's three-day package instruction
alongside the existing generic canned high-acid range. Known brand/barcode
conflicts cannot fall back to the longer generic range. It does not apply the
fruit package's clock to whole pineapple, juice or syrup. Sugo Toscano accepts
the two exact labels `Alnatura` and `Alnatura Origin`, always with its own GTIN;
the previously reviewed Klassik and Kräuter sauces retain their two-day windows.

Skyr has separate label-required evidence from Arla, which describes only a
qualitative short interval under refrigeration. No numeric day limit is inferred.
The reviewed spoonable plain/fruit/vanilla forms keep that uncertainty, while an
explicit package `useWithinDays` still works. Skyr drinks, plant-based alternatives,
quark and other dairy foods do not inherit this profile.

Soy cream and generic plant-based cooking cream have separate profiles from
yoghurt. Both preserve the existing Alpro 5-day rule and its 7 °C cap. The soy
cream profile adds only Soja-Cuisine; generic plant-based cream can select the
verified soy, oat or coconut Cuisine product. Those Alnatura rules require at
most 4 °C and do not apply to yoghurt, dairy cream, coconut cream, plant drinks
or ambiguous dairy/oat alternatives. A known Alnatura barcode paired with a
conflicting Alpro brand cannot fall back to Alpro's longer interval.

The four Origin olive products accept either exact brand label `Alnatura` or
`Alnatura Origin`, always with their own verified barcode. Separate rules encode
these two labels; no substring brand matching is used. The fresh 125 g antipasti
pack is an Alnatura product and receives no Origin alias. The jars' total weights
are shown above; their drained weights differ.

Olive preparation does not select a duration: pitting or chopping a green olive
still requires its original product barcode to choose 5 or 14 days. The two
mixed-olive packages likewise retain their separate 2- and 14-day rules.
Colour-specific profiles cannot borrow a different colour or mix's barcode;
unspecified olives can select any of the five reviewed products. Olive oil,
spreads, Taggiasca olives, stuffed olives and ambiguous alternatives remain
outside these profiles. These preserved products receive no fresh season.

The two Alnatura tofu products add their own 2-day rules to the existing plain
and smoked tofu profiles. Taifun's water-changing conditions and Reishunger's
closed-container condition still apply to their respective rules. The historical
profile IDs remain stable; each rule carries its own manufacturer and product
scope. Alnatura's unopened ambient-storage description does not permit pantry
storage after opening. Natural and smoked tofu barcodes cannot select each
other's rule, and silken tofu stays separate.

The curry rules retain the published 2–3 day range: opening + 2 days is the
reminder and opening + 3 days is the upper advisory date. A matching curry sauce
does not give the same interval to curry paste, powder or coconut milk. Likewise,
salsa does not inherit the passata or generic canned-tomato interval.

The reviewed Alnatura tomato-paste and ketchup pages specify refrigeration after
opening but no number of days. Those packages continue to return `label_required`
without a numeric deadline. Batch 15's separate dmBio tomato-paste rule requires
its own verified package; the Alnatura barcode cannot select it. Jar-labelled
tomato paste retains the label-required profile rather than borrowing a tube's
rule. Ambiguous tomato purée and condiment alternatives remain unassigned.
A known package `useWithinDays` still takes precedence.

Batch 15's dmBio rules retain the brand owner's package-specific instructions:

| Product | Verified GTIN | Days after opening |
| --- | --- | --- |
| Jackfruit Natur in Salzlake, 240 g drained | `4066447443318` | 3 |
| Hummus natur, 180 g | `4066447910865` | 3 |
| Tomatenmark, 200 g tube | `4066447887716` | 21 (the label's exact 3 weeks) |
| Tomatensauce Klassik, 350 ml | `4066447887747` | 1–2 |
| Tomatensauce Klassik, 520 ml | `4066447972153` | 3–4 |

All five require exact `dmBio` brand and GTIN, refrigerator storage and at most
4 °C under the existing BfR cooling guidance. The two sauce sizes deliberately
keep different windows even though their names and ingredient lists are similar.
The shorter end sets the reminder; the longer end sets the advisory deadline,
capped by an earlier printed date. Brand-only entries, another food's barcode,
fresh jackfruit, sweet jackfruit in syrup, beetroot hummus, passata and ketchup
cannot select these rules. Existing Alnatura hummus and sauce intervals remain
unchanged. Product entry and cooking review still require the user's opening
confirmation and expiry opt-in; adding guidance does not start a package clock.

Prepared mustard and mayonnaise now have their own label-required profiles.
Alnatura's mustard, egg mayonnaise and vegan mayo pages require refrigeration
but supply no number of days; Löwensenf likewise gives storage guidance without
a fixed opening interval. These sources therefore create no numeric clock,
including when one of those brands or barcodes is known. Seed/powder forms,
condiment alternatives, homemade mayonnaise and mixed dishes stay separate.

An earlier batch added 52 exact cream, cream-cheese and yoghurt variants with
formulation-dependent label guidance. Fat percentages, serving measures and
recipe section markers do not establish a universal opening interval. Three
additional milk names retain the existing requirement to confirm pasteurization
or UHT treatment and refrigeration; a room-temperature preparation instruction
does not waive cold storage. No generic marker stripping or mixture matching
is introduced.

Batch 14 gives eight reviewed plain cream-cheese names a separate profile.
Philadelphia Original cream cheese (four 8 oz blocks, GTIN `00021000075997`)
and Original cream cheese spread (8 oz tub, GTIN `00021000000142`) each have
a manufacturer-published 10-day window after opening. Each individual opened
package has its own clock. Both rules require exact Philadelphia brand and
GTIN, prompt resealing, and refrigeration at no more than 4 °C (conservatively
below the US FAQ's 40 °F). An earlier printed date still wins. A preparation
instruction to soften cream cheese does not waive these storage conditions.

These are US package rules; the brand alone, another market's package,
herbed/plant-based cheese, Lučina, cottage cheese, frosting and desserts cannot
select them. In particular, [Philadelphia's German FAQ](https://www.philadelphia-professional.de/unternehmen/faq/) has different guidance,
so no global Philadelphia interval is inferred. Fifteen additional cottage-cheese,
crème fraîche and cream-cheese alternative names receive label-required guidance
without an invented duration. A manually entered package interval still works.

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
canned-food interval. Where no product scope is selected, matching brand-family
rules take precedence over generic guidance, even when their handling evidence
is missing. A conflicting reviewed barcode cannot be bypassed by a brand-only
rule. This precedence is independent of rule ordering or interval length.
Generic canned-food guidance remains available for other
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
