# Batch 37: bulk family review

Batch 37 changes the review workflow from target-by-target free-form selection to
explicit reusable family rules. A rule is deliberately **not** an automatic
binding: every approved destination still has its own committed review row and
full target ID. The rules only make the semantic decision reusable and testable.

The batch approves 106 targets from the 1,697-target post-Batch-36 queue:

- **Tier A: 64** direct food/state families or non-compositional presentation
  variants (cutting, serving wording, singular/plural, etc.).
- **Tier B: 42** explicitly reviewed generic category fallbacks where the retained
  snapshot has no sufficiently specific subtype record. Tier B is suitable only
  for generic per-100-g estimation and does not certify subtype, species, brand,
  salt/fat formulation, curing details, manufacturer or laboratory composition.
- **Tier C** is never auto-approved. Mixtures, stocks, sauces, concentrations,
  soaking/draining questions, brands and other context-heavy foods remain unresolved.

The 106 reviewed targets cover 1,683 recorded recipe usages. They reduce the
never-recorded queue from 1,697 to **1,591**. The 12 historical holds stay
separate, so unresolved-or-held becomes **1,603**.

`tools/release_catalog_nutrition_bulk_family_rules.v1.json` contains fully
anchored exact regexes and one retained FDC reference per reviewed family.
`tools/classify_nutrition_review_queue_v60.py` applies those rules only for
work ordering. A matching rule with no explicit review row remains unresolved;
the classifier itself approves zero bindings. Multiple rule matches fail closed.

This is the speed-up mechanism for subsequent batches: review a family once,
then commit every exact destination ID that satisfies the rule, instead of
repeating identical semantic reasoning target by target. New patterns cannot be
expanded automatically; changing or adding a regex requires a reviewed commit
and regression coverage.

No provider/FDC crawl, nutrient population, density/piece-weight/yield inference,
historical rewrite, hold removal, release, catalog activation, deployment,
Home Assistant restart or live-cache mutation is part of this batch.
