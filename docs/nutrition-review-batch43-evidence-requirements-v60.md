# Nutrition review Batch 43 — honor explicit evidence requirements (v60)

Batch 43 creates **no nutrition bindings**. It connects the unresolved-queue classifier to the already validated Batch 35 evidence-requirement ledger so targets with an explicit `deferred-no-binding` requirement cannot be presented as ordinary manual-family candidates.

## Why this is needed

Batch 35 recorded 28 exact target identities whose retained candidate evidence was not sufficient for approval. Each ledger row pins the original evidence bytes, usage count, identity, a reason code and the additional evidence required. Later review batches legitimately resolved 9 of those targets (for example mint, mascarpone, gelatin and grated coconut), leaving **19 active evidence requirements** after Batch 42.

Before Batch 43, the generic name-shape classifier independently placed 10 of those 19 in the context-heavy lane, but **9 still appeared in the manual-family lane** despite their stronger target-specific evidence requirement:

- `Pepper`;
- semantic and provider `Rice`;
- semantic/provider `Crème fraîche` plus `Thick crème fraîche`;
- semantic/provider `Potato starch`;
- `Chopped fresh tarragon`.

Those nine rows represent **6,902 recorded ingredient usages**. Their existing requirement ledger is stronger evidence than a generic lexical classifier, so Batch 43 makes the target-specific ledger authoritative for triage while leaving every target unresolved.

## Exact effect

Using the frozen candidate evidence SHA-256 `e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac` and the merged Batch 42 state:

- recorded review targets: **5,080 → 5,080**;
- unresolved targets: **1,239 → 1,239**;
- active explicit evidence requirements: **19**;
- manual-family lane: **330 → 321**;
- context-heavy lane: **909 → 918**;
- rule-covered-but-unreviewed: **0 → 0**;
- bindings approved by the classifier: **0**;
- provider/FDC network requests: **0**.

## Fail-closed behavior

`classify_nutrition_review_queue_v60.py` now loads the existing `release_catalog_nutrition_review_blockers.v1.json` ledger and validates it against the **same exact retained evidence snapshot** before using it. Ledger catalog/reference-manifest drift, target identity drift, source-row byte drift, usage drift, unsafe policy, invalid reason codes, selected FDC IDs or missing original targets still fail closed through the existing Batch 35 validator.

Only requirements whose exact target ID is still in the current unresolved queue affect classification. Requirements for targets recorded in later batches remain auditable history but do not re-open or alter those recorded decisions. Holds remain separate and unchanged.

The new classification `C-explicit-evidence-requirement` preserves the ledger `reasonCode` on the output row. It does **not** select a candidate, infer provider identity, release a hold, count a deferred row as complete, or authorize automatic family-rule expansion.

## Regression contract

Batch 43 reuses the byte-pinned Batch 35 retained projection plus the Batch 42 continuation fixture; no new large evidence file is committed. Tests prove:

- all 28 original ledger entries still validate against their exact retained rows;
- exactly 9 ledger targets were recorded later and exactly 19 remain active;
- without the ledger, exactly 9 active rows would be manual and 10 would already be context-heavy;
- with the ledger, all 19 active rows are context-heavy;
- the post-state reconciles to **321 manual + 918 context = 1,239 unresolved** with zero new bindings.
