# Nutrition Batch 42: 9 explicit continuation reviews

Base: Batch 41 / PR #133 (`821df54ca14ee0928e03e28141bd688d3cb4f490`).

Batch 42 adds **9 destination-specific nutrition bindings covering 16 recorded ingredient usages**. It deliberately stays small: the post-Batch-41 manual lane still contains many labels whose identity, formulation or measurement state is not established, so this batch only accepts presentation/spelling variants with a defensible retained reference and established review precedent.

## Reviewed continuation

- plain cooking chocolate uses the same retained unsweetened baking-chocolate reference already reviewed for generic cooking-chocolate variants; exact cocoa/sugar formulation remains uncertified;
- two salted-pork piece-size labels use exact retained raw salt pork; piece size does not trigger a mass/yield conversion;
- one seitan-steak presentation uses the established generic vegetarian-fillet fallback, without claiming an exact formulation;
- chikuwa, kamaboko and hanpen cutting variants use the retained generic fish-cake/patty record already used for those named Japanese fish-cake families;
- a crustless sandwich-bread slice uses the established commercial white sandwich-bread reference;
- a halved skate wing uses the established `Fish, NFS` named-fish fallback, with species-specific composition explicitly uncertified.

No generic pepper/rice/curry/crème-fraîche/starch/herb identity, fresh-to-dried herb substitution, species-changing meat substitution, tuna packing-medium assumption, salt-cod species assumption, or historical potato-skin precedent is copied into this batch.

## Exact effect

- recorded review targets: **5,071 → 5,080**
- review files: **260 → 261**
- unresolved targets: **1,248 → 1,239**
- manual-family lane: **339 → 330**
- context-heavy lane: **909 → 909**
- rule-covered-but-unreviewed: **0 → 0**
- recorded usages covered by this batch: **16**
- bindings approved automatically by the classifier: **0**

Frozen evidence remains SHA-256 `e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac` and reference manifest `e135d4235a897688e37f8561602820bb84d186e91c09d9f654f52bf0d8fab29d`. Source target/rank values are locator receipts only. Candidate rank is never identity proof, provider identity is never inferred, and no nutrient values, density, piece weight, cooking/draining yield or concentration conversion is introduced.

The compact JSON regression fixture pins all nine exact pre-Batch-42 manual target projections plus the six exact source candidate records needed for receipt validation. The full frozen evidence was used locally to reproduce the **339 manual / 909 context** baseline and **330 manual / 909 context** post-state; CI independently proves that every selected row belongs to the manual lane and reconciles those pinned counts without committing the 15 MB evidence file.
