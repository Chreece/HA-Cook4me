# Offline ingredient seasons and after-opening guidance

The release catalog now includes a versioned, reviewed lifecycle sidecar:
`custom_components/cook4me/catalog/ingredient_lifecycle.v1.json`.
It is read once during the existing catalog executor warmup. No network, AI,
cloud credentials, or per-scan file reads are needed.

## Reviewed coverage (2026-09-25.9)

- 111 produce groups, including fruit, leafy vegetables, roots, asparagus,
  tomatoes, cultivated button mushrooms, potatoes, new potatoes, fresh herbs,
  savoy cabbage, pak choi, shallots, wild garlic, turnips, snow peas, walnuts,
  hazelnuts, artichokes, melons, kiwi, chestnuts, sweet potatoes, swede and
  chanterelles, mint, tarragon, lovage, oyster/king oyster mushrooms, shiitake,
  fresh coriander leaves, watercress, lemon balm, Romanesco, fresh chillies
  and romaine/Little Gem lettuce, fresh ginger, figs and summer purslane,
  plus Greek regional lemon, orange, grapefruit, mandarin and clementine calendars.
  Nine further produce groups now have Greek evidence, including pomegranate.
- 71 numeric after-opening rule groups: pasteurized/UHT milk, low-acid canned
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
  There are 78 reviewed product barcodes and 1,718 exact canonical names.
- Explicit label-required guidance for reviewed foods with variable product
  formulations, including unverified pesto, dairy yoghurt, unverified cream cheese and
  coconut cream, unverified tomato paste, ketchup and Skyr, plus mustard, mayonnaise and
  additional cream, cream-cheese and yoghurt variants, plus plain/brewed soy sauce,
  cottage cheese and further crème fraîche variants.
- Dry staples have no invented short spoilage countdown. Their package
  instructions still apply; missing data never means indefinitely safe.

Run `python tools/audit_ingredient_lifecycle.py` for counts against the actual
shipped catalog. Counts distinguish seasonal, numeric and label-required
entries. Coverage is explicitly incomplete; unmapped ingredients remain unknown.

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
