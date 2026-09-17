# Cook4Me v107: dietary guidance without a delivery gate

Build `2026.9.17.11` is cumulative from v106, including original-language delivery with appliance-load verification.

## Requested behavior

Vegetarian and other dietary selections continue to filter discovery. Once an official recipe is selected, dietary, allergy, avoid-list and ingredient-exclusion conflicts no longer prevent sending it. This applies to dashboard sends, direct services, queued sends and original-language attempts. The backend still resolves the official recipe and recomputes guidance from current profile rules, so submitted ingredients or fabricated `match.safe` values do not replace official data. Invalid selections and deleted member profiles still return selection errors.

The panel enables Send independently of dietary eligibility. Cooking mode lists incompatible ingredient names struck through, with localized suggested replacements beside them. The ingredient list shows the same changes while keeping quantity and price text intact. Incomplete suggestions are also visible: a concrete conflicting ingredient with no known substitute says “Choose a suitable replacement”. A recipe-level warning does not arbitrarily mark unrelated ingredient rows. Older saved recipes with a `substitutions` list retain their suggestions, and new today-plan records preserve per-ingredient guidance.

The device receives the original official IDs and cooking program. Suggestions are instructions for the person cooking; no cloud recipe, appliance program, cooking time or nutrition value is rewritten. Device connection checks, active-cooking protection, identity checks, queue concurrency and cross-language load verification remain in place.

## Validation

- 71 focused Python tests passed across dietary guidance/delivery, member profiles, cross-language delivery, substitution filtering, runtime lifecycle and queue races.
- Four installer tests passed, including rollback scenarios and preservation of existing profile storage.
- Chromium passed real Send clicks for four foreign catalog editions, preferred device-language mapping, unconfirmed-load errors, dietary mismatches, stale selections and exact original IDs/ingredients/portions.
- Chromium passed the real cooking-mode toggle and step navigation, strikethrough only on incompatible names, Greek/German/English replacements and unresolved labels, original recipe preservation, and 390/1360-pixel layouts. Greek cooking guidance screenshots were visually reviewed.
- Bundle reproduction, JavaScript syntax, Python compilation and whitespace checks passed.

A broader legacy announcement test (`test_slow_state_announcement_is_skipped_after_disconnect_or_recipe_change`) fails both on the untouched v106 baseline and v107, with two failing subcases. It assumes an AI generation path that is separate from this dietary change; announcement code is unchanged in v107. The five delivery/queue tests in that suite pass. No claim is made that the entire historical test collection is green.

Cloud and appliance transport are simulated in these tests. Loading on the user's physical device still needs a live attempt after installation.

Use the pinned v107 installer. It includes dietary-guidance and cross-language tests in preflight, retains the deployment backup and rollback, and checks that Home Assistant serves the exact installed v107 bundle.
