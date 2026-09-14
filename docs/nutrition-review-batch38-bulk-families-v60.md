# Batch 38: second bulk nutrition-family pass

Base: Batch 37 / PR #129, merged at `c9b60bf83bebf588e6dac645eb9c0d460e980ee9`.

This pass adds **111 explicit target-to-FDC reference bindings** covering **2,571 recipe ingredient usages**. It does not auto-expand family rules: the classifier still approves zero rows by itself.

The selected set intentionally excludes generic rice, generic pepper, potato starch, crème fraîche, garam masala, mixed herbs and the two high-usage `Curry` targets. In particular, `Curry` target-local candidate evidence points to curry sauces while the retained curry-powder record is located elsewhere; without recipe/provider context that is not a safe bulk identity decision.

Batch 38 focuses on bacon, culinary mint, gelatin, apple compote, coconut forms, soy flour, sweetcorn, nori, rice vermicelli, tofu, chicken cuts, chili flakes, generic ground meat, stewing beef, beef shin, turkey breast, shimeji, panko, baking soda, rapeseed/canola oil, semi-skimmed milk, mustard seed, plain dry pasta shapes, Pecorino/Romano and Grana/Parmesan category fallbacks, shortcrust/pie crust, sandwich bread/soft crumbs, Romanesco/cauliflower and generic vinegar fallback for white-wine vinegar.

All Tier B rows explicitly state where the retained FDC record is a generic category reference rather than an exact species, brand, formulation, cultivar, fat/moisture, aging, cure or manufacturer certificate. No density, piece weight, edible yield, soaking, draining, cooking conversion or provider-identity inference is introduced.

The 12 existing holds / 22 exact held ingredient identities remain unchanged. The 11 historical provenance discrepancies remain inside that hold set. The retained candidate snapshot remains `e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac` and the reference manifest remains `e135d4235a897688e37f8561602820bb84d186e91c09d9f654f52bf0d8fab29d`.

The reusable family architecture is extended with a separate Batch 38 registry rather than mutating the byte-pinned Batch 37 registry. The classifier now merges all versioned registries, rejects duplicate/overlapping rule matches, and validates every explicit bulk-family review row. A matching rule without a destination review row is still unresolved.

After this batch the recorded target count is **4,839**, the never-reviewed queue is **1,480**, and unresolved-or-held is **1,492**. No provider/FDC network crawl, nutrient population, catalog activation, release, deployment, Home Assistant restart or live-cache mutation is included.
