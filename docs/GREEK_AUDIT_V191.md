# Greek catalog audit v191 — pass 44

Add the approved 33-label Greek presentation overlay after v188. The overlay improves pistachio specificity, unsweetened wording, plant-drink terminology, corn-on-the-cob descriptions and recipe-role wording. All original search aliases are retained by the existing additive locale loader.

This change does not edit ingredient identities, source recipes, quantities, nutrition, pricing categories, countries or currencies. The v189/v190 pricing bundles are separate and are not included in this Greek-only PR.

## Regression coverage

`python tests/test_greek_catalog_audit_v191.py` checks 22 contracts against the actual production presentation functions and repository locale files: all reviewed labels, normalized key reachability, schema/duplicate protection, qualifier preservation, legacy aliases, unaffected languages, unaffected Greek labels and no ingredient mutation.

The `Greek audit regressions` workflow runs these new overlay tests, in addition to the existing repository `Validate` workflow. Development reproduction used sampled source/data; CI uses the checked-out repository files. Neither is a live Home Assistant or browser test.

## Delivery

Backend data change only. The active frontend build is unchanged. Loading changed server-side labels requires reloading/restarting the integration after installing the merged source. No live deployment is performed by this PR.
