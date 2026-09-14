# Nutrition review Batch 42 — Guinea fowl (v60)

Batch 42 adds one destination-specific explicit nutrition review from the exact frozen v60 candidate evidence. It does not expand any bulk-family rule and does not infer identity from candidate rank.

## Frozen evidence

- source evidence SHA-256: `e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac`
- reference manifest SHA-256: `e135d4235a897688e37f8561602820bb84d186e91c09d9f654f52bf0d8fab29d`
- target: `M_FOOD_379` / `Guinea fowl`
- usage count at review: **2**

The target's retained candidates are:

1. FDC `174471` — `Guinea hen, meat only, raw`
2. FDC `172416` — `Guinea hen, meat and skin, raw` — scientific name `Numida meleagris`

## Reviewed decision

Batch 42 selects **FDC 172416**, `Guinea hen, meat and skin, raw`, at retained candidate rank 2.

Rank is only a locator. The semantic decision is based on the target being an unqualified whole-bird identity. The repository already uses the same convention for unqualified `Quail`, which is reviewed to `Quail, meat and skin, raw`; narrower meat-only records are used when the target itself narrows the edible part. The selected retained Guinea fowl candidate additionally identifies the species `Numida meleagris`.

## Effect

- recorded review targets: **5,071 → 5,072**
- unresolved review targets: **1,248 → 1,247**
- Batch-41 manual-family lane: **339 → 338**
- context-heavy lane: **909 → 909**
- new explicit bindings: **1**
- bulk-family rules changed: **0**
- held targets changed: **0**
- food-provider network requests: **0**

The retained Batch 42 fixture contains the exact target row and both candidates needed to audit this decision without checking the multi-megabyte evidence snapshot into Git.
