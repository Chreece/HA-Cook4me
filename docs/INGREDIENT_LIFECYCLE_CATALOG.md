# Offline ingredient seasons and after-opening guidance

The release catalog now includes a versioned, reviewed lifecycle sidecar:
`custom_components/cook4me/catalog/ingredient_lifecycle.v1.json`.
It is read once during the existing catalog executor warmup. No network, AI,
cloud credentials, or per-scan file reads are needed.

## Initial coverage

- 62 produce groups, including fruit, leafy vegetables, roots, asparagus,
  tomatoes and cultivated button mushrooms.
- Six numeric after-opening groups: pasteurized/UHT milk, low-acid canned
  foods, high-acid canned foods, Alpro plant drinks, Taifun plain tofu and
  Taifun silken tofu. Brand and handling conditions remain attached.
- Explicit label-required guidance for reviewed foods with variable product
  formulations, including pesto, yoghurt, cream cheese and coconut milk.
- Dry staples have no invented short spoilage countdown. Their package
  instructions still apply; missing data never means indefinitely safe.

Run `python tools/audit_ingredient_lifecycle.py` for counts against the actual
shipped catalog. Counts distinguish seasonal, numeric and label-required
entries. Coverage is explicitly incomplete; unmapped ingredients remain unknown.

## Season semantics

Season months are German regional availability guidance from the twelve monthly
calendars published by the Hessische Lehrkräfteakademie. The source region
(`DE-HE`), country (`DE`), source links and review date are preserved. The source
includes stored produce and protected cultivation; these months must not be
labelled as exclusively fresh outdoor harvest.

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
handling conditions, source IDs and, where required, brand. Numeric evidence is
general or manufacturer guidance, never a guaranteed spoilage/safety threshold.
The conservative refrigerator cap for general and tofu guidance is 4 °C;
Alpro's published maximum is 7 °C. The corresponding refrigeration sources are
included with each rule.

The date helper accepts existing lot fields `openedAt`, `bestBefore`,
`useWithinDays`, `noExpiry`, `storage` and `brand`:

1. No opening date means no countdown.
2. A package-specific `useWithinDays` wins over generic catalog guidance.
3. Otherwise the catalog rule must match the known brand, refrigerator storage,
   supplied temperature and confirmed handling/food-form conditions.
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
and month boundaries, unknown/preserved forms, package precedence, brand and
temperature gates, leap years, earlier printed dates, unopened packages, exact
identity, recipe/picker propagation, and copy isolation. The existing Validate
workflow runs it and audits the actual release catalog on Python 3.13.
