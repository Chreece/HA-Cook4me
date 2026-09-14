# Nutrition review Batch 41 — triage hardening (v60)

Batch 41 does not approve any nutrition binding. It tightens the unresolved-queue classifier so composition-heavy or formulation-dependent inputs are not presented as ordinary manual family candidates.

## Frozen evidence and baseline

- source evidence SHA-256: `e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac`
- reference manifest SHA-256: `e135d4235a897688e37f8561602820bb84d186e91c09d9f654f52bf0d8fab29d`
- post-Batch-40 recorded review targets: **5,071**
- unresolved review targets: **1,248**
- Batch-40 classifier split: **416 manual-family / 832 context-heavy**
- rule-covered-but-unreviewed: **0**

The retained Batch 41 regression fixture stores every one of the 77 rows moved by this change plus representative rows for seven canonical names that must remain manual (`reviewTargetId`, canonical name, candidate count and usage count). The 416/832 baseline and 339/909 result were independently reproduced against the exact frozen evidence snapshot before the compact fixture was generated. The fixture deliberately does not copy the multi-megabyte candidate evidence snapshot or approve any candidate.

## Why the classifier needed hardening

The previous `COMPLEX` expression recognized terms such as `mix`, `flavor`, `marinated`, `cooked`, `preserve`, `sauce` and `soup`, but missed common grammatical or product forms of the same composition/state problem. Examples that incorrectly remained in the manual lane included:

- `Mixed herbs`, `Mixed vegetables`, and `Oil, mixed with yogurt`;
- `Pistachio flavoring`, `Vanilla flavouring`, and flavoured water;
- marinades, slurry, purée, compote, coulis, mousse, vinaigrette and dressing;
- starters, dumplings and meatballs;
- `Precooked ramen`, rehydrated kombu, preserved lemon and fermented shrimp;
- candied/glazed foods, food coloring, consommé and herb bouquets;
- spreads, pudding, dough, ampersand combinations and `etc.` ingredient lists.

These labels require recipe/formulation, state, component-ratio or product-specific evidence. Search rank is not identity proof, so leaving them in the manual-family lane created pressure to over-interpret retained FDC candidates.

## Result

Against the exact frozen evidence and the merged Batch-40 review state, the hardened classifier moves **77** targets (aggregate usage count **675**) from manual-family review to context-heavy review:

- manual-family candidates: **416 → 339**
- context-heavy targets: **832 → 909**
- total unresolved targets: **1,248 → 1,248**
- explicit bindings created: **0**
- held targets changed: **0**
- network food-provider requests: **0**

The regression fixture pins all 77 rows that move so CI proves the exact reclassification set and also checks representative simple identity controls such as `Guinea fowl`, `Nigella seeds`, `Parsley root`, `Fresh sage leaves`, `Vanilla pod` and `Zucchini flowers` remain manual.

## Safety contract

Batch 41 changes triage only. Existing bulk-family rules remain approval rules only when a destination-specific reviewed row exists. Candidate rank remains a locator, never identity proof. Automatic rule expansion remains forbidden, and the 1,248 unresolved targets remain unresolved until later explicit evidence review.
